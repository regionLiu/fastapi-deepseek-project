
from pymongo import MongoClient
import certifi
# 启用异步客户端配置（取消注释）

#本地mongo启动 mongdo
# brew services start mongodb-community@8.0
MONGO_URI = "mongodb://127.0.0.1:27017/?directConnection=true&serverSelectionTimeoutMS=2000&appName=mongosh+2.5.0"
DATABASE_NAME = "deepseek" 

# 同步客户端（用于初始化）
uri = MONGO_URI
client = MongoClient(uri)

db = client[DATABASE_NAME]

