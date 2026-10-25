# SmartF&B 连锁餐饮智能体平台 · Monorepo

Phase-0 交付（2026-10-24）。总体方案见 `../docs/00-总体方案V1.0.md`（V1.1 决策已锁定）。

## 目录结构

```
smartfnb/
├── db/                     TiDB DDL/索引/视图（fnb 库）
├── tools/
│   ├── data-gen/           1.25亿行模拟数据生成器(8分片, 确定性可重放)
│   ├── redis-warmup/       Redis集群预热(菜单/BOM/库存快照/热点会员/QA种子, 幂等可重放)
│   ├── llm-bench/          LLM吞吐实测(Phase-0 SLO: 先测后诺)
│   └── Dockerfile          工具镜像(单镜像多命令)
├── java/                   Maven reactor(Java21+SpringBoot3.3+Undertow+虚拟线程, 无Tomcat)
│   ├── recipe/             菜品与BOM上下文(主数据/单位字典/别名)
│   ├── inventory/          库存与浪费上下文(差异计算/预警, TiDB读写分离双数据源)
│   ├── portal/             GraphQL BFF + SSE代理 + JWT登录
│   └── Dockerfile.*        运行镜像(eclipse-temurin 25-jre)
├── agent-runtime/          Litestar + Granian + LangGraph(路由→差异专家ReAct→数字溯源Review)
├── mcp-fnb-tools/          FastMCP Server(streamable-http): 差异/浪费/主数据工具, SQL可溯源
├── web-admin/              Vue3 + Element Plus(差异看板/预警/智能体对话SSE)
├── contracts/
│   └── features/           Gherkin验收场景(BDD)
└── deploy/
    ├── 01-infra-jobs.yaml  命名空间/配置/建库建表Job/TiDB读源Service
    ├── 02-datagen.yaml     数据生成Job(8分片Indexed)
    ├── 03-postload.yaml    索引+视图Job
    ├── 04-warmup-bench.yaml warmup/LLM基准/预警CronJob
    ├── 03-services.yaml    6个服务Deployment/Service/Ingress
    └── run.sh              总编排(images|db|datagen|indexes|warmup|bench|svc|verify|all)
```

## 执行（在 k8s-master /opt/fnb/smartfnb）

```bash
./deploy/run.sh all      # 全流程: 镜像→建库→1.25亿数据→索引→warmup→LLM基准→部署→验证
./deploy/run.sh verify   # 端到端验证
```

## 访问入口

| 端 | 地址 | 凭据 |
|---|---|---|
| 管理Web（差异看板/预警/智能体） | http://10.167.2.175:30250 | admin/admin123 |
| H5门店领料扫码 | http://10.167.2.175:30254 | — |
| C端会员助手（点餐/积分/券） | http://10.167.2.175:30255 | — |
| GraphQL(GraphiQL) | http://10.167.2.175:30251/graphiql | — |
| 智能体SSE | POST http://10.167.2.175:30252/api/agent/chat | — |
| Ingress | http://fnb.local（hosts解析到175） | — |

## V2.1 重构（2026-10-25）

| 项 | 落点 | 验证 |
|---|---|---|
| Agent Harness(R1) | app/harness/ 四件套+evalset 100条 | 意图/守卫/解析=100% |
| 事件驱动(R2) | tools/event-consumer + Pulsar | 领料→0.3s预警 |
| 语义缓存(R3) | app/semantic.py (ADR-0013) | 命中<1s HIGH |
| World Model(R4) | world-model/ 服务+MCP 2工具 | 9档推演+最优 |
| A2A(R5) | /a2a + agent-card | message/send✓ |
| OTel(R7) | otel_util (ADR-0012) | gen_ai.* span✓ |
| 前端(R8) | Ops.vue 三页+暗色 | HTTP 200 |
| 压测(R9) | tests/perf K6+Locust | 26条K6+6轮Locust |

## 三阶段完成状态（2026-10-25）

| 阶段 | 内容 | 验收 |
|---|---|---|
| P0 | 1.34亿数据/Redis集群/warmup/LLM实测 | ✅ |
| P1 | 质量门禁/H5扫码/工具直答/FAQ缓存/预警推送 | ✅ |
| P2 | 采购人在环闭环/比价选商/月报/压测(S1 2020RPS) | ✅ |
| P3 | 需求预测(置信度+依赖声明)/会员/C端H5/百万口径压测(4100+RPS全绿) | ✅ |
| 上线 | 见 docs/03-上线报告.md（GO，3项上线后两周补强项） | ✅ |

## 反模式防线映射（PDF教训 → 本仓库落点）

| 教训 | 落点 |
|---|---|
| P1 无数据评估 | tools/data-gen(可重放确定性数据) + 数据质量报告 |
| P2 超支撑承诺 | tools/llm-bench 实测定SLO |
| P5 樱桃数据 | mcp-fnb-tools 每个工具返回 SQL 溯源 |
| P6 预订未接入 | agent-runtime guards.py 降级机制 + 前置依赖声明 |
| P7 数据混乱 | ingredient.aliases 别名映射 + unit_dict 强制换算 + UnitConverterTest |
| 幻觉数字 | numeric_guard 数字溯源校验（'8公斤牛肉'回归测试） |
