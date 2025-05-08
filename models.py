from pydantic import BaseModel, Field
from beanie import Document
import uuid
from datetime import datetime

# 删除所有SQLAlchemy模型


class User(Document):
    username: str = Field(min_length=3, max_length=50)
    passwoed: str
    user_id: str = Field(default_factory=lambda: f"user-{uuid.uuid4().hex}")
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "users"  # MongoDB集合名称
        indexes = [
            "username",  # 自动创建唯一索引
            "user_id"
        ]
