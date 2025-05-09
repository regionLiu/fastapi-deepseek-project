from fastapi import File, UploadFile
from openai import OpenAI
import json
from fastapi.responses import StreamingResponse
from fastapi import HTTPException
import pypandoc

from config.config import PromptManager, get_chat_prompt, get_config, get_excel_prompt, get_mind_summarize_prompt, get_prompt, get_word_prompt
from utils import change_markdown_to_doc, pre_convert_doc, post_convert_doc, spell_doc_url, spell_output_path


async def request_deepseek(question: str, request_type: str, user_id: str, file: UploadFile = File(...)) -> StreamingResponse:
    """
    向deepseek发送请求
    """
    try:
        depepseek_config = get_config("deepseek")
        api_key = depepseek_config["api_key"]
        base_url = depepseek_config["base_url"]
        model_name = depepseek_config["model"]
        if request_type == "excel":
            prompt_dict = get_excel_prompt(question, request_type)
        elif request_type == "word":
            prompt_dict = get_word_prompt(question, request_type)
        elif request_type == "mind_summarize":
            prompt_dict = get_mind_summarize_prompt(question, request_type)

        # 如果存在文件且请求类型为excel，则转换文件
        whole_prompt, result_path = await pre_convert_doc(file, request_type, user_id, prompt_dict)

        messages = [{"role": "system", "content": whole_prompt["system_prompt"]},
                    {"role": "user", "content": whole_prompt["user_prompt"]}]

        client = OpenAI(api_key=api_key, base_url=base_url)
        # 流式选择
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=8000,
            stream=False,
            temperature=float(get_config("deepseek")[
                              "temperature"][request_type]),
            response_format={"type": get_config("deepseek")[
                "response_format"][request_type]}
        )
        result = response.choices[0].message.content
        return post_convert_doc(result, request_type, user_id, result_path)
    except Exception as e:
        print(f"请求deepseek出错: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def request_deepseek_stream(question: str, request_type: str, user_id: str, file: UploadFile = File(None)):
    """
    流式请求Deepseek接口
    """
    try:
        chunked_data = ""
        result_path = ""
        deepseek_config = get_config("deepseek")  # 修正变量名拼写错误
        api_key = deepseek_config["api_key"]
        base_url = deepseek_config["base_url"]
        model_name = deepseek_config["model"]
        if request_type == "word":
            prompt_dict = get_word_prompt(question, request_type)
        elif request_type == "mind_summarize":
            prompt_dict = get_mind_summarize_prompt(question, request_type)
        elif request_type == "chat":
            prompt_dict = get_chat_prompt(question, request_type)

        whole_prompt, result_path = await pre_convert_doc(file, request_type, user_id, prompt_dict)

        messages = [{"role": "system", "content": whole_prompt["system_prompt"]},
                    {"role": "user", "content": whole_prompt["user_prompt"]}]

        client = OpenAI(api_key=api_key, base_url=base_url)

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=True,  # 启用流式模式
            temperature=1.3
        )

        # 流式返回数据

        for chunk in response:
            content = chunk.choices[0].delta.content or ""
            if not content:
                continue
            chunked_data += content
            yield f"data: {json.dumps({'content': chunked_data,'doc_url':'','total_token':len(chunked_data)},ensure_ascii=False)}\n\n"

    except Exception as e:
        print(f"流式请求失败: {e}")
        yield "data: 'error'"
    finally:
        # 处理文档
        if request_type in ["word", "mind_summarize"]:
            doc_url = post_convert_doc(
                chunked_data, request_type, user_id, result_path)
            yield f"data: {json.dumps({'content': chunked_data,'doc_url':doc_url,'total_token':len(chunked_data)},ensure_ascii=False)}\n\n"
