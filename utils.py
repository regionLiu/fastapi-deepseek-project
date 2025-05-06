# 导包
import json
import os
from pathlib import Path
from typing import Any

import yaml
from jose import JWTError, jwt
from fastapi.responses import JSONResponse
from starlette.responses import StreamingResponse

from auth import SECRET_KEY, ALGORITHM
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def Response(code:int=200,content:Any=None):
    if isinstance(content,str):
        retsult = {
            "code":code,
            "msg":"success",
            "data":content
        }
        return JSONResponse(retsult)
    elif isinstance(content,dict):
        retsult = {
            "code":code,
            "msg":"success",
            "data":content
        }
        return JSONResponse(retsult)


def StreamResponse(
        content: Any,
        code: int = 200,
        msg: str = "success",
        media_type: str = "text/event-stream"
):
    async def format_stream():
        async for chunk in content:
            # 调试用：打印原始chunk
            # print(f"Raw chunk: {repr(chunk)}")

            # 严格检测结束事件（考虑各种换行符情况）
            normalized_chunk = chunk.replace("\r", "").strip()
            if normalized_chunk == "event: end\ndata: 'error'":
                yield json.dumps({
                    "code": code,
                    "msg": "completed",
                    "data": None,
                    "status": "completed"
                }, ensure_ascii=False) + "\n\n"
                continue

            # 处理SSE格式的JSON数据
            if chunk.startswith("data: {"):
                try:
                    json_data = json.loads(chunk[6:])  # 移除"data: "前缀
                    yield json.dumps({
                        "code": code,
                        "msg": msg,
                        "data": json_data.get("content", ""),
                        "meta": {
                            "total_token": json_data.get("total_token")
                        }
                    }, ensure_ascii=False) + "\n\n"
                    continue
                except json.JSONDecodeError:
                    pass

            # 处理纯文本数据（非JSON）
            if "\n" not in chunk:  # 简单内容直接返回
                yield json.dumps({
                    "code": code,
                    "msg": msg,
                    "data": chunk
                }, ensure_ascii=False) + "\n\n"

    return StreamingResponse(
        format_stream(),
        media_type=media_type
    )
