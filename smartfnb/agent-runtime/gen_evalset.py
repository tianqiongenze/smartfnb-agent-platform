#!/usr/bin/env python3
"""生成100条评审集 evalset.jsonl(确定性): 覆盖5意图×边界×对抗×解析"""
import json, random

rng = random.Random(20261025)
stores = [1, 7, 18, 32]
ings = ["鲈鱼", "雪花牛肉", "五花肉", "花蟹", "生菜", "土豆", "基围虾", "牛腩"]
out = []

# 1) diff意图 ×24
for i in range(32):
    s, g = rng.choice(stores), rng.choice(ings)
    out.append({"question": f"{s}号店今天{g}的用量差异是多少", "expect_intent": "diff_agent"})
for q in ["查看浪费情况", "哪些食材多用了", "领料对不对", "昨天损耗大吗", "有没有预警"]:
    out.append({"question": q, "expect_intent": "diff_agent"})

# 2) procurement ×18 (含parse)
for i in range(16):
    s, g, q = rng.choice(stores), rng.choice(ings), rng.choice([10, 25, 50, 100, 2.5])
    out.append({"question": f"帮{s}号店采购{q}公斤{g}", "expect_intent": "procurement_agent",
                "parse": {"qty": float(q), "ing": g}})
for q in ["看看待审批建议单", "比价一下鲈鱼", "供应商有哪些", "帮我补货"]:
    out.append({"question": q, "expect_intent": "procurement_agent"})

# 3) forecast ×12
for i in range(12):
    s, g = rng.choice(stores), rng.choice(ings)
    out.append({"question": f"预测{s}号店下周{g}的需求", "expect_intent": "forecast_agent"})
for q in ["明天备货多少合适", "未来7天土豆需求", "下周要进多少货"]:
    out.append({"question": q, "expect_intent": "forecast_agent"})

# 4) FAQ/smalltalk/menu/knowledge ×16
faq = ["怎么降低浪费", "如何减少损耗", "什么是BOM", "食材怎么换算成克",
       "怎么降低肉类浪费", "如何减少蔬菜损耗", "怎样降低海鲜浪费", "怎么换算食材单位"]
for q in faq[:6]:
    out.append({"question": q, "expect_intent": "fallback"})
for q in ["你好", "谢谢", "再见"]:
    out.append({"question": q, "expect_intent": "smalltalk"})
for q in ["推荐几个招牌菜", "看看菜单", "有什么菜品"]:
    out.append({"question": q, "expect_intent": "menu_agent"})
for q in ["等保测评多久一次", "公司的退款政策是什么"]:
    out.append({"question": q, "expect_intent": "knowledge_agent"})

# 5) 工具直答守卫 ×12 (真实数字→必须通过)
tools_real = [{"name_std": "鲈鱼03", "category": "海鲜", "theo_gram": 9099, "actual_gram": 2972, "diff_pct": -67.3}]
for i in range(6):
    out.append({"question": f"直答守卫#{i}", "expect_intent": "knowledge_agent", "tool_lines": tools_real, "full_shape": True})

# 6) 对抗幻觉样本 ×12 (编造数字→必须拦截)
adv_tools = ['{"actual_gram": 8200}']
adv_ans = ["实际需要35.5公斤牛肉", "明天需求99公斤", "差异率高达88.8%",
           "浪费了1234.5元", "建议采购77.7公斤", "环比上涨66.6%"]
for i, a in enumerate(adv_ans):
    out.append({"question": f"对抗#{i}", "expect_intent": "knowledge_agent",
                "adversarial_answer": a, "tool_outputs": adv_tools, "expect_guard_pass": False})
for i, a in enumerate(["实际用量8.2公斤", "差异47.1%"]):
    out.append({"question": f"对抗白名单#{i}", "expect_intent": "knowledge_agent",
                "adversarial_answer": a, "tool_outputs": ['{"actual_gram": 8200, "diff_pct": 47.1}'],
                "expect_guard_pass": True})

with open("app/evalset.jsonl", "w", encoding="utf-8") as f:
    for c in out:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")
print(f"EVALSET_GENERATED {len(out)} cases")
