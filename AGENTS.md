# Repository Guidelines

## Multi-AI Collaboration (Codex / Trae / Opens Code)

### Scope
- `README.md` 负责项目功能、接口与部署说明。
- `changes.log` 负责 AI 协作过程日志（任务开始、结束、交接、阻塞）。
- 若未来新增 `CHANGELOG.md`，仅用于版本发布记录，不混入协作过程。

### Bootstrap On First Task
- `/init` 后任一 AI 开始前先检查 `changes.log`。
- 若缺失，先创建并写入模板，再开始开发任务。

### Required Workflow Per Task
1. 读取 `changes.log` 最新记录。
2. 先写 `START` 再改代码。
3. 结束时必须写 `DONE` / `HANDOFF` / `BLOCKED`。
4. `HANDOFF` / `BLOCKED` 的 `Next` 必须是下一工具可直接执行的第一步。

### `changes.log` Record Format
```md
## [时间] [工具] [任务ID] [状态]
- Intent: 本次目标
- Scope: 改动边界（做什么/不做什么）
- Files: 变更文件（逗号分隔）
- Verify: 验证命令与结果摘要
- Next: 下一步动作（若 DONE 可写 `None`）
```

### Archive Policy (Per Release)
- `changes.log` 仅保留当前迭代协作记录，避免无限增长。
- 每次发版后执行：`bash scripts/archive_changes_log.sh <release-tag>`。
- 脚本会归档到 `changes/archive/<release-tag>.log`，并重置 `changes.log` 为模板。
- 若未发版但日志超过建议阈值（如 800 行），可按日期标签提前归档。

## Project Structure
- `app/`: FastAPI 网关核心代码
- `sql/`: 初始化与迁移 SQL
- `scripts/`: 运维和启动辅助脚本
- `tests/`: 自动化测试

## Build / Test
- `docker compose up -d --build`
- `pytest -q`

## Rules
- 协作沟通默认简体中文。
- 小步提交，单一主题，不混入无关改动。
- 提交前至少运行与本次改动相关的检查命令。

## Debug / Observability Triage
- 当任务涉及“查问题 / debug / 排障 / 生产异常 / 请求失败 / 模型调用失败 / 日志异常 / monitor”时，AI 应先使用只读轻量排障入口收集证据，再提出修复：
  1. 在本仓库运行：`bash scripts/debug/model_gateway_debug_bundle.sh --recent 15m`。
  2. 如有请求号，追加：`--request-id <X-Request-Id>`；如按模型定位，追加：`--model <model_key>`。
  3. 如只需要外部观测源，在 monitor 仓库运行：`DEBUG_SERVICES_REGEX='model-gateway-api|model-gateway-ui' bash scripts/debug_local.sh`。
- 这些入口只读；不要为排障先重启服务、删除日志或修改数据库。
