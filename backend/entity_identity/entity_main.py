#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/6/17 09:16
# @File  : entity_main.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 识别药品和疾病的实体
import os
import logging
logfile = "entity.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(module)s - %(funcName)s - %(message)s",
    handlers=[
        logging.FileHandler(logfile, mode='a+', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
import json
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
import random
from pydantic import BaseModel
from model_config import LLMType, LLMClient
import uvicorn

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EntityInterface():
    def __init__(self):
        """
        Args:
        1. 识别给定句子的疾病和药品。
        2. 需要读取drugs_info和disease_data库，搜索数据库信息，并返回
        """
        self.db = "online"
        self.prompt = """
你是一个医学信息抽取助手，请从下面的文本中提取出所有提到的疾病和药品实体。
请返回以下JSON格式：
```json
{{
  "疾病": [疾病1, 疾病2, ...],
  "药品": [药品1, 药品2, ...]
}}
```
只返回提取结果，不要解释。
以下是输入文本：
{content}
"""
        self.model_client = LLMClient(llm_type=LLMType.DEEPSEEK)
        data = self.cache_database()
        self.table_data = self.table_data_convert(data)

    def table_data_convert(self, data):
        """
        self.table_data 转换成数据库格式
        """
        table_data = {}
        for table_name, tb_data in data.items():
            one_table_name_data = {}
            for one_data in tb_data:
                if table_name == "disease":
                    one_table_name_data[one_data["disease_name"]] = one_data
                elif table_name == "drugs_info":
                    one_table_name_data[one_data["med_name"]] = one_data
                else:
                    raise Exception(f"不支持的表名: {table_name},请设置缓存的表名称")
            table_data[table_name] = one_table_name_data
        return table_data
    def cache_database(self):
        """
        因为数据查询太慢了，我最好把数据缓存下来放到本地
        如果不存在缓存文件，那么获取并缓存，如果存在，那么直接使用
        disease和drugs_info
        """
        cache_file = "cache.json"
        table_fields = {
            "disease": ["id", "disease_name","overview"],
            "drugs_info": ["id","drug_id","med_name","component"]
        }
        # 如果缓存文件不存在，就从数据库取数据并写入本地 sqlite 缓存
        if not os.path.exists(cache_file):
            print("数据库缓存文件不存在，开始从数据库查询...")
            # 查询每个库
            data = {}
            for table_name, fields in table_fields.items():
                query = f"SELECT {','.join(fields)} FROM {table_name}"
                assert "需要编写查询数据的接口"
                # data[table_name] = query_res
            print("缓存完毕。")
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        else:
            print("缓存文件已存在，直接使用本地数据。")
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        return data

    def extract_entities_from_text(self, content):
        """
        识别药品和疾病
        content： 文本内容
        """
        prompt = self.prompt.format(content=content.strip())
        max_retries = 5
        retries = 0
        all_errors = []
        error_messages = ""
        status = True
        json_answer = {"疾病": [], "药品": []}
        while retries < max_retries:
            try:
                if error_messages and retries % 2 == 1:  # 奇数次的时候，加上错误日志
                    prompt = f"{prompt} \n{error_messages}"
                _, final_output = self.model_client.run_inference(prompt=prompt)
                if final_output.startswith("```json"):
                    final_output = final_output[8:-3]
                try:
                    json.loads(final_output)
                except Exception as e:
                    raise Exception(f"输出的格式不是JSON格式,报错: {e}, 模型输出结果是: {final_output}")
                json_answer = json.loads(final_output)
                assert "疾病" in json_answer, "注意，请必须在结果中包含 疾病 字段"
                assert "药品" in json_answer, "注意，请必须在结果中包含 药品 字段"
                # 检查疾病和药品是否是list 格式
                assert isinstance(json_answer["疾病"], list), "注意，请必须在结果中包含 疾病 字段，并且是list 格式"
                assert isinstance(json_answer["药品"], list), "注意，请必须在结果中包含 药品 字段，并且是list 格式"
                # 跳出循环
                break
            except Exception as e:
                retries += 1
                logging.error(f"识别药品和疾病出错，错误信息是: {e}，进行第{retries}次重试")
                error_messages = f"Your last response was incorrect because {e}"
                all_errors.append(f"{e}")
                status = False
        return status, json_answer

    def query_disease_and_drugs(self, disease_names:list[str], drug_names:list[str]) -> dict:
        """
        根据疾病名称和药品名称查询数据库，精确查询，查询结构返回给前端
        # 查询中文的疾病库和药品库
        drugs_info：药品库
        disease:疾病库
        """
        results = {
            "diseases": [],
            "drugs": []
        }

        # 查询疾病库
        if disease_names:
            for one_disease in disease_names:
                one_disease = one_disease.strip()
                one_disease_info = self.table_data["disease"].get(one_disease, {})
                if one_disease_info:
                    # 匹配的疾病名称
                    one_disease_info["match_word"] = one_disease
                    results["diseases"].append(one_disease_info)
                else:
                    logging.warning(f"疾病实体在数据库中未找到信息，请检查：{one_disease} ")
        # 查询药品库
        if drug_names:
            for one_drug in drug_names:
                one_drug = one_drug.strip()
                one_drug_info = self.table_data["drugs_info"].get(one_drug, {})
                if one_drug_info:
                    # 匹配的药品名称
                    one_drug_info["match_word"] = one_drug
                    results["drugs"].append(one_drug_info)
                else:
                    logging.warning(f"药品实体在数据库中未找到信息，请检查：{one_drug}")
        return True, results

    def extract_and_query_disease(self, content, match_db=False):
        """
        实体识别并进行疾病和药品的匹配
        """
        status, json_answer = self.extract_entities_from_text(content)
        if match_db:
            status, match_result = self.query_disease_and_drugs(json_answer["疾病"], json_answer["药品"])
            return status, match_result
        else:
            return status, json_answer
class EntityQuery(BaseModel):
    # 要识别的内容
    content: str
    # 是否要进行数据库匹配
    match_db: bool = False

class DrugDiseaseQuery(BaseModel):
    # 要识别的内容
    disease_names: list[str]
    # 是否要进行数据库匹配
    drug_names: list[str]

@app.post("/api/match_drug_disease")
async def match_drug_disease_api(drug_disease_query: DrugDiseaseQuery):
    # 返回准备好的数据
    logging.info(f"match_drug_disease 接受到请求参数是: {drug_disease_query}")
    status, data = entity_instance.query_disease_and_drugs(disease_names=drug_disease_query.disease_names, drug_names=drug_disease_query.drug_names)
    if not status:
        result = {"code": 4001, "msg": f"发生错误: {data}", "data": {}}
    else:
        result = {"code": 0, "msg": "success", "data": data}
    return result
@app.post("/api/entity_indentify")
async def entity_indentify_api(query_data: EntityQuery):
    # 返回准备好的数据
    logging.info(f"entity_indentify 接受到请求参数是: {query_data}")
    status, data = entity_instance.extract_and_query_disease(content=query_data.content, match_db=query_data.match_db)
    if not status:
        result = {"code": 4001, "msg": f"发生错误: {data}", "data": {}}
    else:
        result = {"code": 0, "msg": "success", "data": data}
    return result
@app.api_route("/ping", methods=["GET", "POST"])
async def root(request: Request):
    return "Pong"

entity_instance = EntityInterface()

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=6200)