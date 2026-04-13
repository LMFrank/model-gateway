\set ON_ERROR_STOP on

-- v0.3.1: 同步百炼 Coding Plan 的 Qwen 模型更新（新增 qwen3-coder-plus）
-- 执行方式: docker exec -i pg psql -U postgres -d model_gateway < sql/migrations/v0.3.1_sync_qwen_coding_plan_models.sql

-- 1) 确保既有 key 的上游模型保持最新配置
UPDATE models
SET
  upstream_model = 'qwen3-max-2026-01-23',
  updated_at = NOW()
WHERE model_key = 'qwen3-max';

UPDATE models
SET
  upstream_model = 'qwen3-coder-next',
  updated_at = NOW()
WHERE model_key = 'qwen3-coder';

-- 2) 新增 qwen3-coder-plus（若已存在则幂等更新）
INSERT INTO models (provider_id, model_key, display_name, upstream_model, is_active, description)
VALUES (
  (SELECT id FROM providers WHERE name = 'bailian_coding_api'),
  'qwen3-coder-plus',
  'Qwen3 Coder Plus',
  'qwen3-coder-plus',
  TRUE,
  'Qwen3 Coder Plus - Coding Plan'
)
ON CONFLICT (model_key) DO UPDATE SET
  display_name = EXCLUDED.display_name,
  upstream_model = EXCLUDED.upstream_model,
  is_active = EXCLUDED.is_active,
  description = EXCLUDED.description,
  updated_at = NOW();

INSERT INTO model_routes (model_key, is_enabled, priority, description)
VALUES ('qwen3-coder-plus', TRUE, 0, 'Qwen3 Coder Plus - Coding Plan')
ON CONFLICT (model_key) DO UPDATE SET
  is_enabled = EXCLUDED.is_enabled,
  description = EXCLUDED.description,
  updated_at = NOW();

INSERT INTO route_rules (model_name, primary_provider, fallback_provider, is_enabled, description)
VALUES ('qwen3-coder-plus', 'bailian_coding_api', NULL, TRUE, 'Qwen3 Coder Plus - Coding Plan')
ON CONFLICT (model_name) DO UPDATE SET
  primary_provider = EXCLUDED.primary_provider,
  fallback_provider = EXCLUDED.fallback_provider,
  is_enabled = EXCLUDED.is_enabled,
  description = EXCLUDED.description,
  updated_at = NOW();

-- 3) 验证
SELECT m.model_key, m.display_name, m.upstream_model, p.name AS provider_name
FROM models m
JOIN providers p ON p.id = m.provider_id
WHERE p.name = 'bailian_coding_api'
  AND m.model_key IN ('qwen3-max', 'qwen3-coder', 'qwen3-coder-plus')
ORDER BY m.model_key;
