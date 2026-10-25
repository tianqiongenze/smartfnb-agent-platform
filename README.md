# 连锁餐饮智能体平台（智慧餐链 SmartF&B Agent Platform）

> 高职教学/生产双用途全栈交付：**DDD + TOGAF + MCP + A2A + Agent Harness + World Model + 事件驱动 + 语义缓存**，K6+Locust 七梯度性能取证（含 **100,000 并发连接 0 错误**），TiDB 读写分离 + 多级缓存，1.34 亿行模拟数据，43/43 功能用例通过。

[![Status](https://img.shields.io/badge/status-V2.1%20GO-brightgreen)]() [![Tests](https://img.shields.io/badge/functional-43%2F43-success)]() [![Load](https://img.shields.io/badge/K6%2BLocust-7%20gradients-blue)]() [![Repo](https://img.shields.io/badge/visibility-private-important)]()

## 一、这是什么

以一份真实失败复盘（《我最惨的AI项目复盘》：120万签约→退款）的 **7 大教训为设计约束**，在 2 节点 K8S（无 GPU、与教学平台混部）上完整落地的连锁餐饮智能体平台：

- **业务切口**：高价值食材"理论用量(销售×BOM) vs 实际领用"差异监控 → 秒级事件预警 → 人在环采购建议闭环 → 需求预测(置信度+依赖声明)
- **智能体**：Litestar+LangGraph 编排，5 意图路由；**工具直答优先**（毫秒级、零幻觉）；LLM 仅做归因且受 **Budget 预算/熔断**管控；回答数字强制 **MCP 工具溯源校验**（"8公斤牛肉"反幻觉回归测试守护）
- **2026 前沿落地**：MCP（streamable-http, 协议 2025-11-25）、A2A（AgentCard+message/send）、Agent Harness（budget/context/loop/eval 四件套+100条评测回路三100%）、World Model（门店数字孪生蒙特卡洛采购推演）、OTel GenAI 语义约定 span、Pulsar 事件驱动（T+1→0.3秒）

## 二、仓库结构

```
docs/                       全套工程文档(GB/T 8567风格)
  00-总体方案V1.0.md          TOGAF四架构+四阶段Go/No-Go(V2.1变更记录在卷首)
  01-Phase0交付报告.md        数据资产评估+LLM实测SLO(先测后诺)
  02-执行记录.md              时间线+镜像清单+问题全留痕
  03-上线报告.md              上线检查单+V2.1附录(维持GO)
  04-多视角审查与重构方案.md   五视角打分(7.10/10)+R1-R10重构定义
  05-功能测试报告.md          43/43用例六域
  06-性能测试报告.md          七梯度矩阵+饱和点+10万并发取证
  07-ADR集.md                ADR-0009~0015
smartfnb/
  agent-runtime/            Litestar+LangGraph+Harness+语义缓存+A2A+OTel
  java/                     5服务 SpringBoot3.3+Undertow+JDK21虚拟线程(recipe/inventory/procurement/member/portal)
  mcp-fnb-tools/            FastMCP 12工具(SQL可溯源)
  forecast-service/         需求预测(MAPE置信度+数据依赖声明)
  world-model/              蒙特卡洛仿真(采购量9档推演+p10/p50/p90)
  tools/                    1.34亿行数据生成/质量门禁/事件枢纽/语义预热/Hermes对比
  web-admin/ h5-store/ h5-member/   管理端+门店扫码+C端会员(Vue3/Element Plus)
  tests/perf/               K6×7脚本+Locust×2+梯度编排器
  deploy/                   K8S清单(namespace fnb-prod)+run.sh一键重放
  contracts/features/       Gherkin验收场景(BDD)
  db/                       TiDB DDL/索引/视图/预计算
参考资料/                    原始复盘PDF(本地保留,未入库——版权属原作者)
```

## 三、快速开始（已有同类 K8S 集群）

```bash
# 1) 修改 deploy/ 内 registry/数据库地址后
./deploy/run.sh all        # 镜像→建库→1.34亿数据→warmup→基准→部署→验证
./tests/perf/run_perf.sh s1 100 60    # K6梯度压测
```

访问：管理端 `/30250`（admin/admin123）｜GraphiQL `/30251/graphiql`｜智能体SSE `POST :30252/api/agent/chat`

## 四、性能摘要（K6 0.54 + Locust 2.47 实测）

| 场景 | 峰值 | P95 | 备注 |
|---|---|---|---|
| S5 会员(1KVU) | 3764 RPS | 86ms | 未饱和 |
| S4 写入+事件(500VU) | 1382 RPS | 395ms | Pulsar发布零感知 |
| 开放模型饱和点 | ≈1.2K RPS/端点 | 13s@3K目标 | 如实取证 |
| **风暴 100K VU** | **10万并发连接 0 错误** | 42s(排队) | 连接容量≠服务容量,双口径陈述 |

## 五、反模式防线（来自失败复盘的7条教训→制度）

| 教训 | 落点 |
|---|---|
| 签约前无数据评估 | Phase 0门禁+每日五规则质量门禁 |
| 承诺技术指标 | 只承诺业务结果;实测定SLO |
| 一次性交付 | 四阶段Go/No-Go |
| 隐瞒问题 | 双周演示+红黄绿灯+问题全ADR/日志留痕 |
| 演示挑好数据 | MCP工具SQL溯源+指标口径随报告交付 |
| 预订数据未接入 | 预测依赖声明,缺数自动降级明示 |
| 三套数据格式 | 一品一码+别名映射+单位字典 |

## 六、相关开源项目（GitHub 检索 2026-10）

| 项目 | 相似点 |
|---|---|
| [someshj5/RestaurantOps-AI](https://github.com/someshj5/RestaurantOps-AI-Agentic-Restaurant-Operations-Platform) | LangGraph编排+库存+预测+what-if（本仓库增加了人在环审批/事件驱动/溯源反幻觉/百万级压测） |
| [rmaidza/Inventory-AI-Agent](https://github.com/rmaidza/Inventory-AI-Agent) | 随机森林预测+LangChain工具 |
| [88Rehaan88/AI-Restaurant-Analytics-Agent](https://github.com/88Rehaan88/AI-Restaurant-Analytics-Agent) | 销售分析+库存预测报表 |
| [adil-044/SouSxChef](https://github.com/adil-044/SouSxChef) | 库存/人力/预测多Agent |

## 七、安全与可见性说明

- 仓库为 **Private**：内容含教学集群内网IP/示例密码（`difyai123456` 等）与教学平台拓扑——公开前请先脱敏（`grep -rn "10.167\|difyai123456"`）。
- 原始复盘 PDF（属第三方作者"一只阿木木"版权）仅因本仓库为 Private 而随资料保存于根目录；**若转 Public 必须先移除**。

---
*五视角审查 7.10/10 → R1-R10 重构 → V2.1 维持 GO。教学场景可直接作为"AI+大数据综合实训"案例库。*
