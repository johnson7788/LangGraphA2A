#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/28 15:04
# @File  : langgraph_planner.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 按计划执行 → 失败回退给 Planner 打补丁 → 重试继续执行 的最小示例。
#          本版本在原始 demo 基础上：
#          1) 增加了更详尽的中文注释；
#          2) 引入统一的 log() 打印函数，包含时间戳/级别；
#          3) 主循环打印更丰富的“状态快照”（计划表、上下文摘要、最后错误等）。

from __future__ import annotations
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# ======================== 日志工具 & 辅助函数 ========================
LOG_TS_FMT = "%H:%M:%S.%f"  # 日志时间戳格式（到毫秒）


def log(state: Dict[str, Any], msg: str, level: str = "INFO") -> None:
    """统一的日志入口：
    - 打印到 stdout，附带时间戳和级别；
    - 同步写入 state["logs"]（供可视化/回放）。
    """
    ts = datetime.now().strftime(LOG_TS_FMT)[:-3]
    line = f"{ts} [{level}] {msg}"
    print(line)
    state.setdefault("logs", []).append(line)


def fmt_task(t: Dict[str, Any]) -> str:
    """将任务字典格式化为紧凑的一行，便于打印。"""
    return (
        f"name={t['name']}, status={t['status']}, tries={t['tries']}/{t['max_retries']}, "
        f"patched={t['patched']}, params={t['params']}"
    )


def context_summary(ctx: Dict[str, Any]) -> str:
    """对 context 里的关键维度做计数摘要，避免在日志里刷屏。"""
    hits = len(ctx.get("search_results", {}).get("hits", []) or [])
    docs = len(ctx.get("fetched_docs", {}).get("docs", {}) or {})
    inno = len(ctx.get("innovations", {}).get("innovations", []) or [])
    return f"hits={hits}, docs={docs}, innovations={inno}"


# ======================== 子 Agent（示意实现） ========================

def agent_search(params: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """模拟检索：根据关键词伪造 3 条命中文献 ID 列表。

    入参：
        params: {"q": <query str>}  检索关键词
        ctx:    上下文（未使用）
    返回：
        {"hits": ["paper-1-<q>", "paper-2-<q>", "paper-3-<q>"]}
    """
    q = params.get("q", "")
    hits = [f"paper-{i}-{q}" for i in range(1, 4)]
    return {"hits": hits}


def agent_fetch(params: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """模拟抓取全文：第一次（未打补丁）时故意失败；打补丁后成功。

    入参：
        params: {"use_backup": bool} 是否启用备份源（补丁）
        ctx:    读取 ctx["search_results"]["hits"] 作为要抓取的文档 ID 列表
    返回：
        成功时 -> {"docs": {paper_id: "FullText(paper_id)", ...}}
        失败时 -> 抛出 RuntimeError
    """
    use_backup = params.get("use_backup", False)
    if not use_backup:
        # 第一次走主源：人为制造网络失败
        raise RuntimeError("NETWORK_ERROR: primary source down")

    # 走备份源：把每篇命中转成“文档内容”字符串
    hits = ctx.get("search_results", {}).get("hits", []) or []
    docs = {h: f"FullText({h})" for h in hits}
    return {"docs": docs}


def agent_extract(params: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """模拟抽取：从全文内容中抽取“创新点”文本。"""
    docs = ctx.get("fetched_docs", {}).get("docs", {}) or {}
    innovations = []
    for pid in docs:
        innovations.append({"paper_id": pid, "claim": f"Novel idea from {pid}"})
    return {"innovations": innovations}


# 子 Agent 注册表（按 name 路由）
AGENTS = {
    "search": agent_search,
    "fetch": agent_fetch,
    "extract": agent_extract,
}


# ======================== 计划任务结构 & 工具函数 ========================

def make_task(name: str, params: Dict[str, Any], max_retries: int = 2) -> Dict[str, Any]:
    """工厂函数：构造一个计划任务字典。"""
    return {
        "name": name,
        "params": params,
        "status": "PENDING",  # 生命周期：PENDING/RUNNING/DONE/FAILED/SKIPPED
        "tries": 0,
        "max_retries": max_retries,
        "patched": False,      # 是否被 Planner 打过“补丁”（改过参数）
    }


def first_pending_index(plan: List[Dict[str, Any]]) -> Optional[int]:
    """返回第一个 PENDING 任务的下标；若无，返回 None。"""
    for i, t in enumerate(plan):
        if t["status"] == "PENDING":
            return i
    return None


def all_done(plan: List[Dict[str, Any]]) -> bool:
    """计划是否全部完成（DONE 或 SKIPPED 均视为“可继续”）。"""
    return all(t["status"] in ("DONE", "SKIPPED") for t in plan)


# ======================== 全局状态（state）规范化 ========================

def ensure_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """为传入的 state 填充默认字段，确保键存在。
    注意：此函数不打印日志，避免噪音；日志在节点内部按需打印。
    """
    state.setdefault("goal", "collect innovations for keyword=LLM agents")
    state.setdefault("plan", [])
    state.setdefault("context", {})      # 跨任务传递的中间结果
    state.setdefault("last_error", None) # 最近一次错误（如果有）
    state.setdefault("last_task_idx", None)
    state.setdefault("logs", [])
    return state


# ======================== 节点 1：Planner（规划/修复） ========================

def planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
    state = ensure_state(state)

    # 1) 若无计划：初始化（按需可生成更复杂的计划 DAG）
    if not state["plan"]:
        goal = state["goal"]
        log(state, f"[Planner] 初始化计划 for goal: {goal}")
        plan = [
            make_task("search", {"q": "LLM agents recent"}, max_retries=1),
            make_task("fetch", {"use_backup": False}, max_retries=2),  # 先不走备份，制造一次失败
            make_task("extract", {}, max_retries=1),
        ]
        state["plan"] = plan
        state["last_error"] = None
        state["last_task_idx"] = None
        return state

    # 2) 如果上一步失败，决定是否修改计划/参数（打补丁或跳过）
    if state["last_error"] is not None:
        err = state["last_error"]
        idx = state["last_task_idx"]
        task = state["plan"][idx]
        log(state, f"[Planner] 接收到失败: task[{idx}]={task['name']}, error={err}", level="WARN")

        # 策略：对 fetch 任务只打一次“备份源”补丁；若已补丁过仍失败/或非 fetch，直接跳过
        if task["name"] == "fetch" and not task["patched"]:
            before = dict(task["params"])  # 记录补丁前参数
            task["params"]["use_backup"] = True  # 启用备选方案
            task["status"] = "PENDING"           # 回到待执行
            task["patched"] = True
            state["last_error"] = None
            log(state, f"[Planner] 打补丁: fetch params {before} -> {task['params']}，重置为 PENDING")
        else:
            task["status"] = "SKIPPED"
            state["last_error"] = None
            log(state, f"[Planner] 跳过 task[{idx}]={task['name']}（已补丁或不支持修复）", level="WARN")

    return state


# ======================== 节点 2：Router（条件路由） ========================

def router_node(state: Dict[str, Any]) -> str:
    """根据计划完成度决定是否结束或继续执行。"""
    state = ensure_state(state)
    if all_done(state["plan"]):
        log(state, "[Router] 所有任务均为 DONE/SKIPPED，流程结束")
        return END
    log(state, "[Router] 仍有待执行任务，流转给 executor")
    return "executor"


# ======================== 节点 3：Executor（按计划执行） ========================

def executor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    state = ensure_state(state)

    idx = first_pending_index(state["plan"])
    if idx is None:
        log(state, "[Executor] 没有 PENDING 任务，保持原状")
        return state

    task = state["plan"][idx]
    name = task["name"]
    params = task["params"]
    fn = AGENTS.get(name)

    if fn is None:
        # 未知任务：标记跳过
        task["status"] = "SKIPPED"
        log(state, f"[Executor] 未知任务 name={name}，标记为 SKIPPED", level="WARN")
        return state

    # 标记 RUNNING & 记次
    task["status"] = "RUNNING"
    task["tries"] += 1
    state["last_task_idx"] = idx

    # 执行前快照
    log(state, f"[Executor] 准备执行 task[{idx}] -> {fmt_task(task)}")
    log(state, f"[Executor] 执行前上下文摘要: {context_summary(state['context'])}")

    try:
        # 调用子 Agent
        result = fn(params, state["context"])  # 可能抛异常

        # 根据任务名将结果写回 context
        if name == "search":
            state["context"]["search_results"] = result
        elif name == "fetch":
            state["context"]["fetched_docs"] = result
        elif name == "extract":
            state["context"]["innovations"] = result

        # 成功收尾
        task["status"] = "DONE"
        state["last_error"] = None
        log(state, f"[Executor] task[{idx}]={name} 执行成功 DONE；结果后上下文摘要: {context_summary(state['context'])}")
        return state

    except Exception as e:
        # 失败处理：由 Planner 决定是否补丁或跳过
        err_msg = f"{type(e).__name__}: {e}"
        log(state, f"[Executor] task[{idx}]={name} 执行失败 -> {err_msg}", level="ERROR")

        # 未超过最大重试：退回 PENDING，等 Planner 打补丁/处理
        if task["tries"] < task["max_retries"]:
            task["status"] = "PENDING"
            log(state, f"[Executor] 将 task[{idx}] 回退为 PENDING，等待 Planner 决策 (tries={task['tries']}/{task['max_retries']})")
        else:
            task["status"] = "FAILED"
            log(state, f"[Executor] task[{idx}] 重试已达上限，标记为 FAILED")

        state["last_error"] = str(e)
        return state


# ======================== 构图 & 编译 ========================

def build_app():
    """构建状态图：planner → router (条件) → executor；executor 成功/失败再回 router 或 planner。"""
    graph = StateGraph(dict)

    # 注册节点
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("router", lambda s: s)  # router节点本身不改状态，条件判断交给 router_node

    # 入口
    graph.set_entry_point("planner")

    # planner → router（初始化或补丁后进入路由）
    graph.add_edge("planner", "router")

    # router 的条件跳转（继续执行或结束）
    graph.add_conditional_edges(
        source="router",
        path=router_node,  # 直接传函数，不要再嵌套 lambda
        path_map={"executor": "executor", END: END},
    )

    # executor 成功或失败后：
    # - 成功：回 router 看是否还有任务
    # - 失败：回 planner 让其修改计划（或跳过）
    graph.add_conditional_edges(
        "executor",
        lambda s: "planner" if s.get("last_error") else "router",
        {"planner": "planner", "router": "router"},
    )

    app = graph.compile(checkpointer=MemorySaver())
    return app


# ======================== 演示运行 ========================
if __name__ == "__main__":
    app = build_app()

    # 初始输入（只需给出目标；其它状态由节点补全）
    init_state = {
        "goal": "Collect innovations for keyword='LLM agents'",
    }
    # 利用 MemorySaver 的线程 ID 将一次 run 的事件归档，便于回放/并发
    config = {"configurable": {"thread_id": "session-1"}}

    print("=== RUN START ===")
    final_state = None

    # .stream 会产生一个事件序列：每个事件是 {node_name: node_state}
    for event in app.stream(init_state, config=config):
        for node_name, node_state in event.items():
            # 为了便于阅读，这里统一精简地打印一个“状态快照”
            print(f"\n--- [{node_name}] ---")

            plan = node_state.get("plan", [])
            ctx = node_state.get("context", {})
            last_error = node_state.get("last_error")
            last_idx = node_state.get("last_task_idx")

            print("plan:")
            for i, t in enumerate(plan):
                print(f"  [{i}] {fmt_task(t)}")

            print(f"context: {context_summary(ctx)}")
            if last_error is not None:
                print(f"last_error: {last_error}")
            print(f"last_task_idx: {last_idx}")

            # 打印最近 10 条日志（若不足则全打）
            logs = node_state.get("logs", [])
            if logs:
                print("logs (tail):")
                for line in logs[-10:]:
                    print("  ", line)

            final_state = node_state

    print("\n=== RUN END ===")
    print("\nFinal context keys:", list(final_state.get("context", {}).keys()))
    print("Innovations:", final_state.get("context", {}).get("innovations"))
