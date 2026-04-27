# Model Gateway v0.1.9

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)

**OpenAI 兼容的 LLM 网关，统一管理多个 Provider，将 CLI 工具封装为 API。**

**当前版本**: `v0.1.9`（2026-04-27）

> ⚠️ **使用提醒**: 使用本项目时请遵守各模型官方的服务条款和使用规则。

## 为什么需要 Model Gateway？

### 痛点

假设你有多个 AI Agent 应用或服务，它们都需要使用 LLM：

| 问题 | 痛点描述 |
|------|----------|
| **重复建设** | 每个项目都要实现一套配置中心：模型列表、API Key 管理、路由逻辑、健康检查... |
| **配置分散** | 同一个 API Key 在多个项目中重复配置，更新时需要逐个修改 |
| **CLI 无法复用** | Kimi Code、Codex 等 CLI 工具只能在终端使用，Web 应用或其他 Agent 无法调用 |
| **缺乏统一视图** | 无法统计所有项目的模型使用量、成本、健康状态 |

**典型场景**：新增一个模型后，需要：
1. 在项目 A 中添加配置代码
2. 在项目 B 中添加配置代码
3. 在项目 C 中添加配置代码
4. ...重复 N 次

### 解决方案

```
Before: 多个应用各自管理模型配置

┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Agent A    │  │  Agent B    │  │  Agent C    │
│ Kimi CLI    │  │ Qwen API    │  │ DeepSeek    │
│ (终端专属)   │  │ (API Key 1) │  │ (API Key 2) │
└─────────────┘  └─────────────┘  └─────────────┘

After: 统一接入 Model Gateway

┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Agent A    │  │  Agent B    │  │  Agent C    │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       └────────────────┼────────────────┘
                        ▼
              ┌─────────────────┐
              │  Model Gateway  │
              │  统一入口 + 路由  │
              └────────┬────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
  ┌─────────┐    ┌──────────┐    ┌──────────┐
  │Kimi CLI │    │  Qwen    │    │DeepSeek  │
  │(API化)  │    │  API     │    │   API    │
  └─────────┘    └──────────┘    └──────────┘
```

### 核心价值

- **单入口**: 一组 `BASE_URL + API_KEY` 访问所有模型
- **CLI API 化**: Kimi Code、Codex 等封装为 OpenAI 兼容 API
- **运行时路由**: 通过 `model` 参数精确选路，实时调整
- **全链路审计**: 调用记录、Token 用量、健康检查

## 功能特性

- ✅ OpenAI 兼容 API（`/v1/chat/completions`）
- ✅ 支持 API 类型和 CLI 类型 Provider
- ✅ Vue 3 管理界面
- ✅ 健康检查与使用统计
- ✅ 多模型路由规则
- ✅ 流式输出支持

## 快速开始

### Docker 部署（推荐）

```bash
# 克隆项目
git clone <your-repo-url>
cd model-gateway

# 配置环境变量
cp .env.example .env

# 启动服务
docker compose up -d --build

# 验证
curl http://localhost:8080/healthz
# {"status": "ok"}
```

### 数据库初始化（空库 / 新环境）

如果是首次创建数据库，不要只执行兼容初始化脚本 `sql/init_model_gateway.sql`。  
完整运行时结构的一键 bootstrap 入口是：

```bash
psql -h <pg-host> -U <pg-admin-user> -d postgres \
  -v mgw_db_password='CHANGE_ME_STRONG_PASSWORD' \
  -f sql/bootstrap_model_gateway.sql
```

该脚本会一次性创建：
- 兼容/审计表：`route_rules`、`call_logs`、`daily_usage_agg`
- 核心表：`providers`、`models`、`model_routes`、`health_checks`
- 当前默认 providers / models / routes（含 `openai_api` 占位 provider）

### 访问地址

- API: http://localhost:8080
- 管理界面: http://localhost:8620

### 运行模式

项目支持两种运行模式，并保持宿主机端口固定为 `localhost:8080`：

1. **本地直连模式**
   - 适用于需要复用宿主机网络能力的私有上游（例如零信任、专线、宿主机本地代理）
   - 切换命令：

   ```bash
   ./scripts/switch_to_local_runtime.sh
   ```

   如需把本地模式做成更稳定的 macOS 用户常驻服务，可选执行：

   ```bash
   ./scripts/install_local_gateway_service.sh
   ./scripts/local_gateway_service_status.sh
   ```

   卸载：

   ```bash
   ./scripts/uninstall_local_gateway_service.sh
   ```

   > 说明：`launchd` 常驻服务当前仅作为实验性能力保留。
   > 对依赖宿主机网络边界的私有上游，当前稳定通过完整验收的是 `tmux` 本地模式。
   > 因此 `./scripts/switch_to_local_runtime.sh` 默认仍回到该模式。
   > 本地模式会尝试自动把 Prometheus target 写到 monitor 仓库的 `app/collector/file_sd/model-gateway-local.json`，并把 stdout/stderr 追加到 `.omx/logs/launchd-local-gateway*.log` 供 Promtail 采集。

2. **Docker 运行模式**
   - 适用于上游模型可由 Docker 直接访问的场景
   - 切换命令：

   ```bash
   ./scripts/switch_to_docker_runtime.sh
   ```

说明：
- 宿主机始终使用 `http://localhost:8080`
- Docker 业务容器建议使用 `http://host.docker.internal:8080/v1`
- `frontend` 会通过 `FRONTEND_GATEWAY_UPSTREAM` 在 `host.docker.internal` 与 `model-gateway` 间切换
- 私有 provider / 文档 / 验收脚本建议放到本地 `sql/private/`、`docs/private/`、`scripts/private/` overlay，并由 `.gitignore` 排除

私有 provider seed 建议使用 `psql -v` 注入密钥，不要把真实 API Key 写进 SQL 文件，例如：

```bash
psql "postgresql://<user>:<pass>@<host>:<port>/<db>" \
  -v private_provider_api_key='REPLACE_WITH_REAL_KEY' \
  -f sql/private/private_provider.seed.sql
```

### 一键切换 / 验收

可直接使用：

```bash
# 仅切换并验收 gateway
./scripts/release_runtime.sh --mode local

# 切换并连同 StockAgents 一起重启、验收
./scripts/release_runtime.sh --mode local --with-stock

# 只跑验收，不切换
./scripts/verify_runtime.sh --mode local --with-stock
```

如果更习惯 `make`：

```bash
make runtime-local
make runtime-local-stock
make runtime-docker
make runtime-docker-stock
make verify-runtime
make verify-runtime-stock
make verify-runtime-docker
make verify-runtime-docker-stock
```

### 升级已有环境

当现网仍使用旧核心路由表名时，先执行数据库迁移，再重建服务：

```bash
docker exec -i pg \
  env PGPASSWORD="$PG_PASSWORD" \
  psql -U "$PG_USER" -d "$PG_DATABASE" \
  < sql/migrations/v0.3.2_rename_route_rules_table.sql

docker compose up -d --build model-gateway frontend
```

升级完成后建议检查：

```bash
curl http://localhost:8080/healthz
curl -H "Authorization: Bearer $GATEWAY_CLIENT_TOKEN" http://localhost:8080/v1/models
curl -H "Authorization: Bearer $GATEWAY_ADMIN_TOKEN" http://localhost:8080/api/providers
```

### 可观测接入

项目已按监控系统约定接入：

- `model-gateway` API 服务
  - `service=model-gateway-api`
  - 暴露 `/metrics`
- `model-gateway-ui` 前端服务
  - `service=model-gateway-ui`
  - 默认仅采集日志，不暴露 Prometheus metrics

接入方式：

```bash
cd model-gateway
docker compose up -d --build
```

接入后可在监控系统中查看：

- Grafana: `http://localhost:3000`
- Prometheus targets 中的 `model-gateway-api`
- Loki 中 `service=model-gateway-api|model-gateway-ui` 的日志

> 本地直连补充：
>
> - Docker runtime 下，monitor 通过 Docker labels + 网络直接采集 `model-gateway` 容器
> - 本地 runtime 下，`./scripts/switch_to_local_runtime.sh` / `./scripts/install_local_gateway_service.sh` 会尝试自动写入 monitor 的 `file_sd` target
> - 若 monitor repo 不在默认位置，可预先设置 `MONITOR_FILE_SD_DIR=/path/to/monitor/app/collector/file_sd`

## 使用示例

### 调用模型

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer ${GATEWAY_CLIENT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-max",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="your-gateway-token"
)

response = client.chat.completions.create(
    model="qwen3-max",
    messages=[{"role": "user", "content": "Hello"}]
)
```

### 接入现有项目

只需修改环境变量：

```bash
# Before: 直接调用 Qwen API
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=sk-xxx

# After: 通过 Model Gateway 调用
OPENAI_BASE_URL=http://model-gateway:8080/v1
OPENAI_API_KEY=your-gateway-token
# model 参数使用 gateway 中配置的 model_key
```

其中：
- `OPENAI_API_KEY` / SDK `api_key` 对应 **`GATEWAY_CLIENT_TOKEN`**
- 管理接口（`/api/*`、`/admin/*`）必须使用 **`GATEWAY_ADMIN_TOKEN`**

## 支持的模型

### API 类型

| model_key | Provider | 说明 |
|-----------|----------|------|
| `qwen3.6-plus` | 百炼 Coding Plan | 订阅制 |
| `qwen3.5-plus` | 百炼 Coding Plan | 订阅制 |
| `qwen3-max` | 百炼 Coding Plan | 订阅制 |
| `qwen3-coder` | 百炼 Coding Plan | 订阅制 |
| `qwen3-coder-plus` | 百炼 Coding Plan | 订阅制 |
| `kimi-k2.5` | 百炼 Coding Plan | 订阅制 |
| `glm-5` | 百炼 Coding Plan | 订阅制 |
| `deepseek-chat` | DeepSeek 官方 | 按 Token |
| `qwen3-max-general` | 百炼通用 API | 按 Token |

### CLI 类型

| model_key | Provider | 说明 |
|-----------|----------|------|
| `kimi-for-coding` | Kimi Code CLI | 订阅制（需安装 kimi-cli） |
| `codex-for-coding` | Codex CLI | 需外部服务 |

> 可通过管理界面添加新的 Provider 和 Model

## 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `GATEWAY_PORT` | 网关端口 | 8080 |
| `GATEWAY_UI_PORT` | 管理界面端口 | 8620 |
| `GATEWAY_CLIENT_TOKEN` | 客户端 Token | - |
| `GATEWAY_ADMIN_TOKEN` | 管理端 Token | - |
| `VITE_GATEWAY_ADMIN_TOKEN` | 前端构建期注入的管理端 Token（可选） | - |
| `FRONTEND_GATEWAY_UPSTREAM` | 前端容器要代理到的 gateway 主机名（`host.docker.internal` 或 `model-gateway`） | `host.docker.internal` |
| `PG_HOST` | PostgreSQL 主机 | localhost |
| `PG_PORT` | PostgreSQL 端口 | 5432 |
| `PG_USER` | PostgreSQL 用户 | postgres |
| `PG_PASSWORD` | PostgreSQL 密码 | - |
| `PG_DATABASE` | PostgreSQL 数据库 | model_gateway |

> 本地直跑补充：
>
> - Docker 场景常把 `PG_HOST` 设成 `pg`
> - 宿主机直接运行 `python -m uvicorn app.main:app --port 8080` 时，仓库现在会自动按 `pg -> 127.0.0.1` 再尝试一次
> - 因此本地直跑通常不需要手工改 `.env`；只有数据库既不在 `pg` 也不在本机 `127.0.0.1` 时，才需要显式覆写 `PG_HOST`

### 多项目接入

适用于需要同时接入多种模型服务的项目：

```bash
# Kimi Code 服务
KIMI_CODE_API_KEY=your-gateway-token
KIMI_CODE_BASE_URL=http://model-gateway:8080/v1
KIMI_CODE_MODEL_NAME=kimi-for-coding

# Qwen Max 服务
QWEN_MAX_API_KEY=your-gateway-token
QWEN_MAX_BASE_URL=http://model-gateway:8080/v1
QWEN_MAX_MODEL_NAME=qwen3-max

# DeepSeek 服务
DEEPSEEK_API_KEY=your-gateway-token
DEEPSEEK_BASE_URL=http://model-gateway:8080/v1
DEEPSEEK_MODEL_NAME=deepseek-chat
```

### 动态发现模型

项目可通过 **client-safe** 的 `/v1/models` 查询 gateway 中可用模型，无需硬编码管理接口。
`/api/models` 仍保留给管理端 CRUD 使用：

```python
import requests

# 获取可用模型列表
response = requests.get(
    "http://model-gateway:8080/v1/models",
    headers={"Authorization": "Bearer YOUR_GATEWAY_CLIENT_TOKEN"},
)
models = [m["id"] for m in response.json()["data"]]
# ["qwen3-max", "kimi-k2.5", "deepseek-chat", ...]
```

详见: [docs/integration.md#动态发现模型](docs/integration.md)

详细接入文档: [docs/integration.md](docs/integration.md)

运行 / 发布 / 验收 SOP: [docs/runtime-release-sop.md](docs/runtime-release-sop.md)

## API 文档

### 核心接口

| 接口 | 说明 |
|------|------|
| `POST /v1/chat/completions` | 聊天补全（支持流式） |
| `GET /v1/models` | 客户端可见模型列表（需 client token） |
| `GET /healthz` | 健康检查 |

### 管理接口

| 接口 | 说明 |
|------|------|
| `GET/POST/PUT/DELETE /api/providers` | Provider 管理 |
| `GET/POST/PUT/DELETE /api/models` | Model 管理 |
| `GET/POST /api/routes` | 路由规则管理 |
| `POST /api/health/check/provider/{id}` | Provider 健康检查 |
| `POST /api/health/check/model/{id}` | Model 测试调用 |
| `GET /admin/calls` | 调用记录 |
| `GET /admin/usage/summary` | 使用统计 |

> 所有管理接口都要求 `Authorization: Bearer ${GATEWAY_ADMIN_TOKEN}`。  
> 前端管理台会在首次 401 时提示输入 admin token，也可在构建时注入 `VITE_GATEWAY_ADMIN_TOKEN`。
>
> 路由 fallback 说明：兼容字段 `fallback_provider` 当前保持为空，运行时只使用 `primary_provider`。
>
> 兼容层说明：`/admin/providers` 与 `/admin/routes` 仅作为 **deprecated compatibility surface** 保留。
> - 创建 / 删除 provider 请使用核心 `/api/providers`
> - 路由写入请优先使用核心 `/api/routes`
> - 兼容层响应会返回 `X-Model-Gateway-Compat: deprecated`

Provider 管理页现已内置 **运行参数配置中心**：
- API Provider 可直接编辑 `timeout_sec`、`connect_retries`、`retry_backoff_sec`、`chat_endpoint`、`upstream_model`
- CLI Provider 可直接编辑 `timeout_sec`、`command`、`args`、`extra_args`、`model_arg`、`prompt_arg`、`stream_arg`、`stdin_prompt_arg`、`response_file` 等运行参数
- 高级扩展参数仍保留在 “高级扩展(JSON)” 区域，保存时会与结构化运行参数合并写回 `providers.config_json`

## 发布前闭环验证清单

发布或切换运行模式后，至少执行以下验证：

```bash
# 基础健康
curl http://localhost:8080/healthz
curl -I http://localhost:8620

# 客户端模型目录
curl -H "Authorization: Bearer $GATEWAY_CLIENT_TOKEN" \
  http://localhost:8080/v1/models

# 管理接口
curl -H "Authorization: Bearer $GATEWAY_ADMIN_TOKEN" \
  http://localhost:8080/api/providers
curl -H "Authorization: Bearer $GATEWAY_ADMIN_TOKEN" \
  "http://localhost:8080/admin/calls?limit=5"
curl -H "Authorization: Bearer $GATEWAY_ADMIN_TOKEN" \
  "http://localhost:8080/admin/usage/summary?date_from=$(date +%F)&date_to=$(date +%F)"

# 公网 provider 冒烟（docker / local 都应验证）
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer ${GATEWAY_CLIENT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.6-plus","messages":[{"role":"user","content":"回复OK，不要解释。"}],"temperature":0}'

```

如果还有业务项目依赖 gateway（例如 StockAgents），发布后还要补以下业务场景验证：

- 设置中心模型配置读取
- 单股分析
- 批量分析 / 定时任务
- `/api/health/check/provider/{id}` 与 `/api/health/check/model/{id}`（公共脚本已按模型名动态解析 ID）
- `admin/calls` / `admin/usage/summary` 是否正常落库统计

## 本地开发

```bash
# 后端
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080

# 前端
cd frontend
npm install
npm run dev

# 测试
pytest -q
```

## 项目结构

```
model-gateway/
├── app/                    # FastAPI 后端
│   ├── main.py            # 应用入口
│   ├── repository.py      # 数据库层
│   ├── adapters/          # Provider 适配器
│   └── schemas.py         # 数据模型
├── frontend/              # Vue 3 前端
│   └── src/
│       ├── views/         # 页面组件
│       └── api/           # API 客户端
├── sql/migrations/        # 数据库迁移
├── docs/                  # 文档
├── docker-compose.yml
└── Dockerfile
```

## 常见问题

<details>
<summary><b>Q: 与直接调用 API 相比有什么优势？</b></summary>

- **CLI 工具 API 化**: Kimi Code、Codex 等 CLI 封装为 API，任意应用可调用
- **统一入口**: 一处配置，所有应用共享
- **成本透明**: 统计 Token 用量，订阅制 vs 按 Token 对比
- **灵活路由**: 实时切换模型，无需改代码
</details>

<details>
<summary><b>Q: 会增加延迟吗？</b></summary>

API 类型 Provider 延迟约 1-5ms。CLI 类型需要启动进程，延迟约 1-3s，建议优先使用 API 类型。
</details>

<details>
<summary><b>Q: API Key 安全吗？</b></summary>

API Key 存储在数据库，建议：
- 生产环境用环境变量注入
- 定期轮换 Key
- 限制管理界面访问
</details>

## 版本历史

- `v0.1.9` (2026-04-27): 新增 Provider 运行参数配置中心；后端增加结构化 `runtime_config/runtime_config_extras` 兼容层并保持 `providers.config_json` 存储不变；前端 Provider 管理页支持结构化编辑超时、重试、endpoint、CLI 命令参数；完成本地生产运行模式重部署与验收验证
- `v0.1.8` (2026-04-27): 收口私有 provider seed 的明文密钥，统一改为 `psql -v` 变量注入；补充私有 overlay 文档示例；新增 OpenAI 兼容 adapter 瞬时连接重试测试与本地 `PG_HOST=pg -> 127.0.0.1` 回退测试；同步前后端版本号与公开文档去私有化校验
- `v0.1.7` (2026-04-23): 增加 OpenAI 兼容 adapter 的瞬时连接重试；补齐本地直跑 `PG_HOST=pg -> 127.0.0.1` 兼容；新增 launchd 本地常驻服务与 monitor file_sd / 本地日志采集衔接；同步 README 与 runtime SOP 的本地部署/可观测说明
- `v0.1.6` (2026-04-10): 补齐 admin/client Bearer 鉴权；新增 client-safe `/v1/models`；provider secret 默认脱敏；新增 `sql/bootstrap_model_gateway.sql` 并完成空库 bootstrap smoke 验证；移除 runtime fallback 语义
- `v0.1.5` (2026-04-08): 同步百炼 Coding Plan 的 Qwen 模型配置（新增 `qwen3-coder-plus`）；新增幂等迁移脚本 `v0.3.1`；完成生产环境迁移与接口实测验证
- `v0.1.4` (2026-04-08): 完成健康检查交互优化（显示进行中与状态中文化）；补齐前端 ESLint 配置；补齐本地测试依赖并完成生产链路验证
- `v0.1.3` (2026-04-02): 接入监控系统；新增 `/metrics` 暴露；补齐指标 labels 与共享网络接入；统一 observability 展示口径
- `v0.1.2` (2026-04-02): 完成前端管理台重构；统一 design-tokens 与共享状态管理；优化前端构建分包并完成生产重建
- `v0.1.1` (2026-04-01): 修复模型测试与健康状态刷新；新增 CLI Provider 健康探针；修正 MiniMax 上游模型名；补齐 `/v1` 前端代理
- `v0.1.0` (2026-03-31): Vue 3 管理界面、健康检查、扩展 providers/models
- `v0.0.5` (2026-03-28): 统一 codex_cli + OpenAI 兼容代理方案
- `v0.0.4` (2026-03-28): 新增 codex_cli provider
- `v0.0.3` (2026-03-28): 修复 kimi_cli 长 prompt
- `v0.0.2` (2026-03-27): 切换 PostgreSQL
- `v0.0.1`: 初始版本

## License

[MIT](LICENSE)
