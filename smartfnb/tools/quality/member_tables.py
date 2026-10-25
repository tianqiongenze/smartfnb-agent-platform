import os
import pymysql
c = pymysql.connect(host=os.getenv("DB_HOST", "tidb.infra.svc.cluster.local"), port=4000,
                    user="root", database="fnb", autocommit=True)
cur = c.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS member_points (
  member_id BIGINT NOT NULL PRIMARY KEY, points INT NOT NULL DEFAULT 0,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)""")
cur.execute("""CREATE TABLE IF NOT EXISTS member_coupons (
  id BIGINT NOT NULL PRIMARY KEY, member_id BIGINT NOT NULL, title VARCHAR(64) NOT NULL,
  amount DECIMAL(8,2) NOT NULL, status ENUM('VALID','USED') NOT NULL DEFAULT 'VALID',
  issued_at DATETIME DEFAULT CURRENT_TIMESTAMP, used_at DATETIME NULL,
  KEY idx_mc_member (member_id, status))""")
print("MEMBER_TABLES_OK")
