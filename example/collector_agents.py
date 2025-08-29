#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/08/29
# @File  : innovation_collector.py
# @Author: johnson (adapted by ChatGPT)
# @Desc  : 使用搜索引擎搜索一些不重复的创新点

from __future__ import annotations
import os
import re
import sys
import json
import time
import math
import uuid
import queue
from tqdm import tqdm
import sqlite3
import logging
import hashlib
import argparse
import datetime as dt
from typing import Annotated, List, Dict, Any, Tuple, Optional, Set, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
import numpy as np
import requests
import dotenv
from pydantic import BaseModel, Field
from pydantic import TypeAdapter
from cache_utils import cache_decorator
# LangChain / LangGraph
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.tools import tool,InjectedToolCallId
from langchain_core.messages import BaseMessage, ToolMessage
from langgraph.prebuilt import create_react_agent, InjectedState
from langgraph.types import Command
from zai import ZhipuAiClient   # pip install zai-sdk
dotenv.load_dotenv()

WebSearchClient = ZhipuAiClient(api_key=os.environ.get("ZHIPU_API_KEY"))


# ===================== Logging =====================
logger = logging.getLogger("innovation_collector")


def setup_logging() -> logging.Logger:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger("innovation_collector")
    logger.setLevel(level)
    logger.propagate = False
    logger.handlers.clear()

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    sh = logging.StreamHandler(stream=sys.stdout)
    sh.setLevel(level)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    noisy_level = logging.WARNING if level > logging.DEBUG else logging.DEBUG
    for noisy in ("httpx", "openai", "langchain", "asyncio"):
        logging.getLogger(noisy).setLevel(noisy_level)

    logger.debug("Logging initialized. Level=%s", level_name)
    return logger

setup_logging()

# ===================== Data Models =====================
class PaperMeta(BaseModel):
    id: str
    title: str
    url: str
    snippet: str
    year: int | None = None
    source: str = "arxiv"
    score: float = 0.0
    pdf_url: Optional[str] = None


class Evidence(BaseModel):
    quote: str = ""
    loc: str = ""  # 页码/段落/句号索引等

#创新点包含哪些字段
class Innovation(BaseModel):
    text: str
    canonical: str
    hash: str
    paper_id: str
    paper_title: str
    source_url: str
    evidence: Evidence = Field(default_factory=Evidence)
    confidence: float = 0.7
    novelty: float = 0.7
    created_at: str = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat())


class Candidate(BaseModel):
    text: str
    why_new: str | None = None
    how: str | None = None
    evidence_quote: str | None = None
    loc: str | None = None
    confidence: float | None = None
    novelty: float | None = None


class CandidateList(BaseModel):
    items: List[Candidate] = Field(description="候选创新点列表")


# ===================== DB Layer (SQLite) =====================
class DB:
    def __init__(self, path: str = "innovation.db"):
        self.path = path
        self._ensure()

    def _ensure(self):
        con = sqlite3.connect(self.path)
        cur = con.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS papers (
                id TEXT PRIMARY KEY,
                title TEXT,
                url TEXT,
                source TEXT,
                year INT,
                pdf_url TEXT,
                meta JSON
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS innovations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                paper_id TEXT,
                paper_title TEXT,
                source_url TEXT,
                text TEXT,
                canonical TEXT,
                hash TEXT UNIQUE,
                evidence JSON,
                confidence REAL,
                novelty REAL,
                created_at TEXT
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_innov_topic ON innovations(topic)")
        con.commit()
        con.close()

    def upsert_papers(self, papers: List[PaperMeta]):
        con = sqlite3.connect(self.path)
        cur = con.cursor()
        for p in papers:
            cur.execute(
                """
                INSERT OR REPLACE INTO papers(id, title, url, source, year, pdf_url, meta)
                VALUES(?,?,?,?,?,?,?)
                """,
                (p.id, p.title, p.url, p.source, p.year, p.pdf_url or "", json.dumps(p.model_dump())),
            )
        con.commit()
        con.close()

    def upsert_innovations(self, topic: str, items: List[Innovation]):
        con = sqlite3.connect(self.path)
        cur = con.cursor()
        for it in items:
            try:
                cur.execute(
                    """
                    INSERT INTO innovations(
                        topic, paper_id, paper_title, source_url, text, canonical, hash,
                        evidence, confidence, novelty, created_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        topic,
                        it.paper_id,
                        it.paper_title,
                        it.source_url,
                        it.text,
                        it.canonical,
                        it.hash,
                        json.dumps(it.evidence.model_dump()),
                        it.confidence,
                        it.novelty,
                        it.created_at,
                    ),
                )
            except sqlite3.IntegrityError:
                # hash UNIQUE: 忽略重复
                pass
        con.commit()
        con.close()

def hash_key(text: str) -> str:
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()

@cache_decorator
def arxiv_search(keyword: str, max_results: int = 20) -> List[PaperMeta]:
    logger.info("WebSearch | query=%r", keyword)
    try:
        response = WebSearchClient.web_search.web_search(
            search_engine="search_std",
            search_query=keyword,
            count=15,  # 返回结果的条数，范围1-50，默认10
            search_recency_filter="noLimit",  # 搜索指定日期范围内的内容
            content_size="high"  # 控制网页摘要的字数，默认medium
        )
        items = response.get("search_result", []) or []
        logger.debug("WebSearch | received %d results", len(items))
        results = [
            PaperMeta(
                id= uuid.uuid4().hex,
                url=item.get('url', ''),
                title=item.get('title', ''),
                snippet=item.get('content', '')
            ) for item in items
        ]
        logger.info("WebSearch | parsed %d results", len(results))
        return results
    except Exception as e:
        logger.exception("WebSearch | error during search: %s", e)
        return []

# ===================== LLMs =====================
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
# 用于生成计划和提取创新点的模型
llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0)
# 用于计算创新点之间的相似性，用于去重
emb = OpenAIEmbeddings(model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"))


EXTRACT_PROMPT = (
    "你是一名研究助理。请从给定论文文本中提取**原子化**创新点。"\
    "每条包含：What(是什么/核心观点)、How(关键机制/组件)、Why-new(为何新/相对谁)。"\
    "每条≤2句，避免营销词。提供最小证据（短引句≤30字+定位，如页码或段落）。"\
    "输出 JSON，字段：text, why_new, how, evidence_quote, loc, confidence(0-1), novelty(0-1)。"
)


def extract_innovations_with_llm(text: str, max_chars: int = 12000, max_items: int = 8) -> List[Candidate]:
    if not text:
        return []
    # 截断，避免超长
    snippet = text[:max_chars]
    structured_llm = llm.with_structured_output(schema=CandidateList)  # Pydantic 结构化输出
    try:
        messages = [
            SystemMessage(content=EXTRACT_PROMPT + f" 限制最多 {max_items} 条。"),
            HumanMessage(content=snippet),
        ]
        result = structured_llm.invoke(messages)
        if isinstance(result, dict):
            result = CandidateList(**result)
        return result.items
    except Exception as e:
        logger.warning("LLM extract failed: %s", e)
        return []


# ===================== Dedupe =====================

def semantic_dedupe(
    existing: List[Innovation], candidates: List[Innovation], sim_threshold: float = 0.85
) -> Tuple[List[Innovation], Set[str]]:
    """将 candidates 与 existing 合并去重，返回新集合与 seen_keys。"""
    merged = list(existing)
    seen_hash: Set[str] = {it.hash for it in existing}

    # 先把所有文本做 embedding（批量）
    cand_texts = [c.canonical for c in candidates]
    exist_texts = [e.canonical for e in existing]
    try:
        vec_c = emb.embed_documents(cand_texts) if cand_texts else []
        vec_e = emb.embed_documents(exist_texts) if exist_texts else []
        E = np.array(vec_e) if vec_e else np.zeros((0, 1536))
    except Exception as e:
        logger.warning("Embedding failed, fallback to hash-only dedupe: %s", e)
        vec_c, E = [], np.zeros((0, 1))

    for i, cand in enumerate(candidates):
        if cand.hash in seen_hash:
            continue
        dup = False
        if len(E) and vec_c:
            v = np.array(vec_c[i])
            # 余弦相似
            if len(E):
                sims = (E @ v) / (np.linalg.norm(E, axis=1) * np.linalg.norm(v) + 1e-9)
                if len(sims) and float(np.max(sims)) >= sim_threshold:
                    dup = True
        if not dup:
            merged.append(cand)
            seen_hash.add(cand.hash)
            # 增量扩展 E（避免再次 embed existing）
            if vec_c:
                if E.size == 0:
                    E = np.array([vec_c[i]])
                else:
                    E = np.vstack([E, vec_c[i]])
    return merged, seen_hash


# ===================== Agent State =====================
class AgentState(TypedDict, total=False):
    # create_react_agent 要求的两个必需字段：
    messages: Annotated[List[BaseMessage], add_messages]
    remaining_steps: int
    # 你自己的业务状态（没有聚合器就按最后写入覆盖）：
    topic: str
    target_n: int
    queries: List[str]
    papers_queue: List[PaperMeta]
    visited_ids: Set[str]
    innovations: List[Innovation]
    seen_keys: Set[str]
    candidates_buffer: List[Innovation]
    stats: Dict[str, Any]


# ===================== Tools =====================
@tool
def plan_queries(topic: str, state: Annotated[AgentState, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId]) -> Any:
    """将主题扩展为若干检索式，写入 state['queries']。"""
    prompt = (
        "请为以下主题生成 6-10 条搜索关键词，按行分隔关键词，要求：每条≤8个词；尽量英文关键词；\n\n主题：" + topic
    )
    try:
        resp = llm.invoke([{"role": "user", "content": prompt}])
        queries = [line.strip() for line in str(resp.content).splitlines() if line.strip()]
    except Exception as e:
        logger.warning("plan_queries LLM failed: %s", e)
        queries = [topic]

    old = state.get("queries", [])
    new = list(dict.fromkeys(old + queries))
    new_msg = json.dumps(new, ensure_ascii=False)
    logger.info(f"Planner | %d queries: {new_msg}")
    return Command(update={"queries": new, "messages": [ToolMessage(content=new_msg, tool_call_id=tool_call_id)]})


@tool
def search_papers(state: Annotated[AgentState, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId], per_query: int = 10) -> Any:
    """使用 arXiv API 检索论文，合并去重到 papers_queue。"""
    queries: List[str] = state.get("queries", [])
    all_results: List[PaperMeta] = []
    for query in queries:
        try:
            res = arxiv_search(query, max_results=per_query)
        except Exception as e:
            logger.warning(f"search_papers: 搜索关键词{query}发生了错误: {e}")
            res = []
        all_results.extend(res)

    # 合并去重: 按 (source,id) 唯一
    seen: Set[str] = set()
    merged: List[PaperMeta] = []
    for p in sorted(all_results, key=lambda x: (-(x.year or 0), -len(x.title))):
        key = f"{p.source}:{p.id}"
        if key not in seen:
            seen.add(key)
            merged.append(p)

    # 合入队列，过滤已访问
    visited: Set[str] = set(state.get("visited_ids", set()))
    old_queue: List[PaperMeta] = state.get("papers_queue", [])
    existing_ids = {f"{p.source}:{p.id}" for p in old_queue}
    new_queue = old_queue + [p for p in merged if f"{p.source}:{p.id}" not in existing_ids and p.id not in visited]
    resulut_msg = f"已经搜索了{len(all_results)} 条结果了。"
    logger.info(f"Searcher 搜索到了{len(new_queue)}篇文献，其中新增{max(0, len(new_queue) - len(old_queue))}篇。")
    return Command(update={"papers_queue": new_queue, "messages": [ToolMessage(content=resulut_msg, tool_call_id=tool_call_id)]})


# 子图：单篇论文的读取 + 抽取
def paper_worker(paper: PaperMeta) -> List[Candidate]:
    """
    读取论文，并提取创新点，返回候选的可能创新点Candidate
    Args:
        paper:
    Returns:

    """
    text = paper.snippet
    if not text:
        return []
    cands = extract_innovations_with_llm(text, max_items=8)
    return cands


@tool
def batch_read_extract(state: Annotated[AgentState, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId]) -> Any:
    """从 papers_queue 取所有要处理的论文内容，读取文章并抽取候选创新点，写入 candidates_buffer 与 visited_ids。"""
    papers_queue: List[PaperMeta] = state.get("papers_queue", [])
    print(f"只保留6篇论文进行处理")
    papers_queue = papers_queue[:6]
    # 读取过的文章
    visited: Set[str] = set(state.get("visited_ids", set()))
    print(f"现有{len(papers_queue)}篇论文，其中已处理{len(visited)}篇。")
    batch: List[PaperMeta] = []
    for p in papers_queue:
        if p.id not in visited:
            batch.append(p)
    if not batch:
        logger.info("Batch | no papers to process")
        return Command(update={"messages": [ToolMessage(content="没有待处理的论文了。", tool_call_id=tool_call_id)]})

    all_cands: List[Innovation] = []
    for one_paper in tqdm(batch, desc="处理论文"):
        #cands代表候选创新点
        cands = paper_worker(one_paper)
        for one_cand in tqdm(cands, desc="处理创新点"):
            canonical = one_cand.text
            # 创新点收集
            h = hash_key(canonical)
            inv = Innovation(
                text=one_cand.text,
                canonical=canonical,
                hash=h,
                paper_id=one_paper.id,
                paper_title=one_paper.title,
                source_url=one_paper.url,
                evidence=Evidence(quote=one_cand.evidence_quote or "", loc=one_cand.loc or ""),
                confidence=float(one_cand.confidence or 0.7),
                novelty=float(one_cand.novelty or 0.7),
            )
            all_cands.append(inv)

    new_visited = visited | {p.id for p in batch}

    # 更新队列（移除已处理）
    remaining = [p for p in papers_queue if p.id not in new_visited]

    logger.info("Batch | processed %d papers, got %d candidates", len(batch), len(all_cands))
    return Command(update={
        "visited_ids": new_visited,
        "papers_queue": remaining,
        "candidates_buffer": state.get("candidates_buffer", []) + all_cands,
        "stats": {**state.get("stats", {}), "read": state.get("stats", {}).get("read", 0) + len(batch)},
        "messages": [ToolMessage(content=f"处理了{len(new_visited)}篇论文。", tool_call_id=tool_call_id)]
    })


@tool
def dedupe_merge(state: Annotated[AgentState, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId], sim_threshold: float = 0.85) -> Any:
    """将 candidates_buffer 合并到 innovations，做语义去重。"""
    existing: List[Innovation] = state.get("innovations", [])
    cands: List[Innovation] = state.get("candidates_buffer", [])
    if not cands:
        return {}

    merged, seen = semantic_dedupe(existing, cands, sim_threshold=sim_threshold)
    new_points = len(merged) - len(existing)
    logger.info("Dedupe | +%d unique (threshold=%.2f)", new_points, sim_threshold)
    return Command(update={
        "innovations": merged,
        "seen_keys": seen,
        "candidates_buffer": [],
        "stats": {**state.get("stats", {}), "new_points": state.get("stats", {}).get("new_points", 0) + new_points},
        "messages": [ToolMessage(content=f"新增了{len(new_points)}个创新点。", tool_call_id=tool_call_id)]
    })


@tool
def store_to_db(state: Annotated[AgentState, InjectedState], db_path: str = "innovation.db") -> Any:
    """把 papers 与 innovations 幂等入库（SQLite）。"""
    db = DB(db_path)
    # 已访问的论文里，可能没有全部保存在 papers_queue。因此汇总：
    papers_pool: List[PaperMeta] = state.get("papers_queue", [])
    logger.info(f"store_to_db 存储创新点到数据库: {papers_pool}")
    # 这里也可以在 search 阶段就 upsert
    try:
        db.upsert_papers(papers_pool)
    except Exception as e:
        logger.warning("DB upsert papers failed: %s", e)

    try:
        db.upsert_innovations(state["topic"], state.get("innovations", []))
    except Exception as e:
        logger.warning("DB upsert innovations failed: %s", e)
    return "stored"


@tool
def progress_check(state: Annotated[AgentState, InjectedState]) -> Any:
    """检查创新点是否达到条数；若达标返回 Command(goto="__end__") 结束。"""
    n = len(state.get("innovations", []))
    target = int(state.get("target_n", 50))
    no_gain = int(state.get("stats", {}).get("no_gain_steps", 0))

    # 简单停滞逻辑：若 candidates_buffer 为空且上一轮没有新增，则 no_gain+1
    if not state.get("candidates_buffer"):
        prev_new = int(state.get("stats", {}).get("_prev_added", 0))
        if prev_new == 0:
            no_gain += 1
        state["stats"] = {**state.get("stats", {}), "no_gain_steps": no_gain}

    if n >= target:
        logger.info("Progress | reached target: %d/%d", n, target)
        return Command(goto="__end__")
    if no_gain >= 5:
        logger.info("Progress | stopping due to stagnation (no_gain=%d)", no_gain)
        return Command(goto="__end__")
    return "continue"


# ===================== Supervisor =====================
SUP_PROMPT = (
    "你是 Supervisor，负责收集某主题的不重复论文创新点（默认50条）。"\
    "请以以下顺序反复调用工具推进：\n"\
    "1) plan_queries → 2) search_papers → 3) batch_read_extract → 4) dedupe_merge → 5) store_to_db → 6) progress_check。"\
    "若未达标则回到 2) 或 3)；如长时间无新增，可改写/扩展检索式再 search。"\
    "所有状态保存在 shared state 中，不要丢失。"
)

supervisor = create_react_agent(
    model=llm,
    tools=[plan_queries, search_papers, batch_read_extract, dedupe_merge, store_to_db, progress_check],
    prompt=SUP_PROMPT,
    state_schema=AgentState,
)

# ===================== Run =====================

def run(topic: str, target_n: int = 50, recursion_limit: int = 200) -> AgentState:
    init: AgentState = {
        "topic": topic,
        "target_n": target_n,
        "queries": [],
        "messages": [],
        "papers_queue": [],
        "visited_ids": set(),
        "innovations": [],
        "seen_keys": set(),
        "candidates_buffer": [],
        "stats": {"read": 0, "new_points": 0, "no_gain_steps": 0, "_prev_added": 0},
    }
    logger.info("=== Supervisor start | topic=%r target=%d ===", topic, target_n)
    final_state = supervisor.invoke(init, config={"recursion_limit": recursion_limit})
    logger.info("=== Supervisor end | collected=%d ===", len(final_state.get("innovations", [])))
    return final_state


# ===================== CLI =====================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=str, default="LLM 对齐技术", help="主题，例如：LLM 对齐技术")
    parser.add_argument("--target", dest="target", type=int, default=5, help="目标创新点数量")
    parser.add_argument("--limit", dest="limit", type=int, default=200, help="递归步数上限")
    args = parser.parse_args()

    state = run(args.topic, args.target, recursion_limit=args.limit)

    # 打印前 10 条结果预览
    items: List[Innovation] = state.get("innovations", [])
    print("\n==== SAMPLE OUTPUT (top 10) ====")
    for i, it in enumerate(items[:10], 1):
        print(f"{i:02d}. {it.text}  [paper={it.paper_title}]  (conf={it.confidence:.2f}, nov={it.novelty:.2f})")
