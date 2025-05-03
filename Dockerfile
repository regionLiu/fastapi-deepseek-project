FROM alibaba-cloud-linux-3-registry.cn-hangzhou.cr.aliyuncs.com/alinux3/python
LABEL authors="liuzixin"
WORKDIR /fastapi-deepseek-project
COPY . /app
RUN pip3 install -r --no-cache-dir requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]