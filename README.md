# Model Gateway

基于 FastAPI 的模型网关，按 OpenAI 风格 `model` 名称进行强制路由，支持主通道+回退通道、流式转发、管理接口与调用审计。

## 功能范围
- `POST /v1/chat/completions`（支持 `stream=true`）
- `GET /healthz`
- `GET/POST /admin/routes`
- `GET /admin/calls`
- `GET /admin/usage/summary`
- `GET/POST /admin/providers`（可选，方便维护 provider 配置）

## 快速开始
1. 初始化数据库：
```bash
mysql -h <mysql-host> -u <mysql-admin-user> -p < sql/init_model_gateway.sql
```
2. 配置环境变量：
```bash
cp .env.example .env
```
3. 启动服务：
```bash
docker compose up -d --build
```

> 默认 `docker-compose.yml` 使用外部网络 `${GATEWAY_DOCKER_NETWORK}`。请先创建网络或改成你现有网络。

## 本地开发
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

## 鉴权
- 业务接口：`Authorization: Bearer $GATEWAY_CLIENT_TOKEN`
- 管理接口：`Authorization: Bearer $GATEWAY_ADMIN_TOKEN`

## 接入任意上游应用
- 将上游应用的模型出口 `BASE_URL` 指向 `http://model-gateway:8080/v1`
- 将上游应用 `API_KEY` 设为 `GATEWAY_CLIENT_TOKEN`
- `MODEL_NAME` 使用网关规则中的 OpenAI 风格模型名（如 `kimi-for-coding`、`qwen3.5-plus`）

## StockAgents 示例
- `BASE_URL`: `http://model-gateway:8080/v1`
- `API_KEY`: `GATEWAY_CLIENT_TOKEN`
- `MODEL_NAME`: `kimi-for-coding` / `qwen3.5-plus`
