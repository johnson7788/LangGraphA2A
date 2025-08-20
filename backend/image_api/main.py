#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import dotenv
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 从其他模块导入核心功能
from read_image import recognize_image_scene
from read_all_files import read_file_content

# 加载环境变量
dotenv.load_dotenv()

# 初始化 FastAPI 应用
app = FastAPI(
    title="多模态内容识别 API",
    description="提供图片和多种格式文件的识别与分析功能。",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 获取模型配置
TEXT_MODEL = os.getenv("TEXT_MODEL", "qwen-turbo-latest")
ALI_API_KEY = os.getenv("ALI_API_KEY")

# 检查 API Key 是否设置
if not ALI_API_KEY:
    raise ValueError("请在 .env 文件中设置 ALI_API_KEY")


# --- Pydantic 模型定义 ---
class ImageRequest(BaseModel):
    image_url: str = Field(..., description="要识别的图片的公开URL", example="https://www.qcdy.com/uploads/allimg/150414/2-1504A1140.jpg")
    question: str = Field(..., description="关于图片的问题", example="这张化验单说明了什么？")

class FileRequest(BaseModel):
    file_path: str = Field(..., description="要识别的文件的绝对路径", example="/path/to/your/document.docx")
    question: str = Field(..., description="关于文件内容的问题", example="总结一下这个文档的核心内容。")

class AnalysisResponse(BaseModel):
    success: bool = Field(..., description="请求是否成功")
    result: str = Field(..., description="分析结果或错误信息")

# --- API 接口 ---
@app.post("/image", response_model=AnalysisResponse, summary="识别图片内容")
async def handle_recognize_image(request: ImageRequest = Body(...)):
    """
    接收图片URL和问题，返回对图片的分析和解答。
    """
    print(f"收到图片识别请求: url='{request.image_url}', question='{request.question}'")
    success, result = await recognize_image_scene(image_url=request.image_url, question=request.question)
    if not success:
        raise HTTPException(status_code=500, detail=result)
    return AnalysisResponse(success=True, result=result)

@app.post("/file", response_model=AnalysisResponse, summary="识别文件内容")
async def handle_recognize_file(request: FileRequest = Body(...)):
    """
    接收文件路径和问题，提取文件内容，并进行分析和解答。
    """
    print(f"收到文件识别请求: path='{request.file_path}', question='{request.question}'")
    try:
        # 1. 提取文件内容
        if not os.path.exists(request.file_path):
            raise HTTPException(status_code=400, detail=f"文件未找到: {request.file_path}")
        
        file_text_list = read_file_content(request.file_path)
        file_text = "\n".join(file_text_list)
        
        if not file_text or file_text.isspace():
            return AnalysisResponse(success=True, result="文件内容为空或无法提取。")
            
        return AnalysisResponse(success=True, result=result)

    except Exception as e:
        print(f"处理文件识别请求时发生错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- 启动服务 ---
if __name__ == "__main__":
    print("启动 FastAPI 服务...")
    # 使用 uvicorn 启动服务，监听在 0.0.0.0:8000
    # 在生产环境中，建议使用 gunicorn + uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
