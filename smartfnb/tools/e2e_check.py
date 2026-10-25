import json, urllib.request

def call():
    req = urllib.request.Request(
        "http://svc-inventory.fnb-prod.svc.cluster.local:8080/api/alerts/compute?date=2026-10-23",
        method="POST")
    print("compute:", urllib.request.urlopen(req, timeout=600).read().decode())

    req2 = urllib.request.Request(
        "http://svc-inventory.fnb-prod.svc.cluster.local:8080/api/alerts?date=2026-10-23")
    alerts = json.loads(urllib.request.urlopen(req2, timeout=300).read().decode())
    print("alerts count:", len(alerts))
    for a in alerts[:5]:
        print("  ", a.get("storeId"), a.get("ingName"), "diff%:", a.get("diffPct"),
              "level:", a.get("level"), "status:", a.get("status"))

    req3 = urllib.request.Request(
        "http://svc-inventory.fnb-prod.svc.cluster.local:8080/api/diff?date=2026-10-23&storeId=7&limit=5")
    diff = json.loads(urllib.request.urlopen(req3, timeout=300).read().decode())
    print("diff top5 for store 7 on 2026-10-23:")
    for d in diff[:5]:
        print("  ", d.get("nameStd") or d.get("ing_name") or d, )

call()
