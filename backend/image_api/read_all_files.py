#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/12 09:00
# @File  : read_all_files.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 读取各种个样的文件

import os
import re
import string
import json
import hashlib
import os
import pickle
import asyncio
from functools import wraps
import tika
from tika import parser as tikaParser
tika_server = r"./bin/tika-server.jar"
assert os.path.exists(tika_server), "tika-server.jar not found"
TIKA_SERVER_JAR = f"file:///{tika_server}"
os.environ['TIKA_SERVER_JAR'] = TIKA_SERVER_JAR
def read_file_content(file_path):
    assert os.path.exists(file_path), f"给定文件不存在: {file_path}"
    tika_jar_path = TIKA_SERVER_JAR.replace('file:///', '')
    assert os.path.exists(tika_jar_path), "tika jar包不存在"
    tika.initVM()
    parsed = tikaParser.from_file(file_path)
    content_text = parsed["content"]
    content = content_text.split("\n")
    return content

if __name__ == '__main__':
    content = read_file_content("/Users/admin/Downloads/多Agent进行PPT生成.docx")
    print(content)