from pymongo import MongoClient
import certifi
import yaml
import os
from config.config import get_config
# 读取配置文件

config = get_config("mongo")

# 从配置文件获取MongoDB配置
MONGO_URI = config["mongo_uri"]
DATABASE_NAME = "deepseek"

# 同步客户端（用于初始化）
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]