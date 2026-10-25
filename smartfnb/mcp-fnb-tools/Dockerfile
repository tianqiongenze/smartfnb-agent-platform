FROM 10.167.2.175:30500/base/python:3.11-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY server.py .
EXPOSE 8000
CMD ["python", "server.py"]
