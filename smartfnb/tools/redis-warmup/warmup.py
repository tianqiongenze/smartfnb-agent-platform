#!/usr/bin/env python3
"""
Redis 集群 warmup（D6: 集群中要有对应数量级缓存数据且支持一键重放）
内容(约 6.2 万键): 单位字典/32店菜单/800 BOM/500食材+别名/14日库存快照/5万热点会员/1万QA种子
幂等: 先 SCAN+DEL fnb:* 再灌入; 重复执行安全。分块pipeline(2000/块)确保写入可靠。
"""
import os, json, time, hashlib, datetime as dt
import pymysql
import redis

DB = dict(host=os.getenv("DB_HOST", "tidb.infra.svc.cluster.local"), port=4000,
          user="root", charset="utf8mb4", database="fnb")
PW = os.getenv("REDIS_PW", "difyai123456")
SEEDS = [f"redis8-node-{i}.dify-plus.svc.cluster.local" for i in range(3)]
HOT_N = int(os.getenv("HOT_N", "50000"))
QA_N = int(os.getenv("QA_N", "10000"))
CHUNK = 2000

def wipe(r):
    n = 0
    for node in r.get_primaries():
        try:
            cur = 0
            client = node.redis_connection
            while True:
                cur, keys = client.scan(cur, match="fnb:*", count=2000)
                if keys:
                    client.delete(*keys); n += len(keys)
                if cur == 0: break
        except Exception as e:
            print(f"wipe node skip: {e}")
    print(f"wiped {n} existing fnb:* keys", flush=True)

class ChunkedPiper:
    """跨集群pipeline分块写入, 每CHUNK条flush并报告错误数"""
    def __init__(self, r):
        self.r = r; self.p = r.pipeline(); self.n = 0; self.errs = 0
    def set(self, key, val, ex=None):
        self.p.set(key, val, ex=ex) if ex else self.p.set(key, val)
        self.n += 1
        if self.n % CHUNK == 0:
            self._flush()
    def hset(self, key, field, val):
        self.p.hset(key, field, val)
        self.n += 1
        if self.n % CHUNK == 0:
            self._flush()
    def _flush(self):
        res = self.p.execute(raise_on_error=False)
        bad = [e for e in res if isinstance(e, Exception)]
        self.errs += len(bad)
        if bad:
            print(f"chunk errs {len(bad)}: {repr(bad[0])[:120]}", flush=True)
        self.p = self.r.pipeline()
    def done(self):
        self._flush()
        print(f"total commands {self.n}, errors {self.errs}", flush=True)

def main():
    t0 = time.time()
    c = pymysql.connect(**DB); cur = c.cursor()
    r = redis.RedisCluster(host=SEEDS[0], port=6379, password=PW,
                           decode_responses=True, require_full_coverage=False)
    wipe(r)
    w = ChunkedPiper(r)
    # 1. 单位字典
    cur.execute("SELECT unit_code, unit_name, ratio_to_gram FROM unit_dict")
    for code, name, ratio in cur.fetchall():
        w.hset("fnb:dict:unit", code, json.dumps({"name": name, "ratio": float(ratio)}))
    # 2. 食材 + 别名
    cur.execute("SELECT ing_id, ing_code, name_std, category, ref_price, aliases FROM ingredient")
    ings = cur.fetchall()
    alias_cnt = 0
    for iid, code, name, cat, price, aliases in ings:
        obj = {"id": iid, "code": code, "name": name, "cat": cat, "price": float(price) if price else None}
        w.set(f"fnb:ing:{iid}", json.dumps(obj, ensure_ascii=False))
        if aliases:
            for a in json.loads(aliases):
                w.set(f"fnb:alias:{a}", iid); alias_cnt += 1
    # 3. 菜单 + BOM
    cur.execute("SELECT dish_id, name, category, price FROM dish")
    dishes = {d[0]: d for d in cur.fetchall()}
    for s in range(1, 33):
        cur.execute("SELECT dish_id FROM store_menu WHERE store_id=%s", (s,))
        for (d,) in cur.fetchall():
            _, name, cat, price = dishes[d]
            w.hset(f"fnb:menu:{s}", d, json.dumps({"n": name, "c": cat, "p": float(price)}, ensure_ascii=False))
    cur.execute("SELECT dish_id, ing_id, grams_per_serving FROM bom")
    bom = {}
    for d, i, g in cur.fetchall(): bom.setdefault(d, []).append({"i": i, "g": float(g)})
    for d, items in bom.items():
        w.set(f"fnb:bom:{d}", json.dumps(items), ex=86400)
    # 4. 近14日库存快照(实际用量聚合)
    today = dt.date.today()
    snap_keys = 0
    for off in range(14):
        d = today - dt.timedelta(days=off)
        cur.execute("""SELECT store_id, ing_id, SUM(qty_base_gram) FROM stock_movement
                       WHERE movement_date=%s AND movement_type='consume' GROUP BY store_id, ing_id""", (d,))
        agg = {}
        for s, i, q in cur.fetchall(): agg.setdefault(s, {})[i] = int(q)
        for s, m in agg.items():
            w.set(f"fnb:inv:snap:{s}:{d:%Y%m%d}", json.dumps(m), ex=604800)
            snap_keys += 1
    # 5. 热点会员
    cur.execute("SELECT hot_id, member_id, order_cnt FROM hot_member ORDER BY hot_id LIMIT %s", (HOT_N,))
    for hid, mid, oc in cur.fetchall():
        w.set(f"fnb:member:hot:{hid}", json.dumps({"m": mid, "oc": oc}), ex=2592000)
    # 6. FAQ 语义缓存种子
    faq_tpl = [
        ("{}号店今天的牛肉用量和理论差多少", "请使用用量差异查询工具获取实盘数据,本条为缓存种子示例"),
        ("食材{}怎么换算成克", "已加载单位字典,1斤=500克,1千克=1000克,箱装按一品一码的箱规换算"),
        ("怎么降低{}浪费", "建议: 1)按BOM领料扫码 2)监控T+1差异 3)复核高价值食材收货称重"),
        ("{}的历史价格是多少", "参考价数据在主数据中,采购建议请查看采购智能体"),
    ]
    cats = ["肉类", "海鲜", "蔬菜", "调料"]
    for i in range(QA_N):
        q, a = faq_tpl[i % len(faq_tpl)]
        fill = [str(1 + i % 32), cats[i % 4]][i % 2] if i % len(faq_tpl) in (0, 3) else cats[i % 4]
        q = q.format(fill); a = a.format(fill)
        w.set(f"fnb:qa:{hashlib.md5(q.encode()).hexdigest()}", json.dumps({"q": q, "a": a}, ensure_ascii=False), ex=604800)
    w.done()
    r.set("fnb:warmup:meta", json.dumps({
        "ts": time.strftime("%F %T"), "ver": "0.1.7",
        "ingredients": len(ings), "aliases": alias_cnt, "menus": 32,
        "bom": len(bom), "inv_snap_keys": snap_keys,
        "hot_members": HOT_N, "qa_seeds": QA_N, "pipeline_errors": w.errs,
    }, ensure_ascii=False))
    print(f"WARMUP DONE in {time.time()-t0:.0f}s, cluster dbsize={r.dbsize():,}", flush=True)
    c.close()

if __name__ == "__main__":
    main()
