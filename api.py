from typing import Union
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Cookie
from fastapi.responses import FileResponse, JSONResponse, Response as FastAPIResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from config.config import get_config
from crud_database import crud_userfile_list, insert_request_document, update_token
from schemas import DP, UserCreate, UserLogin, Token
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
        return Response(code=400, content="用户名已存在")

    password = auth.get_password_hash(user.password)
    user_data = {
        "username": user.username,
        "password": password,
        "user_id": auth.generate_user_id()
    }
    await auth.create_user(user_data)
    return Response(code=200, content="注册成功")


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await auth.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(
        data={"sub": user["username"], "user_id": user["user_id"]})
    token_status = update_token(user["user_id"], access_token)
    if token_status:
        return Response(code=200, content={"access_token": access_token, "token_type": "bearer"})
    else:
        return Response(code=401, content="Failed to update token")


@router.post("/ai_chat")
async def write(
    text: str = Form(...),
    request_type: str = Form(...),
    access_token: str = Form(...),
    file: Union[UploadFile, None] = File(None)
):
    payload = verify_token(access_token)
    if not payload or not payload.get("user_id", ""):
        return Response(code=401, content="Invalid token or token is expired")
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    result_data = await request_deepseek(text, request_type, user_id, file)
    await insert_request_document(user_id=user_id, request_type=request_type, request_content=text, response_content=result_data)
    return FastAPIResponse(
        content=Response(content=result_data).body,
        status_code=200,
        headers={"X-Stream": "false"},
        media_type="application/json"
    )


@router.post("/ai_chat/stream")
async def write_stream(
    text: str = Form(...),
    request_type: str = Form(...),
    access_token: str = Form(...),
    file: Union[UploadFile, None] = File(None)
):
    payload = verify_token(access_token)
    if not payload or not payload.get("user_id", ""):
        return Response(code=401, content="Invalid token")
    if request_type in ["excel"] or file:
        resp = await write(text, request_type, access_token, file)
        resp.headers["X-Stream"] = "false"
        return resp
    else:
        stream_resp = StreamResponse(
            request_deepseek_stream(
                text, request_type, payload.get("user_id"), file),
            media_type="text/event-stream"
        )
        stream_resp.headers["X-Stream"] = "true"
        return stream_resp


@router.get("/download/user_file/{file_path:path}")
async def download_file(file_path: str, access_token: str = Cookie(None)):
    # 校验token
    payload = verify_token(access_token)
    if not payload or not payload.get("user_id", ""):
        raise HTTPException(status_code=401, detail="无效的token")
    base_file_path = get_config("file_path")["base_file_path"]
    file_location = f"{base_file_path}{file_path}"
    if not os.path.exists(file_location):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_location, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=file_path)


@router.get("user_file/list/{token}")
async def get_user_file_list(token: str):
    payload = verify_token(token)
    if not payload or not payload.get("user_id", ""):
        return Response(code=401, content="Invalid token")
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_file_list = await crud_userfile_list(user_id)
    return Response(code=200, content=user_file_list)
