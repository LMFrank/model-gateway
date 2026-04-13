# Model Gateway 接入文档

本文档详细说明如何将上游应用接入 Model Gateway。

## 接入原理

Model Gateway 兼容 OpenAI API 格式，任何支持 OpenAI API 的应用都可以通过修改配置接入：

```
原配置:
  BASE_URL=https://api.openai.com/v1
  API_KEY=sk-xxx
  MODEL=gpt-4

接入后:
  BASE_URL=http://model-gateway:8080/v1
  API_KEY=<GATEWAY_CLIENT_TOKEN>
  MODEL=qwen3-max  # 使用 gateway 中配置的 model_key
```

## 前置条件

1. Model Gateway 已部署并运行
2. 已获取 `GATEWAY_CLIENT_TOKEN`
3. 目标应用与 Model Gateway 网络互通

> 说明：
> - 客户端调用 `/v1/*` 使用 `GATEWAY_CLIENT_TOKEN`
> - 管理接口 `/api/*`、`/admin/*` 使用 `GATEWAY_ADMIN_TOKEN`
> - legacy 结构中的 `fallback_provider` 已废弃，当前运行时只使用 `primary_provider`

## 接入方式

### 方式一: 环境变量注入

适用于大多数应用，通过环境变量配置模型服务。

#### 单一模型

```bash
# .env 或 docker-compose.yml environment
OPENAI_API_KEY=mgw_client_a0a0f11b33884a1f187526151cdb3c75
OPENAI_BASE_URL=http://model-gateway:8080/v1
OPENAI_MODEL_NAME=qwen3-max
```

#### 多模型服务（多服务接入模式）

应用按服务名配置多个模型，运行时动态切换：

```bash
# Kimi Code 服务（通过 CLI）
KIMI_CODE_API_KEY=mgw_client_a0a0f11b33884a1f187526151cdb3c75
KIMI_CODE_BASE_URL=http://model-gateway:8080/v1
KIMI_CODE_MODEL_NAME=kimi-for-coding

# Qwen Max 服务
QWEN_MAX_API_KEY=mgw_client_a0a0f11b33884a1f187526151cdb3c75
QWEN_MAX_BASE_URL=http://model-gateway:8080/v1
QWEN_MAX_MODEL_NAME=qwen3-max

# DeepSeek 服务
DEEPSEEK_API_KEY=mgw_client_a0a0f11b33884a1f187526151cdb3c75
DEEPSEEK_BASE_URL=http://model-gateway:8080/v1
DEEPSEEK_MODEL_NAME=deepseek-chat
```

应用代码通过服务名获取配置：

```python
import os

def get_model_config(service_name: str) -> dict:
    """按服务名获取模型配置"""
    prefix = service_name.upper()
    return {
        "api_key": os.getenv(f"{prefix}_API_KEY"),
        "base_url": os.getenv(f"{prefix}_BASE_URL"),
        "model": os.getenv(f"{prefix}_MODEL_NAME"),
    }

# 使用
config = get_model_config("KIMI_CODE")
# config = {"api_key": "mgw_client_xxx", "base_url": "http://...", "model": "kimi-for-coding"}
```

#### 动态发现模型（推荐）

当 gateway 新增 model 后，其他项目可以通过 **client-safe** 的 `/v1/models` 自动感知：

**查询可用模型列表：**

```bash
curl http://model-gateway:8080/v1/models \
  -H "Authorization: Bearer ${GATEWAY_CLIENT_TOKEN}"
```

**响应示例：**

```json
{
  "object": "list",
  "data": [
    {"id": "qwen3-max", "object": "model", "owned_by": "bailian_coding_api", "display_name": "Qwen3 Max"},
    {"id": "kimi-k2.5", "object": "model", "owned_by": "bailian_coding_api", "display_name": "Kimi K2.5"},
    {"id": "deepseek-chat", "object": "model", "owned_by": "deepseek_api", "display_name": "DeepSeek Chat"}
  ]
}
```

**Python 示例：**

```python
import requests

class GatewayClient:
    def __init__(self, base_url: str = "http://model-gateway:8080"):
        self.base_url = base_url

    def list_models(self) -> list[str]:
        """获取所有可用模型"""
        response = requests.get(
            f"{self.base_url}/v1/models",
            headers={"Authorization": "Bearer YOUR_GATEWAY_CLIENT_TOKEN"},
        )
        return [m["id"] for m in response.json()["data"]]

    def get_model_info(self, model_key: str) -> dict:
        """获取模型详情"""
        response = requests.get(
            f"{self.base_url}/v1/models",
            headers={"Authorization": "Bearer YOUR_GATEWAY_CLIENT_TOKEN"},
        )
        for m in response.json()["data"]:
            if m["id"] == model_key:
                return m
        return None

# 使用
client = GatewayClient()
available_models = client.list_models()
# ["qwen3-max", "kimi-k2.5", "deepseek-chat", ...]
```

**应用启动时验证模型可用性：**

```python
def validate_model_config(model_name: str) -> bool:
    """验证配置的模型在 gateway 中是否存在"""
    client = GatewayClient()
    available = client.list_models()
    if model_name not in available:
        raise ValueError(f"Model '{model_name}' not found. Available: {available}")
    return True
```

**优势：**
- 新增 model 后无需修改项目配置
- 前端可展示可选模型列表
- 启动时验证避免运行时报错

### 方式二: 配置文件

适用于需要持久化配置的应用。

#### YAML 配置

```yaml
# config.yaml
model:
  default_service: "QWEN_MAX"
  services:
    QWEN_MAX:
      api_key: "${QWEN_MAX_API_KEY}"
      base_url: "${QWEN_MAX_BASE_URL}"
      model_name: "${QWEN_MAX_MODEL_NAME}"
    DEEPSEEK:
      api_key: "${DEEPSEEK_API_KEY}"
      base_url: "${DEEPSEEK_BASE_URL}"
      model_name: "${DEEPSEEK_MODEL_NAME}"
```

#### JSON 配置

```json
// custom_models.json
[
  {
    "service_name": "QWEN_MAX",
    "api_key": "mgw_client_xxx",
    "base_url": "http://model-gateway:8080/v1",
    "model_name": "qwen3-max"
  },
  {
    "service_name": "DEEPSEEK",
    "api_key": "mgw_client_xxx",
    "base_url": "http://model-gateway:8080/v1",
    "model_name": "deepseek-chat"
  }
]
```

### 方式三: 代码中直接使用

```python
from openai import OpenAI

client = OpenAI(
    api_key="mgw_client_a0a0f11b33884a1f187526151cdb3c75",
    base_url="http://model-gateway:8080/v1"
)

response = client.chat.completions.create(
    model="qwen3-max",  # model_key
    messages=[{"role": "user", "content": "Hello"}]
)
```

## Docker 网络配置

### 同一 docker-compose

```yaml
# docker-compose.yml
services:
  model-gateway:
    image: model-gateway
    ports:
      - "8080:8080"
    networks:
      - app-network

  your-app:
    image: your-app
    environment:
      - OPENAI_BASE_URL=http://model-gateway:8080/v1
      - OPENAI_API_KEY=mgw_client_xxx
    networks:
      - app-network

networks:
  app-network:
```

### 跨 docker-compose

```yaml
# your-app/docker-compose.yml
services:
  your-app:
    environment:
      - OPENAI_BASE_URL=http://model-gateway:8080/v1
    networks:
      - model-gateway_default

networks:
  model-gateway_default:
    external: true  # 使用 model-gateway 创建的网络
```

### 使用 host.docker.internal

如果 model-gateway 运行在宿主机：

```yaml
services:
  your-app:
    environment:
      - OPENAI_BASE_URL=http://host.docker.internal:8080/v1
```

## 可用模型列表

### API 类型（推荐）

| model_key | 说明 | 计费方式 |
|-----------|------|----------|
| `qwen3.5-plus` | Qwen3.5 Plus | 百炼 Coding Plan |
| `qwen3-max` | Qwen3 Max | 百炼 Coding Plan |
| `qwen3-coder` | Qwen3 Coder | 百炼 Coding Plan |
| `qwen3-coder-plus` | Qwen3 Coder Plus | 百炼 Coding Plan |
| `kimi-k2.5` | Kimi K2.5 | 百炼 Coding Plan |
| `glm-5` | GLM-5 | 百炼 Coding Plan |
| `qwen3-max-general` | Qwen3 Max | 百炼按 Token |
| `deepseek-v3.2` | DeepSeek V3.2 | 百炼按 Token |
| `deepseek-chat` | DeepSeek Chat | DeepSeek 官方 |

### CLI 类型

| model_key | 说明 | 要求 |
|-----------|------|------|
| `kimi-for-coding` | Kimi Code CLI | 容器内安装 kimi-cli |
| `codex-for-coding` | Codex CLI | 需要外部服务支持 |

## 添加新模型

### 1. 通过管理 API

```bash
# 1. 创建 Provider（如果不存在）
curl -X POST http://localhost:8080/api/providers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "new_api",
    "display_name": "New API",
    "provider_type": "api",
    "base_url": "https://api.new-service.com/v1",
    "api_key": "sk-xxx",
    "is_enabled": true
  }'

# 2. 创建 Model
curl -X POST http://localhost:8080/api/models \
  -H "Authorization: Bearer ${GATEWAY_ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id": 7,
    "model_key": "new-model",
    "display_name": "New Model",
    "upstream_model": "actual-model-name",
    "is_active": true
  }'

# 3. 创建路由规则
curl -X POST http://localhost:8080/api/routes \
  -H "Authorization: Bearer ${GATEWAY_ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rules": [
      {
        "model_key": "new-model",
        "is_enabled": true,
        "priority": 0,
        "description": "New Model route"
      }
    ]
  }'
```

### 2. 通过管理界面

访问 http://localhost:8620（本地开发态 Vite 为 `http://localhost:3000`），在对应页面添加：
1. Providers → 新增 Provider
2. Models → 新增 Model
3. Routes → 新增路由规则

### 3. 通过 SQL 迁移

```sql
-- sql/migrations/v0.4.0_add_new_model.sql
INSERT INTO providers (name, display_name, provider_type, base_url, api_key, is_enabled)
VALUES ('new_api', 'New API', 'api', 'https://api.example.com/v1', 'sk-xxx', true);

INSERT INTO models (provider_id, model_key, display_name, upstream_model, is_active)
SELECT id, 'new-model', 'New Model', 'actual-model-name', true
FROM providers WHERE name = 'new_api';

INSERT INTO route_rules_v2 (model_key, is_enabled)
VALUES ('new-model', true);
```

## 健康检查

### 前端界面

- Provider 列表 → 点击「健康检查」按钮
- Model 列表 → 点击「测试」按钮

### API 调用

```bash
# Provider 健康检查
curl -X POST http://localhost:8080/api/health/check/provider/6

# Model 测试调用
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen3-max", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 20}'
```

## 故障排查

### 1. 返回 502 错误

**原因**: Provider 不可用或路由配置错误

**排查**:
```bash
# 检查路由配置
curl http://localhost:8080/api/routes \
  -H "Authorization: Bearer ${GATEWAY_ADMIN_TOKEN}"

# 检查 Provider 配置
curl http://localhost:8080/api/providers \
  -H "Authorization: Bearer ${GATEWAY_ADMIN_TOKEN}"

# 检查健康状态
curl -X POST http://localhost:8080/api/health/check/model/{id}
```

### 2. 返回 400 错误 "model not found"

**原因**: model_key 未配置或路由规则缺失

**解决**:
```bash
# 检查 model 是否存在
curl http://localhost:8080/v1/models \
  -H "Authorization: Bearer ${GATEWAY_CLIENT_TOKEN}" | grep "your-model-key"

# 添加路由规则
curl -X POST http://localhost:8080/api/routes \
  -H "Authorization: Bearer ${GATEWAY_ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"rules":[{"model_key":"your-model-key","is_enabled":true,"priority":0,"description":"Manual route"}]}'
```

### 3. CLI 模型返回 "command not found"

**原因**: 容器内未安装对应 CLI 工具

**解决**: 更新 `requirements.txt` 添加对应包，或使用 API 类型的 Provider

## 最佳实践

1. **优先使用 API 类型 Provider**: 稳定性更好，易于调试
2. **为不同用途配置不同 model_key**: 如 `qwen3-max` 用于推理，`qwen3-coder-plus` 用于代码
3. **定期检查健康状态**: 使用管理界面或 API 定期检测
4. **监控调用日志**: 通过 `/api/calls` 接口查看调用记录
