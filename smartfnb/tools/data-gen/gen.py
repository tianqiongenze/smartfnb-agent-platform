#!/usr/bin/env python3
"""
SmartF&B Phase-0 模拟数据生成器（D6: ≥1亿条, 确定性可重放）
按日期分片(每Pod独占一段日期, 保证 sales↔stock_movement 关联一致):
  shard 0 额外负责主数据种子 + gen_status 标记
  总量约 1.25 亿行: sales_line 6000万 / sales_order 1500万 / stock_movement 3000万
              / waste 500万 / purchase 400万+明细1000万 / member 100万
叙事注入(复刻PDF重生项目的演示故事):
  门店7/18 + 高价值食材(肉类/海鲜) 的 consume 少记 40~55% => 差异预警演示
  供应商12 的 receive 少记 15% => 收货缺斤演示
"""
import os, sys, time, random, datetime as dt, hashlib

import pymysql

DB = dict(host=os.getenv("DB_HOST", "tidb.infra.svc.cluster.local"),
          port=int(os.getenv("DB_PORT", "4000")), user="root", charset="utf8mb4",
          autocommit=False)
SHARD = int(os.getenv("JOB_COMPLETION_INDEX", os.environ.get("SHARD", "0")))
SHARDS = int(os.getenv("SHARDS", "8"))
D0 = dt.date(2024, 1, 1)
DAYS_TOTAL = 1027                      # 2024-01-01 .. 2026-10-23
STORES = 32; INGS = 500; DISHES = 800; MEMBERS = 1_000_000
BATCH = 2000

def conn(db=None):
    return pymysql.connect(database=db, **DB)

def exec_many(cur, sql, rows, log_every=50):
    t0, n = time.time(), 0
    for i in range(0, len(rows), BATCH):
        cur.executemany(sql, rows[i:i+BATCH])
        n += len(rows[i:i+BATCH])
        if (i // BATCH) % log_every == 0:
            print(f"  {n}/{len(rows)} rows {n/max(time.time()-t0,0.01):,.0f}/s", flush=True)
    print(f"  DONE {n} rows in {time.time()-t0:.0f}s", flush=True)

# ---------------- 主数据（确定性, 仅 shard 0 执行） ----------------
CAT_ING = [("肉类", 80, ("牛柳","牛腩","雪花牛肉","腱子肉","猪里脊","五花肉","鸡腿肉","鸭胸")), 
           ("海鲜", 60, ("鲈鱼","多宝鱼","龙虾仁","基围虾","花蟹","扇贝","生蚝","带鱼")),
           ("蔬菜", 120, ("生菜","菜心","西兰花","土豆","番茄","彩椒","芦笋","莲藕")),
           ("调料", 80, ("生抽","蚝油","料酒","白糖","淀粉","豆瓣酱","花椒","八角")),
           ("粮油", 60, ("大米","面粉","花生油","菜籽油","芝麻油","糯米")),
           ("干货", 100, ("香菇","木耳","粉丝","腐竹","干贝","虾米","枸杞","红枣"))]
ALIAS_POOL = [("鸡翅膀","翅中","鸡翅（中）"), ("土豆","马铃薯","洋芋"), ("生抽","酱油","黄豆酱油"),
              ("生菜","莴苣菜","油麦生菜"), ("白糖","砂糖","绵白糖"), ("基围虾","明虾","青虾")]

def seed_master(c):
    cur = c.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS gen_status(k VARCHAR(32) PRIMARY KEY, v VARCHAR(64), ts DATETIME)""")
    cur.execute("DELETE FROM gen_status")   # 幂等: 重试时清空标记
    cur.execute("DELETE FROM store"); cur.execute("DELETE FROM unit_dict")
    cur.execute("DELETE FROM ingredient"); cur.execute("DELETE FROM supplier")
    cur.execute("DELETE FROM dish"); cur.execute("DELETE FROM store_menu")
    cur.execute("DELETE FROM member"); cur.execute("DELETE FROM hot_member")
    cur.execute("DELETE FROM bom")
    exec_many(cur, "INSERT INTO store VALUES (%s,%s,%s,%s,%s)",
              [(i, f"粤味轩{i:02d}号店", "广州" if i < 20 else "深圳", 300+40*(i%9), D0 - dt.timedelta(days=1500+i*30)) for i in range(1, STORES+1)])
    units = [("g","克",1),("kg","千克",1000),("jin","斤",500),("liang","两",50),("box","箱",-1)]
    exec_many(cur, "INSERT INTO unit_dict VALUES (%s,%s,%s)", units)
    # 食材: 一品一码 + 别名
    rows, cat_of, ing_meta = [], {}, {}
    iid = 1
    for cat, cnt, bases in CAT_ING:
        for j in range(cnt):
            name = f"{bases[j % len(bases)]}" + (f"{j//len(bases)+1:02d}" if j >= len(bases) else "")
            aliases = ALIAS_POOL[iid % len(ALIAS_POOL)] if cat in ("肉类","蔬菜","调料") else None
            box_ratio = round(5000 + (iid % 20) * 2500, 1) if cat in ("调料","粮油") else None
            rows.append((iid, f"IMG-{iid:04d}", name, cat, "g", box_ratio,
                         str(list(aliases)).replace("'", '"') if aliases else None,
                         round(8 + (iid * 37) % 90 + (30 if cat in ("肉类","海鲜") else 0), 1)))
            cat_of[iid] = cat
            if iid <= 5: ing_meta[iid] = name   # 1-5号=高价值肉类海鲜
            iid += 1
    exec_many(cur, "INSERT INTO ingredient VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", rows)
    exec_many(cur, "INSERT INTO supplier VALUES (%s,%s,%s,%s)",
              [(i, f"供应商-{i:03d}({['肉类','海鲜','蔬菜','粮油','综合'][i%5]})", ['肉类','海鲜','蔬菜','粮油','综合'][i%5], round(3.5+(i%6)*0.25,1)) for i in range(1, 201)])
    rows, dish_price = [], {}
    for d in range(1, DISHES+1):
        cat = ["热菜","凉菜","汤羹","主食","甜品","海鲜档"][d % 6]
        price = round(18 + (d*13) % 280, 0)
        rows.append((d, f"菜品{d:03d}-{cat}", cat, price)); dish_price[d] = price
    exec_many(cur, "INSERT INTO dish VALUES (%s,%s,%s,%s)", rows)
    bom_rows = []
    rng = random.Random(20261024)
    for d in range(1, DISHES+1):
        for iid2 in rng.sample(range(1, INGS+1), rng.randint(4, 8)):
            g = {"肉类": rng.randint(80,400), "海鲜": rng.randint(60,300)}.get(cat_of[iid2], rng.randint(5,120))
            bom_rows.append((d, iid2, g))
    exec_many(cur, "INSERT INTO bom (dish_id, ing_id, grams_per_serving) VALUES (%s,%s,%s)", bom_rows)
    exec_many(cur, "INSERT INTO store_menu VALUES (%s,%s)",
              [(s, d) for s in range(1, STORES+1) for d in range(1, DISHES+1)])
    # 会员100万 + 热点10万
    t0 = time.time()
    rows = [(100000+i, f"会员{i:07d}", hashlib.sha256(f"138{i:08d}".encode()).hexdigest(), 1+(i%5), D0 - dt.timedelta(days=(i%1400)))
            for i in range(MEMBERS)]
    exec_many(cur, "INSERT INTO member VALUES (%s,%s,%s,%s,%s)", rows, log_every=100)
    print(f"members done {time.time()-t0:.0f}s", flush=True)
    exec_many(cur, "INSERT INTO hot_member VALUES (%s,%s,%s)",
              [(i+1, 100000 + i*10 + 3, 8 + (i*7) % 92) for i in range(100_000)])
    c.commit()
    cur.execute("INSERT INTO gen_status VALUES ('master_done','1',NOW())")
    cur.execute("INSERT INTO gen_status VALUES ('high_value_ing','1,2,3,4,5',NOW())")
    c.commit()
    print("MASTER DATA SEEDED", flush=True)

def my_days():
    per = DAYS_TOTAL // SHARDS
    return [D0 + dt.timedelta(days=SHARD*per + k) for k in range(per if SHARD < SHARDS-1 else DAYS_TOTAL - SHARD*per)]

def wait_master(c):
    if SHARD == 0: return
    cur = c.cursor()
    for _ in range(180):
        try:
            cur.execute("SELECT v FROM fnb.gen_status WHERE k='master_done'")
            if cur.fetchone(): return
        except pymysql.err.ProgrammingError:
            pass                      # 表尚未由 shard0 创建, 继续等待
        print("waiting master data...", flush=True); time.sleep(10)
    raise RuntimeError("master seed timeout")

def gen_facts(c):
    rng = random.Random(987_000 + SHARD)
    cur = c.cursor()
    cur.execute("SELECT dish_id, price FROM fnb.dish")
    dish_price = {d: float(p) for d, p in cur.fetchall()}
    cur.execute("SELECT dish_id, ing_id, grams_per_serving FROM fnb.bom")
    bom = {}
    for d, i, g in cur.fetchall(): bom.setdefault(d, []).append((i, float(g)))
    cur.execute("SELECT store_id, dish_id FROM fnb.store_menu")
    menu = {}
    for s, d in cur.fetchall(): menu.setdefault(s, []).append(d)
    cur.execute("SELECT ing_id, category FROM fnb.ingredient"); ing_cat = dict(cur.fetchall())
    HV = {"肉类","海鲜"}; biased = {7, 18}; bad_sup = 12
    days = my_days(); per_store = max(200, 456 * 8 // 1)  # ~456单/店/日(基准)
    for day in days:
        dow = day.weekday()
        factor = 1.35 if dow >= 5 else 1.0          # 周末高峰
        # ---- 销售订单+明细 ----
        orders, lines = [], []
        oid_base = SHARD * 100_000_000 + (day - D0).days * 20_000
        lid_base = SHARD * 1_000_000_000 + (day - D0).days * 100_000
        li = 0
        for s in range(1, STORES+1):
            n_orders = int(per_store/8 * factor * (0.9 + 0.2*rng.random()))
            for k in range(n_orders):
                oid = oid_base + k*STORES + s
                ndish = rng.randint(3, 5)
                mem = 100000 + rng.randrange(MEMBERS) if rng.random() < 0.3 else None
                ch = 3 if rng.random() < 0.02 else (2 if rng.random() < 0.08 else 1)
                hh = rng.randrange(10, 22); mm = rng.randrange(60)
                otime = dt.datetime.combine(day, dt.time(hh, mm))
                total = 0.0; olines = []
                for _ in range(ndish):
                    d = rng.choice(menu[s]); q = rng.randint(1, 3)
                    amt = round(q * dish_price[d], 2); total += amt
                    olines.append((oid, s, day, d, q, amt))
                orders.append((oid, s, mem, day, otime, ch, round(total, 2)))
                for o in olines:
                    li += 1
                    lines.append((lid_base + li,) + o)
        exec_many(cur, "INSERT IGNORE INTO sales_order (order_id,store_id,member_id,order_date,order_time,channel,amount) VALUES (%s,%s,%s,%s,%s,%s,%s)", orders, log_every=100)
        exec_many(cur, "INSERT IGNORE INTO sales_line (line_id,order_id,store_id,order_date,dish_id,qty,line_amount) VALUES (%s,%s,%s,%s,%s,%s,%s)", lines, log_every=100)
        # ---- 理论用量(按店日聚合) ----
        theo = {}
        for (_lid, _oid, s, _day, d, q, _a) in lines:
            for (i, g) in bom[d]:
                key = (s, i); theo[key] = theo.get(key, 0) + q * g
        # ---- 出入库流水(consume=理论×噪声; 7/18店高价值少记) ----
        movs, wastes = [], []
        mov_base = SHARD * 1_000_000_000 + (day - D0).days * 250_000
        mi = 0
        for (s, i), tg in theo.items():
            if tg <= 0: continue
            f = rng.gauss(1.05, 0.15)
            if s in biased and ing_cat[i] in HV: f *= rng.uniform(0.45, 0.60)
            actual = max(0, int(tg * f))
            parts = rng.randint(1, 3); left = actual
            for p in range(parts):
                q = left if p == parts-1 else left // parts
                if q <= 0: continue
                left -= q; mi += 1
                movs.append((mov_base+mi, s, i, day, 'consume', q, f"MV-{day:%Y%m%d}-{s:02d}-{mi}"))
            # receive: 供应商12 少记15%
            rec = int(tg * rng.uniform(1.05, 1.25) * (0.85 if i % 12 == 0 else 1.0))
            mi += 1
            movs.append((mov_base+mi, s, i, day, 'receive', rec, f"RC-{day:%Y%m%d}-{s:02d}-{mi}"))
        for i in range(1, INGS+1):
            for s in range(1, STORES+1):
                if rng.random() < 0.005:                # ~5M行/全程
                    mi += 1
                    wastes.append((SHARD*100_000_000+ (day-D0).days*800 + mi, s, i, day,
                                   int(rng.uniform(500, 15000)), 1+(mi%4), None))
        exec_many(cur, "INSERT IGNORE INTO stock_movement (mov_id,store_id,ing_id,movement_date,movement_type,qty_base_gram,ref_no,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                  [(m[0],m[1],m[2],m[3],m[4],m[5],m[6],dt.datetime.combine(day, dt.time(8+(mi%12)))) for m in movs], log_every=100)
        exec_many(cur, "INSERT IGNORE INTO waste_record (waste_id,store_id,ing_id,waste_date,qty_base_gram,reason,note) VALUES (%s,%s,%s,%s,%s,%s,%s)", wastes, log_every=100)
        # ---- 采购 ----
        pos, pis = [], []
        po_base = SHARD * 10_000_000 + (day - D0).days * 3_000
        pi = 0
        for s in range(1, STORES+1):
            for _ in range(4):
                pi += 1
                sup = rng.randrange(1, 201)
                po_id = po_base + pi
                pos.append((po_id, s, sup, day, 3, round(rng.uniform(800, 25000), 2)))
                for _ in range(rng.randint(2, 3)):
                    pi += 1
                    i2 = rng.randrange(1, INGS+1)
                    ucode = 'box' if ing_cat[i2] in ("调料","粮油") else ('kg' if ing_cat[i2] in ("肉类","海鲜") else 'jin')
                    pis.append((po_base+pi, po_id, i2, round(rng.uniform(1, 100),1), ucode, round(rng.uniform(5, 90),2)))
        exec_many(cur, "INSERT IGNORE INTO purchase_order (po_id,store_id,sup_id,order_date,status,total_amount) VALUES (%s,%s,%s,%s,%s,%s)", pos, log_every=200)
        exec_many(cur, "INSERT IGNORE INTO purchase_item (pi_id,po_id,ing_id,qty,unit_code,unit_price) VALUES (%s,%s,%s,%s,%s,%s)", pis, log_every=200)
        c.commit()
        print(f"[shard {SHARD}] {day} done. today rows~{len(orders)+len(lines)+len(movs)+len(wastes)+len(pos)+len(pis):,}", flush=True)

if __name__ == "__main__":
    t0 = time.time()
    c = conn("fnb") if SHARD == 0 else conn("fnb")
    wait_master(c)
    if SHARD == 0:
        seed_master(c)
    gen_facts(c)
    c.close()
    print(f"SHARD {SHARD} COMPLETE in {(time.time()-t0)/60:.1f} min", flush=True)
