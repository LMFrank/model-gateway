-- 当前 schema 的一键 bootstrap 脚本（PostgreSQL 14+）
-- 用法：
-- psql -h <pg-host> -U <pg-admin-user> -d postgres -v mgw_db_password='CHANGE_ME_STRONG_PASSWORD' -f sql/bootstrap_model_gateway.sql

\set ON_ERROR_STOP on

SELECT format('CREATE ROLE model_gateway_user LOGIN PASSWORD %L', :'mgw_db_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'model_gateway_user')
\gexec

SELECT 'CREATE DATABASE model_gateway OWNER model_gateway_user'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'model_gateway')
\gexec

\connect model_gateway

GRANT ALL PRIVILEGES ON DATABASE model_gateway TO model_gateway_user;
GRANT USAGE, CREATE ON SCHEMA public TO model_gateway_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO model_gateway_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO model_gateway_user;

-- ============================================================================
-- Compatibility tables（兼容接口 / 审计）
-- ============================================================================

CREATE TABLE IF NOT EXISTS route_rules (
  model_name VARCHAR(128) PRIMARY KEY,
  primary_provider VARCHAR(64) NOT NULL,
  fallback_provider VARCHAR(64),
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  description VARCHAR(255),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS provider_configs (
  provider_name VARCHAR(64) PRIMARY KEY,
  config_json JSONB NOT NULL,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS call_logs (
  id BIGSERIAL PRIMARY KEY,
  request_id VARCHAR(64) NOT NULL,
  task_id VARCHAR(64),
  stock_code VARCHAR(32),
  model_name VARCHAR(128) NOT NULL,
  primary_provider VARCHAR(64),
  fallback_provider VARCHAR(64),
  route_chain JSONB,
  selected_provider VARCHAR(64),
  status VARCHAR(16) NOT NULL,
  http_status INT,
  error_message VARCHAR(2000),
  prompt_tokens INT,
  completion_tokens INT,
  total_tokens INT,
  latency_ms INT,
  is_stream BOOLEAN NOT NULL DEFAULT FALSE,
  request_body JSONB,
  response_body JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_call_logs_created_at ON call_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_call_logs_model_name ON call_logs (model_name);
CREATE INDEX IF NOT EXISTS idx_call_logs_status ON call_logs (status);
CREATE INDEX IF NOT EXISTS idx_call_logs_task_stock ON call_logs (task_id, stock_code);

CREATE TABLE IF NOT EXISTS daily_usage_agg (
  stat_date DATE NOT NULL,
  provider_name VARCHAR(64) NOT NULL,
  model_name VARCHAR(128) NOT NULL,
  call_count INT NOT NULL DEFAULT 0,
  failed_count INT NOT NULL DEFAULT 0,
  total_tokens BIGINT NOT NULL DEFAULT 0,
  p95_latency_ms INT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (stat_date, provider_name, model_name)
);

-- ============================================================================
-- Current schema tables
-- ============================================================================

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

CREATE TABLE IF NOT EXISTS model_routes (
  model_key VARCHAR(128) PRIMARY KEY REFERENCES models(model_key),
  is_enabled BOOLEAN DEFAULT TRUE,
  priority INTEGER DEFAULT 0,
  description VARCHAR(255),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS health_checks (
  id SERIAL PRIMARY KEY,
  check_type VARCHAR(16) NOT NULL CHECK (check_type IN ('provider', 'model')),
  target_id INTEGER NOT NULL,
  target_name VARCHAR(128) NOT NULL,
  status VARCHAR(16) NOT NULL CHECK (status IN ('healthy', 'unhealthy', 'unknown')),
  check_result JSONB DEFAULT '{}',
  latency_ms INTEGER,
  error_message TEXT,
  checked_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_models_provider_id ON models (provider_id);
CREATE INDEX IF NOT EXISTS idx_models_health_status ON models (health_status);
CREATE INDEX IF NOT EXISTS idx_models_is_active ON models (is_active);
CREATE INDEX IF NOT EXISTS idx_model_routes_enabled ON model_routes (is_enabled);
CREATE INDEX IF NOT EXISTS idx_health_checks_target ON health_checks (check_type, target_id);
CREATE INDEX IF NOT EXISTS idx_health_checks_checked_at ON health_checks (checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_checks_status ON health_checks (status);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_providers_updated_at') THEN
    CREATE TRIGGER update_providers_updated_at
      BEFORE UPDATE ON providers
      FOR EACH ROW
      EXECUTE FUNCTION update_updated_at_column();
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_models_updated_at') THEN
    CREATE TRIGGER update_models_updated_at
      BEFORE UPDATE ON models
      FOR EACH ROW
      EXECUTE FUNCTION update_updated_at_column();
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_model_routes_updated_at') THEN
    CREATE TRIGGER update_model_routes_updated_at
      BEFORE UPDATE ON model_routes
      FOR EACH ROW
      EXECUTE FUNCTION update_updated_at_column();
  END IF;
END $$;

-- ============================================================================
-- Seed compatibility provider_configs（便于兼容与迁移）
-- ============================================================================

INSERT INTO provider_configs (provider_name, config_json, is_enabled)
VALUES
  (
    'kimi_cli',
    jsonb_build_object(
      'command', 'kimi',
      'args', jsonb_build_array('chat'),
      'model_arg', '--model',
      'prompt_arg', '--prompt',
      'use_stdin_prompt', TRUE,
      'stream_arg', '--stream',
      'timeout_sec', 120
    ),
    TRUE
  ),
  (
    'codex_cli',
    jsonb_build_object(
      'command', 'codex',
      'args', jsonb_build_array('exec', '--skip-git-repo-check', '--sandbox', 'read-only', '--color', 'never', '-o', '/tmp/codex_last_message.txt'),
      'model_arg', '--model',
      'upstream_model', 'gpt-5.3-codex',
      'use_stdin_prompt', TRUE,
      'force_stdin_prompt', TRUE,
      'stdin_prompt_arg', '-',
      'response_file', '/tmp/codex_last_message.txt',
      'stream_arg', NULL,
      'timeout_sec', 300
    ),
    TRUE
  ),
  (
    'qwen_api',
    jsonb_build_object(
      'base_url', 'https://dashscope.aliyuncs.com/compatible-mode/v1',
      'chat_endpoint', '/chat/completions',
      'api_key', '',
      'upstream_model', 'qwen3.5-plus',
      'timeout_sec', 120
    ),
    FALSE
  )
ON CONFLICT (provider_name) DO UPDATE SET
  config_json = EXCLUDED.config_json,
  is_enabled = EXCLUDED.is_enabled,
  updated_at = NOW();

-- ============================================================================
-- Seed providers（以当前 schema 为准）
-- ============================================================================

INSERT INTO providers (name, display_name, provider_type, base_url, api_key, config_json, description, is_enabled)
VALUES
  ('kimi_cli', 'Kimi CLI', 'cli', NULL, NULL,
    jsonb_build_object(
      'command', 'kimi',
      'args', jsonb_build_array('chat'),
      'model_arg', '--model',
      'prompt_arg', '--prompt',
      'use_stdin_prompt', TRUE,
      'stream_arg', '--stream',
      'timeout_sec', 120
    ),
    'Kimi CLI 调用入口',
    TRUE
  ),
  ('codex_cli', 'Codex CLI', 'cli', NULL, NULL,
    jsonb_build_object(
      'command', 'codex',
      'args', jsonb_build_array('exec', '--skip-git-repo-check', '--sandbox', 'read-only', '--color', 'never', '-o', '/tmp/codex_last_message.txt'),
      'model_arg', '--model',
      'upstream_model', 'gpt-5.3-codex',
      'use_stdin_prompt', TRUE,
      'force_stdin_prompt', TRUE,
      'stdin_prompt_arg', '-',
      'response_file', '/tmp/codex_last_message.txt',
      'timeout_sec', 300
    ),
    'Codex CLI 调用入口',
    TRUE
  ),
  ('qwen_api', 'Qwen API', 'api', 'https://dashscope.aliyuncs.com/compatible-mode/v1', '', '{}'::jsonb,
    'Qwen API 兼容配置，占位供兼容结构使用',
    FALSE
  ),
  ('bailian_coding_api', '百炼 Coding Plan', 'api', 'https://coding.dashscope.aliyuncs.com/v1', '', '{}'::jsonb,
    '阿里云百炼 Coding Plan API，需手动配置 API Key',
    TRUE
  ),
  ('bailian_api', '百炼通用 API', 'api', 'https://dashscope.aliyuncs.com/compatible-mode/v1', '', '{}'::jsonb,
    '阿里云百炼标准 API，需手动配置 API Key',
    FALSE
  ),
  ('deepseek_api', 'DeepSeek 官方', 'api', 'https://api.deepseek.com/v1', '', '{}'::jsonb,
    'DeepSeek 官方 API，需手动配置 API Key',
    FALSE
  ),
  ('openai_api', 'OpenAI / Compatible Proxy', 'api', 'https://api.openai.com/v1', '', '{}'::jsonb,
    'OpenAI 或 OpenAI 兼容代理入口；bootstrap 默认创建占位 provider，需手动补齐 base_url 与 API Key 后启用',
    FALSE
  )
ON CONFLICT (name) DO UPDATE SET
  display_name = EXCLUDED.display_name,
  provider_type = EXCLUDED.provider_type,
  base_url = EXCLUDED.base_url,
  config_json = EXCLUDED.config_json,
  description = EXCLUDED.description,
  updated_at = NOW();

-- ============================================================================
-- Seed models
-- ============================================================================

INSERT INTO models (provider_id, model_key, display_name, upstream_model, is_active, description)
VALUES
  ((SELECT id FROM providers WHERE name = 'kimi_cli'), 'kimi-for-coding', 'Kimi for Coding', 'kimi-k2.5', TRUE, 'Kimi CLI 调用'),
  ((SELECT id FROM providers WHERE name = 'codex_cli'), 'codex-for-coding', 'Codex for Coding', 'gpt-5.3-codex', TRUE, 'Codex CLI 调用'),
  ((SELECT id FROM providers WHERE name = 'bailian_coding_api'), 'qwen3.5-plus', 'Qwen3.5 Plus', 'qwen3.5-plus', TRUE, 'Qwen3.5 Plus - Coding Plan'),
  ((SELECT id FROM providers WHERE name = 'bailian_coding_api'), 'qwen3-max', 'Qwen3 Max', 'qwen3-max-2026-01-23', TRUE, 'Qwen3 Max - Coding Plan'),
  ((SELECT id FROM providers WHERE name = 'bailian_coding_api'), 'qwen3-coder', 'Qwen3 Coder', 'qwen3-coder-next', TRUE, 'Qwen3 Coder - Coding Plan'),
  ((SELECT id FROM providers WHERE name = 'bailian_coding_api'), 'qwen3-coder-plus', 'Qwen3 Coder Plus', 'qwen3-coder-plus', TRUE, 'Qwen3 Coder Plus - Coding Plan'),
  ((SELECT id FROM providers WHERE name = 'bailian_coding_api'), 'kimi-k2.5', 'Kimi K2.5', 'kimi-k2.5', TRUE, 'Kimi K2.5 - Coding Plan'),
  ((SELECT id FROM providers WHERE name = 'bailian_coding_api'), 'glm-5', 'GLM-5', 'glm-5', TRUE, 'GLM-5 - Coding Plan'),
  ((SELECT id FROM providers WHERE name = 'bailian_coding_api'), 'glm-4.7', 'GLM-4.7', 'glm-4.7', TRUE, 'GLM-4.7 - Coding Plan'),
  ((SELECT id FROM providers WHERE name = 'bailian_coding_api'), 'minimax-m2.5', 'MiniMax M2.5', 'minimax-m2.5', TRUE, 'MiniMax M2.5 - Coding Plan'),
  ((SELECT id FROM providers WHERE name = 'bailian_api'), 'qwen3-max-general', 'Qwen3 Max 通用', 'qwen3-max', TRUE, 'Qwen3 Max - 百炼标准 API'),
  ((SELECT id FROM providers WHERE name = 'bailian_api'), 'deepseek-v3.2', 'DeepSeek V3.2', 'deepseek-v3.2', TRUE, 'DeepSeek V3.2 - 百炼托管'),
  ((SELECT id FROM providers WHERE name = 'deepseek_api'), 'deepseek-chat', 'DeepSeek Chat', 'deepseek-chat', TRUE, 'DeepSeek Chat - 官方 API'),
  ((SELECT id FROM providers WHERE name = 'openai_api'), 'gpt-5.3-codex', 'GPT-5.3 Codex', 'gpt-5.3-codex', TRUE, 'GPT-5.3 Codex - OpenAI 兼容代理')
ON CONFLICT (model_key) DO UPDATE SET
  display_name = EXCLUDED.display_name,
  upstream_model = EXCLUDED.upstream_model,
  is_active = EXCLUDED.is_active,
  description = EXCLUDED.description,
  updated_at = NOW();

-- ============================================================================
-- Seed route rules（核心表 + 兼容表）
-- ============================================================================

INSERT INTO model_routes (model_key, is_enabled, priority, description)
VALUES
  ('kimi-for-coding', TRUE, 0, 'Kimi CLI 调用'),
  ('codex-for-coding', TRUE, 0, 'Codex CLI 调用'),
  ('qwen3.5-plus', TRUE, 0, 'Qwen3.5 Plus - Coding Plan'),
  ('qwen3-max', TRUE, 0, 'Qwen3 Max - Coding Plan'),
  ('qwen3-coder', TRUE, 0, 'Qwen3 Coder - Coding Plan'),
  ('qwen3-coder-plus', TRUE, 0, 'Qwen3 Coder Plus - Coding Plan'),
  ('kimi-k2.5', TRUE, 0, 'Kimi K2.5 - Coding Plan'),
  ('glm-5', TRUE, 0, 'GLM-5 - Coding Plan'),
  ('glm-4.7', TRUE, 0, 'GLM-4.7 - Coding Plan'),
  ('minimax-m2.5', TRUE, 0, 'MiniMax M2.5 - Coding Plan'),
  ('qwen3-max-general', TRUE, 0, 'Qwen3 Max - 百炼标准 API'),
  ('deepseek-v3.2', TRUE, 0, 'DeepSeek V3.2 - 百炼托管'),
  ('deepseek-chat', TRUE, 0, 'DeepSeek Chat - 官方 API'),
  ('gpt-5.3-codex', TRUE, 0, 'GPT-5.3 Codex - OpenAI 兼容代理')
ON CONFLICT (model_key) DO UPDATE SET
  is_enabled = EXCLUDED.is_enabled,
  priority = EXCLUDED.priority,
  description = EXCLUDED.description,
  updated_at = NOW();

INSERT INTO route_rules (model_name, primary_provider, fallback_provider, is_enabled, description)
VALUES
  ('kimi-for-coding', 'kimi_cli', NULL, TRUE, 'Kimi CLI 调用'),
  ('codex-for-coding', 'codex_cli', NULL, TRUE, 'Codex CLI 调用'),
  ('qwen3.5-plus', 'bailian_coding_api', NULL, TRUE, 'Qwen3.5 Plus - Coding Plan'),
  ('qwen3-max', 'bailian_coding_api', NULL, TRUE, 'Qwen3 Max - Coding Plan'),
  ('qwen3-coder', 'bailian_coding_api', NULL, TRUE, 'Qwen3 Coder - Coding Plan'),
  ('qwen3-coder-plus', 'bailian_coding_api', NULL, TRUE, 'Qwen3 Coder Plus - Coding Plan'),
  ('kimi-k2.5', 'bailian_coding_api', NULL, TRUE, 'Kimi K2.5 - Coding Plan'),
  ('glm-5', 'bailian_coding_api', NULL, TRUE, 'GLM-5 - Coding Plan'),
  ('glm-4.7', 'bailian_coding_api', NULL, TRUE, 'GLM-4.7 - Coding Plan'),
  ('minimax-m2.5', 'bailian_coding_api', NULL, TRUE, 'MiniMax M2.5 - Coding Plan'),
  ('qwen3-max-general', 'bailian_api', NULL, TRUE, 'Qwen3 Max - 百炼标准 API'),
  ('deepseek-v3.2', 'bailian_api', NULL, TRUE, 'DeepSeek V3.2 - 百炼托管'),
  ('deepseek-chat', 'deepseek_api', NULL, TRUE, 'DeepSeek Chat - 官方 API'),
  ('gpt-5.3-codex', 'openai_api', NULL, TRUE, 'GPT-5.3 Codex - OpenAI 兼容代理')
ON CONFLICT (model_name) DO UPDATE SET
  primary_provider = EXCLUDED.primary_provider,
  fallback_provider = EXCLUDED.fallback_provider,
  is_enabled = EXCLUDED.is_enabled,
  description = EXCLUDED.description,
  updated_at = NOW();

SELECT 'bootstrap_model_gateway.sql applied' AS info;
