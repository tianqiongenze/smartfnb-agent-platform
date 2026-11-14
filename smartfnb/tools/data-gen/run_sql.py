#!/usr/bin/env python3
"""通用SQL执行器: run_sql.py 001_schema.sql 004_views.sql ..."""
import sys, os
import pymysql

c = pymysql.connect(host=os.getenv("DB_HOST", "tidb.infra.svc.cluster.local"),
                    port=4000, user="root", charset="utf8mb4", autocommit=True)
cur = c.cursor()
for f in sys.argv[1:]:
    print(f"=== applying {f} ===", flush=True)
    sql = open(f, encoding="utf-8").read()
    for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
        # [V4-OPT][O1修复] 剥离整行注释后再判空: O1 重建的 001_schema.sql 在
        # CREATE DATABASE / CREATE TABLE 前有节注释, 原实现按 chunk 首行是否
        # 以 -- 开头整块跳过, 导致建库/建表语句被漏掉(db-init 报 Unknown
        # database 'fnb')。整行注释剥离对 MySQL 解析无影响, 行内注释保留。
        lines = [l for l in stmt.splitlines() if not l.strip().startswith("--")]
        stmt = "\n".join(lines).strip()
        if not stmt:
            continue
        try:
            cur.execute(stmt)
        except Exception as e:
            if "already exists" in str(e).lower() or "Duplicate" in str(e):
                print(f"  skip (exists): {e}")
            else:
                raise
    print(f"=== {f} OK ===", flush=True)

# 汇报行数(数据质量报告素材)
cur.execute("""SELECT table_name, table_rows FROM information_schema.tables
               WHERE table_schema='fnb' ORDER BY table_name""")
for r in cur.fetchall():
    print(f"  {r[0]}: ~{r[1]:,}")
c.close()
