"""R7 OTel GenAI语义约定span(轻量SDK, Console/OTLP双导出, ADR-0012)
span对象经_SpanCtx包装: with + set_attribute 双兼容, 采集端不可用时noop。"""
from __future__ import annotations

import os

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    _provider = TracerProvider(resource=Resource.create({
        "service.name": os.getenv("OTEL_SVC", "agent-runtime")}))
    # ADR-0012: 本集群CPU代次<x86-64-v2, 官方collector镜像无法exec →
    # Console导出器(span→Pod stdout→Loki), OTLP端点可用时叠加
    _provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    _otlp = os.getenv("OTEL_ENDPOINT", "")
    if _otlp:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            _provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=_otlp)))
        except Exception:
            pass
    trace.set_tracer_provider(_provider)
    _tracer = trace.get_tracer("fnb.genai")
    OTEL_ON = True
except Exception:
    OTEL_ON = False

class _SpanCtx:
    def __init__(self, span):
        self._s = span
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        try:
            self._s.end()
        except Exception:
            pass
        return False
    def set_attribute(self, k, v):
        try:
            self._s.set_attribute(k, v)
        except Exception:
            pass

def gen_ai_agent(intent: str = "") -> _SpanCtx:
    if not OTEL_ON:
        return _SpanCtx(None)
    try:
        sp = _tracer.start_span("gen_ai.agent")
        sp.set_attribute("gen_ai.system", "smartfnb")
        sp.set_attribute("gen_ai.agent.name", "fnb-orchestrator")
        sp.set_attribute("fnb.intent", intent)
        return _SpanCtx(sp)
    except Exception:
        return _SpanCtx(None)

def gen_ai_tool(name: str = "", ok: bool = True) -> _SpanCtx:
    if not OTEL_ON:
        return _SpanCtx(None)
    try:
        sp = _tracer.start_span("gen_ai.tool")
        sp.set_attribute("gen_ai.tool.name", name)
        sp.set_attribute("gen_ai.tool.mcp", True)
        sp.set_attribute("fnb.tool.ok", ok)
        return _SpanCtx(sp)
    except Exception:
        return _SpanCtx(None)

def gen_ai_llm(model: str = "", prompt_tokens: int = 0, completion_tokens: int = 0) -> _SpanCtx:
    if not OTEL_ON:
        return _SpanCtx(None)
    try:
        sp = _tracer.start_span("gen_ai.completion")
        sp.set_attribute("gen_ai.request.model", model)
        sp.set_attribute("gen_ai.usage.input_tokens", prompt_tokens)
        sp.set_attribute("gen_ai.usage.output_tokens", completion_tokens)
        return _SpanCtx(sp)
    except Exception:
        return _SpanCtx(None)
