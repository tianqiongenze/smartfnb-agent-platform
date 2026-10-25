#!/usr/bin/env python3
"""R2 事件枢纽(双角色):
1) HTTP生产网关 :8081/publish ← svc-inventory投递领料事件(pulsar python客户端)
2) 消费者: fnb-stock-movement → 实时单店差异预警(30s店级防抖) → notify_log即时推送
"""
import json, os, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pulsar
import redis
import pymysql

PULSAR_URL = os.getenv("PULSAR_URL", "pulsar://pulsar-broker.infra.svc.cluster.local:6650")
TOPIC = "persistent://public/default/fnb-stock-movement"
INVENTORY = os.getenv("INVENTORY_URL", "http://svc-inventory:8080")
DB = dict(host=os.getenv("DB_HOST", "tidb.infra.svc.cluster.local"), port=4000,
          user="root", charset="utf8mb4", database="fnb")

producer = None

class Gateway(BaseHTTPRequestHandler):
    def do_POST(self):
        global producer
        if self.path != "/publish" or producer is None:
            self.send_response(503); self.end_headers(); return
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            producer.send(body)
            self.send_response(202)
        except Exception as e:
            print(f"[GW_ERR] {e}", flush=True)
            self.send_response(502)
        self.end_headers()
    def log_message(self, *a):
        pass

def post(url, timeout=180):
    req = urllib.request.Request(url, method="POST")
    return urllib.request.urlopen(req, timeout=timeout).read().decode()

def push_high_alerts(date, store_id):
    c = pymysql.connect(**DB)
    try:
        cur = c.cursor(pymysql.cursors.DictCursor)
        cur.execute("""SELECT a.store_id, s.name store_name, a.ing_id, i.name_std, a.diff_pct
                       FROM alert a JOIN ingredient i ON i.ing_id=a.ing_id
                       JOIN store s ON s.store_id=a.store_id
                       WHERE a.diff_date=%s AND a.store_id=%s AND a.level='HIGH' AND a.status='OPEN'
                       ORDER BY ABS(a.diff_pct) DESC LIMIT 10""", (date, store_id))
        n = 0
        for a in cur.fetchall():
            text = (f"⚡【实时预警】{date} {a['store_name']}: {a['name_std']} 差异{a['diff_pct']}% "
                    f"(事件驱动, 分钟级)")
            cur.execute("""INSERT INTO notify_log (notified_at, channel, alert_date, store_id,
                            ing_id, content, ok) VALUES (NOW(),'event',%s,%s,%s,%s,1)""",
                        (date, store_id, a["ing_id"], text[:500]))
            n += 1
        c.commit()
        return n
    finally:
        c.close()

def main():
    global producer
    r = redis.RedisCluster(host=os.getenv("REDIS_SEED", "redis8-node-0.dify-plus.svc.cluster.local"),
                           port=6379, password=os.getenv("REDIS_PW", "difyai123456"),
                           decode_responses=True, require_full_coverage=False)
    client = pulsar.Client(PULSAR_URL)
    producer = client.create_producer(TOPIC)
    consumer = client.subscribe(TOPIC, "fnb-realtime-alert",
                                consumer_type=pulsar.ConsumerType.Shared,
                                initial_position=pulsar.InitialPosition.Latest)
    Thread(target=lambda: ThreadingHTTPServer(("0.0.0.0", 8081), Gateway).serve_forever(),
           daemon=True).start()
    print("EVENT_HUB_READY gw=:8081/publish", flush=True)
    while True:
        try:
            msg = consumer.receive(timeout_millis=60000)
            evt = json.loads(msg.data().decode())
            consumer.acknowledge(msg)
            sid, d = evt["storeId"], evt["date"]
            key = f"fnb:evt:debounce:{sid}"
            if r.set(key, "1", ex=30, nx=True):
                t0 = time.time()
                post(f"{INVENTORY}/api/alerts/compute-store?date={d}&storeId={sid}")
                post(f"{INVENTORY}/api/alerts/orphan-check?date={d}&storeId={sid}")
                n = push_high_alerts(d, sid)
                print(f"[EVT] store={sid} date={d} pushed={n} in {time.time()-t0:.1f}s",
                      flush=True)
        except pulsar.Timeout:
            continue
        except Exception as e:
            print(f"[EVT_ERR] {type(e).__name__}: {e}", flush=True)
            time.sleep(3)

if __name__ == "__main__":
    main()
