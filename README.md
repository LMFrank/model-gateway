# Model Gateway v0.1.4

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)

**OpenAI 兼容的 LLM 网关，统一管理多个 Provider，将 CLI 工具封装为 API。**

**当前版本**: `v0.1.4`（2026-04-08）

> ⚠️ **声明**: 本项目仅供个人学习研究使用。使用时请遵守各模型官方的服务条款和使用规则。

## 为什么需要 Model Gateway？

### 痛点

假设你有多个 AI Agent 项目（如 StockAgents、ContextOS、TradingAgent），每个项目都需要使用 LLM：

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
git clone https://github.com/LMFrank/model-gateway.git
cd model-gateway

# 配置环境变量
cp .env.example .env

# 启动服务
docker compose up -d --build

# 验证
curl http://localhost:8080/healthz
# {"status": "ok"}
```

### 访问地址

- API: http://localhost:8080
- 管理界面: http://localhost:8620

### 可观测接入

项目已按 monitor 中台约定接入：

- `model-gateway` API 服务
  - `monitor.service=model-gateway-api`
  - 暴露 `/metrics`
- `model-gateway-ui` 前端服务
  - `monitor.service=model-gateway-ui`
  - 默认仅采集日志，不暴露 Prometheus metrics

接入方式：

```bash
cd /Users/xushuchi/Library/CloudStorage/OneDrive-个人/Code/stock/model-gateway
docker compose up -d --build
```

接入后可在 monitor 中查看：

- Grafana: `http://localhost:3000`
- Prometheus targets 中的 `model-gateway-api`
- Loki 中 `service=model-gateway-api|model-gateway-ui` 的日志

## 使用示例

### 调用模型

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
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

## 支持的模型

### API 类型

| model_key | Provider | 说明 |
|-----------|----------|------|
| `qwen3.5-plus` | 百炼 Coding Plan | 订阅制 |
| `qwen3-max` | 百炼 Coding Plan | 订阅制 |
| `qwen3-coder` | 百炼 Coding Plan | 订阅制 |
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
| `PG_HOST` | PostgreSQL 主机 | localhost |
| `PG_PORT` | PostgreSQL 端口 | 5432 |
| `PG_USER` | PostgreSQL 用户 | postgres |
| `PG_PASSWORD` | PostgreSQL 密码 | - |
| `PG_DATABASE` | PostgreSQL 数据库 | model_gateway |

### 多项目接入

StockAgents / ContextOS 等多模型项目：

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

项目可通过 API 查询 gateway 中可用的模型，无需硬编码：

```python
import requests

# 获取可用模型列表
response = requests.get("http://model-gateway:8080/api/models")
models = [m["model_key"] for m in response.json()["items"]]
# ["qwen3-max", "kimi-k2.5", "deepseek-chat", ...]
```

详见: [docs/integration.md#动态发现模型](docs/integration.md)

详细接入文档: [docs/integration.md](docs/integration.md)

## API 文档

### 核心接口

| 接口 | 说明 |
|------|------|
| `POST /v1/chat/completions` | 聊天补全（支持流式） |
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

- `v0.1.4` (2026-04-08): 完成健康检查交互优化（显示进行中与状态中文化）；补齐前端 ESLint 配置；补齐本地测试依赖并完成生产链路验证
- `v0.1.3` (2026-04-02): 接入 monitor 中台；新增 `/metrics` 暴露；补齐 monitor labels 与共享网络接入；统一 observability 展示口径
- `v0.1.2` (2026-04-02): 完成前端管理台重构；统一 design-tokens 与共享状态管理；优化前端构建分包并完成生产重建
- `v0.1.1` (2026-04-01): 修复模型测试与健康状态刷新；新增 CLI Provider 健康探针；修正 MiniMax 上游模型名；补齐 `/v1` 前端代理
- `v0.1.0` (2026-03-31): Vue 3 管理界面、健康检查、扩展 providers/models
- `v0.0.5` (2026-03-28): 统一 codex_cli + sub2api 方案
- `v0.0.4` (2026-03-28): 新增 codex_cli provider
- `v0.0.3` (2026-03-28): 修复 kimi_cli 长 prompt
- `v0.0.2` (2026-03-27): 切换 PostgreSQL
- `v0.0.1`: 初始版本

## License

[MIT](LICENSE)
