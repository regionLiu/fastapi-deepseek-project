# 导包
import os
from pathlib import Path
from typing import Any

import yaml
from jose import JWTError, jwt

from auth import SECRET_KEY, ALGORITHM
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def get_config(config_name:str):
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

def process_env_placeholders(config:Any) ->Any:
    if isinstance(config,dict):
        return {k:process_env_placeholders(v) for k,v in config.items()}
    elif isinstance(config,list):
        return [process_env_placeholders(v) for v in config]
    elif isinstance(config,str):
        if config.startswith("${") and config.endswith("}"):
            env_var = config[2:-1]
            if ":" in env_var:
                env_var, default = env_var.split(":")[1]
            else:
                default = None
            return os.getenv(env_var, default)
        return config