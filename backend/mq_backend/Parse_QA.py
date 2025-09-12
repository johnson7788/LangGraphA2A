#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/20 10:33
# @File  : Parse_QA.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :

import httpx
from typing import Any, Dict, List, Tuple, Optional


class QAParser:
    """
    将 user_question 中的图片/文件条目用远端 API 解析后替换为纯文本条目。
    兼容两种输入结构：
    1) 扁平列表: [
          {"text": "...", "type": "text"},
          {"url": "...", "type": "image"|"file"},
          ...
       ]
    2) Chat 列表: [
          {"role": "user", "content": [
              {"text": "...", "type": "text"},
              {"url": "...", "type": "image"|"file"},
          ]}
       ]
    """
    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        default_image_question: str = "用户上传的图片",
        default_file_question: str = "用户上传的文档",
        headers: Optional[Dict[str, str]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.default_image_question = default_image_question
        self.default_file_question = default_file_question
        self.headers = headers or {"content-type": "application/json"}

    # -----------------------------
    # 公共入口
    # -----------------------------
    def transform_user_question(self, user_question: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        输入：原始 user_question
        输出：将所有图片/文件条目替换为文本后的同构结构
        """
        transformed = []
        for msg in user_question:
            if "content" in msg and isinstance(msg["content"], list):
                out_list, out_content = self._transform_content_list(msg["content"])
                # 保持其他字段（如 role）不变，仅替换 content
                new_msg = dict(msg)
                new_msg["content"] = out_content
                transformed.append(new_msg)
            else:
                # 若该消息不含 content，原样返回
                transformed.append(msg)
        return transformed

    # -----------------------------
    # 结构判断 & 处理
    # -----------------------------
    @staticmethod
    def _looks_like_chat_list(obj: Any) -> bool:
        """
        判断是否为形如 [{"role": "...", "content": [...]}] 的结构
        """
        if isinstance(obj, list) and obj:
            first = obj[0]
            return isinstance(first, dict) and "role" in first and "content" in first
        return False

    def _transform_content_list(self, contents: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
        """
        遍历 content 列表，文本保留；图片/文件调用 API 并替换为文本。
        解析问题（question）优先使用“最近一次出现的上文文本”，否则使用默认问题。

        返回:
            out: List[Dict[str, Any]]，处理后的列表
            all_text: str，所有文本拼接
        """
        out: List[Dict[str, Any]] = []
        last_text_question_hint: Optional[str] = None
        text_accumulator: List[str] = []

        for item in contents:
            # 1) 纯文本：直接保留，并更新“最近文本提示”
            if item.get("type") == "text" and "text" in item:
                out.append(item)
                if isinstance(item["text"], str) and item["text"].strip():
                    last_text_question_hint = item["text"].strip()
                    text_accumulator.append(item["text"].strip())
                continue

            # 2) 图片/文件：调用 API 后替换为文本
            filetype = item.get("type")
            url = item.get("url")

            if filetype in {"image", "file"} and isinstance(url, str) and url:
                try:
                    if filetype == "image":
                        question = last_text_question_hint or self.default_image_question
                        parsed = self._call_image_api(url, question)
                        text = parsed if parsed else "【解析失败】图片识别接口未返回结果。"
                    else:
                        question = last_text_question_hint or self.default_file_question
                        parsed = self._call_file_api(url, question)
                        text = parsed if parsed else "【解析失败】文件解析接口未返回结果。"

                    out.append({"type": "text", "text": text})
                    text_accumulator.append(text)

                    # 更新提示
                    last_text_question_hint = text if text.strip() else last_text_question_hint
                except Exception as e:
                    error_text = f"【解析异常】{e}"
                    out.append({"type": "text", "text": error_text})
                    text_accumulator.append(error_text)
                continue

            # 3) 未识别的条目：转存为文本提示，避免丢数据
            unknown_text = f"【未处理的条目】{item}"
            out.append({"type": "text", "text": unknown_text})
            text_accumulator.append(unknown_text)

        all_text = "\n".join(text_accumulator)
        return out, all_text

    # -----------------------------
    # API 调用
    # -----------------------------
    def _call_file_api(self, file_path: str, question: str) -> str:
        """
        POST {base_url}/file
        data = {"file_path": file_path, "question": question}
        期望响应：{"success": true, "result": "..."}
        """
        url = f"{self.base_url}/file"
        data = {"file_path": file_path, "question": question}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=data, headers=self.headers)
            resp.raise_for_status()
            payload = resp.json()
        if not isinstance(payload, dict):
            raise ValueError("文件解析接口返回非 JSON 对象。")
        if not payload.get("success", False):
            # 尽量把服务端的错误信息原样呈现
            msg = payload.get("message") or payload.get("error") or "服务器返回 success=false"
            raise RuntimeError(f"文件解析失败：{msg}")
        result = payload.get("result")
        if not isinstance(result, str):
            raise ValueError("文件解析接口缺少 result 字段或类型不为字符串。")
        return result

    def _call_image_api(self, image_url: str, question: str) -> str:
        """
        POST {base_url}/image
        data = {"image_url": image_url, "question": question}
        期望响应：{"success": true, "result": "..."}
        """
        url = f"{self.base_url}/image"
        data = {"image_url": image_url, "question": question}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=data, headers=self.headers)
            resp.raise_for_status()
            payload = resp.json()
        if not isinstance(payload, dict):
            raise ValueError("图片识别接口返回非 JSON 对象。")
        if not payload.get("success", False):
            msg = payload.get("message") or payload.get("error") or "服务器返回 success=false"
            raise RuntimeError(f"图片识别失败：{msg}")
        result = payload.get("result")
        if not isinstance(result, str):
            raise ValueError("图片识别接口缺少 result 字段或类型不为字符串。")
        return result


if __name__ == "__main__":
    # 1) 扁平结构
    flat_user_question = [
        {
            "role": "user",
            "content": [
                {"text": "您好，看一下图片是什么内容", "type": "text"},
                {"url": "https://wallpapercave.com/wp/wp8788340.jpg", "type": "image"},
            ]
        }
    ]

    # 2) Chat 结构
    chat_user_question = [
        {
            "role": "user",
            "content": [
                {"text": "您好，文件里说了什么内容", "type": "text"},
                {"url": "https://rahacollege.co.in/learning/38.pdf", "type": "file"},
            ]
        },
        {
            "role": "assistant",
            "content": "这个文件说了很多"
        },
        {
            "role": "user",
            "content": "翻译成中文"
        }
    ]

    parser_instance = QAParser(
        base_url="http://127.0.0.1:9700",   # ← 替换为你的后端 base_url
        timeout=30.0,
    )

    # 实际调用
    out_content = parser_instance.transform_user_question(flat_user_question)
    print(out_content)
    out_content = parser_instance.transform_user_question(chat_user_question)
    print(out_content)
