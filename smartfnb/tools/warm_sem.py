import sys
sys.path.insert(0, "/srv")
from app import semantic
from app.semantic import _hash_embed
from pymilvus import MilvusClient

client = MilvusClient(uri="http://milvus.infra.svc.cluster.local:19530")
if client.has_collection("fnb_qa_hash"):
    client.drop_collection("fnb_qa_hash")
semantic.ensure_collection()

cats = ["肉类", "海鲜", "蔬菜", "调料", "粮油", "干货"]
qa = []
for c in cats:
    qa.append((f"怎么降低{c}浪费", f"建议: 按BOM领料扫码/监控T+1差异>15%预警/复核{c}收货称重/周内因子备货"))
    qa.append((f"如何减少{c}损耗", f"{c}损耗控制: 标准BOM执行/先进先出/差异超15%当日核查/比价复检"))
    qa.append((f"{c}怎么备货合适", f"{c}备货: 参考7日预测均值×周内因子(周末1.3), 高价值按World Model仿真最优量"))
for u, v in [("斤", "500克"), ("千克", "1000克"), ("两", "50克")]:
    qa.append((f"1{u}等于多少克", f"1{u}={v}。单位字典强制换算, 领料入库自动转克。"))
    qa.append((f"{u}怎么换算成克", f"{u}换算: {v}。所有出入库以克为基准。"))
qa += [("什么是BOM", "BOM是菜品标准配方, 理论用量=销售数量×BOM克重。"),
       ("理论用量怎么算", "理论用量=Σ(销售数量×BOM克重), 按门店/食材/日聚合。"),
       ("差异率怎么计算", "(实际-理论)/理论×100%, >15%预警, >30% HIGH。"),
       ("预警什么时候发", "领料登记即事件驱动实时计算(秒级), 每日07:35全量兜底。"),
       ("什么是以次充好", "低价食材顶替高价食材: 高价值食材消耗远低于理论(负差异大)。"),
       ("收货缺斤短两怎么发现", "关注收货与消耗对比及供应商维度差异。"),
       ("采购建议单怎么审批", "管理端采购建议页: DRAFT→人工APPROVE/REJECT, AI不越权。"),
       ("供应商怎么选", "按近90天成交均价+评分≥3.5自动推荐。"),
       ("需求预测准吗", "输出回测MAPE与置信度: HIGH≤20% MEDIUM≤35% LOW>35%。"),
       ("预测用什么方法", "加权移动平均×周内因子×趋势, 滞后>3天自动降级。"),
       ("什么是world model仿真", "门店数字孪生: 蒙特卡洛推演采购量缺货/浪费期望成本。"),
       ("会员积分怎么算", "消费1元=1分。"),
       ("数据质量怎么保证", "每日06:00五规则门禁, 看板公开。"),
       ("为什么数字要溯源", "数字必须来自MCP工具返回, 编造会被拦截。"),
       ("MCP是什么", "Model Context Protocol: 智能体调工具标准协议, 工具全MCP化。"),
       ("A2A是什么", "Agent2Agent: 智能体互操作, 支持message/send委派。")]
rows = [{"vector": _hash_embed(q), "q": q, "a": a} for q, a in qa]
client.insert("fnb_qa_hash", rows)
print("WARMED", len(rows))
for t in ["怎么降低海鲜浪费", "如何减少海鲜的浪费", "怎样降低海鲜类浪费",
          "1斤等于多少克", "一斤是多少克", "7号店差异多少"]:
    r = semantic.search_similar(t)
    print("  ", t[:16], "->", (r["mode"], r["score"]) if r else "miss")
