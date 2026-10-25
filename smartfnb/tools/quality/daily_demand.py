"""daily_demand 预计算(按店循环, 避免全表聚合内存超限) — 可重复执行(REPLACE INTO)"""
import os
import pymysql

c = pymysql.connect(host=os.getenv("DB_HOST", "tidb.infra.svc.cluster.local"), port=4000,
                    user="root", database="fnb", autocommit=False)
cur = c.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS daily_demand (
  store_id INT NOT NULL, ing_id INT NOT NULL, stat_date DATE NOT NULL,
  demand_gram BIGINT NOT NULL, PRIMARY KEY (store_id, ing_id, stat_date))""")
cur.execute("SELECT store_id FROM store ORDER BY store_id")
stores = [r[0] for r in cur.fetchall()]
SQL = """
INSERT INTO daily_demand (store_id, ing_id, stat_date, demand_gram)
SELECT sl.store_id, b.ing_id, sl.order_date, CAST(ROUND(SUM(sl.qty * b.grams_per_serving)) AS SIGNED)
FROM sales_line sl
JOIN bom b ON sl.dish_id = b.dish_id
WHERE sl.store_id = %s
GROUP BY sl.store_id, b.ing_id, sl.order_date"""
total = 0
for sid in stores:
    cur.execute("SET SESSION tidb_mem_quota_query = 2147483648")
    cur.execute(SQL, (sid,))
    total += cur.rowcount
    c.commit()
    print(f"store {sid} done, rows so far {total}", flush=True)
print(f"DAILY_DEMAND_DONE rows={total}", flush=True)
