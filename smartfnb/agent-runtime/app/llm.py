"""LLM 接入: MVP 直连 Ollama(OpenAI兼容); LiteLLM 网关接入位已预留(方案§8.4分级路由)"""
import os
from langchain_ollama import ChatOllama

OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://fnb-ollama.fnb-prod.svc.cluster.local:11434")
LLM_MAIN = os.getenv("LLM_MAIN", "qwen3:8b")      # 业务分析(默认)
LLM_FAST = os.getenv("LLM_FAST", "qwen3:4b")      # 简单意图/寒暄
LLM_HEAVY = os.getenv("LLM_HEAVY", "qwen3:14b")   # 复杂归因(排队)
# Phase-0实测(反P2): 该环境CPU推理 4b≈5 tok/s, 8b≈2.8 tok/s, 24线程最优;
# 默认线程数(=物理核数)会超出cgroup限额导致10倍抖动, 必须显式固定
NUM_THREAD = int(os.getenv("LLM_NUM_THREAD", "24"))

def main_llm(streaming: bool = False) -> ChatOllama:
    return ChatOllama(model=LLM_MAIN, base_url=OLLAMA_BASE,
                      temperature=0.2, streaming=streaming, num_thread=NUM_THREAD,
                      num_predict=int(os.getenv("LLM_MAX_PREDICT", "600")))

def fast_llm() -> ChatOllama:
    return ChatOllama(model=LLM_FAST, base_url=OLLAMA_BASE, temperature=0.3, num_thread=NUM_THREAD,
                      num_predict=int(os.getenv("LLM_FAST_PREDICT", "256")))

def heavy_llm() -> ChatOllama:
    return ChatOllama(model=LLM_HEAVY, base_url=OLLAMA_BASE, temperature=0.1, num_thread=NUM_THREAD,
                      num_predict=int(os.getenv("LLM_MAX_PREDICT", "600")))
