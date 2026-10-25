import os
import pymysql
c = pymysql.connect(host=os.getenv("DB_HOST", "tidb.infra.svc.cluster.local"), port=4000,
                    user="root", database="fnb", autocommit=True)
c.cursor().execute("""
CREATE TABLE IF NOT EXISTS po_suggestion (
  id BIGINT NOT NULL PRIMARY KEY, store_id INT NOT NULL, ing_id INT NOT NULL,
  sug_date DATE NOT NULL, suggest_qty DECIMAL(12,2) NOT NULL, unit_code VARCHAR(8) NOT NULL,
  sup_id INT, est_price DECIMAL(10,2), reason VARCHAR(300),
  status ENUM('DRAFT','APPROVED','REJECTED') NOT NULL DEFAULT 'DRAFT',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, decided_at DATETIME NULL,
  decided_by VARCHAR(32) NULL, KEY idx_sug_status (status, store_id))""")
print("PO_SUG_TABLE_OK")
