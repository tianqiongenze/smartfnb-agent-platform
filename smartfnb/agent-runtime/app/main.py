"""Litestar 应用(全异步) + Agent Harness入口(V2: R1收编)"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from datetime import date as _date
from typing import AsyncGenerator

from litestar import Litestar, post, get
from litestar.response import Stream
from litestar.status_codes import HTTP_200_OK

from .graph import graph, _redis
from .llm import fast_llm
from .mcp_client import load_tools
from .direct import faq_hit
from .harness import Budget, run_eval
from .a2a import AGENT_CARD
from . import otel_util

MCP_TOOLS = []
REDIS_CLIENT = None

@asynccontextmanager
async def _lifespan(app: Litestar) -> AsyncGenerator[None, None]:
    global MCP_TOOLS, REDIS_CLIENT
    try:
        MCP_TOOLS = await load_tools()
        print(f"MCP tools loaded: {[t.name for t in MCP_TOOLS]}", flush=True)
    except Exception as e:
        MCP_TOOLS = []
        print(f"MCP tools load FAILED (agent will degrade): {e}", flush=True)
    try:
        REDIS_CLIENT = _redis()
        print("Redis FAQ cache connected", flush=True)
    except Exception as e:
        REDIS_CLIENT = None
        print(f"Redis cache disabled: {e}", flush=True)
    yield
    MCP_TOOLS = []

def _sse(obj: dict) -> str:
    return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"

@get("/health")
async def health() -> dict:
    return {"status": "ok", "mcp_tools": len(MCP_TOOLS), "harness": "v2",
            "models": {"main": os.getenv("LLM_MAIN", "qwen3:8b"),
                       "fast": os.getenv("LLM_FAST", "qwen3:4b")}}

@post("/api/agent/chat", status_code=HTTP_200_OK, media_type="text/event-stream")
async def chat(data: dict) -> Stream:
    """SSE 流式对话: harness循环(路由→专家[ACT+VERIFY内联]→输出), 全程Budget管控"""
    question = str(data.get("question", "")).strip()
    store_id = int(data.get("storeId", 7))
    day = str(data.get("date") or _date.today())
    if not question:
        raise ValueError("question required")

    async def gen():
        budget = Budget()
        yield _sse({"event": "start", "intent_hint": question[:50]})
        config = {"configurable": {"mcp_tools": MCP_TOOLS, "fallback_llm": fast_llm(),
                                   "redis": REDIS_CLIENT, "budget": budget}}
        try:
            async for chunk in graph.astream(
                    {"question": question, "store_id": store_id, "date": day,
                     "tool_outputs": [], "degraded": False, "cache_hit": False,
                     "budget_snapshot": {}},
                    config=config, stream_mode="updates"):
                for node, delta in chunk.items():
                    if node == "route":
                        yield _sse({"event": "route", "intent": delta["intent"]})
                    elif delta.get("answer") is not None:
                        ev = {"event": "answer", "node": node,
                              "answer": delta["answer"],
                              "confidence": delta.get("confidence", "LOW"),
                              "budget": budget.snapshot}
                        if delta.get("cache_hit"):
                            ev["cache_hit"] = True
                        yield _sse(ev)
            yield _sse({"event": "done"})
        except Exception as e:   # 智能体故障不静默(反P4)
            yield _sse({"event": "error", "message": str(e)[:300],
                        "fallback": "请稍后重试或查看管理端差异报表"})
    return Stream(gen(), media_type="text/event-stream")

@post("/api/agent/diff-explain")
async def diff_explain(data: dict) -> dict:
    """非流式: 差异归因(供预警推送直接调用)"""
    budget = Budget()
    config = {"configurable": {"mcp_tools": MCP_TOOLS, "fallback_llm": fast_llm(),
                               "redis": REDIS_CLIENT, "budget": budget}}
    state = {"question": f"分析{data.get('date')}的用量差异并归因",
             "store_id": int(data.get("storeId", 7)),
             "date": str(data.get("date") or _date.today()),
             "tool_outputs": [], "degraded": False, "cache_hit": False,
             "budget_snapshot": {}}
    final = None
    async for chunk in graph.astream(state, config=config, stream_mode="updates"):
        for node, delta in chunk.items():
            if delta.get("answer"):
                final = delta
    return {"answer": final["answer"] if final else "(无输出)",
            "confidence": final.get("confidence", "LOW") if final else "LOW"}

@get("/api/agent/cache-check")
async def cache_check(question: str) -> dict:
    """诊断: FAQ缓存是否命中"""
    hit = faq_hit(REDIS_CLIENT, question)
    return {"question": question, "hit": bool(hit)}

@get("/api/agent/eval")
async def eval_run() -> dict:
    """R1 评测回路: 评审集回归(意图/守卫/解析), 确定性路径不耗LLM"""
    r = run_eval()
    return {"total": r.total, "intent_acc": r.intent_acc,
            "guard_pass": r.guard_pass, "parse_pass": r.parse_pass,
            "failures": r.failures[:10]}


@get("/.well-known/agent-card.json")
async def agent_card() -> dict:
    """R5 A2A: 能力发现(AgentCard)"""
    return AGENT_CARD

@post("/a2a")
async def a2a_message(data: dict) -> dict:
    """R5 A2A: message/send任务委派(JSON-RPC over HTTP)"""
    import traceback as _tb
    try:
        return await _a2a_impl(data)
    except Exception as e:
        return {"jsonrpc": "2.0", "id": data.get("id"),
                "error": {"code": -32603,
                          "message": f"{type(e).__name__}: {e}",
                          "data": _tb.format_exc()[-800:]}}

async def _a2a_impl(data: dict) -> dict:
    with otel_util.gen_ai_agent("a2a_delegate"):
        if data.get("method") != "message/send":
            return {"jsonrpc": "2.0", "id": data.get("id"),
                    "error": {"code": -32601, "message": "method not found"}}
        msg = (data.get("params") or {}).get("message") or {}
        text = ""
        for p in msg.get("parts", []):
            if p.get("type") == "text":
                text = p.get("text", ""); break
        if not text:
            text = str(msg.get("content", ""))
        md = msg.get("metadata") or {}
        budget = Budget()
        config = {"configurable": {"mcp_tools": MCP_TOOLS,
                                   "fallback_llm": fast_llm(),
                                   "redis": REDIS_CLIENT, "budget": budget}}
        state = {"question": text,
                 "store_id": int(md.get("storeId", 7)),
                 "date": str(md.get("date") or _date.today()),
                 "tool_outputs": [], "degraded": False, "cache_hit": False,
                 "budget_snapshot": {}}
        answer, confidence = "", "LOW"
        async for chunk in graph.astream(state, config=config, stream_mode="updates"):
            for node, delta in chunk.items():
                if delta.get("answer"):
                    answer, confidence = delta["answer"], delta.get("confidence", "LOW")
        task_id = f"a2a-{int(__import__('time').time()*1000)}"
        return {"jsonrpc": "2.0", "id": data.get("id"),
                "result": {"id": task_id, "contextId": "fnb",
                           "status": {"state": "completed"},
                           "artifacts": [{"parts": [{"type": "text",
                                                     "text": answer + '\n' + "(confidence=" + confidence + ")"}]}]}}

app = Litestar(route_handlers=[health, chat, diff_explain, cache_check, eval_run,
                              agent_card, a2a_message],
               lifespan=[_lifespan])
