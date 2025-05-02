from openai import OpenAI, api_key
import yaml
from pathlib import Path
import json
def get_apikey():
    """
    从yaml文件中读取apikey
    """
    try:
        config_path = Path(__file__).parent/"config.yml"
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            return config["deepseek"]
    except FileNotFoundError:
        print("apikey.yaml文件不存在")
        return RuntimeError("apikey.yaml文件不存在")

async def request_deepseek(question: str):
    """
    向deepseek发送请求
    """
    try:
        depepseek_config = get_apikey()
        api_key = depepseek_config["api_key"]
        base_url = depepseek_config["base_url"]
        system_prompt = """
                你是一个专业的文章撰写助手。你将根据用户的要求，输出一篇文章。
                请根据用户的要求先写出提纲，再输出文章以及文本字数。同时将输出格式调整为一个JSON，分别是 outline、content、total_num

                EXAMPLE INPUT: 
                写一个100字的文章概括一下最近党的会议精神

                EXAMPLE JSON OUTPUT:
                {
                    "content": "最近我国。。。。。。",
                    "outline": "整篇文章大纲为。。。",
                    "total_num": 100
                }
                """

        user_prompt = f"以一名认真刻苦的公务员的视角，{question}"

        messages = [{"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}]

        client = OpenAI(api_key=api_key, base_url=base_url)

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            response_format={
                'type': 'json_object'
            }
        )
        json_response = json.loads(response.choices[0].message.content)
        return json_response
    except Exception as e:
        print(f"请求deepseek出错: {e}")

async def request_deepseek_stream(question: str):
    """
    流式请求Deepseek接口
    """
    try:
        deepseek_config = get_apikey()  # 修正变量名拼写错误
        api_key = deepseek_config["api_key"]
        base_url = deepseek_config["base_url"]
        
        system_prompt = """
                你是一个专业的文章撰写助手。你将根据用户的要求，输出一篇文章。
                请根据用户的要求先写出提纲，再输出文章以及文本字数。

                EXAMPLE INPUT: 
                写一个100字的文章概括一下最近党的会议精神

                EXAMPLE JSON OUTPUT:
                "这是一个。。。。"
                """

        user_prompt = f"以一名认真刻苦的公务员的视角，{question}"

        messages = [{"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}]


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