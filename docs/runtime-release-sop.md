# Model Gateway 运行 / 发布 / 验收 SOP

本文档用于收口以下三类动作：

1. **运行模式切换**
2. **生产发布**
3. **闭环验收**

目标是：每次切换或发布后，都能按一套固定清单确认 **gateway、本地 UI、管理接口、业务接入方（如 StockAgents）** 全部正常。

---

## 1. 运行模式说明

### 1.1 本地直连模式

适用场景：

- 需要复用宿主机网络能力
- 私有 / 专线 / 零信任上游只能由宿主机直接访问
- 这类私有配置建议放在本地 `sql/private/`、`docs/private/`、`scripts/private/` overlay 中

私有 provider seed 一律用变量注入密钥，例如：

```bash
psql "postgresql://<user>:<pass>@<host>:<port>/<db>" \
  -v private_provider_api_key='REPLACE_WITH_REAL_KEY' \
  -f sql/private/private_provider.seed.sql
```

特点：

- 实际 gateway 主进程运行在宿主机
- 对外端口仍为 `localhost:8080`
- 前端容器通过 `host.docker.internal:8080` 访问宿主机 gateway
- StockAgents 容器通过 `host.docker.internal:8080/v1` 访问宿主机 gateway
- 若 `.env` 里沿用 Docker 口径 `PG_HOST=pg`，本地直跑现在会自动回退尝试 `127.0.0.1`，避免因宿主机无法解析 `pg` 而启动失败

切换命令：

```bash
./scripts/switch_to_local_runtime.sh
```

如果需要把本地直连模式托管为 macOS 用户常驻服务：

```bash
./scripts/install_local_gateway_service.sh
./scripts/local_gateway_service_status.sh
```

卸载：

```bash
./scripts/uninstall_local_gateway_service.sh
```

说明：

- launchd service 名称：`ai.model-gateway.local`
- service 会在用户登录后自动拉起
- 当前它仅作为**实验性能力**保留
- 对依赖宿主机网络边界的私有上游，当前稳定通过完整验收的是 **tmux 本地模式**
- 因此日常切换建议仍使用 `./scripts/switch_to_local_runtime.sh`
- 本地模式会尝试自动写入 monitor 的 `app/collector/file_sd/model-gateway-local.json`，并把 gateway stdout/stderr 追加到 `.omx/logs/launchd-local-gateway*.log` 供 Promtail 采集；若 monitor repo 不在默认位置，可预先设置 `MONITOR_FILE_SD_DIR`

切换后检查：

```bash
tmux ls | grep model-gateway-local
curl http://localhost:8080/healthz
docker ps | grep model-gateway-ui
```

如果要验证 **StockAgents → 本地 gateway → 私有上游模型** 实际链路，可追加：

```bash
curl -H "Authorization: Bearer $GATEWAY_ADMIN_TOKEN" \
  "http://localhost:8080/admin/calls?limit=5"

cd ../StockAgents
curl -X POST http://127.0.0.1:8501/api/macro/trigger
```

然后用 task_id 回查：

```bash
curl -H "Authorization: Bearer $GATEWAY_ADMIN_TOKEN" \
  "http://localhost:8080/admin/calls?task_id=<macro_task_id>&limit=5"
```

预期：

- `selected_provider=<private_provider_name>`
- `model_name=<private_model_key>`
- 不出现 fallback provider

---

### 1.2 Docker 运行模式

适用场景：

- 上游模型可由 Docker 直接访问
- 想复现纯容器发布形态
- 不依赖宿主机零信任出口

特点：

- gateway 主进程运行在 `model-gateway` 容器
- 对外端口仍为 `localhost:8080`
- 前端容器通过 Docker 内部 `model-gateway:8080` 访问 gateway
- StockAgents 如果统一用 `host.docker.internal:8080/v1`，则无需额外改动

切换命令：

```bash
./scripts/switch_to_docker_runtime.sh
```

切换后检查：

```bash
docker ps | grep model-gateway
curl http://localhost:8080/healthz
```

---

## 2. 发布前准备

发布前至少确认：

```bash
git diff --check
pytest -q tests/test_main_helpers.py
python -m py_compile app/main.py app/repository.py
```

如果本次改动涉及前端反代：

```bash
docker compose build frontend
```

如果本次改动涉及对接方（如 StockAgents）：

```bash
cd ../StockAgents
docker compose config | rg 'host.docker.internal|MODEL_GATEWAY_BASE_URL|KIMI_K2_5_BASE_URL|CODEX_BASE_URL'
```

也可以直接走一键脚本：

```bash
./scripts/release_runtime.sh --mode local --with-stock
./scripts/release_runtime.sh --mode docker --with-stock
```

或者使用 Make 入口：

```bash
make runtime-local
make runtime-local-stock
make runtime-docker
make runtime-docker-stock
```

---

## 3. 生产发布步骤

### 3.1 本地直连模式发布

```bash
cd model-gateway
./scripts/switch_to_local_runtime.sh
```

或：

```bash
./scripts/release_runtime.sh --mode local
./scripts/release_runtime.sh --mode local --with-stock
```

如果依赖方也要跟随切换（例如 StockAgents）：

```bash
cd ../StockAgents
docker compose up -d --force-recreate stockagents-core stockagents-webui
```

---

### 3.2 Docker 运行模式发布

```bash
cd model-gateway
./scripts/switch_to_docker_runtime.sh
```

或：

```bash
./scripts/release_runtime.sh --mode docker
./scripts/release_runtime.sh --mode docker --with-stock
```

如果依赖方也要跟随切换：

```bash
cd ../StockAgents
docker compose up -d --force-recreate stockagents-core stockagents-webui
```

---

## 4. 闭环验收清单

> **必须全部通过，才算可以退出。**

也可以直接执行：

```bash
./scripts/verify_runtime.sh --mode local
./scripts/verify_runtime.sh --mode local --with-stock
./scripts/verify_runtime.sh --mode docker
./scripts/verify_runtime.sh --mode docker --with-stock
```

或者使用 Make 入口：

```bash
make verify-runtime
make verify-runtime-stock
make verify-runtime-docker
make verify-runtime-docker-stock
```

---

### 4.1 Gateway 基础可用性

```bash
curl http://localhost:8080/healthz
curl -I http://localhost:8620
```

期望：

- `healthz` 返回 `{"status":"ok"}`
- `8620` 返回 `200`

---

### 4.2 客户端模型目录

```bash
curl -H "Authorization: Bearer $GATEWAY_CLIENT_TOKEN" \
  http://localhost:8080/v1/models
```

重点检查：

- `qwen3.6-plus`
- 如启用了 private overlay，再额外确认你的私有模型

---

### 4.3 管理接口

```bash
curl -H "Authorization: Bearer $GATEWAY_ADMIN_TOKEN" \
  http://localhost:8080/api/providers

curl -H "Authorization: Bearer $GATEWAY_ADMIN_TOKEN" \
  http://localhost:8080/api/models

curl -H "Authorization: Bearer $GATEWAY_ADMIN_TOKEN" \
  http://localhost:8080/api/routes
```

重点检查：

- 公共 provider / model 是否都已出现
- 如启用了 private overlay，再确认私有 provider / model 是否都已出现
- 从 `v0.1.9` 开始，`/api/providers` 与前端代理 `/api/providers` 还应返回 `runtime_config` 与 `runtime_config_extras`

---

### 4.4 模型实际调用冒烟

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer ${GATEWAY_CLIENT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.6-plus","messages":[{"role":"user","content":"回复OK，不要解释。"}],"temperature":0}'
```

期望：

- 公共 smoke model 返回 `200`
- 回复内容应含 `OK`

> 如果你在本地启用了 private overlay，请在 `scripts/private/` 中追加私有模型冒烟；这类校验不应写进公共仓库默认脚本。

---

### 4.5 健康检测接口

公共脚本 `./scripts/verify_runtime.sh` 已按 `model_key` 动态解析 provider/model ID 并执行健康检查，避免把 seed 顺序或数据库自增 ID 写死在仓库里。

重点检查：

- 公共 smoke model 对应的 provider / model health 都应为 `healthy`
- 如启用了 private overlay，再在本地脚本中补私有上游健康检查

期望：

- 公共 smoke model 在目标模式下应为 `healthy`
- 私有上游是否可用，取决于你本地 overlay 的网络边界与运行模式

---

### 4.6 调用记录与使用统计

```bash
curl -H "Authorization: Bearer $GATEWAY_ADMIN_TOKEN" \
  "http://localhost:8080/admin/calls?limit=5"

curl -H "Authorization: Bearer $GATEWAY_ADMIN_TOKEN" \
  "http://localhost:8080/admin/usage/summary?date_from=$(date +%F)&date_to=$(date +%F)"
```

重点检查：

- 最新调用是否落库
- `selected_provider` 是否正确
- usage summary 是否有当日调用统计

---

### 4.7 前端管理台

```bash
curl -H "Authorization: Bearer $GATEWAY_ADMIN_TOKEN" \
  http://localhost:8620/api/providers
```

期望：

- 能经由 `8620` 正常访问后台接口
- 前端页面可正常打开 provider/model/routes 页面

---

### 4.8 业务侧真实场景（以 StockAgents 为例）

1. 设置页检查：

```bash
curl http://127.0.0.1:8501/api/settings
```

重点检查：

- `QWEN3_6_PLUS`
- `KIMI_K2_5`
- `CODEX`

对应 `base_url` 应为：

```text
http://host.docker.internal:8080/v1
```

2. 单股分析：

```bash
curl -X POST http://127.0.0.1:8501/api/analyze/single \
  -H "Content-Type: application/json" \
  -d '{"code":"300757","save_prediction":false}'
```

轮询任务结果直到结束，期望：

- `status=success`

3. 如本次发布涉及批量 / 调度：

- 再补批量分析
- 再补定时任务
- 再检查 gateway `admin/calls` / `usage summary`

---

## 5. 退出条件

只有以下条件同时满足，才算本次发布 / 切换真正闭环，可退出：

1. 目标运行模式已切到位
2. `healthz` 正常
3. `v1/models` 正常
4. 目标模型冒烟成功
5. provider/model health check 符合预期
6. `admin/calls` / `admin/usage/summary` 正常
7. 前端可用
8. 至少一个真实业务场景成功
9. 文档 / changes.log 已同步更新

---

## 6. 当前推荐口径

当前推荐：

- **默认运行态：本地直连模式**
- **StockAgents：直连 `host.docker.internal:8080/v1`**
- **Docker 运行模式：保留为兼容 / 回归验证能力，不作为依赖宿主机网络边界的私有上游默认模式**
