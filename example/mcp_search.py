#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/8 10:51
# @File  : mcp_search.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :


# math_server.py
from mcp.server.fastmcp import FastMCP
import time

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

@mcp.tool()
def search_guideline_db(query: str, max_results: int = 3):
    """
    模拟搜索指南库：包括推荐内容、content 字段详实说明建议依据与适应症。
    Args:
        query (str): 搜索查询关键词
        max_results (int, optional): 最大返回结果数量，默认为3
    Returns:
        list: 包含指南信息的字典列表，每个字典包含title, snippet, content, source, timestamp字段
    """
    print(f"search_guideline_db, {query}")
    results = [
        {
            "title": "MDS 2025：治疗运动波动的循证综述",
            "snippet": "官方推荐多种药物与手术选项用于改善 levodopa 相关起伏。",
            "content": (
                "2025 年 5 月 MDS 更新基于 Cochrane 与 GRADE 方法，对 levodopa 延释剂、"
                "pramipexole（速释与长效）、ropinirole、rotigotine、opicapone、"
                "safinamide、双侧 STN DBS 等评为“有效”；连续肠道 levodopa 输注、"
                "皮下 apomorphine、rasagiline、istradefylline、amantadine 延释剂、"
                "Zonisamide、GPI DBS 等评为“可能有效”用于 motor fluctuations。"
            ),
            "source": "Movement Disorders (MDS EBM Review)",
            "timestamp": "2025‑05"
        },
        {
            "title": "FDA 批准 adaptive DBS（闭环深部脑刺激，aDBS）",
            "snippet": "首个可根据脑电信号自动调节的 DBS 系统获 FDA 批准。",
            "content": (
                "美国 FDA 于 2025 年批准 Medtronic 的 BrainSense Adaptive aDBS 系统，"
                "这种闭环设备可持续监测桥臂核的异常脑电信号，并即时调节电刺激，"
                "相比传统 DBS 可减少 40% 电能用量，改善 tremor 与肌肉僵硬，"
                "并支持算法切换以优化响应并降低副作用。"
            ),
            "source": "UCSF 公告 / Medical News",
            "timestamp": "2025‑02"
        },
        {
            "title": "Onapgo 药物输注治疗 motor fluctuations",
            "snippet": "FDA 批准皮下输注 apomorphine，用于显著 “off” 时间的患者。",
            "content": (
                "2025 年 2 月 FDA 批准 Onapgo（apomorphine HCl）连续皮下注射输注疗法，"
                "适用于经历明显 motor fluctuations 或 off-time 的帕金森患者。"
                "输注系统可持续提供较稳定的血药浓度，迅速缓解 tremor 与运动迟缓，"
                "成为 levodopa 波动管理的重要补充治疗手段。"
            ),
            "source": "Michael J. Fox 基金会新闻",
            "timestamp": "2025‑02‑04"
        },
    ]
    return results[:max_results]

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
