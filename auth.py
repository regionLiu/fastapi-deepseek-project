from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from models import User
import os
import uuid
from database import db  # 导入数据库连接

# 安全配置
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, password):
    return pwd_context.verify(plain_password, password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def authenticate_user(username: str, password: str):
    # 添加await等待查询结果
    user = db.users.find_one({"username": username})
    if not user or not verify_password(password, user["password"]):
        return False
    return user  # 直接返回完整用户对象

# 使用示例（假设在路由中）：
# user_data = await authenticate_user("test_user", "password123")
# username = user_data["username"]
# user_id = user_data["user_id"]

async def create_user(user_data: dict):
    try:
        # 添加await等待插入操作
        result = await db.users.insert_one(user_data)
        # 返回包含完整字段的新建用户
        return await db.users.find_one({"_id": result.inserted_id})
    except Exception as e:
        print(f"用户创建失败: {e}")
        return None


def generate_user_id():
    # 生成一个唯一的用户ID
    return "user-" + str(uuid.uuid4())
