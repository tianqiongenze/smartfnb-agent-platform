"""S3 智能体SSE(Locust): K6对SSE流式支持弱, 用Locust http客户端读完整流。
三档问题: FAQ缓存命中 / 工具直答 / 预测(依赖声明路径)。"""
import json, random, time
from locust import HttpUser, task, between

FAQS = ["怎么降低蔬菜浪费", "如何减少肉类损耗", "什么是BOM", "怎么换算食材单位",
        "怎样降低海鲜浪费", "怎么降低调料浪费"]
DIRECTS = [
    {"q": "7号店2026-10-23的用量差异是多少", "s": 7, "d": "2026-10-23"},
    {"q": "18号店2026-10-23的差异是多少", "s": 18, "d": "2026-10-23"},
    {"q": "3号店2026-10-22的差异", "s": 3, "d": "2026-10-22"},
]
FORECASTS = ["预测7号店下周鲈鱼的需求", "预测18号店下周土豆的需求", "预测3号店下周五花肉的需求"]

class AgentUser(HttpUser):
    host = "http://10.167.2.175:30252"
    wait_time = between(0.2, 0.8)

    def _chat(self, question, store_id=7, date="2026-10-23"):
        t0 = time.time()
        with self.client.post("/api/agent/chat",
                              json={"question": question, "storeId": store_id, "date": date},
                              catch_response=True, name="/agent/chat") as resp:
            body = resp.text or ""
            ok = ('"event": "answer"' in body or '"event":"answer"' in body) and '"event": "error"' not in body
            if not ok:
                resp.failure(f"no answer event: {body[:120]}")

    @task(5)
    def faq_cache(self):
        self._chat(random.choice(FAQS))

    @task(3)
    def tool_direct(self):
        d = random.choice(DIRECTS)
        self._chat(d["q"], d["s"], d["d"])

    @task(2)
    def forecast(self):
        self._chat(random.choice(FORECASTS))
