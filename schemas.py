from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str 

class UserLogin(UserBase):
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class DP(Token):
    text: str
    request_type:str