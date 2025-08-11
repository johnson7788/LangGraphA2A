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
import dotenv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from mq_handler import start_consumer, MQHandler
from A2Aclient import A2AClientWrapper
dotenv.load_dotenv()


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
            async for chunk in stream_response:
                try:
                    data_type = chunk.get("type")
                    if data_type == "final":
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
                    elif data_type == "data":
                        chunk_data = chunk.get("data", {})
                        tools_data = chunk_data.get("data", [])
                        # 发送给前端的数据，list格式，里面是字典
                        front_data = [tool["front_data"] for tool in tools_data]
                        #工具是调用还是结束了，只需要工具结束了的数据
                        tool_type = chunk_data.get("type")
                        answer_queue_message = {
                            "sessionId": session_id,
                            "userId": user_id,
                            "functionId": function_id,
                            "message": json.dumps(front_data, ensure_ascii=False),
                            "reasoningMessage": "",
                            "type": 5,
                        }
                        print(f"[Info] 发送状态数据完成（type 5)：{answer_queue_message}")
                        # 发送引用数据和参考，即匹配的结果
                        if tool_type == "tool_result":
                            tool_retrieve_data = [one.get("data",{}) for one in tools_data]
                            answer_reference = {
                                "sessionId": session_id,
                                "userId": user_id,
                                "functionId": function_id,
                                "message": json.dumps(tool_retrieve_data, ensure_ascii=False),
                                "reasoningMessage": "",
                                "type": 6,
                            }
                            mq_handler.send_message(answer_reference)
                            print(f"[Info] 发送引用和参考数据完成(type 6)：{answer_reference}")
                    elif data_type == "artifact":
                        print(f"[Info] 收到artifact数据，如果我们设置的Stream，那么这条数据需要忽略：{chunk}")
                        #识别实体
                        artifact_content = chunk["text"]
                        if ENTITY_URL:
                            entities = entity_indentify_extract_match_db(artifact_content)
                            entities_data = entities["data"]
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
    user_question_dict = messages.pop()
    user_question = user_question_dict["content"]
    # attachment = rabbit_message['attachment']
    # link_id = rabbit_message.get('linkId', None)

    if function_id == 1:
        # Agent RAG的问答
        wrapper = A2AClientWrapper(session_id=session_id, agent_url=AGENT_URL)
        stream_response = wrapper.generate(user_question=user_question, history=messages)
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
    start_consumer(callback, auto_ack=False)
