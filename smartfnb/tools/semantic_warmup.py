"""R3 语义库预热(v3, ADR-0013 hash嵌入): 语料生成+哈希向量入库+阈值自验证"""
import os
from pymilvus import MilvusClient
import sys
sys.path.insert(0, "/opt/fnb/smartfnb/tools")

def gen_corpus():
    cats = ["肉类", "海鲜", "蔬菜", "调料", "粮油", "干货"]
    qa = []
    for c in cats:
        qa.append((f"怎么降低{c}浪费", f"建议: 1)按BOM领料扫码 2)监控T+1差异(>15%预警) 3)复核{c}收货称重 4)周内因子备货"))
        qa.append((f"如何减少{c}损耗", f"{c}损耗控制: 标准BOM用量执行、先进先出、差异超15%当日核查、供应商比价复检"))
        qa.append((f"{c}的合理损耗率是多少", f"{c}行业参考损耗率: 加工损耗3-8%, 管理损耗应<2%, 超出部分进差异预警"))
        qa.append((f"{c}怎么备货合适", f"{c}备货: 参考7日预测均值×周内因子(周末1.3), 高价值{c}按World Model仿真最优量"))
    units = [("斤", "500克"), ("千克", "1000克"), ("两", "50克"), ("箱", "按食材一品一码箱规换算")]
    for u, v in units:
        qa.append((f"1{u}等于多少克", f"1{u}={v}。系统单位字典强制换算, 领料入库自动转克。"))
        qa.append((f"{u}怎么换算成克", f"{u}换算: {v}。所有出入库以克为基准。"))
    qa += [
        ("什么是BOM", "BOM是菜品标准配方: 每道菜各食材的克重标准, 理论用量=销售数量×BOM克重。"),
        ("理论用量怎么算", "理论用量=Σ(菜品销售数量×该菜品BOM标准克重), 按门店/食材/日聚合。"),
        ("差异率怎么计算", "差异率=(实际领用-理论用量)/理论用量×100%, 绝对值>15%预警, >30%为HIGH。"),
        ("预警什么时候发", "领料登记即事件驱动实时计算(秒级), 每日07:35全量兜底复核, HIGH级即时推送。"),
        ("什么是以次充好", "用低价食材顶替菜单标注的高价食材: 表现为高价值食材消耗远低于理论(负差异大)。"),
        ("收货缺斤短两怎么发现", "关注收货(receive)与消耗(consume)对比及供应商维度差异, 供应商12历史有少记模式可参照。"),
        ("采购建议单怎么审批", "管理端【采购建议】页: AI生成DRAFT→采购主管APPROVE/REJECT, AI不越过人工审批。"),
        ("供应商怎么选", "按近90天实际成交均价+评分(≥3.5)自动推荐, 无合格比价则待人工指派。"),
        ("需求预测准吗", "预测输出回测MAPE与置信度: HIGH≤20%, MEDIUM≤35%, LOW>35%将明示。"),
        ("预测用什么方法", "加权移动平均×周内季节因子×趋势比; 数据滞后>3天自动降级并给fallback。"),
        ("什么是world model仿真", "基于历史需求分布的门店数字孪生: 蒙特卡洛推演采购量的缺货/浪费期望成本, 输出最优量。"),
        ("会员积分怎么算", "消费1元=1分, 会员中心可查积分与券。"),
        ("数据质量怎么保证", "每日06:00五规则门禁: 新鲜度/完整性/单位一致性/别名覆盖/异常值, 看板公开。"),
        ("为什么数字要溯源", "智能体回答的数字必须来自MCP工具返回(可溯源), 编造数字会被校验拦截并标注。"),
        ("MCP是什么", "Model Context Protocol: 智能体调用业务工具的标准协议, 本平台工具全MCP化, SQL可溯源。"),
        ("A2A是什么", "Agent2Agent协议: 智能体间互操作标准, 差异分析Agent可被外部Agent以message/send委派。"),
        ("菜单怎么查", "GraphQL {stores{id,name}} 与 {ingredients{id,name,category}} 可查门店与食材主数据。"),
        ("怎么登录系统", "管理端admin/admin123, 采购buyer/buyer123, 门店store7/store123(JWT 8小时)。"),
    ]
    return qa

import importlib.util
spec = importlib.util.spec_from_file_location("sem", "/opt/fnb/smartfnb/agent-runtime/app/semantic.py")
sem = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sem)

client = MilvusClient(uri=f"http://{os.getenv('MILVUS_HOST','milvus.infra.svc.cluster.local')}:19530")
for col in ("fnb_qa_hash",):
    if client.has_collection(col):
        client.drop_collection(col)
sem.ensure_collection()
corpus = gen_corpus()
rows = [{"vector": sem._hash_embed(q), "q": q[:200], "a": a[:800]} for q, a in corpus]
client.insert("fnb_qa_hash", rows)
print(f"HASH_WARMUP_DONE rows={len(rows)}")

# 阈值自验证: 同义变体 vs 无关问题
tests = [
    ("怎么降低海鲜浪费", "hit"), ("如何减少海鲜的浪费", "hit"),
    ("怎样降低海鲜类浪费", "hit"), ("1斤等于多少克", "hit"),
    ("一斤是多少克", "hit"), ("7号店差异多少", None),
]
for q, expect in tests:
    r = sem.search_similar(q)
    print(f"  {q[:18]:20s} -> {r['mode'] if r else 'miss'} score={r['score'] if r else '-'}")
