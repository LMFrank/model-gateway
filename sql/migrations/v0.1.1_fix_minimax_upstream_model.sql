-- v0.1.1: 修复百炼 Coding Plan 的 MiniMax 上游模型名大小写
-- 执行方式:
--   docker exec -i pg psql -U postgres -d model_gateway < sql/migrations/v0.1.1_fix_minimax_upstream_model.sql

BEGIN;

UPDATE models
SET upstream_model = 'MiniMax-M2.5',
    updated_at = NOW()
WHERE model_key = 'minimax-m2.5'
  AND upstream_model = 'minimax-m2.5';

COMMIT;
