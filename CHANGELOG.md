# CHANGELOG

## [v0.1.12] - 2026-07-26

- fallback 仅在主 Provider 于响应开始前发生连接失败时触发，并要求 `fallback_provider` 与 `fallback_model_key` 成对配置；HTTP、鉴权、请求错误及流式响应开始后的错误保持 fail-fast。
- OpenAI-compatible adapter 支持连接级流式重试、`connect_retries=0` 和显式关闭失败流；Provider 新增 `force_temperature`，模型 `default_params` 在客户端显式参数之前合入。
- 核心与兼容路由改为单事务同步，公开 schema 新增显式 fallback 模型外键及孤儿模型 fail-fast 校验。
- 调用审计默认不保存正文，新增保留期清理；健康统计只取每个目标最新状态，并支持可选周期 Provider 健康检查。
- Provider/Model 删除改为事务级联清理相关核心路由、兼容路由与配置，避免外键冲突返回 HTTP 500；调用审计历史保留。
- 前端补齐命令式删除确认框样式、fallback 路由展示和 `force_temperature` 配置；新增前端回归测试及 GitHub Actions CI。
- API 契约说明：本版本没有新增公开 endpoint；更新了 `/api/routes` 的 fallback 字段约束，以及 `DELETE /api/providers/{id}`、`DELETE /api/models/{id}` 的删除语义。

## [v0.1.10] - 2026-05-18

- 修复 `/v1/models` client-safe 模型目录：过滤已禁用 Provider 下的模型，避免下游自动发现不可调用模型。
- OpenAI-compatible adapter 使用 `trust_env=False`，避免本机代理环境变量污染 部分 OpenAI-compatible 上游连接。
- 新增 `scripts/debug/model_gateway_debug_bundle.sh` 只读排障入口，聚合 health、Prometheus、admin call logs、usage、Loki 与本地日志。
- 补充 AGENTS/README 中 Codex/OpenCode 轻量排障流程。
- 验证本地 launchd 与 Docker 容器迁移到 `~/Code` 后的服务健康状态。
