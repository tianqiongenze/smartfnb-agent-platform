FROM 10.167.2.175:30500/base/python:3.11-slim
WORKDIR /srv
RUN pip install --no-cache-dir litestar "uvicorn[standard]" pymysql -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--http", "httptools"]
