from fastapi import File, UploadFile
from openai import OpenAI
import json
from fastapi.responses import StreamingResponse
from fastapi import HTTPException

from config.config import get_config, get_prompt
from utils import pre_convert_doc, post_convert_doc



async def request_deepseek(question: str, request_type: str, user_id: str, file: UploadFile = File(None)) -> StreamingResponse:
    """
    向deepseek发送请求
    """
    try:
        depepseek_config = get_config("deepseek")
        api_key = depepseek_config["api_key"]
        base_url = depepseek_config["base_url"]
        model_name = depepseek_config["model"]
        prompt_dict = get_prompt(question, request_type)

        # 如果存在文件且请求类型为excel，则转换文件
        whole_prompt,result_path = await pre_convert_doc(file, request_type,user_id, prompt_dict)

        messages = [{"role": "system", "content": whole_prompt["system_prompt"]},
                    {"role": "user", "content": whole_prompt["user_prompt"]}]

        client = OpenAI(api_key=api_key, base_url=base_url)

        response = client.chat.completions.create(
            model=model_name,
            messages=messages
        )
        result = response.choices[0].message.content

        # 返回文件下载响应
        return await post_convert_doc(result, request_type,user_id,result_path)
    except Exception as e:
        print(f"请求deepseek出错: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

async def request_deepseek_stream(question: str,request_type:str):
    """
    流式请求Deepseek接口
    """
    try:
        deepseek_config = get_apikey()  # 修正变量名拼写错误
        api_key = deepseek_config["api_key"]
        base_url = deepseek_config["base_url"]
        model_name = deepseek_config["model"]
        whole_prompt = get_prompt(question, request_type)

        messages = [{"role": "system", "content": whole_prompt["system_prompt"]},
                    {"role": "user", "content": whole_prompt["user_prompt"]}]

        client = OpenAI(api_key=api_key, base_url=base_url)

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=True,  # 启用流式模式
            temperature=1.5
        )

        # 流式返回数据
        chunked_data = ""
        for chunk in response:
            content = chunk.choices[0].delta.content or ""
            if not content:
                continue
            chunked_data += content
            yield f"data: {json.dumps({'content': chunked_data,'total_token':len(chunked_data)},ensure_ascii=False)}\n\n"
            
    except Exception as e:
        print(f"流式请求失败: {e}")
        yield "data: 'error'"
    finally:
        yield "event: end\ndata: 'error"