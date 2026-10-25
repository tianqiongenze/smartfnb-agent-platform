"""Phase1: 智能体工具直答与FAQ语义缓存(纯函数可测)
工具直答: 数据类问题用MCP工具结果生成模板回答(毫秒级, 零幻觉), LLM仅做归因解读。
FAQ缓存: 问题md5精确命中Redis L2(P0已灌1万种子), 未命中才走LLM。
"""
from __future__ import annotations

import hashlib
import json

def faq_cache_key(question: str) -> str:
    return "fnb:qa:" + hashlib.md5(question.strip().encode()).hexdigest()

def faq_hit(r, question: str) -> dict | None:
    """r: redis client(可为None=禁用)。命中返回 {answer, cache_hit: True}"""
    if r is None:
        return None
    try:
        raw = r.get(faq_cache_key(question))
        if not raw:
            return None
        obj = json.loads(raw)
        return {"answer": obj.get("a", ""), "cache_hit": True, "confidence": "HIGH"}
    except Exception:
        return None

def kg(g: float | int | None) -> str:
    """克→友好显示: ≥1000g显示kg"""
    if g is None:
        return "-"
    return f"{g/1000:.1f}kg" if g >= 1000 else f"{g:.0f}g"

def direct_diff_answer(tool_result: dict, store_id: int, date: str, top_n: int = 5) -> dict:
    """用 get_diff 工具的结构化结果直接生成回答(反幻觉: 数字全部来自工具, 带SQL溯源)。
    返回 {answer, confidence: HIGH, tool_traced: True}"""
    lines = tool_result.get("lines") or []
    if not lines:
        return {"answer": f"{date} 门店{store_id} 无差异数据(可能未营业或数据未生成)。",
                "confidence": "MEDIUM", "tool_traced": True}
    lines = sorted(lines, key=lambda x: abs(x.get("diff_pct") or 0), reverse=True)
    top = lines[:top_n]
    high = [l for l in lines if abs(l.get("diff_pct") or 0) > 30]
    buf = [f"【{date} 门店{store_id} 用量差异报告】(数据来源: MCP工具get_diff, SQL可溯源)"]
    for l in top:
        buf.append(f"· {l.get('name_std')}({l.get('category')}): 理论{kg(l.get('theo_gram'))} / "
                   f"实际{kg(l.get('actual_gram'))} / 差异{l.get('diff_pct')}%"
                   + (" ⚠️HIGH" if abs(l.get("diff_pct") or 0) > 30 else ""))
    if high:
        buf.append(f"其中 {len(high)} 项差异超过30%, 建议核查收货称重与领料登记。")
    buf.append(f"共返回 {len(lines)} 项有用量数据的食材, 本次展示Top{len(top)}。")
    return {"answer": "\n".join(buf), "confidence": "HIGH", "tool_traced": True}

def needs_llm_analysis(question: str) -> bool:
    """归因解读类问题才进LLM(其余工具直答)"""
    keys = ("为什么", "原因", "分析", "归因", "解读", "怎么降", "如何降", "建议")
    return any(k in question for k in keys)
