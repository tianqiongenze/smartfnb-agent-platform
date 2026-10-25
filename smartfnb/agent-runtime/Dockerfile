FROM 10.167.2.175:30500/base/python:3.11-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY . .
EXPOSE 8000
# Granian: Rust内核 ASGI 服务器 (ADR-0002, 弃用 uvicorn/FastAPI 路线)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--http", "httptools"]
