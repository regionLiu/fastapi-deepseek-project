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
    token: str

    class Settings:
        name = "users"  # MongoDB集合名称
        indexes = [
            "username",  # 自动创建唯一索引
            "user_id"
        ]


class RequestDocument(Document):
    user_id: str = Field(..., description="用户ID")
    request_type: str = Field(..., description="请求类型")
    request_content: str = Field(..., description="请求内容")
    response_content: str = Field(..., description="响应内容")
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "request_documents"  # MongoDB集合名称
        indexes = [
            "user_id"
        ]
