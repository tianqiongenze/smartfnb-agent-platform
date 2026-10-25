FROM 10.167.2.175:30500/base/python:3.11-slim
RUN pip install --no-cache-dir "numpy<2" pymysql redis aiohttp pymilvus \
    -i https://pypi.tuna.tsinghua.edu.cn/simple
WORKDIR /app
COPY data-gen/ /app/
COPY redis-warmup/ /app/
COPY llm-bench/ /app/
COPY quality/ /app/
COPY e2e_check.py /app/
COPY loadgen/ /app/
COPY semantic_warmup.py /app/
COPY test_quality_rules.py /app/
CMD ["python", "run_sql.py", "001_schema.sql"]
