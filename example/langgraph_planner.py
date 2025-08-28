#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/28 15:04
# @File  : langgraph_planner.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 按计划执行，错误之后

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# ========== 子Agent（示意） ==========
def agent_search(params: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """模拟检索：根据关键词给出伪造命中文献列表"""
    q = params.get("q", "")
    hits = [f"paper-{i}-{q}" for i in range(1, 4)]
    return {"hits": hits}

def agent_fetch(params: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    模拟下载/抓取全文：
    - 第一次（未打补丁）时，故意失败；
    - Planner 打补丁后（use_backup=True）再执行就会成功。
    """
    use_backup = params.get("use_backup", False)
    if not use_backup:
        raise RuntimeError("NETWORK_ERROR: primary source down")
    # 成功时把每篇命中转成“文档内容”
    docs = {h: f"FullText({h})" for h in ctx.get("search_results", {}).get("hits", [])}
    return {"docs": docs}

def agent_extract(params: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """模拟从全文中抽取创新点"""
    docs = ctx.get("fetched_docs", {}).get("docs", {})
    innovations = []
    for pid, txt in docs.items():
        innovations.append({"paper_id": pid, "claim": f"Novel idea from {pid}"})
    return {"innovations": innovations}

AGENTS = {
    "search": agent_search,
    "fetch": agent_fetch,
    "extract": agent_extract,
}

# ========== 工具函数 ==========
def make_task(name: str, params: Dict[str, Any], max_retries: int = 2) -> Dict[str, Any]:
    return {
        "name": name,
        "params": params,
        "status": "PENDING",  # PENDING/RUNNING/DONE/FAILED/SKIPPED
        "tries": 0,
        "max_retries": max_retries,
        "patched": False,     # Planner 是否已对该任务打过补丁
    }

def first_pending_index(plan: List[Dict[str, Any]]) -> Optional[int]:
    for i, t in enumerate(plan):
        if t["status"] == "PENDING":
            return i
    return None

def all_done(plan: List[Dict[str, Any]]) -> bool:
    return all(t["status"] in ("DONE", "SKIPPED") for t in plan)

# ========== 图的状态：用 dict，最简单 ==========
def ensure_state(state: Dict[str, Any]) -> Dict[str, Any]:
    # print(f"state: {state}")
    state.setdefault("goal", "collect innovations for keyword=LLM agents")
    state.setdefault("plan", [])
    state.setdefault("context", {})      # 跨任务传递的中间结果
    state.setdefault("last_error", None) # 最近一次错误（如果有）
    state.setdefault("last_task_idx", None)
    state.setdefault("logs", [])
    return state

# ========== 节点 1：Planner（唯一的大脑） ==========
def planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
    state = ensure_state(state)
    logs = state["logs"]

    # 1) 若无计划：初始化（可以按需生成更复杂的计划）
    if not state["plan"]:
        goal = state["goal"]
        logs.append(f"[Planner] init plan for goal: {goal}")
        plan = [
            make_task("search", {"q": "LLM agents recent"}, max_retries=1),
            make_task("fetch", {"use_backup": False}, max_retries=2),  # 先不走备份，制造一次失败
            make_task("extract", {}, max_retries=1),
        ]
        state["plan"] = plan
        state["last_error"] = None
        state["last_task_idx"] = None
        return state

    # 2) 如果上一步失败，决定是否修改计划/参数
    if state["last_error"] is not None:
        err = state["last_error"]
        idx = state["last_task_idx"]
        task = state["plan"][idx]
        logs.append(f"[Planner] got failure from task[{idx}]={task['name']}: {err}")

        # 简单策略：对 fetch 任务打一次“备份源”补丁；否则若已补丁过仍失败，就跳过该任务。
        if task["name"] == "fetch" and not task["patched"]:
            task["params"]["use_backup"] = True  # 启用备选方案
            task["status"] = "PENDING"           # 重新执行
            task["patched"] = True
            logs.append("[Planner] patch: fetch.use_backup=True ; reset to PENDING")
            state["last_error"] = None
        else:
            # 达到最大重试或已补丁过仍失败 → 跳过
            task["status"] = "SKIPPED"
            logs.append(f"[Planner] skip task[{idx}] after failure")
            state["last_error"] = None

    return state

# ========== 节点 2：Router（决定是继续执行还是结束） ==========
def router_node(state: Dict[str, Any]) -> str:
    state = ensure_state(state)
    if all_done(state["plan"]):
        return END
    # 仍有待执行任务
    return "executor"

# ========== 节点 3：Executor（按计划执行子Agent；失败则反馈给 Planner） ==========
def executor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    state = ensure_state(state)
    logs = state["logs"]
    plan = state["plan"]

    idx = first_pending_index(plan)
    if idx is None:
        logs.append("[Executor] nothing pending")
        return state

    task = plan[idx]
    name = task["name"]
    params = task["params"]
    fn = AGENTS.get(name)

    if fn is None:
        # 未知任务：标记跳过
        logs.append(f"[Executor] unknown task '{name}', skip")
        task["status"] = "SKIPPED"
        return state

    logs.append(f"[Executor] run task[{idx}]={name} params={params}")
    task["status"] = "RUNNING"
    task["tries"] += 1
    state["last_task_idx"] = idx

    try:
        # 调用子Agent
        result = fn(params, state["context"])

        # 根据任务名把结果放到 context
        if name == "search":
            state["context"]["search_results"] = result
        elif name == "fetch":
            state["context"]["fetched_docs"] = result
        elif name == "extract":
            state["context"]["innovations"] = result

        task["status"] = "DONE"
        state["last_error"] = None
        logs.append(f"[Executor] task[{idx}]={name} DONE")
        return state

    except Exception as e:
        # 失败：若未超过最大重试，让 Planner 决定是否补丁；否则标记失败并回 Planner
        err_msg = str(e)
        logs.append(f"[Executor] task[{idx}]={name} FAIL: {err_msg}")

        if task["tries"] < task["max_retries"]:
            # 把任务回退到 PENDING，交给 Planner 来“改计划/改参数”
            task["status"] = "PENDING"
        else:
            task["status"] = "FAILED"

        state["last_error"] = err_msg
        return state

# ========== 构图 ==========
def build_app():
    graph = StateGraph(dict)

    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("router", lambda s: s)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "router")
    # router 的条件跳转（继续执行或结束）
    graph.add_conditional_edges(
        source="router",
        path= router_node,  # 直接传函数，不要再嵌套 lambda 调用
        path_map={"executor": "executor", END: END}
    )

    # executor 成功或失败后：
    # - 成功：回 router 看是否还有任务
    # - 失败：回 planner 让其修改计划（或跳过）
    graph.add_conditional_edges(
        "executor",
        lambda s: "planner" if s.get("last_error") else "router",
        {"planner": "planner", "router": "router"}
    )

    app = graph.compile(checkpointer=MemorySaver())
    return app

# ========== 演示运行 ==========
if __name__ == "__main__":
    app = build_app()

    # 初始输入（目标即可；其它状态由节点补全）
    init_state = {
        "goal": "Collect innovations for keyword='LLM agents'",
    }
    config = {"configurable": {"thread_id": "session-1"}}

    # 连续调用直到结束；为了方便展示，这里用 stream 打印每步状态
    print("=== RUN START ===")
    final_state = None
    for event in app.stream(init_state,config=config):
        for node_name, node_state in event.items():
            print(f"\n--- [{node_name}] ---")
            # 精简打印
            plan = node_state.get("plan", [])
            logs = node_state.get("logs", [])
            print("plan:", [(i, t["name"], t["status"], t["params"]) for i, t in enumerate(plan)])
            if logs:
                print("logs:"); [print(" ", l) for l in logs[-3:]]  # 只看最近几条

            final_state = node_state

    print("\n=== RUN END ===")
    print("\nFinal context keys:", list(final_state.get("context", {}).keys()))
    print("Innovations:", final_state.get("context", {}).get("innovations"))
