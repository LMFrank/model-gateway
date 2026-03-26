-- 在任意 MySQL 8.0+ 实例中执行：
-- mysql -h <mysql-host> -u <admin-user> -p < sql/init_model_gateway.sql

CREATE DATABASE IF NOT EXISTS model_gateway CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'model_gateway_user'@'%' IDENTIFIED BY 'CHANGE_ME_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON model_gateway.* TO 'model_gateway_user'@'%';
FLUSH PRIVILEGES;

USE model_gateway;

CREATE TABLE IF NOT EXISTS route_rules (
  model_name VARCHAR(128) NOT NULL PRIMARY KEY,
  primary_provider VARCHAR(64) NOT NULL,
  fallback_provider VARCHAR(64) NULL,
  is_enabled TINYINT(1) NOT NULL DEFAULT 1,
  description VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS provider_configs (
  provider_name VARCHAR(64) NOT NULL PRIMARY KEY,
  config_json JSON NOT NULL,
  is_enabled TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS call_logs (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  request_id VARCHAR(64) NOT NULL,
  task_id VARCHAR(64) NULL,
  stock_code VARCHAR(32) NULL,
  model_name VARCHAR(128) NOT NULL,
  primary_provider VARCHAR(64) NULL,
  fallback_provider VARCHAR(64) NULL,
  route_chain JSON NULL,
  selected_provider VARCHAR(64) NULL,
  status VARCHAR(16) NOT NULL,
  http_status INT NULL,
  error_message VARCHAR(2000) NULL,
  prompt_tokens INT NULL,
  completion_tokens INT NULL,
  total_tokens INT NULL,
  latency_ms INT NULL,
  is_stream TINYINT(1) NOT NULL DEFAULT 0,
  request_body JSON NULL,
  response_body JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_created_at (created_at),
  KEY idx_model_name (model_name),
  KEY idx_status (status),
  KEY idx_task_stock (task_id, stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS daily_usage_agg (
  stat_date DATE NOT NULL,
  provider_name VARCHAR(64) NOT NULL,
  model_name VARCHAR(128) NOT NULL,
  call_count INT NOT NULL DEFAULT 0,
  failed_count INT NOT NULL DEFAULT 0,
  total_tokens BIGINT NOT NULL DEFAULT 0,
  p95_latency_ms INT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (stat_date, provider_name, model_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 示例路由规则
INSERT INTO route_rules (model_name, primary_provider, fallback_provider, is_enabled, description)
VALUES
  ('kimi-for-coding', 'kimi_cli', 'qwen_api', 1, 'Kimi 主通道, Qwen 回退'),
  ('qwen3.5-plus', 'qwen_api', NULL, 1, 'Qwen 直连')
ON DUPLICATE KEY UPDATE
  primary_provider = VALUES(primary_provider),
  fallback_provider = VALUES(fallback_provider),
  is_enabled = VALUES(is_enabled),
  description = VALUES(description);

-- provider_configs 示例（请替换为真实密钥/地址）
INSERT INTO provider_configs (provider_name, config_json, is_enabled)
VALUES
  ('kimi_cli', JSON_OBJECT(
      'command', 'kimi',
      'args', JSON_ARRAY('chat'),
      'model_arg', '--model',
      'prompt_arg', '--prompt',
      'stream_arg', '--stream',
      'timeout_sec', 120
    ), 1),
  ('qwen_api', JSON_OBJECT(
      'base_url', 'https://dashscope.aliyuncs.com/compatible-mode/v1',
      'chat_endpoint', '/chat/completions',
      'api_key', 'REPLACE_WITH_REAL_KEY',
      'upstream_model', 'qwen3.5-plus',
      'timeout_sec', 120
    ), 1)
ON DUPLICATE KEY UPDATE
  config_json = VALUES(config_json),
  is_enabled = VALUES(is_enabled);
