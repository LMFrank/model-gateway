-- Model Gateway v0.1.0 Schema Refactor
-- 重构数据库 schema 支持统一配置中心架构
-- 执行方式: psql -h <host> -U <user> -d model_gateway -f v0.1.0_schema_refactor.sql

\set ON_ERROR_STOP on

-- ============================================================================
-- 1. 创建新表结构
-- ============================================================================

-- providers 表（重构）
CREATE TABLE IF NOT EXISTS providers (
  id SERIAL PRIMARY KEY,
  name VARCHAR(64) UNIQUE NOT NULL,
  display_name VARCHAR(128) NOT NULL,
  provider_type VARCHAR(32) NOT NULL CHECK (provider_type IN ('cli', 'api')),
  base_url VARCHAR(512),
  api_key VARCHAR(512),
  config_json JSONB DEFAULT '{}',
  description TEXT,
  is_enabled BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE providers IS 'Provider 配置表，支持 CLI 和 API 两种类型';
COMMENT ON COLUMN providers.provider_type IS 'provider 类型: cli 或 api';
COMMENT ON COLUMN providers.config_json IS '额外配置参数，CLI 模式下存储命令参数等';

-- models 表（新建）
CREATE TABLE IF NOT EXISTS models (
  id SERIAL PRIMARY KEY,
  provider_id INTEGER REFERENCES providers(id) ON DELETE CASCADE,
  model_key VARCHAR(128) UNIQUE NOT NULL,
  display_name VARCHAR(128) NOT NULL,
  upstream_model VARCHAR(128) NOT NULL,
  default_params JSONB DEFAULT '{}',
  description TEXT,
  notes TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  health_status VARCHAR(32) DEFAULT 'unknown',
  last_health_check TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE models IS '模型配置表，每个模型关联一个 Provider';
COMMENT ON COLUMN models.model_key IS '模型标识符（如 kimi-k2.5, qwen3.5-plus）';
COMMENT ON COLUMN models.upstream_model IS '上游模型名称，用于调用 Provider';
COMMENT ON COLUMN models.default_params IS '默认请求参数（JSON）';
COMMENT ON COLUMN models.health_status IS '健康状态: unknown, healthy, unhealthy';

-- route_rules 表（改造）
CREATE TABLE IF NOT EXISTS model_routes (
  model_key VARCHAR(128) PRIMARY KEY REFERENCES models(model_key),
  is_enabled BOOLEAN DEFAULT TRUE,
  priority INTEGER DEFAULT 0,
  description VARCHAR(255),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE model_routes IS '模型路由表，通过 model_key 关联模型';

-- ============================================================================
-- 2. 创建索引
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_models_provider_id ON models (provider_id);
CREATE INDEX IF NOT EXISTS idx_models_health_status ON models (health_status);
CREATE INDEX IF NOT EXISTS idx_models_is_active ON models (is_active);
CREATE INDEX IF NOT EXISTS idx_model_routes_enabled ON model_routes (is_enabled);

-- ============================================================================
-- 3. 创建更新时间触发器
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_providers_updated_at
  BEFORE UPDATE ON providers
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_models_updated_at
  BEFORE UPDATE ON models
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_model_routes_updated_at
  BEFORE UPDATE ON model_routes
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 4. 从旧表迁移数据
-- ============================================================================

-- 4.1 从 provider_configs 迁移到 providers
INSERT INTO providers (name, display_name, provider_type, config_json, description, is_enabled, created_at, updated_at)
SELECT 
  provider_name,
  provider_name,
  CASE 
    WHEN provider_name LIKE '%_cli' THEN 'cli'
    WHEN provider_name LIKE '%_api' THEN 'api'
    ELSE 'api'
  END,
  config_json,
  NULL,
  is_enabled,
  created_at,
  updated_at
FROM provider_configs
ON CONFLICT (name) DO UPDATE SET
  display_name = EXCLUDED.display_name,
  provider_type = EXCLUDED.provider_type,
  config_json = EXCLUDED.config_json,
  is_enabled = EXCLUDED.is_enabled,
  updated_at = NOW();

-- 4.2 从 route_rules 迁移到 models（创建基础模型记录）
-- 注意：这里为每个 route_rule 创建一个对应的 model
INSERT INTO models (provider_id, model_key, display_name, upstream_model, description, is_active, created_at, updated_at)
SELECT 
  p.id,
  rr.model_name,
  rr.model_name,
  CASE 
    WHEN rr.primary_provider = 'kimi_cli' THEN 'kimi-k2.5'
    WHEN rr.primary_provider = 'codex_cli' THEN 'gpt-5.3-codex'
    WHEN rr.primary_provider = 'qwen_api' THEN 'qwen3.5-plus'
    ELSE rr.model_name
  END,
  rr.description,
  rr.is_enabled,
  rr.created_at,
  rr.updated_at
FROM route_rules rr
JOIN providers p ON p.name = rr.primary_provider
ON CONFLICT (model_key) DO UPDATE SET
  display_name = EXCLUDED.display_name,
  upstream_model = EXCLUDED.upstream_model,
  description = EXCLUDED.description,
  is_active = EXCLUDED.is_active,
  updated_at = NOW();

-- 4.3 迁移 route_rules 到核心路由表
INSERT INTO model_routes (model_key, is_enabled, priority, description, created_at, updated_at)
SELECT 
  rr.model_name,
  rr.is_enabled,
  0,
  rr.description,
  rr.created_at,
  rr.updated_at
FROM route_rules rr
ON CONFLICT (model_key) DO UPDATE SET
  is_enabled = EXCLUDED.is_enabled,
  description = EXCLUDED.description,
  updated_at = NOW();

-- ============================================================================
-- 5. 为 Provider 设置 base_url 和 api_key（从 config_json 提取）
-- ============================================================================

UPDATE providers
SET 
  base_url = config_json->>'base_url',
  api_key = config_json->>'api_key'
WHERE provider_type = 'api';

-- ============================================================================
-- 6. 验证数据迁移
-- ============================================================================

SELECT 'Migration Summary:' AS info;
SELECT COUNT(*) AS total_providers FROM providers;
SELECT COUNT(*) AS total_models FROM models;
SELECT COUNT(*) AS total_routes FROM model_routes;
