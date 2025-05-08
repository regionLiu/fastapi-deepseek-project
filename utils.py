# 导包
import json
import os
from pathlib import Path
import time
from typing import Any

import yaml
from jose import JWTError, jwt
from fastapi.responses import JSONResponse
from starlette.responses import StreamingResponse
from fastapi import UploadFile
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import NamedStyle
import io
import subprocess
import tempfile

from auth import SECRET_KEY, ALGORITHM
from config.config import PromptManager, get_config


async def change_file_type(file: UploadFile, user_id: str, request_type: str) -> str:
    if request_type == "excel":
        # 使用 spell_input_path 生成文件路径
        temp_file_path = spell_input_path(user_id)
        # 如果路径不存在就生成
        if not os.path.exists(get_config("file_path")["base_file_path"]+user_id):
            os.makedirs(get_config("file_path")["base_file_path"]+user_id)
        # 将文件保存到指定位置
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file.read())

        # 读取Excel文件并转换为CSV数据
        df = pd.read_excel(temp_file_path, engine='openpyxl')
        csv_data = df.to_csv(index=False)

        return csv_data
    return None


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def Response(code: int = 200, content: Any = None):
    if isinstance(content, str):
        retsult = {
            "code": code,
            "msg": "success",
            "data": content
        }
        return JSONResponse(retsult)
    elif isinstance(content, dict):
        retsult = {
            "code": code,
            "msg": "success",
            "data": content
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


async def pre_convert_doc(file: UploadFile, request_type: str, user_id: str, prompt_dict: dict) -> str:
    if request_type == "excel":
        result_path = spell_excel_path(user_id)
        if file:
            csv_data = await change_file_type(file, user_id, request_type)
        # 把文件存到指定路径
            input_path = spell_input_path(user_id)
            if csv_data:
                prompt_dict["user_question"] = prompt_dict["user_question"] + \
                    f"以下为转换过的csv数据只是为了让你理解表格的内容\n\n{csv_data}便于传输,原文件是excel,写一个python脚本只能使用pandas和openpyxl,目的是把excel文件进行更改并且代码中原文件路径是{input_path},输出路径是{result_path},生成的代码应该是可以直接执行的不要出现例如'Markdown 代码块标记'之类的东西。且执行成功后会在控制台输出<执行完成>,只需要给脚本其他文字都不要有"
        else:
            prompt_dict["user_question"] = prompt_dict["user_question"] + \
                f"以上为表格的要求,请根据要求生成一个python脚本,写一个python脚本生成这个表格,只能使用pandas和openpyxl,生成的文件路径是{result_path},生成的代码应该是可以直接执行的不要出现例如'Markdown 代码块标记'之类的东西。且执行成功后会在控制台输出<执行完成>,只需要给脚本其他文字都不要有"

    whole_prompt = PromptManager().get_full_prompt(system_kwargs=prompt_dict)
    return whole_prompt, result_path


async def post_convert_doc(result: str, request_type: str, user_id: str, result_path: str) -> str:
    if request_type == "excel":
        # 移除 Markdown 代码块标记
        cleaned_result = result.replace("```python", "").replace("```", "")

        # 打印生成的脚本内容以进行调试
        print("Generated script content:")
        print(cleaned_result)

        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp_script:
            # 确保写入的内容是有效的 Python 代码
            temp_script.write(cleaned_result.encode('utf-8'))
            temp_script_path = temp_script.name

        try:
            # 执行临时脚本
            if not os.path.exists(get_config("file_path")["base_file_path"]+user_id):
                os.makedirs(get_config("file_path")["base_file_path"]+user_id)

            process = subprocess.run(
                ['python3', temp_script_path], capture_output=True, text=True)
            output = process.stdout

            # 检查输出
            if "执行完成" in output:
                print("脚本执行成功")
            else:
                print("脚本执行失败")

        finally:
            # 删除临时脚本
            os.remove(temp_script_path)

        # 返回文件下载链接
        return spell_doc_url("/"+result_path.split('./')[-1])
    return result


def spell_input_path(user_id: str):
    base_file_path = get_config("file_path")["base_file_path"]
    return f"{base_file_path}{user_id}/input-{time.strftime('%Y%m%d%H%M%S')}.xlsx"


def spell_excel_path(user_id: str):
    base_file_path = get_config("file_path")["base_file_path"]
    return f"{base_file_path}{user_id}/result-{time.strftime('%Y%m%d%H%M%S')}.xlsx"


def spell_doc_url(file_path: str):
    base_url = get_config("base_url")["base_url"]
    return f"{base_url}download{file_path}"
