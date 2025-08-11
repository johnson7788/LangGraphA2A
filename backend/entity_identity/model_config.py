#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/6/10 15:14
# @File  : model_config.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :
import os
import logging
from enum import Enum
from typing import Optional, Union
from openai import OpenAI as OpenAIClient
import google.generativeai as genai  #google-generativeai
from openai import AzureOpenAI
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class LLMType(Enum):
    # 模型类型
    GLM = "glm"
    OPENAI = "openai"
    AZURE = "azureOpenai"
    GEMINI = "gemini"
    AZUREDS = "azureDeepSeek"
    AZURE4 = "gpt-4o"
    DEEPSEEK = "deepseek"

class LLMClient:
    def __init__(
            self,
            llm_type: Union[LLMType, str],
            **kwargs
    ):
        """
        多模型客户端初始化
        :param llm_type: 模型类型，支持GLM/OPENAI/AZURE/GEMINI
        :param api_key: 对应平台的API密钥
        :param base_url: API基础地址（GLM/OPENAI/Azure需要）
        :param model: 使用的模型名称
        """
        self.llm_type = LLMType(llm_type) if isinstance(llm_type, str) else llm_type
        self.model = None
        if self.llm_type == LLMType.GLM:
            self.model = os.environ["GLM_MODEL"]
            self.client = OpenAIClient(api_key=os.environ["GLM_KEY"], base_url=os.environ["GLM_BASEURL"])
        elif self.llm_type == LLMType.OPENAI:
            self.model = os.environ["OPENAI_MODEL"]
            self.client = OpenAIClient(api_key=os.environ["OPENAI_API_KEY"], base_url=os.environ["OPENAI_BASEURL"])
        elif self.llm_type == LLMType.AZURE or self.llm_type == LLMType.AZURE4:
            self.model = os.environ["AZURE_OPENAI_API_DEPLOYMENT"]
            self.client = AzureOpenAI(
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
                api_version=os.environ["AZURE_OPENAI_API_VERSION"],
                azure_endpoint=os.environ["AZURE_OPENAI_API_ENDPOINT"],
                azure_deployment=os.environ["AZURE_OPENAI_API_DEPLOYMENT"],
            )
        elif self.llm_type == LLMType.GEMINI:
            genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
            self.client = genai.GenerativeModel(model_name=os.environ["GOOGLE_MODEL"])
        elif self.llm_type == LLMType.DEEPSEEK:
            self.model = os.environ["DEEPSEEK_MODEL"]
            api_key = os.environ["DEEPSEEK_API_KEY"]
            self.client = OpenAIClient(api_key=api_key,base_url="https://api.deepseek.com")
        else:
            raise NotImplementedError("暂不支持的模型类型")

    def openai_compatible_raw_message(self, messages, **generate_args):
        logging.info(f"使用接口openai_compatible_raw_message: {messages}")
        response = self.client.chat.completions.create(
            messages=messages,
            model=self.model,
            **generate_args
        )
        output = response.choices[0].message.content
        logging.info(f"openai_compatible_raw_message的输出是: {output}")
        return output
    def azure_deepseek(self, messages, **generate_args):
        logging.info(f"使用接口azure_deepseek: {messages}")
        payload = {
            "messages": messages,
            "max_tokens": 2048
        }
        response = self.client.complete(payload)
        output = response.choices[0].message.content
        logging.info(f"azure_deepseek的输出是: {output}")
        return output
    def gemini_raw_prompt(self, prompt: str, **generate_args) -> str:
        logging.info(f"使用接口gemini_raw_prompt: {prompt}")
        response = self.client.generate_content(prompt, **generate_args)
        output = response.text
        logging.info(f"gemini_raw_prompt的输出是: {output}")
        return output
    def run_inference(self, prompt: str=None, messages:list=None, **generate_args) -> str:
        """
        统一执行方法
        :param prompt: 输入提示词， prompt和messages应该二选一
        :param messages: 消息
        :param generate_args: 生成参数（temperature等）
        :return: 模型生成的文本
        """
        try:
            logging.info(f"使用接口run_inference: {prompt}")
            assert prompt or messages, "prompt和messages应该二选一"
            if prompt:
                messages = [{"role": "user", "content": prompt}]
            if self.llm_type in [LLMType.GLM, LLMType.OPENAI, LLMType.AZURE,LLMType.AZURE4, LLMType.DEEPSEEK]:
                output = self.openai_compatible_raw_message(messages, **generate_args)
            elif self.llm_type == LLMType.AZUREDS:
                output = self.azure_deepseek(messages, **generate_args)
            elif self.llm_type == LLMType.GEMINI:
                output = self.gemini_raw_prompt(prompt, **generate_args)
            else:
                raise NotImplementedError(f"暂不支持的模型类型, {self.llm_type}")
            logging.info(f"run_inference的输出是: {output}")
            output = output.strip() #去掉空行
            return True, output
        except Exception as e:
            logging.error(f"run_inference,模型调用失败: {str(e)}")
            return False, f"模型调用失败: {str(e)}"


if __name__ == '__main__':
    messages = [{'role': 'user', 'content':'你好'}]
    ds_client = LLMClient(llm_type=LLMType.DEEPSEEK)
    result, content = ds_client.run_inference(messages=messages)
    print(result, content)