FROM alibaba-cloud-linux-3-registry.cn-hangzhou.cr.aliyuncs.com/alinux3/python:3.11.1
LABEL authors="liuzixin"
WORKDIR /fastapi-deepseek-project
COPY . .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]