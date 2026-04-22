-- Model Gateway v0.3.3
-- 1) 补齐 qwen3.6-plus 模型与路由
-- 2) 回填历史失败调用的 selected_provider，避免 usage summary 统计为 unknown

INSERT INTO models (provider_id, model_key, display_name, upstream_model, is_active, description)
SELECT
  p.id,
  'qwen3.6-plus',
  'Qwen3.6 Plus',
  'qwen3.6-plus',
  TRUE,
  'Qwen3.6 Plus - Coding Plan'
FROM providers p
WHERE p.name = 'bailian_coding_api'
  AND NOT EXISTS (
    SELECT 1 FROM models m WHERE m.model_key = 'qwen3.6-plus'
  );

INSERT INTO model_routes (model_key, is_enabled, priority, description)
SELECT
  'qwen3.6-plus',
  TRUE,
  0,
  'Qwen3.6 Plus - Coding Plan'
WHERE NOT EXISTS (
  SELECT 1 FROM model_routes r WHERE r.model_key = 'qwen3.6-plus'
);

INSERT INTO route_rules (model_name, primary_provider, fallback_provider, is_enabled, description)
SELECT
  'qwen3.6-plus',
  'bailian_coding_api',
  NULL,
  TRUE,
  'Qwen3.6 Plus - Coding Plan'
WHERE NOT EXISTS (
  SELECT 1 FROM route_rules rr WHERE rr.model_name = 'qwen3.6-plus'
);

UPDATE call_logs
SET selected_provider = primary_provider
WHERE selected_provider IS NULL
  AND primary_provider IS NOT NULL
  AND status <> 'success';
