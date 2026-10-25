import json
import redis
r = redis.RedisCluster(host="redis8-node-0.dify-plus.svc.cluster.local", port=6379,
                       password="difyai123456", decode_responses=True, require_full_coverage=False)
cur = 0
n = 0
for key in r.scan_iter(match="fnb:qa:*", count=500):
    obj = json.loads(r.get(key))
    print("Q:", obj["q"][:50])
    n += 1
    if n >= 6:
        break
