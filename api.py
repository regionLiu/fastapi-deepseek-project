from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from schemas import DP, UserCreate, UserLogin,Token
from database import db  # 修改导入
import models
import auth
import utils
from deepseek import request_deepseek, request_deepseek_stream
from fastapi.responses import StreamingResponse
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/register")
async def register(user: UserCreate):
    existing_user = db.users.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    password = auth.get_password_hash(user.password)
    user_data = {
        "username": user.username,
        "password": password,
        "user_id": auth.generate_user_id()
    }
    created_user = await auth.create_user(user_data)
    return {"message": "用户创建成功"}

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
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/write")
async def write(token: DP):
    payload = utils.verify_token(token.access_token)
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    result_data = await request_deepseek("what")
    return JSONResponse(content=result_data)

@router.post("/write/stream")
async def write_stream(token: DP):
    payload = utils.verify_token(token.access_token)
    if not payload or not payload.get("user_id",""):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return StreamingResponse(
        request_deepseek_stream("what"),  # 替换为实际的问题参数
        media_type="text/event-stream"
    )