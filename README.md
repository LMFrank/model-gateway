# Model Gateway v0.0.4

基于 FastAPI 的模型网关，按 OpenAI 风格 `model` 名称进行强制路由，支持流式转发、管理接口与调用审计。

**当前版本**: `v0.0.4`

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
psql -h <pg-host> -U <pg-admin-user> -d postgres -v mgw_db_password='<strong-password>' -f sql/init_model_gateway.sql
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
> 如果数据库在另一个 Docker 网络，请设置 `${DB_DOCKER_NETWORK}` 并确保网关容器可连通 `${PG_HOST}`。

## 访问地址
- 网关入口：`http://localhost:${GATEWAY_PORT:-8080}/v1`
- 健康检查：`http://localhost:${GATEWAY_PORT:-8080}/healthz`

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

## 关键环境变量
- 网络与端口：`GATEWAY_PORT`、`GATEWAY_DOCKER_NETWORK`、`DB_DOCKER_NETWORK`
- PostgreSQL：`PG_HOST`、`PG_PORT`、`PG_USER`、`PG_PASSWORD`、`PG_DATABASE`
- Kimi CLI：`KIMI_HOME_DIR`、`KIMI_CLI_CMD`
- Codex CLI：`CODEX_HOME_DIR`（建议填绝对路径，如 `/Users/you/.codex`，需已 `codex login`），模型建议 `gpt-5.3-codex`

## 接入任意上游应用
- 将上游应用的模型出口 `BASE_URL` 指向 `http://model-gateway:8080/v1`
- 将上游应用 `API_KEY` 设为 `GATEWAY_CLIENT_TOKEN`
- `MODEL_NAME` 使用网关规则中的 OpenAI 风格模型名（如 `kimi-for-coding`、`codex-for-coding`、`qwen3.5-plus`）

## StockAgents 示例
- `BASE_URL`: `http://model-gateway:8080/v1`
- `API_KEY`: `GATEWAY_CLIENT_TOKEN`
- `MODEL_NAME`: `kimi-for-coding` / `codex-for-coding` / `qwen3.5-plus`

## 版本历史
- `v0.0.4` (2026-03-28): 新增 `codex_cli` provider 与 `codex-for-coding` 路由，补充容器内 Codex CLI 运行支持（含 `.codex` 挂载与默认模型配置），并完善对应测试与初始化 SQL。
- `v0.0.3` (2026-03-28): 根修 `kimi_cli` 长 prompt 触发 `Argument list too long`，默认改为 stdin 传 prompt，保留参数兼容模式并补充测试。
- `v0.0.2` (2026-03-27): 切换数据库到 PostgreSQL，网关支持跨网络连接 DB，脚本与文档通用化。
- `v0.0.1`: 初始版本（FastAPI 网关基础能力）。
