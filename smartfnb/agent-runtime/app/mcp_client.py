"""MCP 工具接入(langchain-mcp-adapters → streamable-http, 2026标准传输)"""
import os
from langchain_mcp_adapters.client import MultiServerMCPClient

MCP_URL = os.getenv("MCP_URL", "http://mcp-fnb-tools:8000/mcp")

async def load_tools():
    client = MultiServerMCPClient({
        "fnb": {"url": MCP_URL, "transport": "streamable_http"}
    })
    return await client.get_tools()
