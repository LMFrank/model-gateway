-- Model Gateway v0.3.0 Add Providers and Models
-- 新增百炼 Coding Plan、百炼通用 API、DeepSeek 官方 providers 及对应 models
-- 执行方式: docker exec -i pg psql -U postgres -d model_gateway < sql/migrations/v0.3.0_add_providers_models.sql

\set ON_ERROR_STOP on

-- ============================================================================
-- 1. 清理旧数据
-- ============================================================================

-- 删除旧的路由规则 (route_rules_v2 有外键约束，需要先删除)
DELETE FROM route_rules_v2 WHERE model_key IN ('qwen3.5-plus');
DELETE FROM route_rules WHERE model_name IN ('qwen3.5-plus');

-- 删除旧的 models（关联到要删除的 providers）
DELETE FROM models WHERE provider_id IN (SELECT id FROM providers WHERE name IN ('kimi_api', 'qwen_api'));

-- 删除旧的 providers
DELETE FROM providers WHERE name IN ('kimi_api', 'qwen_api');

-- ============================================================================
-- 2. 新增 Providers
-- ============================================================================

INSERT INTO providers (name, display_name, provider_type, base_url, api_key, is_enabled, description) VALUES
('bailian_coding_api', '百炼 Coding Plan', 'api', 'https://coding.dashscope.aliyuncs.com/v1', '', true, '阿里云百炼 Coding Plan API，按订阅计费（需手动配置 API Key）'),
('bailian_api', '百炼通用 API', 'api', 'https://dashscope.aliyuncs.com/compatible-mode/v1', '', true, '阿里云百炼标准 API，按 Token 计费（需手动配置 API Key）'),
('deepseek_api', 'DeepSeek 官方', 'api', 'https://api.deepseek.com/v1', '', true, 'DeepSeek 官方 API（需手动配置 API Key）');

-- ============================================================================
-- 3. 新增 Models
-- ============================================================================

-- 3.1 百炼 Coding Plan Models
INSERT INTO models (provider_id, model_key, display_name, upstream_model, is_active, description) VALUES
((SELECT id FROM providers WHERE name = 'bailian_coding_api'), 'qwen3.5-plus', 'Qwen3.5 Plus', 'qwen3.5-plus', true, 'Qwen3.5 Plus - Coding Plan'),
((SELECT id FROM providers WHERE name = 'bailian_coding_api'), 'qwen3-max', 'Qwen3 Max', 'qwen3-max-2026-01-23', true, 'Qwen3 Max - Coding Plan'),
((SELECT id FROM providers WHERE name = 'bailian_coding_api'), 'qwen3-coder', 'Qwen3 Coder', 'qwen3-coder-next', true, 'Qwen3 Coder - Coding Plan'),
((SELECT id FROM providers WHERE name = 'bailian_coding_api'), 'kimi-k2.5', 'Kimi K2.5', 'kimi-k2.5', true, 'Kimi K2.5 - Coding Plan'),
((SELECT id FROM providers WHERE name = 'bailian_coding_api'), 'glm-5', 'GLM-5', 'glm-5', true, 'GLM-5 - Coding Plan'),
((SELECT id FROM providers WHERE name = 'bailian_coding_api'), 'glm-4.7', 'GLM-4.7', 'glm-4.7', true, 'GLM-4.7 - Coding Plan'),
((SELECT id FROM providers WHERE name = 'bailian_coding_api'), 'minimax-m2.5', 'MiniMax M2.5', 'minimax-m2.5', true, 'MiniMax M2.5 - Coding Plan');

-- 3.2 百炼通用 API Models
INSERT INTO models (provider_id, model_key, display_name, upstream_model, is_active, description) VALUES
((SELECT id FROM providers WHERE name = 'bailian_api'), 'qwen3-max-general', 'Qwen3 Max 通用', 'qwen3-max', true, 'Qwen3 Max - 百炼标准 API'),
((SELECT id FROM providers WHERE name = 'bailian_api'), 'deepseek-v3.2', 'DeepSeek V3.2', 'deepseek-v3.2', true, 'DeepSeek V3.2 - 百炼托管');

-- 3.3 DeepSeek 官方 Models
INSERT INTO models (provider_id, model_key, display_name, upstream_model, is_active, description) VALUES
((SELECT id FROM providers WHERE name = 'deepseek_api'), 'deepseek-chat', 'DeepSeek Chat', 'deepseek-chat', true, 'DeepSeek Chat - 官方 API');

-- 3.4 OpenAI API (sub2api) Models
INSERT INTO models (provider_id, model_key, display_name, upstream_model, is_active, description) VALUES
((SELECT id FROM providers WHERE name = 'openai_api'), 'gpt-5.3-codex', 'GPT-5.3 Codex', 'gpt-5.3-codex', true, 'GPT-5.3 Codex - sub2api 代理');

-- ============================================================================
-- 4. 新增 Route Rules (v2)
-- ============================================================================

INSERT INTO route_rules_v2 (model_key, is_enabled, priority, description) VALUES
-- CLI providers
('kimi-for-coding', true, 0, 'Kimi CLI 调用'),
('codex-for-coding', true, 0, 'Codex CLI 调用'),
-- 百炼 Coding Plan
('qwen3.5-plus', true, 0, 'Qwen3.5 Plus - Coding Plan'),
('qwen3-max', true, 0, 'Qwen3 Max - Coding Plan'),
('qwen3-coder', true, 0, 'Qwen3 Coder - Coding Plan'),
('kimi-k2.5', true, 0, 'Kimi K2.5 - Coding Plan'),
('glm-5', true, 0, 'GLM-5 - Coding Plan'),
('glm-4.7', true, 0, 'GLM-4.7 - Coding Plan'),
('minimax-m2.5', true, 0, 'MiniMax M2.5 - Coding Plan'),
-- 百炼通用 API
('qwen3-max-general', true, 0, 'Qwen3 Max - 百炼标准 API'),
('deepseek-v3.2', true, 0, 'DeepSeek V3.2 - 百炼托管'),
-- DeepSeek 官方
('deepseek-chat', true, 0, 'DeepSeek Chat - 官方 API'),
-- OpenAI API (sub2api)
('gpt-5.3-codex', true, 0, 'GPT-5.3 Codex - sub2api 代理')
ON CONFLICT (model_key) DO UPDATE SET
  is_enabled = EXCLUDED.is_enabled,
  description = EXCLUDED.description,
  updated_at = NOW();

-- 保留旧的 route_rules 表兼容
INSERT INTO route_rules (model_name, primary_provider, fallback_provider, is_enabled, description) VALUES
-- CLI providers
('kimi-for-coding', 'kimi_cli', NULL, true, 'Kimi CLI 调用'),
('codex-for-coding', 'codex_cli', NULL, true, 'Codex CLI 调用'),
-- 百炼 Coding Plan
('qwen3.5-plus', 'bailian_coding_api', NULL, true, 'Qwen3.5 Plus - Coding Plan'),
('qwen3-max', 'bailian_coding_api', NULL, true, 'Qwen3 Max - Coding Plan'),
('qwen3-coder', 'bailian_coding_api', NULL, true, 'Qwen3 Coder - Coding Plan'),
('kimi-k2.5', 'bailian_coding_api', NULL, true, 'Kimi K2.5 - Coding Plan'),
('glm-5', 'bailian_coding_api', NULL, true, 'GLM-5 - Coding Plan'),
('glm-4.7', 'bailian_coding_api', NULL, true, 'GLM-4.7 - Coding Plan'),
('minimax-m2.5', 'bailian_coding_api', NULL, true, 'MiniMax M2.5 - Coding Plan'),
-- 百炼通用 API
('qwen3-max-general', 'bailian_api', NULL, true, 'Qwen3 Max - 百炼标准 API'),
('deepseek-v3.2', 'bailian_api', NULL, true, 'DeepSeek V3.2 - 百炼托管'),
-- DeepSeek 官方
('deepseek-chat', 'deepseek_api', NULL, true, 'DeepSeek Chat - 官方 API'),
-- OpenAI API (sub2api)
('gpt-5.3-codex', 'openai_api', NULL, true, 'GPT-5.3 Codex - sub2api 代理')
ON CONFLICT (model_name) DO UPDATE SET
  primary_provider = EXCLUDED.primary_provider,
  is_enabled = EXCLUDED.is_enabled,
  description = EXCLUDED.description;

-- ============================================================================
-- 5. 验证结果
-- ============================================================================

SELECT 'Providers:' AS category;
SELECT id, name, display_name, provider_type, is_enabled FROM providers ORDER BY id;

SELECT 'Models:' AS category;
SELECT m.id, m.model_key, m.display_name, p.name AS provider_name, m.upstream_model, m.is_active
FROM models m
JOIN providers p ON m.provider_id = p.id
ORDER BY p.name, m.model_key;

SELECT 'Route Rules:' AS category;
SELECT id, model_name, primary_provider, is_enabled FROM route_rules ORDER BY model_name;