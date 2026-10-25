"""S7 混合业务流(Locust): 模拟真实用户链 菜单→(点餐积分)→领料→查差异, 按权重混合。"""
import random, time
from locust import HttpUser, task, between, SequentialTaskSet

class RealUserFlow(SequentialTaskSet):
    """一次完整用户旅程(顺序): 看菜单→积分→领料→看差异"""
    def on_start(self):
        self.store = random.randint(1, 32)
        self.member = 100000 + random.randint(0, 999999)

    @task
    def journey(self):
        g = self.client.post("http://svc-portal:8080/graphql",
                             json={"query": "{stores{id,name}}"},
                             name="graphql/menu")
        m = self.client.get(f"http://svc-member:8080/api/members/{self.member}",
                            name="member/profile")
        w = self.client.post("http://svc-inventory:8080/api/stock-movements",
                             json={"storeId": self.store, "ingId": random.randint(1, 500),
                                   "movementType": "consume", "qty": 2.0, "unitCode": "kg"},
                             name="movement/ingest")
        d = self.client.post("http://svc-portal:8080/graphql",
                             json={"query": "query($s:Int,$d:String!){diffReport(storeId:$s,date:$d,limit:10){alertCount}}",
                                   "variables": {"s": self.store, "d": "2026-10-23"}},
                             name="graphql/diff")
        time.sleep(random.uniform(0.5, 1.5))
        self.interrupt()

class MixedUser(HttpUser):
    tasks = {RealUserFlow: 3}

    @task(2)
    def browse_only(self):
        self.client.get("http://10.167.2.175:30250/", name="web/home")

    wait_time = between(0.3, 1.0)
