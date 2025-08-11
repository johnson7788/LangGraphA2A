#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/11 10:34
# @File  : custom_state.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :
from typing import Any, Literal,Dict
from typing import Annotated, NotRequired
from pydantic import BaseModel
from langgraph.prebuilt.chat_agent_executor import AgentState
import operator

class ResponseFormat(BaseModel):
    """按照这个格式回答用户。"""

    status: Literal['completed', 'error'] = 'completed'
    message: str

class CustomState(AgentState):
    # The user_name field in short-term state
    structured_response: NotRequired[ResponseFormat]
    # 搜索的数据库的metadata信息的存储
    search_dbs: Annotated[list[dict], operator.add]