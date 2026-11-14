# smartfnb/deploy 部署说明（密钥与恢复要点）

> 本目录清单按"仓库=真源"维护。现网任何改动必须回写清单（docs/10 教训6）。
> 密钥治理为 [O4/V4] 引入：**ConfigMap 一律不含口令**，明文值仅经 SOPS+age 加密入库，私钥不入库。

## 一、密钥清单（fnb-prod）

| Secret | 键 | 消费方 | 来源 |
|---|---|---|---|
| `fnb-redis-auth` | `REDIS_PW` | agent-runtime（03-services.yaml）、event-consumer（12-event-consumer.yaml）、redis-warmup（04-warmup-bench.yaml） | `secrets.enc.yaml` 加密保存，部署时解密注入 |
| `fnb-secret` | `jwt-secret` | (鉴权相关服务) | 01-infra-jobs.yaml 中为 `<SET_AT_APPLY>` 占位，**部署时必须覆盖注入**；历史明文值加密保留于 `secrets.enc.yaml` 第二个文档（fnb-secret 的 `jwt-secret` 字段，建议轮换） |

## 二、SOPS + age 密钥文件

- **私钥**：`D:/projects/连锁餐饮智能体/.sops.agekey`（根目录，**已加入 .gitignore，绝不入库**）。丢失该文件 = 加密字段永久不可解。
- **公钥**：入库于本目录 `.sops.yaml`（creation rule 的 `age:` recipient）。
- **加密文件**：本目录 `secrets.enc.yaml`（入库；文件内含 sops 元数据段，`stringData` 字段全部为 ENC[...] 密文）。

### 加密 / 解密命令（Windows 本机，sops v3.13.3 + age v1.3.2，安装于 ~/bin）

```bash
export SOPS_AGE_KEY_FILE="D:/projects/连锁餐饮智能体/.sops.agekey"

# 解密查看（stdout）
sops -d smartfnb/deploy/secrets.enc.yaml

# 编辑后重新加密（in-place，走 .sops.yaml creation rule 定位公钥）
sops smartfnb/deploy/secrets.enc.yaml

# 用本地明文暂存文件重新加密（绕过编辑器）：
#   sops -e smartfnb/deploy/secrets.enc.yaml > tmp.enc.yaml && mv tmp.enc.yaml smartfnb/deploy/secrets.enc.yaml

# 解密后直接 apply（部署路径 a）
sops -d smartfnb/deploy/secrets.enc.yaml | kubectl apply -f -
```

> 私钥换机时：把 `.sops.agekey` 拷贝到新机同路径（或 `SOPS_AGE_KEY_FILE` 指向任意可读路径）。
> 新增 recipient（多机协作）：`age-keygen` 生成新密钥 → `.sops.yaml` 追加 recipient → `sops updatekeys smartfnb/deploy/secrets.enc.yaml`。

## 三、部署时 Secret 注入（两种方式二选一）

```bash
# 方式 a（推荐）：kubectl create secret 覆盖注入（真实口令取值：sops -d secrets.enc.yaml）
kubectl -n fnb-prod create secret generic fnb-redis-auth \
  --from-literal=REDIS_PW="<真实口令>"
kubectl -n fnb-prod create secret generic fnb-secret \
  --from-literal=jwt-secret="<真实JWT密钥>"

# 方式 b：SOPS 解密后 apply（fnb-redis-auth 的真实值在加密文件内）
sops -d smartfnb/deploy/secrets.enc.yaml | kubectl apply -f -
```

> 注意顺序：`run.sh db` 会 `apply -f deploy/01-infra-jobs.yaml`，其中两个 Secret 为占位/加密值——
> **必须先执行上面注入，或注入放在 apply 之后覆盖**（apply 会以占位值覆盖手工 Secret，故推荐顺序：`run.sh db` → 上述注入 → 再跑 warmup/svc）。
> `kubectl apply` 01-infra-jobs.yaml 会把 `<SET_AT_APPLY>` 写回 Secret，任何"先注入后 apply"都需重新注入。

## 四、与本目录相关的已知处置

- `14-otel.yaml`：**不可部署**（ADR-0012：collector 要求 x86-64-v2，本集群 Xeon E5 exec 必失败），保留仅为历史，勿加入部署序列。
- `fnb-sql` ConfigMap 的 `001_schema.sql` 与仓库 `smartfnb/db/001_schema.sql` 字节一致（19 表，含 member_coupons/member_points；[O1/V4] 对齐）。
- `run.sh build_images` 的 tag 与 `deploy/*.yaml` 清单引用一致并经 registry `/v2/<repo>/tags/list` 核对（[O2/V4] 对齐）。

## 五、GitOps（ADR-0017 已实施, 2026-11-15）

- 本目录清单由 Flux Kustomization `fnb-apps`(flux-system)经 **OCI artifact**(10.167.2.175:30500/flux/smartfnb-deploy, tag main, insecure)持续 reconcile, drift=0 为达标态。
- **构建口径**见本目录 `kustomization.yaml` 头注: 15 yaml − 14-otel(ADR-0012); 另剥离 otel-collector-config.yaml(非 k8s 清单)、secrets.enc.yaml(SOPS 密文)、两个 `<SET_AT_APPLY>` 占位 Secret 文档(防覆盖现网真实值)、6 个一次性 Job 文档(TTL 删除后会被复活重跑 + 完成态 Job SSA immutable 拒绝)。
- **日常变更路径**: 改清单 → commit → `flux push artifact oci://10.167.2.175:30500/flux/smartfnb-deploy:main --path=smartfnb/deploy --source=smartfnb-repo --revision="main@sha1:<短SHA>"` → Flux 自动收敛; **禁止 kubectl 直改造成漂移**(docs/10 教训6; 应急路径见 ADR-0017 revert 语义)。
- bootstrap 与验证命令: 见 `../gitops/README.md`。
