import json
import os
from pathlib import Path
from typing import Any, Dict

import yaml
from uvicorn import logging


def get_config(config_name: str):
    """
    从yaml文件中读取apikey
    """
    try:
        config_path = Path(__file__).parent/"config.yml"
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            config = process_env_placeholders(config)
            return config[config_name]
    except FileNotFoundError:
        print("config.yaml文件不存在")
        return RuntimeError("config.yaml文件不存在")


def process_env_placeholders(config: Any) -> Any:
    if isinstance(config, dict):
        return {k: process_env_placeholders(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [process_env_placeholders(v) for v in config]
    elif isinstance(config, str):
        if config.startswith("${") and config.endswith("}"):
            env_var = config[2:-1]
            if ":" in env_var:
                env_var, default = env_var.split(":")[1]
            else:
                default = None
            return os.environ.get(env_var, default)
        return config


class PromptManager:
    def __init__(self):
        self.template_path = Path(__file__).parent/"prompt_templates.json"
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Any]:
        with open(self.template_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def render_system_prompt(self, **kwargs) -> str:
        template = self.templates["system_prompt"]["template"]
        # 合并默认值和传入参数
        variables = {
            **self.templates["system_prompt"]["default_values"], **kwargs}
        return template.format(**variables)

    def render_user_prompt(self, system_kwargs: dict) -> str:
        template = self.templates["user_prompt"]["template"]
        return template.format(user_question=system_kwargs["user_question"], user_character=system_kwargs["user_character"])

    def get_full_prompt(self, system_kwargs) -> Dict[str, str]:
        return {
            "system_prompt": self.render_system_prompt(**{"example_input": system_kwargs["example_input"], "example_output": system_kwargs["example_output"]}),
            "user_prompt": self.render_user_prompt(system_kwargs)
        }


def get_prompt(user_question: str, request_type: str) -> Dict[str, str]:
    try:
        config_path = Path(__file__).parent/"prompt.yml"
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            system_kwargs = {
                "user_question": user_question,
                "user_character": config[request_type]["user_character"],
                "example_output": config[request_type]["example_output"],
                "example_input": config[request_type]["example_input"],
                "1_1_excel": config[request_type]["1_1_excel"],
                "0_1_excel": config[request_type]["0_1_excel"]
            }
        return system_kwargs
    except Exception as e:
        raise Exception("ai提问类型错误:{}".format(e))
