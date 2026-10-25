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
    for stmt in [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]:
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
