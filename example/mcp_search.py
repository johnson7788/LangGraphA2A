#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/8 10:51
# @File  : mcp_search.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :

import logging
from mcp.server.fastmcp import FastMCP
import time

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

mcp = FastMCP("MCP搜索工具", host="127.0.0.1", port=9000)

@mcp.tool()
def search_document_db(query: str, max_results: int = 3):
    """
    模拟搜索文献库：包括标题、snippet、content、来源、时间等。

    Args:
        query (str): 搜索查询关键词
        max_results (int, optional): 最大返回结果数量，默认为3

    Returns:
        list: 包含文献信息的字典列表，每个字典包含title, snippet, content, source, timestamp字段
    """
    print(f"search_document_db, {query}")
    results = [
        {
            "title": "CuATSM 恢复 SOD1 功能：小鼠病症逆转研究",
            "snippet": "在帕金森小鼠模型中，用 CuATSM 递送铜可防止神经退化，显著改善运动能力。",
            "content": (
                "研究由悉尼大学领导，27 只小鼠进行剂量探索后确立15 mg/kg 为最佳剂量；"
                "之后对10 只帕金森样模型连续用药3 个月。治疗组运动能力保持稳定，"
                "多巴胺神经元在黑质得到保护，而对照组出现神经退化与运动恶化。"
                "CuATSM 恢复了 SOD1 抗氧化功能，预防自由基损伤，从而阻止疾病进展。"
            ),
            "source": "Wired 报道",
            "timestamp": "2025‑07‑10"
        },
        {
            "title": "MLi‑2 抑制 LRRK2：促进神经纤毛再生与神经保护",
            "snippet": "MLi‑2 在 LRRK2 突变型小鼠中，再生纤毛，恢复细胞通信并提升神经保护。",
            "content": (
                "斯坦福团队对 LRRK2 高活性基因突变小鼠施用 MLi‑2，共持续3 个月；"
                "结果显示 striatum 中神经和神经胶质细胞的初级纤毛数量恢复至健康水平，"
                "神经信号传递增强，多巴胺突触密度翻倍，提示可能逆转病理性功能损害。"
            ),
            "source": "Wired 报道",
            "timestamp": "2025‑07‑10"
        },
        {
            "title": "Tavapadon 新药：TEMPO 3 期临床数据",
            "snippet": "腾博登（tavapadon）靶向 D1/D5 受体，延长“on time”，不良反应少。",
            "content": (
                "TEMPO 3 试验结果显示，tavapadon 每日口服一次可延长患者的运动控制“on time”，"
                "且诱发幻觉、血压变化等不良事件明显少于传统 levodopa；该药可用于早期"
                "或与 levodopa 联用治疗中晚期患者，正在申请 FDA 批准阶段。"
            ),
            "source": "NY Post / AAN 大会报告",
            "timestamp": "2025‑04‑18"
        },
    ]
    return results[:max_results]

if __name__ == "__main__":
    mcp.run(transport="sse")
    # mcp.run(transport="streamable-http")
