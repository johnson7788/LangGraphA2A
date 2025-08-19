#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/6 10:48
# @File  : tools.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : Agent使用的工具, 设置3个知识库工具
import os
import httpx
import re
import time
import json
from datetime import datetime
import random
from rapidfuzz import fuzz   #pip install rapidfuzz
from typing import Annotated, NotRequired
from langchain_core.tools import tool
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from custom_state import CustomState
def search_with_retry(index, query, limit, retries=1, delay=0.1):
    for attempt in range(retries + 1):
        try:
            response = es.search(index=index, body=query, size=limit)
            return response
        except Exception as e:
            if attempt < retries:
                time.sleep(delay)  # 等待一会再重试
                continue
            else:
                raise e  # 最后一轮也失败，就抛出异常

def fuzzy_search(keyword: str, content: str, idprefix="01", db_id="01") -> str:

    # 输入段落和关键词

    # 按句子切分（中文用句号、问号、感叹号）
    sentences = re.split(r'[。！？!?]', content)
    sentences = [s.strip() for s in sentences if s.strip()]

    # 计算相似度
    scores = [fuzz.partial_ratio(keyword, s) for s in sentences]
    max_index = scores.index(max(scores))

    # 取最相似句子及其上下文, 取上文的3个句子+目标句子+下文的3个句子
    start = max(0, max_index - 3)
    end = min(len(sentences), max_index + 4)
    result = sentences[start:end]
    match_content = "。".join(result)
    # 输出
    match_sentences = []
    id = idprefix + "_" + datetime.now().strftime('%f')[2:5]
    for idx, one in enumerate(result):
        min_idx = max(0, idx-2)
        max_idx = min(len(result), idx+3)
        prefix_sentence = "\n".join(result[min_idx:idx])
        tail_sentence = "\n".join(result[idx+1:max_idx])
        match_sentences.append({"id": f"{id}_{idx}", "sentence": one, "db_id": db_id, "prefix_sentence": prefix_sentence, "tail_sentence": tail_sentence})
    print( f"最相似的句子和它的前后文：{match_content}")
    match_sentence = sentences[max_index]
    return {"match_sentence": match_sentence, "match_content": match_content, "match_sentences": match_sentences}

@tool
def search_document_db(keyword: str, tool_call_id: Annotated[str, InjectedToolCallId], state: Annotated[CustomState, InjectedState]) -> Command:
    """
    搜索医学文献库
    :param keyword: 关键词, eg: 乳腺癌
    :return:
    """
    print("SearchDocument: " + keyword)
    data = [{'title': "Initiation Of Medications For Parkinson'S Disease: A Qualitative Description", 'id': 34264430, 'match_sentence': '目的与目标：了解帕金森病患者在开始使用帕金森病药物治疗时的经历，以促进该疾病的药物治疗', 'match_sentences': [{'id': '03_770_0', 'sentence': '目的与目标：了解帕金森病患者在开始使用帕金森病药物治疗时的经历，以促进该疾病的药物治疗', 'db_id': 34264430, 'prefix_sentence': '', 'tail_sentence': '背景：先前的研究已经记录了帕金森病患者对药物治疗方案的不依从性以及他们对开始使用药物治疗的犹豫不决\n然而，在美国，关于帕金森病患者开始使用抗帕金森病药物的经历、决策以及他们对这些药物的信念或理解程度，所知甚少'}, {'id': '03_770_1', 'sentence': '背景：先前的研究已经记录了帕金森病患者对药物治疗方案的不依从性以及他们对开始使用药物治疗的犹豫不决', 'db_id': 34264430, 'prefix_sentence': '目的与目标：了解帕金森病患者在开始使用帕金森病药物治疗时的经历，以促进该疾病的药物治疗', 'tail_sentence': '然而，在美国，关于帕金森病患者开始使用抗帕金森病药物的经历、决策以及他们对这些药物的信念或理解程度，所知甚少\n设计：采用探索性和描述性的定性研究方法'}, {'id': '03_770_2', 'sentence': '然而，在美国，关于帕金森病患者开始使用抗帕金森病药物的经历、决策以及他们对这些药物的信念或理解程度，所知甚少', 'db_id': 34264430, 'prefix_sentence': '目的与目标：了解帕金森病患者在开始使用帕金森病药物治疗时的经历，以促进该疾病的药物治疗\n背景：先前的研究已经记录了帕金森病患者对药物治疗方案的不依从性以及他们对开始使用药物治疗的犹豫不决', 'tail_sentence': '设计：采用探索性和描述性的定性研究方法'}, {'id': '03_770_3', 'sentence': '设计：采用探索性和描述性的定性研究方法', 'db_id': 34264430, 'prefix_sentence': '背景：先前的研究已经记录了帕金森病患者对药物治疗方案的不依从性以及他们对开始使用药物治疗的犹豫不决\n然而，在美国，关于帕金森病患者开始使用抗帕金森病药物的经历、决策以及他们对这些药物的信念或理解程度，所知甚少', 'tail_sentence': ''}], 'url': 'https://bing.com/26420046_f4d7548c646a49bcbf1f59c01f612f50.pdf'}, {'title': 'Antiviral Therapy In Patients With Chronic Hepatitis C Is Associated With A Reduced Risk Of Parkinsonism', 'id': 2731487, 'match_sentence': '背景：慢性丙型肝炎（CHC）抗病毒治疗后帕金森综合征的风险尚不明确', 'match_sentences': [{'id': '03_785_0', 'sentence': '背景：慢性丙型肝炎（CHC）抗病毒治疗后帕金森综合征的风险尚不明确', 'db_id': 2731487, 'prefix_sentence': '', 'tail_sentence': '目的：研究CHC与帕金森综合征和抗病毒治疗的有效性之间的关联\n方法：通过2004年至2012年台湾的国家健康保险研究数据库，采用倾向评分匹配CHC患者与非CHC患者、接受聚乙二醇干扰素为基础的抗病毒治疗患者及未接受该治疗的患者，并随访新发的帕金森综合征和帕金森病（PD）诊断'}, {'id': '03_785_1', 'sentence': '目的：研究CHC与帕金森综合征和抗病毒治疗的有效性之间的关联', 'db_id': 2731487, 'prefix_sentence': '背景：慢性丙型肝炎（CHC）抗病毒治疗后帕金森综合征的风险尚不明确', 'tail_sentence': '方法：通过2004年至2012年台湾的国家健康保险研究数据库，采用倾向评分匹配CHC患者与非CHC患者、接受聚乙二醇干扰素为基础的抗病毒治疗患者及未接受该治疗的患者，并随访新发的帕金森综合征和帕金森病（PD）诊断\n进行多变量Cox比例风险回归分析'}, {'id': '03_785_2', 'sentence': '方法：通过2004年至2012年台湾的国家健康保险研究数据库，采用倾向评分匹配CHC患者与非CHC患者、接受聚乙二醇干扰素为基础的抗病毒治疗患者及未接受该治疗的患者，并随访新发的帕金森综合征和帕金森病（PD）诊断', 'db_id': 2731487, 'prefix_sentence': '背景：慢性丙型肝炎（CHC）抗病毒治疗后帕金森综合征的风险尚不明确\n目的：研究CHC与帕金森综合征和抗病毒治疗的有效性之间的关联', 'tail_sentence': '进行多变量Cox比例风险回归分析'}, {'id': '03_785_3', 'sentence': '进行多变量Cox比例风险回归分析', 'db_id': 2731487, 'prefix_sentence': '目的：研究CHC与帕金森综合征和抗病毒治疗的有效性之间的关联\n方法：通过2004年至2012年台湾的国家健康保险研究数据库，采用倾向评分匹配CHC患者与非CHC患者、接受聚乙二醇干扰素为基础的抗病毒治疗患者及未接受该治疗的患者，并随访新发的帕金森综合征和帕金森病（PD）诊断', 'tail_sentence': ''}], 'url': 'https://bing.com/31505068_0d205110fefc4abc98a0d93caa66c1ab.pdf'}, {'title': "Survey On General Knowledge On Parkinson'S Disease In Patients With Parkinson'S Disease And Current Clinical Practice For Parkinson'S Disease Among General Neurologists From Southwest China", 'id': 34121438, 'match_sentence': '目的：评估四川省基层医院帕金森病（PD）患者对帕金森病的一般知识以及神经科医生对帕金森病诊断和治疗现状及选择情况', 'match_sentences': [{'id': '03_791_0', 'sentence': '目的：评估四川省基层医院帕金森病（PD）患者对帕金森病的一般知识以及神经科医生对帕金森病诊断和治疗现状及选择情况', 'db_id': 34121438, 'prefix_sentence': '', 'tail_sentence': '方法：于2010年10月至2012年10月，在四川省基层医院对344名帕金森病患者和368名神经科医生进行了横断面问卷调查\n针对患者，设计了一份关于帕金森病一般知识的问卷；针对神经科医生，设计了一份关于帕金森病诊断和治疗的问卷'}, {'id': '03_791_1', 'sentence': '方法：于2010年10月至2012年10月，在四川省基层医院对344名帕金森病患者和368名神经科医生进行了横断面问卷调查', 'db_id': 34121438, 'prefix_sentence': '目的：评估四川省基层医院帕金森病（PD）患者对帕金森病的一般知识以及神经科医生对帕金森病诊断和治疗现状及选择情况', 'tail_sentence': '针对患者，设计了一份关于帕金森病一般知识的问卷；针对神经科医生，设计了一份关于帕金森病诊断和治疗的问卷\n结果：帕金森病患者在病因、抗帕金森病药物的副作用、左旋多巴的使用以及手术治疗等方面缺乏相关信息'}, {'id': '03_791_2', 'sentence': '针对患者，设计了一份关于帕金森病一般知识的问卷；针对神经科医生，设计了一份关于帕金森病诊断和治疗的问卷', 'db_id': 34121438, 'prefix_sentence': '目的：评估四川省基层医院帕金森病（PD）患者对帕金森病的一般知识以及神经科医生对帕金森病诊断和治疗现状及选择情况\n方法：于2010年10月至2012年10月，在四川省基层医院对344名帕金森病患者和368名神经科医生进行了横断面问卷调查', 'tail_sentence': '结果：帕金森病患者在病因、抗帕金森病药物的副作用、左旋多巴的使用以及手术治疗等方面缺乏相关信息'}, {'id': '03_791_3', 'sentence': '结果：帕金森病患者在病因、抗帕金森病药物的副作用、左旋多巴的使用以及手术治疗等方面缺乏相关信息', 'db_id': 34121438, 'prefix_sentence': '方法：于2010年10月至2012年10月，在四川省基层医院对344名帕金森病患者和368名神经科医生进行了横断面问卷调查\n针对患者，设计了一份关于帕金森病一般知识的问卷；针对神经科医生，设计了一份关于帕金森病诊断和治疗的问卷', 'tail_sentence': ''}], 'url': 'https://bing.com/24529223_c72b29a066b0421886842388c59b6654.pdf'}, {'title': "Novel Models For Parkinson'S Disease And Their Impact On Future Drug Discovery", 'id': 4525353, 'match_sentence': '从基于细胞的模型、熟知的毒素基动物模型，到最近的基因模型和越来越多使用的非哺乳动物模型，每个模型都在寻找更好的帕金森病治疗方法方面具有价值', 'match_sentences': [{'id': '03_796_0', 'sentence': '为了寻找更好的治疗方法，最近已经开发了多种新的体内和体外帕金森病模型', 'db_id': 4525353, 'prefix_sentence': '', 'tail_sentence': '涵盖领域：作者概述了各种传统的帕金森病模型，并讨论了近年来新开发的模型\n他们还探讨了这些模型在帕金森病患者中发现具有潜在治疗价值药物方面的应用'}, {'id': '03_796_1', 'sentence': '涵盖领域：作者概述了各种传统的帕金森病模型，并讨论了近年来新开发的模型', 'db_id': 4525353, 'prefix_sentence': '为了寻找更好的治疗方法，最近已经开发了多种新的体内和体外帕金森病模型', 'tail_sentence': '他们还探讨了这些模型在帕金森病患者中发现具有潜在治疗价值药物方面的应用\n从基于细胞的模型、熟知的毒素基动物模型，到最近的基因模型和越来越多使用的非哺乳动物模型，每个模型都在寻找更好的帕金森病治疗方法方面具有价值'}, {'id': '03_796_2', 'sentence': '他们还探讨了这些模型在帕金森病患者中发现具有潜在治疗价值药物方面的应用', 'db_id': 4525353, 'prefix_sentence': '为了寻找更好的治疗方法，最近已经开发了多种新的体内和体外帕金森病模型\n涵盖领域：作者概述了各种传统的帕金森病模型，并讨论了近年来新开发的模型', 'tail_sentence': '从基于细胞的模型、熟知的毒素基动物模型，到最近的基因模型和越来越多使用的非哺乳动物模型，每个模型都在寻找更好的帕金森病治疗方法方面具有价值\n专家意见：在发现帕金森病近60年后，左旋多巴仍然是帕金森病患者的黄金标准治疗方法'}, {'id': '03_796_3', 'sentence': '从基于细胞的模型、熟知的毒素基动物模型，到最近的基因模型和越来越多使用的非哺乳动物模型，每个模型都在寻找更好的帕金森病治疗方法方面具有价值', 'db_id': 4525353, 'prefix_sentence': '涵盖领域：作者概述了各种传统的帕金森病模型，并讨论了近年来新开发的模型\n他们还探讨了这些模型在帕金森病患者中发现具有潜在治疗价值药物方面的应用', 'tail_sentence': '专家意见：在发现帕金森病近60年后，左旋多巴仍然是帕金森病患者的黄金标准治疗方法\n似乎不太可能有一个模型能够完全再现帕金森病的复杂性，就像认为不可能有一种单一治疗方案能够同时缓解帕金森病的运动和非运动症状一样'}, {'id': '03_796_4', 'sentence': '专家意见：在发现帕金森病近60年后，左旋多巴仍然是帕金森病患者的黄金标准治疗方法', 'db_id': 4525353, 'prefix_sentence': '他们还探讨了这些模型在帕金森病患者中发现具有潜在治疗价值药物方面的应用\n从基于细胞的模型、熟知的毒素基动物模型，到最近的基因模型和越来越多使用的非哺乳动物模型，每个模型都在寻找更好的帕金森病治疗方法方面具有价值', 'tail_sentence': '似乎不太可能有一个模型能够完全再现帕金森病的复杂性，就像认为不可能有一种单一治疗方案能够同时缓解帕金森病的运动和非运动症状一样\n因此，治疗可能需要多种疗法的组合'}, {'id': '03_796_5', 'sentence': '似乎不太可能有一个模型能够完全再现帕金森病的复杂性，就像认为不可能有一种单一治疗方案能够同时缓解帕金森病的运动和非运动症状一样', 'db_id': 4525353, 'prefix_sentence': '从基于细胞的模型、熟知的毒素基动物模型，到最近的基因模型和越来越多使用的非哺乳动物模型，每个模型都在寻找更好的帕金森病治疗方法方面具有价值\n专家意见：在发现帕金森病近60年后，左旋多巴仍然是帕金森病患者的黄金标准治疗方法', 'tail_sentence': '因此，治疗可能需要多种疗法的组合'}, {'id': '03_796_6', 'sentence': '因此，治疗可能需要多种疗法的组合', 'db_id': 4525353, 'prefix_sentence': '专家意见：在发现帕金森病近60年后，左旋多巴仍然是帕金森病患者的黄金标准治疗方法\n似乎不太可能有一个模型能够完全再现帕金森病的复杂性，就像认为不可能有一种单一治疗方案能够同时缓解帕金森病的运动和非运动症状一样', 'tail_sentence': ''}], 'url': 'https://bing.com/29363335_5f171d8a03154e2b97f4ecbdcdd6eeab.pdf'}, {'title': "Parkinson'S Syndrome After Cranial Radiotherapy: A Case Report", 'id': 35867594, 'match_sentence': '帕金森综合征是以运动迟缓为核心问题的一组体征和症状，可能是特发性帕金森病(帕金森病，PD)、继发性帕金森病或由神经退行性疾病引起的帕金森病的一种表现', 'match_sentences': [{'id': '03_799_0', 'sentence': '帕金森综合征是以运动迟缓为核心问题的一组体征和症状，可能是特发性帕金森病(帕金森病，PD)、继发性帕金森病或由神经退行性疾病引起的帕金森病的一种表现', 'db_id': 35867594, 'prefix_sentence': '', 'tail_sentence': '帕金森病是帕金森综合症最常见的病因，约占80%的病例\n帕金森综合征的继发病因包括肿瘤、创伤、脑积水、化疗、两性霉素B、甲氧氯普胺等药物和放射治疗'}, {'id': '03_799_1', 'sentence': '帕金森病是帕金森综合症最常见的病因，约占80%的病例', 'db_id': 35867594, 'prefix_sentence': '帕金森综合征是以运动迟缓为核心问题的一组体征和症状，可能是特发性帕金森病(帕金森病，PD)、继发性帕金森病或由神经退行性疾病引起的帕金森病的一种表现', 'tail_sentence': '帕金森综合征的继发病因包括肿瘤、创伤、脑积水、化疗、两性霉素B、甲氧氯普胺等药物和放射治疗\n放射治疗后继发的帕金森症状在文献中很少报道，通常卡比多巴-左旋多巴不能缓解'}, {'id': '03_799_2', 'sentence': '帕金森综合征的继发病因包括肿瘤、创伤、脑积水、化疗、两性霉素B、甲氧氯普胺等药物和放射治疗', 'db_id': 35867594, 'prefix_sentence': '帕金森综合征是以运动迟缓为核心问题的一组体征和症状，可能是特发性帕金森病(帕金森病，PD)、继发性帕金森病或由神经退行性疾病引起的帕金森病的一种表现\n帕金森病是帕金森综合症最常见的病因，约占80%的病例', 'tail_sentence': '放射治疗后继发的帕金森症状在文献中很少报道，通常卡比多巴-左旋多巴不能缓解'}, {'id': '03_799_3', 'sentence': '放射治疗后继发的帕金森症状在文献中很少报道，通常卡比多巴-左旋多巴不能缓解', 'db_id': 35867594, 'prefix_sentence': '帕金森病是帕金森综合症最常见的病因，约占80%的病例\n帕金森综合征的继发病因包括肿瘤、创伤、脑积水、化疗、两性霉素B、甲氧氯普胺等药物和放射治疗', 'tail_sentence': ''}], 'url': 'https://bing.com/35619842_150f93ae06f14988a4f13ad3f6d2d553.pdf'}]
    contents = ""
    for item in data:
        match_sentences = item.get("match_sentences")
        for one_sentence in match_sentences:
            sentence_id = one_sentence.get("id")
            sentence = one_sentence.get("sentence")
            contents += f"{sentence_id} -- {sentence}\n"
        contents += "\n"
    print(f"tool_call_id: {tool_call_id}")
    return Command(update={
        "search_dbs": [{"db": "search_document_db", "result": data}],
        "messages": [
            ToolMessage(content=contents, tool_call_id=tool_call_id)
        ]
    })

@tool
def search_guideline_db(keyword: str, tool_call_id: Annotated[str, InjectedToolCallId], state: Annotated[CustomState, InjectedState]) -> Command:
    """
    搜索医学指南数据
    :param keyword: 关键词, eg: 乳腺癌
    :return:
    """
    print("SearchGuideline: " + keyword)

    data = [{'title': 'The Recommendations Of A Consensus Panel For The Screening, Diagnosis, And Treatment Of Neurogenic Orthostatic Hypotension And Associated Supine Hypertension', 'id': 1093, 'match_sentence': '神经源性直立性低血压(nOH)常见于神经退行性疾病，如帕金森病、多系统萎缩、纯自主神经功能衰竭、路易小体痴呆和周围神经病变(包括淀粉样变性或糖尿病神经病变)', 'match_sentences': [{'id': '02_787_0', 'sentence': '神经源性直立性低血压(nOH)常见于神经退行性疾病，如帕金森病、多系统萎缩、纯自主神经功能衰竭、路易小体痴呆和周围神经病变(包括淀粉样变性或糖尿病神经病变)', 'db_id': 1093, 'prefix_sentence': '', 'tail_sentence': '由于nOH在老龄人口中的频率，临床医生需要了解其诊断和管理\n迄今为止，关于nOH的研究使用了不同的结果测量方法和不同的诊断方法，因此阻止了循证指南的产生，以指导临床医生在治疗nOH和相关仰卧位高血压患者时的“最佳实践”'}, {'id': '02_787_1', 'sentence': '由于nOH在老龄人口中的频率，临床医生需要了解其诊断和管理', 'db_id': 1093, 'prefix_sentence': '神经源性直立性低血压(nOH)常见于神经退行性疾病，如帕金森病、多系统萎缩、纯自主神经功能衰竭、路易小体痴呆和周围神经病变(包括淀粉样变性或糖尿病神经病变)', 'tail_sentence': '迄今为止，关于nOH的研究使用了不同的结果测量方法和不同的诊断方法，因此阻止了循证指南的产生，以指导临床医生在治疗nOH和相关仰卧位高血压患者时的“最佳实践”\n为了解决这些问题,美国自主学会、全国帕金森基金会启动一个项目来开发一个声明的建议开始在波士顿的一个专家小组会议共识11月7日,2015年,继续沟通和贡献在2016年10月的建议'}, {'id': '02_787_2', 'sentence': '迄今为止，关于nOH的研究使用了不同的结果测量方法和不同的诊断方法，因此阻止了循证指南的产生，以指导临床医生在治疗nOH和相关仰卧位高血压患者时的“最佳实践”', 'db_id': 1093, 'prefix_sentence': '神经源性直立性低血压(nOH)常见于神经退行性疾病，如帕金森病、多系统萎缩、纯自主神经功能衰竭、路易小体痴呆和周围神经病变(包括淀粉样变性或糖尿病神经病变)\n由于nOH在老龄人口中的频率，临床医生需要了解其诊断和管理', 'tail_sentence': '为了解决这些问题,美国自主学会、全国帕金森基金会启动一个项目来开发一个声明的建议开始在波士顿的一个专家小组会议共识11月7日,2015年,继续沟通和贡献在2016年10月的建议'}, {'id': '02_787_3', 'sentence': '为了解决这些问题,美国自主学会、全国帕金森基金会启动一个项目来开发一个声明的建议开始在波士顿的一个专家小组会议共识11月7日,2015年,继续沟通和贡献在2016年10月的建议', 'db_id': 1093, 'prefix_sentence': '由于nOH在老龄人口中的频率，临床医生需要了解其诊断和管理\n迄今为止，关于nOH的研究使用了不同的结果测量方法和不同的诊断方法，因此阻止了循证指南的产生，以指导临床医生在治疗nOH和相关仰卧位高血压患者时的“最佳实践”', 'tail_sentence': ''}], 'url': 'https://bing.com/28050656_50981e9456f444f6ab219f1a5443e03c.pdf'}, {'title': 'Management Of Rem Sleep Behavior Disorder: An American Academy Of Sleep Medicine Clinical Practice Guideline', 'id': 2048, 'match_sentence': '7. AASM建议临床医生使用经皮利瓦斯汀(vs无治疗)治疗成人因身体状况(帕金森病)引起的继发性RBD', 'match_sentences': [{'id': '02_831_0', 'sentence': '(有条件)', 'db_id': 2048, 'prefix_sentence': '', 'tail_sentence': '6. * AASM建议临床医生使用立即释放的褪黑激素(相对于不治疗)来治疗成人因身体状况引起的继发性RBD\n(有条件)'}, {'id': '02_831_1', 'sentence': '6. * AASM建议临床医生使用立即释放的褪黑激素(相对于不治疗)来治疗成人因身体状况引起的继发性RBD', 'db_id': 2048, 'prefix_sentence': '(有条件)', 'tail_sentence': '(有条件)\n7. AASM建议临床医生使用经皮利瓦斯汀(vs无治疗)治疗成人因身体状况(帕金森病)引起的继发性RBD'}, {'id': '02_831_2', 'sentence': '(有条件)', 'db_id': 2048, 'prefix_sentence': '(有条件)\n6. * AASM建议临床医生使用立即释放的褪黑激素(相对于不治疗)来治疗成人因身体状况引起的继发性RBD', 'tail_sentence': '7. AASM建议临床医生使用经皮利瓦斯汀(vs无治疗)治疗成人因身体状况(帕金森病)引起的继发性RBD\n(有条件)'}, {'id': '02_831_3', 'sentence': '7. AASM建议临床医生使用经皮利瓦斯汀(vs无治疗)治疗成人因身体状况(帕金森病)引起的继发性RBD', 'db_id': 2048, 'prefix_sentence': '6. * AASM建议临床医生使用立即释放的褪黑激素(相对于不治疗)来治疗成人因身体状况引起的继发性RBD\n(有条件)', 'tail_sentence': '(有条件)\n8. * AASM建议临床医生不要使用深部脑刺激(DBS;与不治疗相比)用于治疗成人因医疗状况引起的继发性RBD'}, {'id': '02_831_4', 'sentence': '(有条件)', 'db_id': 2048, 'prefix_sentence': '(有条件)\n7. AASM建议临床医生使用经皮利瓦斯汀(vs无治疗)治疗成人因身体状况(帕金森病)引起的继发性RBD', 'tail_sentence': '8. * AASM建议临床医生不要使用深部脑刺激(DBS;与不治疗相比)用于治疗成人因医疗状况引起的继发性RBD\n(有条件)'}, {'id': '02_831_5', 'sentence': '8. * AASM建议临床医生不要使用深部脑刺激(DBS;与不治疗相比)用于治疗成人因医疗状况引起的继发性RBD', 'db_id': 2048, 'prefix_sentence': '7. AASM建议临床医生使用经皮利瓦斯汀(vs无治疗)治疗成人因身体状况(帕金森病)引起的继发性RBD\n(有条件)', 'tail_sentence': '(有条件)'}, {'id': '02_831_6', 'sentence': '(有条件)', 'db_id': 2048, 'prefix_sentence': '(有条件)\n8. * AASM建议临床医生不要使用深部脑刺激(DBS;与不治疗相比)用于治疗成人因医疗状况引起的继发性RBD', 'tail_sentence': ''}], 'url': 'https://bing.com/#/'}, {'title': "Diagnostic And Therapeutic Recommendations In Adult Dystonia: A Joint Document By The Italian Society Of Neurology, The Italian Academy For The Study Of Parkinson'S Disease And Movement Disorders, And The Italian Network On Botulinum Toxin", 'id': 2063, 'match_sentence': '本文的目的是描述由意大利神经病学学会、意大利帕金森氏病和运动障碍研究学院和意大利肉毒杆菌毒素网络的意大利专家小组提供的肌张力障碍的诊断和治疗建议', 'match_sentences': [{'id': '02_843_0', 'sentence': '成人肌张力障碍患者的诊断框架和治疗管理对临床神经科医生来说是一个挑战', 'db_id': 2063, 'prefix_sentence': '', 'tail_sentence': '本文的目的是描述由意大利神经病学学会、意大利帕金森氏病和运动障碍研究学院和意大利肉毒杆菌毒素网络的意大利专家小组提供的肌张力障碍的诊断和治疗建议\n我们首先讨论临床方法和仪器评估有用的诊断目的'}, {'id': '02_843_1', 'sentence': '本文的目的是描述由意大利神经病学学会、意大利帕金森氏病和运动障碍研究学院和意大利肉毒杆菌毒素网络的意大利专家小组提供的肌张力障碍的诊断和治疗建议', 'db_id': 2063, 'prefix_sentence': '成人肌张力障碍患者的诊断框架和治疗管理对临床神经科医生来说是一个挑战', 'tail_sentence': '我们首先讨论临床方法和仪器评估有用的诊断目的\n然后，我们分析成人肌张力障碍的药物、手术和康复治疗方案'}, {'id': '02_843_2', 'sentence': '我们首先讨论临床方法和仪器评估有用的诊断目的', 'db_id': 2063, 'prefix_sentence': '成人肌张力障碍患者的诊断框架和治疗管理对临床神经科医生来说是一个挑战\n本文的目的是描述由意大利神经病学学会、意大利帕金森氏病和运动障碍研究学院和意大利肉毒杆菌毒素网络的意大利专家小组提供的肌张力障碍的诊断和治疗建议', 'tail_sentence': '然后，我们分析成人肌张力障碍的药物、手术和康复治疗方案\n最后，我们提出成人肌张力障碍管理的医院-区域网络模型'}, {'id': '02_843_3', 'sentence': '然后，我们分析成人肌张力障碍的药物、手术和康复治疗方案', 'db_id': 2063, 'prefix_sentence': '本文的目的是描述由意大利神经病学学会、意大利帕金森氏病和运动障碍研究学院和意大利肉毒杆菌毒素网络的意大利专家小组提供的肌张力障碍的诊断和治疗建议\n我们首先讨论临床方法和仪器评估有用的诊断目的', 'tail_sentence': '最后，我们提出成人肌张力障碍管理的医院-区域网络模型'}, {'id': '02_843_4', 'sentence': '最后，我们提出成人肌张力障碍管理的医院-区域网络模型', 'db_id': 2063, 'prefix_sentence': '我们首先讨论临床方法和仪器评估有用的诊断目的\n然后，我们分析成人肌张力障碍的药物、手术和康复治疗方案', 'tail_sentence': ''}], 'url': 'https://bing.com/36190683_c22a4d88a32d4aadae9cba088f0f80cc.pdf'}, {'title': "Screening, Diagnosis, And Management Of Parkinson'S Disease Psychosis: Recommendations From An Expert Panel", 'id': 2081, 'match_sentence': '简介:伴有精神病的幻觉和妄想是帕金森病的衰弱性非运动症状，在病程的某一阶段患病率高达50-70%', 'match_sentences': [{'id': '02_851_0', 'sentence': '简介:伴有精神病的幻觉和妄想是帕金森病的衰弱性非运动症状，在病程的某一阶段患病率高达50-70%', 'db_id': 2081, 'prefix_sentence': '', 'tail_sentence': '通常，除非被特别询问，否则患者和护理人员不会报告出现幻觉或妄想\n神经病学和老年精神病学专家小组召开会议，制定帕金森病精神病(PDP)诊断和治疗的简单筛查工具和指南'}, {'id': '02_851_1', 'sentence': '通常，除非被特别询问，否则患者和护理人员不会报告出现幻觉或妄想', 'db_id': 2081, 'prefix_sentence': '简介:伴有精神病的幻觉和妄想是帕金森病的衰弱性非运动症状，在病程的某一阶段患病率高达50-70%', 'tail_sentence': '神经病学和老年精神病学专家小组召开会议，制定帕金森病精神病(PDP)诊断和治疗的简单筛查工具和指南\n方法:工作组回顾了现有PDP诊断和管理指南的文献，并确定了建议中的差距'}, {'id': '02_851_2', 'sentence': '神经病学和老年精神病学专家小组召开会议，制定帕金森病精神病(PDP)诊断和治疗的简单筛查工具和指南', 'db_id': 2081, 'prefix_sentence': '简介:伴有精神病的幻觉和妄想是帕金森病的衰弱性非运动症状，在病程的某一阶段患病率高达50-70%\n通常，除非被特别询问，否则患者和护理人员不会报告出现幻觉或妄想', 'tail_sentence': '方法:工作组回顾了现有PDP诊断和管理指南的文献，并确定了建议中的差距'}, {'id': '02_851_3', 'sentence': '方法:工作组回顾了现有PDP诊断和管理指南的文献，并确定了建议中的差距', 'db_id': 2081, 'prefix_sentence': '通常，除非被特别询问，否则患者和护理人员不会报告出现幻觉或妄想\n神经病学和老年精神病学专家小组召开会议，制定帕金森病精神病(PDP)诊断和治疗的简单筛查工具和指南', 'tail_sentence': ''}], 'url': 'https://bing.com/35906500_df4ec18bd6024e39a516bc4d989619df.pdf'}, {'title': "European Academy Of Neurology/Movement Disorder Society - European Section Guideline On The Treatment Of Parkinson'S Disease: I. Invasive Therapies", 'id': 2089, 'match_sentence': '侵袭性治疗是为特定的患者群体和临床情况保留的，主要是在帕金森病(PD)的晚期', 'match_sentences': [{'id': '02_861_0', 'sentence': '建议是基于高水平的证据，并分为三个等级', 'db_id': 2089, 'prefix_sentence': '', 'tail_sentence': '如果只有较低级别的证据，但该主题被认为是高度重要的，则收集指南工作组的临床共识\n结果:回答了两个研究问题，提出了8项建议和5项临床共识声明'}, {'id': '02_861_1', 'sentence': '如果只有较低级别的证据，但该主题被认为是高度重要的，则收集指南工作组的临床共识', 'db_id': 2089, 'prefix_sentence': '建议是基于高水平的证据，并分为三个等级', 'tail_sentence': '结果:回答了两个研究问题，提出了8项建议和5项临床共识声明\n侵袭性治疗是为特定的患者群体和临床情况保留的，主要是在帕金森病(PD)的晚期'}, {'id': '02_861_2', 'sentence': '结果:回答了两个研究问题，提出了8项建议和5项临床共识声明', 'db_id': 2089, 'prefix_sentence': '建议是基于高水平的证据，并分为三个等级\n如果只有较低级别的证据，但该主题被认为是高度重要的，则收集指南工作组的临床共识', 'tail_sentence': '侵袭性治疗是为特定的患者群体和临床情况保留的，主要是在帕金森病(PD)的晚期\n只有在文本中提到的特殊患者情况下才能考虑干预措施'}, {'id': '02_861_3', 'sentence': '侵袭性治疗是为特定的患者群体和临床情况保留的，主要是在帕金森病(PD)的晚期', 'db_id': 2089, 'prefix_sentence': '如果只有较低级别的证据，但该主题被认为是高度重要的，则收集指南工作组的临床共识\n结果:回答了两个研究问题，提出了8项建议和5项临床共识声明', 'tail_sentence': '只有在文本中提到的特殊患者情况下才能考虑干预措施\n与目前的药物治疗相比，治疗效果发生了变化'}, {'id': '02_861_4', 'sentence': '只有在文本中提到的特殊患者情况下才能考虑干预措施', 'db_id': 2089, 'prefix_sentence': '结果:回答了两个研究问题，提出了8项建议和5项临床共识声明\n侵袭性治疗是为特定的患者群体和临床情况保留的，主要是在帕金森病(PD)的晚期', 'tail_sentence': '与目前的药物治疗相比，治疗效果发生了变化\nSTN-DBS是研究最充分的晚期PD干预措施，口服药物不能令人满意地控制波动;它可以改善运动症状和生活质量，应向符合条件的患者提供治疗'}, {'id': '02_861_5', 'sentence': '与目前的药物治疗相比，治疗效果发生了变化', 'db_id': 2089, 'prefix_sentence': '侵袭性治疗是为特定的患者群体和临床情况保留的，主要是在帕金森病(PD)的晚期\n只有在文本中提到的特殊患者情况下才能考虑干预措施', 'tail_sentence': 'STN-DBS是研究最充分的晚期PD干预措施，口服药物不能令人满意地控制波动;它可以改善运动症状和生活质量，应向符合条件的患者提供治疗'}, {'id': '02_861_6', 'sentence': 'STN-DBS是研究最充分的晚期PD干预措施，口服药物不能令人满意地控制波动;它可以改善运动症状和生活质量，应向符合条件的患者提供治疗', 'db_id': 2089, 'prefix_sentence': '只有在文本中提到的特殊患者情况下才能考虑干预措施\n与目前的药物治疗相比，治疗效果发生了变化', 'tail_sentence': ''}], 'url': 'https://bing.com/#/'}]
    contents = ""
    for item in data:
        match_sentences = item.get("match_sentences")
        for one_sentence in match_sentences:
            sentence_id = one_sentence.get("id")
            sentence = one_sentence.get("sentence")
            contents += f"{sentence_id} -- {sentence}\n"
        contents += "\n"
    print(f"tool_call_id: {tool_call_id}")
    return Command(update={
        "search_dbs": [{"db": "search_guideline_db", "result": data}],
        "messages": [
            ToolMessage(content=contents, tool_call_id=tool_call_id)
        ]
    })

@tool
def search_personal_db(keyword: str, tool_call_id: Annotated[str, InjectedToolCallId], state: Annotated[dict, InjectedState]) -> Command:
    """
    搜索个人知识库中关键疾病等相关内容
    Args:
        keyword (str): 搜索查询关键词
    Returns:
        list: 返回相关知识
    """
    print(f"触发了调用search_personal_db: {keyword}")
    user_id = state.get("user_id", "")
    if not user_id:
        return Command(update={
            "messages": [
                ToolMessage(content="未找到对应的个人知识库，没有检索到有用结果", tool_call_id=tool_call_id)
            ]
        })
    search_status, search_data = personal_db_search_api(user_id=user_id, query=keyword)
    if not search_status:
        return Command(update={
            "messages": [
                ToolMessage(content="个人知识库搜索错误，请联系管理员", tool_call_id=tool_call_id)
            ]
        })
    documents = search_data["documents"]
    metadatas = search_data["metadatas"]
    data = []
    if isinstance(documents[0], list):
        documents = documents[0]
    if isinstance(metadatas[0], list):
        metadatas = metadatas[0]
    for document, meta in zip(documents, metadatas):
        if not document:
            # 跳过空数据
            continue
        pdf_name = meta["file_name"]
        id = meta["file_id"]
        url = meta.get("url", "https://bing.com/#/")
        plain_content = document
        fuzzy_res = fuzzy_search(keyword, plain_content, idprefix="06", db_id=id)
        data.append({
            "title": pdf_name.title(),
            "id": id,
            "match_sentence": fuzzy_res["match_sentence"],
            "match_sentences": fuzzy_res["match_sentences"],
            "url": url,
        })
    contents = ""
    for item in data:
        match_sentences = item.get("match_sentences")
        for one_sentence in match_sentences:
            sentence_id = one_sentence.get("id")
            sentence = one_sentence.get("sentence")
            contents += f"{sentence_id} -- {sentence}\n"
        contents += "\n"
    print(f"tool_call_id: {tool_call_id}")
    return Command(update={
        "search_dbs": [{"db": "search_personal_db", "result": data}],
        "messages": [
            ToolMessage(content=contents, tool_call_id=tool_call_id)
        ]
    })

def personal_db_search_api(user_id: int, query: str, topk=3):
    """
    搜索知识库
    """
    PERSONENAL_DB = os.environ.get('PERSONENAL_DB', '')
    assert PERSONENAL_DB, "PERSONENAL_DB is not set"
    url = f"{PERSONENAL_DB}/search"
    # 正确的请求数据格式
    data = {
        "userId": user_id,
        "query": query,
        "keyword": "",  # 关键词匹配，是否需要强制包含一些关键词
        "topk": topk
    }
    headers = {'content-type': 'application/json'}
    try:
        # 发送POST请求
        response = httpx.post(url, json=data, headers=headers, timeout=20.0)

        # 检查HTTP状态码
        response.raise_for_status()
        assert response.status_code == 200, f"{PERSONENAL_DB}搜索个人知识库报错"

        # 解析返回的JSON数据
        result = response.json()
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        data = {"documents": documents, "metadatas": metadatas}
        print("Response status:", response.status_code)
        print("Response body:", result)
        return True, data

    except Exception as e:
        print(f"{PERSONENAL_DB}搜索个人知识库报错: {e}")
        return False, f"{PERSONENAL_DB}搜索个人知识库报错: {str(e)}"