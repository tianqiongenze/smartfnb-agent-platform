"""LangGraph 编排(V2: 收编进R1 Agent Harness)。
路由→专家(diff/procurement/forecast)统一走 harness.loop 的
observe→plan→act→verify→reflect 循环; LLM路径受 Budget 预算/熔断管控。
"""
from __future__ import annotations

import json
import operator
import os
from contextlib import asynccontextmanager
from typing import Annotated, TypedDict

import redis as redis_lib
from langgraph.graph import StateGraph, START, END

from .guards import route_intent, DEGRADED_NOTICE, parse_proc_request
from .direct import faq_hit, direct_diff_answer, needs_llm_analysis
from . import semantic
from .llm import main_llm, fast_llm
from .harness import Budget, BudgetExceeded, SessionContext
from .harness.loop import act_with_tools, verify, reflect_on_budget

REDIS_PW = os.getenv("REDIS_PW", "difyai123456")
REDIS_SEED = os.getenv("REDIS_SEED", "redis8-node-0.dify-plus.svc.cluster.local")

class AgentState(TypedDict):
    question: str
    store_id: int
    date: str
    intent: str
    answer: str
    confidence: str
    tool_outputs: Annotated[list[str], operator.add]
    cache_hit: bool
    degraded: bool
    reason: str
    budget_snapshot: dict

def _redis():
    try:
        return redis_lib.RedisCluster(host=REDIS_SEED, port=6379, password=REDIS_PW,
                                      decode_responses=True, require_full_coverage=False)
    except Exception:
        return None

async def node_route(state: AgentState) -> dict:
    return {"intent": route_intent(state["question"])}

async def _call_tool(tools, name: str, args: dict) -> dict | None:
    tool = next((t for t in tools if t.name == name), None)
    if tool is None:
        return None
    try:
        raw = await tool.ainvoke(args)
        parsed = None
        if isinstance(raw, str):
            parsed = json.loads(raw)
        elif isinstance(raw, list):
            for block in raw:
                if isinstance(block, dict) and "text" in block:
                    parsed = json.loads(block["text"]); break
                if isinstance(block, dict) and "lines" in block:
                    parsed = block; break
        else:
            parsed = raw
        if isinstance(parsed, list):
            parsed = {"lines": parsed}
        return parsed
    except Exception:
        return None

def _ctx_of(state) -> SessionContext:
    return SessionContext(question=state["question"], store_id=state["store_id"],
                          date=state["date"])

_NO_TOOL_REASONS = {"faq_cache", "semantic_cache", "non_data_intent",
                    "semantic_ref", "need_qty", "need_ingredient"}

async def _finish(state, ctx, answer, conf, outputs, reason="", cache=False, deg=False):
    if outputs:                      # 仅工具数据路径做数字溯源校验
        v_answer, v_conf = verify(ctx, answer)
    else:
        v_answer, v_conf = answer, conf
    return {"answer": v_answer, "confidence": v_conf, "tool_outputs": outputs,
            "cache_hit": cache, "degraded": deg, "reason": reason}

async def node_diff_agent(state: AgentState, config) -> dict:
    """差异专家: harness循环 — ACT(get_diff)→直答→(归因类)LLM(Budget管控)→VERIFY"""
    tools = config["configurable"]["mcp_tools"]
    budget: Budget = config["configurable"].get("budget") or Budget()
    ctx = _ctx_of(state)
    data = await act_with_tools(ctx, budget, _call_tool_wrap(tools), "get_diff",
                                {"store_id": state["store_id"], "date": state["date"], "limit": 20})
    if data is None:
        return await _finish(state, ctx, DEGRADED_NOTICE.format(
            reason="MCP数据工具不可用", fallback="请在管理端直接查看差异报表"),
            "LOW", [], "mcp_unavailable", deg=True)
    direct = direct_diff_answer(data, state["store_id"], state["date"])
    outputs = [json.dumps(data, ensure_ascii=False)]
    if not needs_llm_analysis(state["question"]):
        return await _finish(state, ctx, direct["answer"], "HIGH", outputs)
    try:
        llm = main_llm()
        budget.charge_call(ctx.token_estimate + 600)
        result = await llm.ainvoke("/no_think " + ctx.assembled() +
                                   "\n请基于以上工具数据做归因解读, 数字只能引用数据中的值。")
        budget.record_success()
        return await _finish(state, ctx,
                             direct["answer"] + "\n\n【归因解读】\n" + str(result.content),
                             "HIGH", outputs)
    except BudgetExceeded as e:
        return await _finish(state, ctx, reflect_on_budget(e, direct["answer"]),
                             "HIGH", outputs, "budget_degraded")

def _call_tool_wrap(tools):
    async def _f(name, args):
        return await _call_tool(tools, name, args)
    return _f

async def node_procurement(state: AgentState, config) -> dict:
    """采购专家(人在环): 查单/比价直答; 生成建议单解析受Budget保护"""
    tools = config["configurable"]["mcp_tools"]
    ctx = _ctx_of(state)
    q = state["question"]
    outputs = []
    if ("建议单" in q) or ("查看" in q) or ("待审批" in q) or ("比价" not in q and parse_proc_request(q)["qty"] is None):
        data = await act_with_tools(ctx, Budget(), _call_tool_wrap(tools), "get_suggestions",
                                    {"store_id": state["store_id"], "status": "DRAFT"})
        if data is None:
            return await _finish(state, ctx, DEGRADED_NOTICE.format(
                reason="采购工具不可用", fallback="请在管理端处理采购建议单"),
                "LOW", [], "mcp_unavailable", deg=True)
        outputs.append(json.dumps(data, ensure_ascii=False))
        sug = data.get("suggestions") or []
        buf = [f"【门店{state['store_id']} 待审批采购建议单】共{len(sug)}条:"]
        for s in sug[:8]:
            buf.append(f"· #{s.get('id')} {s.get('name_std')} {s.get('suggest_qty')}{s.get('unit_code')} "
                       f"→ {s.get('sup_name') or '待指派供应商'} 参考价{s.get('est_price')}")
        buf.append("审批请到管理端【采购建议】页(人在环: AI仅生成DRAFT, 不自动下单)。")
        return await _finish(state, ctx, "\n".join(buf) if sug else "当前无待审批建议单。",
                             "HIGH", outputs)
    req = parse_proc_request(q)
    if req["qty"] is None:
        return await _finish(state, ctx, "请告诉我采购数量, 例如: \"帮7号店采购50公斤鲈鱼\"。",
                             "MEDIUM", [])
    ing = await _call_tool(tools, "get_ingredient", {"name_or_alias": req["ing_hint"]})
    matches = (ing or {}).get("matches") or []
    if not matches:
        return await _finish(state, ctx,
                             f"未匹配到食材\"{req['ing_hint']}\", 请使用标准名称或别名重试。",
                             "MEDIUM", [], "ingredient_not_found")
    name = matches[0].get("name_std")
    data = await act_with_tools(ctx, Budget(), _call_tool_wrap(tools), "suggest_po",
                                {"store_id": state["store_id"], "ing_name": name, "qty_kg": req["qty"]})
    if data is None or data.get("error"):
        return await _finish(state, ctx, DEGRADED_NOTICE.format(
            reason="建议单生成失败", fallback="请在管理端手动创建"),
            "LOW", [], "suggest_failed", deg=True)
    outputs.append(json.dumps(data, ensure_ascii=False))
    sug = data.get("suggestion") or {}
    buf = [f"【采购建议单已生成】{name} {req['qty']}kg",
           f"· 供应商: {data.get('supplier') or '待人工指派(无合格历史比价)'}",
           f"· 参考价: {data.get('estPrice')} 元/kg",
           f"· 单号: #{sug.get('id')} 状态: DRAFT",
           "· 人在环: 等待采购主管在管理端审批(APPROVE后才会生成正式采购单)"]
    return await _finish(state, ctx, "\n".join(buf), "HIGH", outputs)

async def node_forecast(state: AgentState, config) -> dict:
    """预测专家: get_forecast直答(置信度+依赖声明透出)"""
    tools = config["configurable"]["mcp_tools"]
    ctx = _ctx_of(state)
    req = parse_proc_request(state["question"])
    hint = req["ing_hint"]
    if not hint:
        return await _finish(state, ctx, "请告诉我预测哪种食材, 例如: \"预测7号店下周鲈鱼的需求\"。",
                             "MEDIUM", [], "need_ingredient")
    data = await act_with_tools(ctx, Budget(), _call_tool_wrap(tools), "get_forecast",
                                {"store_id": state["store_id"], "ing_name": hint, "days": 7})
    if data is None or data.get("error"):
        return await _finish(state, ctx,
                             f"未匹配到食材\"{hint}\"或预测服务暂不可用, 请使用标准名称重试。",
                             "MEDIUM", [], "forecast_failed")
    outputs = [json.dumps(data, ensure_ascii=False)]
    dep = data.get("dependency") or {}
    buf = [f"【{hint} 未来7天需求预测】门店{state['store_id']} (方法: 加权移动平均×周内因子×趋势)"]
    conf = None
    for d in data.get("days", [])[:7]:
        if d.get("degraded"):
            buf.append(f"· {d['date']}: 预测不可用 — {d.get('reason')}; {d.get('fallback')}")
        else:
            conf = d.get("confidence")
            buf.append(f"· {d['date']}: {d['demand_gram']/1000:.1f}kg (回测MAPE {d.get('mape')}%)")
    if dep.get("degraded"):
        buf.append(f"⚠️ 数据依赖: {dep.get('reason')} → 已按声明降级输出")
    if conf:
        buf.append(f"置信度: {conf} (HIGH: MAPE≤20% / MEDIUM: ≤35% / LOW: >35%)")
    return await _finish(state, ctx, "\n".join(buf), conf or "LOW", outputs)

async def node_fallback(state: AgentState, config) -> dict:
    """三级缓存: Redis精确→Milvus语义(≥0.93命中)→LLM(Budget管控, 答后后台回写)"""
    ctx = _ctx_of(state)
    hit = faq_hit(config["configurable"].get("redis"), state["question"])
    if hit:
        return await _finish(state, ctx, hit["answer"] + "\n\n(语义缓存命中, 仅供参考)",
                             "HIGH", [], "faq_cache", cache=True)
    sem = semantic.search_similar(state["question"])
    if sem and sem["mode"] == "hit":
        return await _finish(state, ctx, sem["answer"] + f"\n\n(语义缓存命中 相似度{sem['score']})",
                             "HIGH", [], "semantic_cache", cache=True)
    budget: Budget = config["configurable"].get("budget") or Budget()
    try:
        llm = config["configurable"]["fallback_llm"]
        budget.charge_call(ctx.token_estimate + 400)
        result = await llm.ainvoke(
            "/no_think " + ctx.assembled() +
            "\n回答要求: 通用知识类50字以内; 涉及具体数据(用量/价格/差异)时告知"
            "'请在用量差异看板查看或使用分析功能', 不得编造数字。")
        budget.record_success()
        answer_text = str(result.content)
        semantic.add_pair_async(state["question"], answer_text)   # 后台回写学习(ADR-0013)
        prefix = f"(相近问答参考 相似度{sem['score']}: {sem['answer'][:60]})\n" if sem else ""
        return await _finish(state, ctx, prefix + answer_text,
                             "HIGH" if sem else "MEDIUM", [],
                             "semantic_ref" if sem else "non_data_intent")
    except BudgetExceeded as e:
        return await _finish(state, ctx, reflect_on_budget(e, None), "LOW", [],
                             "budget_degraded", deg=True)

def build_graph():
    g = StateGraph(AgentState)
    g.add_node("route", node_route)
    g.add_node("diff_agent", node_diff_agent)
    g.add_node("procurement", node_procurement)
    g.add_node("forecast", node_forecast)
    g.add_node("fallback", node_fallback)
    g.add_edge(START, "route")
    g.add_conditional_edges("route",
        lambda s: {"diff_agent": "diff_agent",
                   "procurement_agent": "procurement",
                   "forecast_agent": "forecast"}.get(s["intent"], "fallback"),
        {"diff_agent": "diff_agent", "procurement": "procurement",
         "forecast": "forecast", "fallback": "fallback"})
    for n in ("diff_agent", "procurement", "forecast"):
        g.add_edge(n, END)          # verify已内联于_finish(harness)
    g.add_edge("fallback", END)
    return g.compile()

graph = build_graph()
