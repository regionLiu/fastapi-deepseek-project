# 导包
import json
import os
from pathlib import Path
import time
from typing import Any

import docx
import pypandoc
import yaml
from jose import JWTError, jwt
from fastapi.responses import JSONResponse
from starlette.responses import StreamingResponse
from fastapi import File, UploadFile
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import NamedStyle
import io
import subprocess
import tempfile

from auth import SECRET_KEY, ALGORITHM
from config.config import PromptManager, get_config, get_prompt
from crud_database import verify_database_token


async def change_file_type(file: UploadFile, user_id: str, request_type: str) -> str:
    temp_file_path = spell_input_path(user_id)

    try:
        # 关键点：一次性读取流内容并保存到内存
        contents = await file.read()

        if request_type == "excel":
            temp_file_path += ".xlsx"
            base_path = os.path.join(get_config("file_path")[
                                     "base_file_path"], user_id)
            os.makedirs(base_path, exist_ok=True)

            # 直接使用内存中的内容写入文件
            with open(temp_file_path, "wb") as buffer:
                buffer.write(contents)

            df = pd.read_excel(temp_file_path, engine='openpyxl')
            csv_data = df.to_csv(index=False)
            return csv_data, temp_file_path

        elif request_type in ["mind_summarize", "word"]:
            temp_file_path += ".docx"

            # 直接使用内存中的内容写入文件
            with open(temp_file_path, "wb") as buffer:
                buffer.write(contents)

            return word_to_markdown_string(temp_file_path)

    except Exception as e:
        # 处理异常
        raise RuntimeError(f"文件处理失败: {str(e)}")


def word_to_markdown_string(input_file):
    # 确认 input_file 是有效的 Word 文档路径
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file {input_file} does not exist.")

    # 创建一个临时文件来存储 markdown 输出
    with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as tmpfile:
        pypandoc.convert_file(
            input_file,
            'md',
            format='docx',
            outputfile=tmpfile.name,  # 输出到临时文件
            extra_args=['--wrap=none']  # 不自动换行
        )
        tmpfile_path = tmpfile.name

    # 读取临时文件内容
    with open(tmpfile_path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()

    # 删除临时文件
    os.remove(tmpfile_path)

    return markdown_content


def verify_token(token: str):
    try:
        user = verify_database_token(token)
        if not user:
            return None
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
        return JSONResponse(status_code=code, content=retsult)
    elif isinstance(content, dict) or isinstance(content, list):
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
            # normalized_chunk = chunk.replace("\r", "").strip()
            # if normalized_chunk == "event: end\ndata: 'error'":
            #     yield json.dumps({
            #         "code": code,
            #         "msg": "completed",
            #         "data": None,
            #         "status": "completed"
            #     }, ensure_ascii=False) + "\n\n"
            #     continue

            # 处理SSE格式的JSON数据
            if chunk.startswith("data: {"):
                try:
                    json_data = json.loads(chunk[6:])  # 移除"data: "前缀
                    yield json.dumps({
                        "code": code,
                        "msg": msg,
                        "data": json_data.get("content", ""),
                        "meta": {
                            "total_token": json_data.get("total_token"),
                            "doc_url": json_data.get("doc_url")
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
    result_path = spell_output_path(user_id)
    if request_type == "excel":
        result_path = result_path+".xlsx"
        if file:
            csv_data, input_path = await change_file_type(file, user_id, request_type)
        # 把文件存到指定路径
            if csv_data:
                prompt_dict["user_question"] = prompt_dict["user_question"] + \
                    prompt_dict["1_1_excel"].format(
                        csv_data, input_path, result_path)
        else:
            prompt_dict["user_question"] = prompt_dict["user_question"] + \
                prompt_dict["0_1_excel"].format(result_path)
    elif request_type in ["mind_summarize", "word"]:
        result_path = result_path+".docx"
        if file:
            doc_data = await change_file_type(file, user_id, request_type)
            if doc_data:
                prompt_dict["user_question"] = prompt_dict["user_question"] + \
                    prompt_dict["1_1_"+request_type] + f"\n{doc_data}"
    whole_prompt = PromptManager().get_full_prompt(system_kwargs=prompt_dict)
    return whole_prompt, result_path


def post_convert_doc(result: str, request_type: str, user_id: str, result_path: str) -> str:
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
            return spell_doc_url("/"+result_path.split('./')[-1])
    elif request_type in ["mind_summarize", "word"]:
        # 返回文件下载链接
        return change_markdown_to_doc(user_id, result, result_path)
    return result


def spell_input_path(user_id: str):
    base_file_path = get_config("file_path")["base_file_path"]
    return f"{base_file_path}{user_id}/input-{time.strftime('%Y%m%d%H%M%S')}"


def spell_output_path(user_id: str):
    base_file_path = get_config("file_path")["base_file_path"]
    return f"{base_file_path}{user_id}/result-{time.strftime('%Y%m%d%H%M%S')}"


def spell_doc_url(file_path: str):
    base_url = get_config("base_url")["base_url"]
    return f"{base_url}download{file_path}"


def change_markdown_to_doc(user_id: str, result: str, doc_path: str):
    # 将markdown转换为docx
    pypandoc.convert_text(
        result, 'docx', format='markdown', outputfile=doc_path
    )

    return spell_doc_url("/" + doc_path.split('./')[-1])


async def read_upload_file(file: UploadFile):
    if file.file.closed:
        raise ValueError("文件流已关闭")
    await file.seek(0)
    return await file.read()
