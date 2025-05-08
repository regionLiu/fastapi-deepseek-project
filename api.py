from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from config.config import get_config
from schemas import DP, UserCreate, UserLogin,Token
from database import db  # 修改导入
import models
import auth
from utils import Response, verify_token, StreamResponse
from deepseek import request_deepseek, request_deepseek_stream
from fastapi.responses import StreamingResponse
import json
import os

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/register")
async def register(user: UserCreate):
    existing_user = db.users.find_one({"username": user.username})
    if existing_user:
        return Response(code=400,content="用户名已存在")
    
    password = auth.get_password_hash(user.password)
    user_data = {
        "username": user.username,
        "password": password,
        "user_id": auth.generate_user_id()
    }
    await auth.create_user(user_data)
    return Response(code=200,content="注册成功")

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await auth.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user["username"],"user_id":user["user_id"]})
    return Response(code=200,content={"access_token": access_token, "token_type": "bearer"})


@router.post("/ai_chat")
async def write(user_data: DP = Depends(), file: UploadFile = File(None)):
    # 验证 token
    payload = verify_token(user_data.access_token)
    if not payload or not payload.get("user_id",""):
        return Response(code=401,content="Invalid token")
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 调用 deepseek
    result_data = await request_deepseek(user_data.text, user_data.request_type, user_id, file)
    return Response(content=result_data)

@router.post("/ai_chat/stream")
async def write_stream(token: DP):
    payload = verify_token(token.access_token)
    if not payload or not payload.get("user_id",""):
        return Response(code=401,content="Invalid token")

    # 使用方式
    return StreamResponse(
        request_deepseek_stream(token.text, token.request_type)
    )

@router.get("/download/user_file/{file_path:path}")
async def download_file(file_path: str):
    base_file_path = get_config("file_path")["base_file_path"]
    file_location = f"{base_file_path}{file_path}"
    if not os.path.exists(file_location):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_location, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=file_path)