#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/29 15:49
# @File  : langgraph_sequential.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/08/29
# @File  : innovation_collector_seq.py
# @Author: johnson (refactored by ChatGPT)
# @Desc  : 顺序 Agent（无 LangGraph/Tool 调度）收集主题下的不重复“创新点”

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
from typing import List, Dict, Any, Tuple, Optional, Set, TypedDict

import numpy as np
import requests
import dotenv
from pydantic import BaseModel, Field

dotenv.load_dotenv()

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

# ===================== External Clients =====================
# ZhipuAI Web Search（与原实现兼容）
try:
    from zai import ZhipuAiClient   # pip install zai-sdk
    WebSearchClient = ZhipuAiClient(api_key=os.environ.get("ZHIPU_API_KEY"))
except Exception:
    WebSearchClient = None
    logger.warning("未安装或未配置 zai-sdk；web 搜索将不可用。")

# LangChain OpenAI（用于 LLM 结构化抽取 & Embedding 去重）
try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from langchain_core.messages import SystemMessage, HumanMessage
except Exception as e:
    logger.error("需要 langchain_openai 与 langchain_core: %s", e)
    raise

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0)
emb = OpenAIEmbeddings(model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"))

# ===================== Data Models =====================
class PaperMeta(BaseModel):
    id: str
    title: str
    url: str
    snippet: str
    year: Optional[int] = None
    source: str = "web"
    score: float = 0.0
    pdf_url: Optional[str] = None

class Evidence(BaseModel):
    quote: str = ""
    loc: str = ""  # 页码/段落/句号索引等

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
    why_new: Optional[str] = None
    how: Optional[str] = None
    evidence_quote: Optional[str] = None
    loc: Optional[str] = None
    confidence: Optional[float] = None
    novelty: Optional[float] = None

class CandidateList(BaseModel):
    items: List[Candidate]

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
                (p.id, p.title, p.url, p.source, p.year, p.pdf_url or "", json.dumps(p.model_dump(), ensure_ascii=False)),
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
                        json.dumps(it.evidence.model_dump(), ensure_ascii=False),
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

# ===================== Utils =====================
def hash_key(text: str) -> str:
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()

# 简易缓存装饰（避免频繁搜索同一关键词）；也可以换成你现有的 cache_utils.cache_decorator
from functools import lru_cache

@lru_cache(maxsize=256)
def arxiv_search(keyword: str, max_results: int = 20) -> List[PaperMeta]:
    """实际上调用的是 Zhipu 的通用 Web 搜索；名称沿用原始实现。"""
    if WebSearchClient is None:
        logger.error("WebSearchClient 不可用；请安装 zai-sdk 并配置 ZHIPU_API_KEY。")
        return []
    logger.info("WebSearch | query=%r", keyword)
    try:
        response = WebSearchClient.web_search.web_search(
            search_engine="search_std",
            search_query=keyword,
            count=min(max_results, 15),
            search_recency_filter="noLimit",
            content_size="high",
        )
        items = response.get("search_result", []) or []
        results = [
            PaperMeta(
                id=uuid.uuid4().hex,
                url=item.get("url", ""),
                title=item.get("title", ""),
                snippet=item.get("content", ""),
                source="web",
            )
            for item in items
        ]
        logger.info("WebSearch | parsed %d results", len(results))
        return results
    except Exception as e:
        logger.exception("WebSearch | error during search: %s", e)
        return []

EXTRACT_PROMPT = (
    "你是一名研究助理。请从给定论文文本中提取**原子化**创新点。"
    "每条包含：What(是什么/核心观点)、How(关键机制/组件)、Why-new(为何新/相对谁)。"
    "每条≤2句，避免营销词。提供最小证据（短引句≤30字+定位，如页码或段落）。"
    "输出 JSON，字段：text, why_new, how, evidence_quote, loc, confidence(0-1), novelty(0-1)。"
)

# ===================== Core Ops（顺序函数） =====================

def plan_queries(topic: str, old: Optional[List[str]] = None, k: int = 10) -> List[str]:
    """用 LLM 生成检索式列表。"""
    prompt = (
        "请为以下主题生成 6-10 条搜索关键词，按行分隔关键词，要求：每条≤8个词；尽量英文关键词；\n\n主题：" + topic
    )
    try:
        resp = llm.invoke([{"role": "user", "content": prompt}])
        lines = [l.strip() for l in str(resp.content).splitlines() if l.strip()]
    except Exception as e:
        logger.warning("plan_queries LLM failed: %s", e)
        lines = [topic]
    merged = list(dict.fromkeys((old or []) + lines))[:k]
    logger.info("Planner | %d queries", len(merged))
    return merged


def search_papers(queries: List[str], per_query: int = 10) -> List[PaperMeta]:
    all_results: List[PaperMeta] = []
    for q in queries:
        res = arxiv_search(q, max_results=per_query) or []
        all_results.extend(res)
    # 合并去重：基于 (url,title) 近似去重
    seen: Set[Tuple[str, str]] = set()
    merged: List[PaperMeta] = []
    for p in all_results:
        key = (p.url, p.title)
        if key not in seen:
            seen.add(key)
            merged.append(p)
    logger.info("Searcher | %d unique papers", len(merged))
    return merged


def extract_innovations_with_llm(text: str, max_chars: int = 12000, max_items: int = 8) -> List[Candidate]:
    if not text:
        return []
    snippet = text[:max_chars]
    structured_llm = llm.with_structured_output(schema=CandidateList)
    try:
        messages = [SystemMessage(content=EXTRACT_PROMPT + f" 限制最多 {max_items} 条。"), HumanMessage(content=snippet)]
        result = structured_llm.invoke(messages)
        if isinstance(result, dict):
            result = CandidateList(**result)
        return result.items
    except Exception as e:
        logger.warning("LLM extract failed: %s", e)
        return []


def paper_worker(paper: PaperMeta, max_items: int = 8) -> List[Candidate]:
    text = paper.snippet
    if not text:
        return []
    return extract_innovations_with_llm(text, max_items=max_items)


def semantic_dedupe(existing: List[Innovation], candidates: List[Innovation], sim_threshold: float = 0.85) -> Tuple[List[Innovation], int]:
    """把 candidates 合并到 existing，并做语义去重；返回 (merged, 新增条数)。"""
    merged = list(existing)
    seen_hash: Set[str] = {it.hash for it in existing}

    cand_texts = [c.canonical for c in candidates]
    exist_texts = [e.canonical for e in existing]

    try:
        vec_c = emb.embed_documents(cand_texts) if cand_texts else []
        vec_e = emb.embed_documents(exist_texts) if exist_texts else []
        E = np.array(vec_e) if vec_e else np.zeros((0, 1536))
    except Exception as e:
        logger.warning("Embedding failed, fallback to hash-only dedupe: %s", e)
        vec_c, E = [], np.zeros((0, 1))

    added = 0
    for i, cand in enumerate(candidates):
        if cand.hash in seen_hash:
            continue
        dup = False
        if len(E) and vec_c:
            v = np.array(vec_c[i])
            if E.size and v.size:
                sims = (E @ v) / (np.linalg.norm(E, axis=1) * np.linalg.norm(v) + 1e-9)
                if sims.size and float(np.max(sims)) >= sim_threshold:
                    dup = True
        if not dup:
            merged.append(cand)
            seen_hash.add(cand.hash)
            added += 1
            if vec_c:
                E = np.vstack([E, vec_c[i]]) if E.size else np.array([vec_c[i]])
    return merged, added


# ===================== 顺序 Agent =====================
class AgentState(TypedDict, total=False):
    topic: str
    target_n: int
    queries: List[str]
    papers_queue: List[PaperMeta]
    visited_ids: Set[str]
    innovations: List[Innovation]
    candidates_buffer: List[Innovation]
    stats: Dict[str, Any]

class CollectorAgent:
    def __init__(self, db_path: str = "innovation.db"):
        self.db = DB(db_path)

    def run(self, topic: str, target_n: int = 50, per_query: int = 10, max_rounds: int = 50, per_batch: int = 6, sim_threshold: float = 0.85) -> AgentState:
        state: AgentState = {
            "topic": topic,
            "target_n": target_n,
            "queries": [],
            "papers_queue": [],
            "visited_ids": set(),
            "innovations": [],
            "candidates_buffer": [],
            "stats": {"read": 0, "new_points": 0, "no_gain_steps": 0, "_prev_added": 0},
        }

        # 第 0 步：生成检索词
        state["queries"] = plan_queries(topic, old=state["queries"]) or [topic]

        for round_idx in range(1, max_rounds + 1):
            logger.info("=== Round %d/%d ===", round_idx, max_rounds)

            # 1) 搜索
            papers = search_papers(state["queries"], per_query=per_query)
            # 合并到队列（去掉已访问）
            visited = state["visited_ids"]
            existing_ids = {p.id for p in state["papers_queue"]}
            new_queue = state["papers_queue"] + [p for p in papers if (p.id not in visited and p.id not in existing_ids)]
            state["papers_queue"] = new_queue
            logger.info("Queue | %d papers queued (visited=%d)", len(new_queue), len(visited))

            if not state["papers_queue"]:
                # 若没结果，尝试扩展/改写检索式
                state["queries"] = plan_queries(topic, old=state["queries"]) or state["queries"]
                continue

            # 2) 读取 + 抽取
            batch: List[PaperMeta] = []
            for p in state["papers_queue"]:
                if p.id not in visited:
                    batch.append(p)
                if len(batch) >= per_batch:
                    break

            if not batch:
                logger.info("Batch | no unvisited papers; expanding queries…")
                state["queries"] = plan_queries(topic, old=state["queries"]) or state["queries"]
                continue

            all_cands: List[Innovation] = []
            for one in tqdm(batch, desc="处理论文"):
                cands = paper_worker(one, max_items=8)
                for c in cands:
                    canonical = c.text
                    h = hash_key(canonical)
                    inv = Innovation(
                        text=c.text,
                        canonical=canonical,
                        hash=h,
                        paper_id=one.id,
                        paper_title=one.title,
                        source_url=one.url,
                        evidence=Evidence(quote=c.evidence_quote or "", loc=c.loc or ""),
                        confidence=float(c.confidence or 0.7),
                        novelty=float(c.novelty or 0.7),
                    )
                    all_cands.append(inv)

            # 标记访问 & 维护队列
            visited |= {p.id for p in batch}
            state["visited_ids"] = visited
            state["papers_queue"] = [p for p in state["papers_queue"] if p.id not in visited]
            state["stats"]["read"] += len(batch)

            # 3) 语义去重合并
            merged, added = semantic_dedupe(state["innovations"], all_cands, sim_threshold=sim_threshold)
            state["innovations"] = merged
            state["stats"]["new_points"] += added
            state["stats"]["_prev_added"] = added
            logger.info("Dedupe | +%d new unique innovations (total=%d)", added, len(merged))

            # 4) 入库（幂等）
            try:
                self.db.upsert_papers(batch)
                self.db.upsert_innovations(topic, merged)
                logger.info("DB | upserted batch + merged innovations")
            except Exception as e:
                logger.warning("DB upsert error: %s", e)

            # 5) 进度判定
            if len(state["innovations"]) >= target_n:
                logger.info("Target reached: %d/%d", len(state["innovations"]), target_n)
                break

            if added == 0:
                state["stats"]["no_gain_steps"] += 1
            else:
                state["stats"]["no_gain_steps"] = 0

            if state["stats"]["no_gain_steps"] >= 5:
                logger.info("Stop due to stagnation (no_gain_steps=%d)", state["stats"]["no_gain_steps"])
                break

            # 6) 若创新新增不多，扩展检索式
            if added == 0 or len(state["papers_queue"]) < per_batch:
                state["queries"] = plan_queries(topic, old=state["queries"]) or state["queries"]

        logger.info("=== Done | collected=%d innovations ===", len(state.get("innovations", [])))
        return state


# ===================== CLI =====================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=str, default="LLM Alignment", help="主题，例如：LLM 对齐技术")
    parser.add_argument("--target", dest="target", type=int, default=5, help="目标创新点数量")
    parser.add_argument("--per_query", dest="per_query", type=int, default=10, help="每个检索式返回条数上限")
    parser.add_argument("--rounds", dest="rounds", type=int, default=50, help="最大轮数")
    parser.add_argument("--batch", dest="batch", type=int, default=6, help="每轮处理论文数上限")
    parser.add_argument("--sim", dest="sim", type=float, default=0.85, help="去重相似度阈值(0-1)")
    parser.add_argument("--db", dest="db", type=str, default="innovation.db", help="SQLite 路径")
    args = parser.parse_args()

    agent = CollectorAgent(db_path=args.db)
    state = agent.run(
        topic=args.topic,
        target_n=args.target,
        per_query=args.per_query,
        max_rounds=args.rounds,
        per_batch=args.batch,
        sim_threshold=args.sim,
    )

    items: List[Innovation] = state.get("innovations", [])
    print("\n==== SAMPLE OUTPUT (top 10) ====")
    for i, it in enumerate(items[:10], 1):
        print(f"{i:02d}. {it.text}  [paper={it.paper_title}]  (conf={it.confidence:.2f}, nov={it.novelty:.2f})")
