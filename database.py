
from pymongo import MongoClient
import certifi
# 启用异步客户端配置（取消注释）
MONGO_URI = "mongodb+srv://liuzixin0418:lzx990418@deepseek.kfpqcch.mongodb.net/?retryWrites=true&w=majority&appName=deepseek"
DATABASE_NAME = "deepseek" 

# 同步客户端（用于初始化）
uri = MONGO_URI
client = MongoClient(uri,
                     tls=True,
                     tlsCAFile=certifi.where())

db = client[DATABASE_NAME]

