-- 在 PostgreSQL 14+ 实例中通过 psql 执行：
-- psql -h <pg-host> -U <pg-admin-user> -d postgres -v mgw_db_password='CHANGE_ME_STRONG_PASSWORD' -f sql/init_model_gateway.sql

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

-- 示例路由规则
INSERT INTO route_rules (model_name, primary_provider, fallback_provider, is_enabled, description)
VALUES
  ('kimi-for-coding', 'kimi_cli', NULL, TRUE, 'Kimi 主通道（无回退）'),
  ('codex-for-coding', 'codex_cli', NULL, TRUE, 'Codex 主通道（无回退）'),
  ('qwen3.5-plus', 'qwen_api', NULL, TRUE, 'Qwen 直连')
ON CONFLICT (model_name) DO UPDATE SET
  primary_provider = EXCLUDED.primary_provider,
  fallback_provider = EXCLUDED.fallback_provider,
  is_enabled = EXCLUDED.is_enabled,
  description = EXCLUDED.description,
  updated_at = NOW();

-- provider_configs 示例（请替换为真实密钥/地址）
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
      'api_key', 'REPLACE_WITH_REAL_KEY',
      'upstream_model', 'qwen3.5-plus',
      'timeout_sec', 120
    ),
    TRUE
  )
ON CONFLICT (provider_name) DO UPDATE SET
  config_json = EXCLUDED.config_json,
  is_enabled = EXCLUDED.is_enabled,
  updated_at = NOW();
