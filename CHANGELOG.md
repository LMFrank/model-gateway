# CHANGELOG

## [v0.1.10] - 2026-05-18

- 修复 `/v1/models` client-safe 模型目录：过滤已禁用 Provider 下的模型，避免下游自动发现不可调用模型。
- OpenAI-compatible adapter 使用 `trust_env=False`，避免本机代理环境变量污染 部分 OpenAI-compatible 上游连接。
- 新增 `scripts/debug/model_gateway_debug_bundle.sh` 只读排障入口，聚合 health、Prometheus、admin call logs、usage、Loki 与本地日志。
- 补充 AGENTS/README 中 Codex/OpenCode 轻量排障流程。
- 验证本地 launchd 与 Docker 容器迁移到 `~/Code` 后的服务健康状态。

