from openai import OpenAI
import json

from config.config import get_config, get_prompt


def get_apikey():
    """
    从yaml文件中读取apikey
    """
    try:
        config = get_config("deepseek")
        return config
    except FileNotFoundError:
        print("apikey.yaml文件不存在")
        return RuntimeError("apikey.yaml文件不存在")

async def request_deepseek(question: str, request_type:str):
    """
    向deepseek发送请求
    """
    try:
        depepseek_config = get_apikey()
        api_key = depepseek_config["api_key"]
        base_url = depepseek_config["base_url"]

        whole_prompt = get_prompt(question,request_type)

        messages = [{"role": "system", "content": whole_prompt["system_prompt"]},
                    {"role": "user", "content": whole_prompt["user_prompt"]}]

        client = OpenAI(api_key=api_key, base_url=base_url)

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages
        )
        result = response.choices[0].message.content
        return result
    except Exception as e:
        print(f"请求deepseek出错: {e}")

async def request_deepseek_stream(question: str,request_type:str):
    """
    流式请求Deepseek接口
    """
    try:
        deepseek_config = get_apikey()  # 修正变量名拼写错误
        api_key = deepseek_config["api_key"]
        base_url = deepseek_config["base_url"]

        whole_prompt = get_prompt(question, request_type)

        messages = [{"role": "system", "content": whole_prompt["system_prompt"]},
                    {"role": "user", "content": whole_prompt["user_prompt"]}]

        client = OpenAI(api_key=api_key, base_url=base_url)

        response = client.chat.completions.create(
            model="deepseek-chat",
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