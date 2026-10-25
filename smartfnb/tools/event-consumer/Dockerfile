FROM 10.167.2.175:30500/base/python:3.11-slim
RUN pip install --no-cache-dir pulsar-client==3.6.1 pymysql redis -i https://pypi.tuna.tsinghua.edu.cn/simple
WORKDIR /app
COPY consumer.py .
CMD ["python", "consumer.py"]
