# smartfnb/gitops — Flux 落地面（ADR-0017，2026-11-15）

本目录是 **flux-system bootstrap 面**（不进 fnb-apps 构建，避免自举环）。应用面在 `../deploy/`。

## 文件清单

| 文件 | 用途 |
|---|---|
| `flux-system-install.yaml` | `flux install --export --registry=10.167.2.175:30500/flux` 生成的 flux-system 全量安装清单（6 控制器 + CRD + RBAC + NP），镜像已改写为本地 registry；控制器 requests 为上游默认小值（source=50m/64Mi，其余=100m/64Mi，limits 1cpu/1Gi）。**重复 apply 幂等。** |
| `flux-system-ocirepository.yaml` | OCIRepository `smartfnb-deploy`：`oci://10.167.2.175:30500/flux/smartfnb-deploy`，tag `main`，`insecure: true`（本地 registry 为 plain HTTP）。 |
| `flux-system-kustomization.yaml` | Kustomization `fnb-apps`：sourceRef=上述 OCIRepository，`targetNamespace: fnb-prod`，wait+healthChecks（agent-runtime/svc-portal），prune=false（首期），interval 5m。 |

## bootstrap 步骤（新环境重建）

```bash
# 0) 前置: 本地 registry 已有 flux/* 6 控制器镜像(镜像改写记录见 docs/07 ADR-0017 落地记录);
#    master /usr/local/bin/flux v2.3.0(k8s 1.28 兼容上限版本)
# 1) 安装 flux-system
kubectl apply -f smartfnb/gitops/flux-system-install.yaml
kubectl -n flux-system rollout status deploy/source-controller
# 2) 首个 artifact(由仓库 deploy/ 目录打包)
flux push artifact oci://10.167.2.175:30500/flux/smartfnb-deploy:main \
  --path=smartfnb/deploy --source=smartfnb-repo --revision="main@sha1:<短SHA>"
# 3) 源与 Kustomization
kubectl apply -f smartfnb/gitops/flux-system-ocirepository.yaml
kubectl apply -f smartfnb/gitops/flux-system-kustomization.yaml
# 4) 密钥(README 方式b, flux 不管理 Secret)
export SOPS_AGE_KEY_FILE="D:/projects/连锁餐饮智能体/.sops.agekey"
sops -d smartfnb/deploy/secrets.enc.yaml | kubectl apply -f -
# 5) 验证
flux get kustomizations -n flux-system     # fnb-apps READY=True
flux diff kustomization fnb-apps --path smartfnb/deploy   # 期望空输出(rc=0)=无漂移
```

## 日常发布路径

改 `smartfnb/deploy/*.yaml` → commit → 重推 artifact(`flux push artifact ... :main --path=smartfnb/deploy`)→
`flux reconcile kustomization fnb-apps -n flux-system --with-source`，Flux 自动收敛；回滚=`git revert` 后同样重推。
**禁止 kubectl 直改 fnb-prod 造成漂移**（docs/10 教训6；应急路径见 ADR-0017 revert 语义）。

## 构建口径（详见 ../deploy/kustomization.yaml 头注）

15 个 yaml − 14-otel(ADR-0012)；另剥离：otel-collector-config.yaml(非 k8s 清单)、secrets.enc.yaml(SOPS 密文)、
两个占位 Secret 文档(防覆盖现网真实值)、6 个一次性 Job 文档(TTL 删除后会被复活重跑 + 完成态 Job SSA immutable 拒绝)。
