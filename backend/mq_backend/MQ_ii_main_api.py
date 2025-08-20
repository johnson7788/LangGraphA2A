#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 用于和rabbitMQ进行交互
import os
import random
import string
import requests
import time
import json
import asyncio
import traceback
import aiohttp
import dotenv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from mq_handler import start_consumer, MQHandler
from A2Aclient import A2AClientWrapper
from Parse_QA import QAParser
dotenv.load_dotenv()

IMAGE_API = os.environ.get('IMAGE_API')
parser_message = QAParser(
    base_url=IMAGE_API,
    timeout=30.0,
)

# 创建一个线程池，定义线程池的大小10
executor = ThreadPoolExecutor(max_workers=20)

RABBITMQ_HOST = os.environ["RABBITMQ_HOST"]
RABBITMQ_PORT = os.environ["RABBITMQ_PORT"]
RABBITMQ_USERNAME = os.environ["RABBITMQ_USERNAME"]
RABBITMQ_PASSWORD = os.environ["RABBITMQ_PASSWORD"]
RABBITMQ_VIRTUAL_HOST = os.environ["RABBITMQ_VIRTUAL_HOST"]
QUEUE_NAME_ANSWER = os.environ["QUEUE_NAME_ANSWER"]
QUEUE_NAME_QUESTION = os.environ["QUEUE_NAME_QUESTION"]
AGENT_URL = os.environ["AGENT_URL"]
ENTITY_URL = os.environ["ENTITY_URL"]

def entity_indentify_extract_match_db(content):
    """entity_indentify_extract识别接口
    eg: content: 近年来，糖尿病患者数量逐年上升，常用的治疗药物包括盐酸二甲双胍片、胰岛素注射液等。部分患者还伴有高血压，需要服用氯沙坦或硝苯地平进行控制。"
    Returns:
        eg:
{
    "code": 0,
    "msg": "success",
    "data": {
        "diseases": [
            {
                "id": 4633,
                "disease_name": "高血压",
                "overview": "高血压（hypertension）是指以体循环动脉血压（收缩压和/或舒张压）增高为主要特征（收缩压≥140毫米汞柱，舒张压≥90毫米汞柱），可伴有心、脑、肾等器官的功能或器质性损害的临床综合征。高血压是最常见的慢性病，也是心脑血管病最主要的危险因素。正常人的血压随内外环境变化在一定范围内波动。在整体人群，血压水平随年龄逐渐升高，以收缩压更为明显，但50岁后舒张压呈现下降趋势，脉压也随之加大。近年来，人们对心血管病多重危险因素的作用以及心、脑、肾靶器官保护的认识不断深入，高血压的诊断标准也在不断调整，目前认为同一血压水平的患者发生心血管病的危险不同，因此有了血压分层的概念，即发生心血管病危险度不同的患者，适宜血压水平应有不同。血压值和危险因素评估是诊断和制定高血压治疗方案的主要依据，不同患者高血压管理的目标不同，医生面对患者时在参考标准的基础上，根据其具体情况判断该患者最合适的血压范围，采用针对性的治疗措施。在改善生活方式的基础上，推荐使用24小时长效降压药物控制血压。除评估诊室血压外，患者还应注意家庭清晨血压的监测和管理，以控制血压，降低心脑血管事件的发生率。",
                "match_word": "高血压"
            },
            {
                "id": 7608,
                "disease_name": "糖尿病",
                "overview": "糖尿病是一组以高血糖为特征的代谢性疾病。高血糖则是由于胰岛素分泌缺陷或其生物作用受损，或两者兼有引起。糖尿病时长期存在的高血糖，导致各种组织，特别是眼、肾、心脏、血管、神经的慢性损害、功能障碍。",
                "match_word": "糖尿病"
            }
        ],
        "drugs": [
            {
                "id": 259152,
                "drug_id": "185917",
                "med_name": "盐酸二甲双胍片",
                "component": "<p>【化学名称】 <br/>\n1,1-二甲基双胍盐酸盐</p>\n\n<p>【化学结构式】</p>\n\n<p><img rel=\"https://img1.dxycdn.com/2019/1211/311/3384551398150199955-73.gif\"  src = \"https://img1.dxycdn.com/2019/1211/311/3384551398150199955-73.gif\" alt = \"\" /></p>\n\n<p>【分子量】 <br/>\n165.63</p>",
                "match_word": "盐酸二甲双胍片"
            },
            {
                "id": 236868,
                "drug_id": "177275",
                "med_name": "胰岛素注射液",
                "component": "本品主要成份为胰岛素（猪或牛）的灭菌水溶液。辅料为：甘油。",
                "match_word": "胰岛素注射液"
            }
        ]
    }
}

    """
    url = f"{ENTITY_URL}/api/entity_indentify"
    start_time = time.time()
    headers = {'content-type': 'application/json'}
    data = {"match_db": True,"content": content}
    r = requests.post(url, data=json.dumps(data), headers=headers)
    assert r.status_code == 200, f"返回的status code不是200，请检查"
    # 检查转换结果
    res = r.json()
    print(json.dumps(res, indent=4, ensure_ascii=False))
    msg = res.get("msg")
    assert msg == "success", f"接口返回的msg不是成功，请检查"
    print(f"花费时间: {time.time() - start_time}秒")
    return res

async def entity_indentify_extract_match_db_async(content):
    """异步版本的实体识别接口"""
    url = f"{ENTITY_URL}/api/entity_indentify"
    start_time = time.time()
    headers = {'content-type': 'application/json'}
    data = {"match_db": True, "content": content}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as resp:
            assert resp.status == 200, f"返回的status code不是200，请检查"
            res = await resp.json()
            print(json.dumps(res, indent=4, ensure_ascii=False))
            msg = res.get("msg")
            assert msg == "success", f"接口返回的msg不是成功，请检查"
            print(f"花费时间: {time.time() - start_time}秒")
            return res

def call_tool_mapper(one_chunk_data):
    """
    工具调用时，改成前端需要的数据格式
    """
    print(f"进行tool的转换: {one_chunk_data}")
    assert isinstance(one_chunk_data, dict), f"必须是字典格式: {one_chunk_data}"
    func_name = one_chunk_data["function"]["name"]
    func_args = one_chunk_data["function"]["arguments"]
    id = one_chunk_data["id"]
    mapper = {
        "search_document_db": {
            "name": "文献库",
            "globalization": "国内"
        },
        "search_guideline_db": {
            "name": "指南",
            "globalization": "国际"
        },
        "search_personal_db": {
            "name": "个人知识库",
            "globalization": "个人"
        }
    }
    db_name = mapper[func_name]["name"]
    globalization = mapper[func_name]["globalization"]
    data = [
        {"status": "Working",
         "display": f"正在检索{db_name}\n",
         "name": db_name,
         "globalization": globalization,
         "func_name": func_name,
         "arguments": func_args,
         "id": id
         }
    ]
    print(f"转换的结果是: {data}")
    return data
def result_tool_mapper(one_chunk_data):
    """
    工具结果时，改成前端需要的数据格式
    """
    print(f"进行tool的转换: {one_chunk_data}")
    assert isinstance(one_chunk_data, dict), f"必须是字典格式: {one_chunk_data}"
    func_name = one_chunk_data["name"]
    func_output = one_chunk_data["tool_output"]
    id = one_chunk_data["tool_call_id"]
    mapper = {
        "search_document_db": {
            "name": "文献库",
            "globalization": "国内"
        },
        "search_guideline_db": {
            "name": "指南",
            "globalization": "国际"
        },
        "search_personal_db": {
            "name": "个人知识库",
            "globalization": "个人"
        }
    }
    db_name = mapper[func_name]["name"]
    globalization = mapper[func_name]["globalization"]
    data = [
        {"status": "Done",
         "display": f"检索{db_name}完成\n",
         "name": db_name,
         "globalization": globalization,
         "func_name": func_name,
         "func_output": func_output,
         "id": id
         }
    ]
    print(f"转换的结果是: {data}")
    return data
def metadata_tool_mapper(one_chunk_data):
    """
    metadata信息发送给前端
    """
    print(f"进行metadata的转换: {one_chunk_data}")
    assert isinstance(one_chunk_data, dict), f"必须是字典格式: {one_chunk_data}"
    search_dbs = one_chunk_data["search_dbs"]
    data = []
    for search_db_res in search_dbs:
        func_name = search_db_res["db"]
        result = search_db_res["result"]
        mapper = {
            "search_document_db": {
                "name": "文献库",
                "globalization": "国内"
            },
            "search_guideline_db": {
                "name": "指南",
                "globalization": "国际"
            },
            "search_personal_db": {
                "name": "个人知识库",
                "globalization": "个人"
            }
        }
        db_name = mapper[func_name]["name"]
        globalization = mapper[func_name]["globalization"]
        one_data = {
             "globalization": globalization,
             "name": db_name,
             "data": result,
             }
        data.append(one_data)
    print(f"转换的结果是: {data}")
    return data


def handle_gpt_stream_response(session_id, user_id, function_id, stream_response):
    """
    处理GPT流式响应
    """
    mq_handler = MQHandler(RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD, RABBITMQ_VIRTUAL_HOST,
                           QUEUE_NAME_ANSWER)
    # 如果发生错误，先处理错误：stream_response是字符串就是错误，应该默认是生成器
    def send_error_message(error_msg):
        """发送错误信息到消息队列"""
        mq_handler.send_message({
            "sessionId": session_id,
            "userId": user_id,
            "functionId": function_id,
            "message": f'发生错误：{error_msg}',
            "reasoningMessage": "",
            "type": 4,
        })
        time.sleep(0.01)
        mq_handler.send_message({
            "sessionId": session_id,
            "userId": user_id,
            "functionId": function_id,
            "message": '[stop]',
            "reasoningMessage": "",
            "type": 4,
        })

    if isinstance(stream_response, str):
        send_error_message(stream_response)
        mq_handler.close_connection()
        return
    async def consume():
        try:
            # 记录所有停止的tools
            running_tools = []  # 正在检索的工具，也只发送给前端一次
            stopped_tools = []
            reponse_content = ""
            async for chunk in stream_response:
                print(f"chunk: {chunk}")
                try:
                    data_type = chunk.get("type")
                    if data_type == "final":
                        print(f"data_type是final，开始最终的stop返回")
                        answer_queue_message = {
                            "sessionId": session_id,
                            "userId": user_id,
                            "functionId": function_id,
                            "message": '[stop]',
                            "reasoningMessage": "",
                            "type": 4,
                        }
                    elif data_type == "reasoning":
                        answer_queue_message = {
                            "sessionId": session_id,
                            "userId": user_id,
                            "functionId": function_id,
                            "message": '',
                            "reasoningMessage": chunk.get("reasoning", ""),
                            "type": 4,
                        }
                    elif data_type == "text":
                        answer_queue_message = {
                            "sessionId": session_id,
                            "userId": user_id,
                            "functionId": function_id,
                            "message": chunk.get("text", ""),
                            "reasoningMessage": '',
                            "type": 4,
                        }
                        reponse_content += chunk.get("text", "")
                    elif data_type == "metadata":
                        metadata = chunk.get("data", {})
                        metadata_to_front = metadata_tool_mapper(metadata)
                        answer_queue_message = {
                            "sessionId": session_id,
                            "userId": user_id,
                            "functionId": function_id,
                            "message": json.dumps(metadata_to_front, ensure_ascii=False),
                            "reasoningMessage": '',
                            "type": 6,
                        }
                        print(f"[Info] 发送引用数据完成type6：{answer_queue_message}")
                    elif data_type == "tool_call":
                        chunk_data = chunk.get("data", {})
                        print(f"触发了函数调用: {chunk_data}")
                        tool_to_fronts = []
                        for one_chunk_data in chunk_data:
                            # 只处理函数的返回结果，不处理函数的调用请求
                            tool_to_front = call_tool_mapper(one_chunk_data)
                            # 每个工具只停止一次
                            tool_name = tool_to_front[0]["name"]
                            if tool_name in running_tools:
                                continue
                            running_tools.append(tool_name)
                            tool_to_fronts.extend(tool_to_front)
                        if tool_to_fronts:
                            answer_queue_message = {
                                "sessionId": session_id,
                                "userId": user_id,
                                "functionId": function_id,
                                "message": json.dumps(tool_to_fronts, ensure_ascii=False),
                                "reasoningMessage": "",
                                "type": 5,
                            }
                            mq_handler.send_message(answer_queue_message)
                            print(f"[Info] 发送工具使用状态type5：{answer_queue_message}")
                        continue
                    elif data_type == "tool_result":
                        chunk_data = chunk.get("data", {})
                        print(f"触发了函数结果返回: {chunk_data}")
                        for one_chunk_data in chunk_data:
                            # 只处理函数的返回结果，不处理函数的调用请求
                            tool_to_front = result_tool_mapper(one_chunk_data)
                            # 每个工具只停止一次
                            tool_name = tool_to_front[0]["name"]
                            if tool_name in stopped_tools:
                                continue
                            stopped_tools.append(tool_name)
                            answer_queue_message = {
                                "sessionId": session_id,
                                "userId": user_id,
                                "functionId": function_id,
                                "message": json.dumps(tool_to_front, ensure_ascii=False),
                                "reasoningMessage": "",
                                "type": 5,
                            }
                            mq_handler.send_message(answer_queue_message)
                            print(f"[Info] 发送工具调用完成type5：{answer_queue_message}")
                        continue
                    elif data_type == "artifact":
                        print(f"[Info] 收到artifact数据，如果我们设置的Stream，那么这条数据需要忽略：{chunk}")
                        #识别实体,artifact_content应该是空的，使用收集的reponse_content进行实体识别
                        artifact_content = chunk["text"]
                        if ENTITY_URL:
                            # entities = entity_indentify_extract_match_db(reponse_content)
                            loop = asyncio.get_running_loop()
                            entities = await loop.run_in_executor(None, entity_indentify_extract_match_db,reponse_content)
                            entities_data = entities["data"]
                            diseases = entities_data.get("diseases")
                            drugs = entities_data.get("drugs")
                            # 如果没有疾病和药品，则不进行返回
                            if not diseases and not drugs:
                                continue
                            entities_message = {
                                "sessionId": session_id,
                                "userId": user_id,
                                "functionId": function_id,
                                "message": json.dumps(entities_data, ensure_ascii=False),
                                "reasoningMessage": "",
                                "type": 7,
                            }
                            mq_handler.send_message(entities_message)
                            print(f"[Info] 发送实体识别数据(type 7)：{entities_message}")
                        continue
                    else:
                        print(f"[警告] 未知的chunk类型：{data_type}，已跳过")
                        continue

                    mq_handler.send_message(answer_queue_message)
                    if function_id not in [5000, 9001]:
                        time.sleep(0.01)
                except Exception as chunk_error:
                    print("[错误] 处理 chunk 时发生异常：", chunk_error)
                    traceback.print_exc()
                    send_error_message(f"处理数据块出错：{chunk_error}")
        except Exception as stream_error:
            print("[错误] 流消费失败：", stream_error)
            traceback.print_exc()
            send_error_message(f"处理流出错：{stream_error}")
        finally:
            mq_handler.close_connection()

    asyncio.run(consume())


def handle_rabbit_queue_message(rabbit_message):
    """
    处理从RabbitMQ 队列接收到的消息
    """
    # 解析mq消息
    print(f"处理消息handle_rabbit_queue_message: {rabbit_message}")
    session_id = rabbit_message['sessionId']
    user_id = rabbit_message['userId']
    function_id = rabbit_message['functionId']
    messages = rabbit_message['messages']
    convert_messages = parser_message.transform_user_question(messages)
    user_question_dict = convert_messages.pop()
    # 解析出来的用户问题
    user_question = user_question_dict["content"]
    attachment = rabbit_message.get('attachment')
    if not attachment:
        attachment = {}
    assert isinstance(attachment, dict), f"attachment字段必须是字典: {attachment}"
    tools = attachment.get("tools", [])

    if function_id == 8:
        # Agent RAG的问答
        wrapper = A2AClientWrapper(session_id=session_id, agent_url=AGENT_URL)
        stream_response = wrapper.generate(user_question=user_question, history=convert_messages, tools=tools, user_id=user_id)
        handle_gpt_stream_response(session_id, user_id, function_id, stream_response)
    else:
        print('不在进行处理这条消息，function_id NOT  : ' + str(function_id))
        return

def callback(ch, method, properties, body):
    """
    mq接收到消息后的回调函数，多线程处理
    """
    try:
        # 接收到mq的消息：转换成dict
        print(f"😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        rabbit_message = json.loads(json.loads(body.decode('utf-8')))
        print(f" [🚚] 从mq接受到消息：{rabbit_message}")
        # 提交任务到线程池
        executor.submit(handle_rabbit_queue_message, rabbit_message)
        # 手动发送消息确认
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"处理消息时出错: {e}")
        # 出错时拒绝消息并重新入队
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


if __name__ == '__main__':
    print("开始监听RabbitMQ队列...")
    start_consumer(callback, auto_ack=False)
