#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

LOG_FILE="changes.log"
ARCHIVE_DIR="changes/archive"
RELEASE_TAG="${1:-}"

if [[ ! -f "$LOG_FILE" ]]; then
  echo "ERROR: $LOG_FILE 不存在"
  exit 1
fi

if [[ -z "$RELEASE_TAG" ]]; then
  RELEASE_TAG="$(date +%Y%m%d-%H%M%S)"
fi

ARCHIVE_FILE="$ARCHIVE_DIR/$RELEASE_TAG.log"
mkdir -p "$ARCHIVE_DIR"

if [[ -f "$ARCHIVE_FILE" ]]; then
  echo "ERROR: 归档文件已存在: $ARCHIVE_FILE"
  exit 1
fi

cp "$LOG_FILE" "$ARCHIVE_FILE"

cat > "$LOG_FILE" <<'TEMPLATE'
# changes.log

AI 协作过程日志（append-only），与版本发布日志分离。

## 写入规则
- 每个任务至少两条：`START` + (`DONE` | `HANDOFF` | `BLOCKED`)。
- 仅追加，不改写历史记录。
- 每条记录必须包含：`Intent`、`Scope`、`Files`、`Verify`、`Next`。
- 发版后归档：`bash scripts/archive_changes_log.sh <release-tag>`，归档到 `changes/archive/` 后重置本文件为模板。

## 记录模板
```md
## [时间] [工具] [任务ID] [状态]
- Intent: 本次目标
- Scope: 改动边界（做什么/不做什么）
- Files: 变更文件（逗号分隔）
- Verify: 验证命令与结果摘要
- Next: 下一步动作（若 DONE 可写 `None`）
```
TEMPLATE

echo "Archived $LOG_FILE -> $ARCHIVE_FILE"
echo "Reset $LOG_FILE to template"
