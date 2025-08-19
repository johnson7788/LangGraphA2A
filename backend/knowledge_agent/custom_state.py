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

class CustomState(AgentState):
    # The user_name field in short-term state
    # 搜索的数据库的metadata信息的存储
    search_dbs: Annotated[list[dict], operator.add]
    user_id: NotRequired[str|int]