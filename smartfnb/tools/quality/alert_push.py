"""Phase1: 预警推送(每日07:35, 计算T-1后)
读取昨日HIGH/OPEN预警 → 企业微信webhook(如配置) + notify_log表(可审计, 反P4透明)
"""
import os, json, datetime as dt, urllib.request
import pymysql

DB = dict(host=os.getenv("DB_HOST", "tidb.infra.svc.cluster.local"), port=4000,
          user="root", charset="utf8mb4", database="fnb")
WECOM = os.getenv("WECOM_WEBHOOK", "")

def main():
    today = dt.date.today()
    d = today - dt.timedelta(days=1)
    c = pymysql.connect(**DB)
    cur = c.cursor(pymysql.cursors.DictCursor)
    cur.execute("""CREATE TABLE IF NOT EXISTS notify_log (
        id BIGINT NOT NULL PRIMARY KEY AUTO_RANDOM(4),
        notified_at DATETIME, channel VARCHAR(16), alert_date DATE,
        store_id INT, ing_id INT, content VARCHAR(500), ok TINYINT)""")
    cur.execute("""SELECT a.store_id, s.name store_name, a.ing_id, i.name_std, a.diff_pct, a.level
                   FROM alert a JOIN ingredient i ON i.ing_id=a.ing_id JOIN store s ON s.store_id=a.store_id
                   WHERE a.diff_date=%s AND a.level='HIGH' AND a.status='OPEN'
                   ORDER BY ABS(a.diff_pct) DESC LIMIT 50""", (d,))
    alerts = cur.fetchall()
    n_sent = 0
    for a in alerts:
        text = (f"⚠️【用量差异HIGH预警】{d} {a['store_name']}: {a['name_std']} "
                f"差异{a['diff_pct']}%(理论vs实际), 请核查收货称重与领料登记。")
        ok = 1
        if WECOM:
            try:
                body = json.dumps({"msgtype": "text", "text": {"content": text}}).encode()
                req = urllib.request.Request(WECOM, body, {"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=10)
            except Exception:
                ok = 0
        cur.execute("INSERT INTO notify_log (notified_at, channel, alert_date, store_id, ing_id, content, ok) VALUES (NOW(),%s,%s,%s,%s,%s,%s)",
                    ("wecom" if WECOM else "log_only", d, a["store_id"], a["ing_id"], text[:500], ok))
        n_sent += 1
    c.commit()
    print(json.dumps({"date": str(d), "pushed": n_sent, "channel": "wecom" if WECOM else "log_only"},
                     ensure_ascii=False))
    c.close()

if __name__ == "__main__":
    main()
