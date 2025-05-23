from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import models
import api
import uvicorn


app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Stream"],
)

# 挂载路由
app.include_router(api.router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
