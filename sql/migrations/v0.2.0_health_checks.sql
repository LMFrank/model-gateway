-- Model Gateway v0.2.0 Health Checks
-- 健康检查系统表结构与基础功能
-- 执行方式: psql -h <host> -U <user> -d model_gateway -f v0.2.0_health_checks.sql

\set ON_ERROR_STOP on

-- ============================================================================
-- 1. 创建健康检查记录表
-- ============================================================================

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

COMMENT ON TABLE health_checks IS '健康检查记录表，存储 Provider 和 Model 的检查结果';
COMMENT ON COLUMN health_checks.check_type IS '检查类型: provider 或 model';
COMMENT ON COLUMN health_checks.target_id IS '目标 ID（provider_id 或 model_id）';
COMMENT ON COLUMN health_checks.target_name IS '目标名称（便于查询）';
COMMENT ON COLUMN health_checks.status IS '健康状态: healthy, unhealthy, unknown';
COMMENT ON COLUMN health_checks.check_result IS '检查结果详情（JSON）';
COMMENT ON COLUMN health_checks.latency_ms IS '检查耗时（毫秒）';

-- ============================================================================
-- 2. 创建索引
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_health_checks_target ON health_checks (check_type, target_id);
CREATE INDEX IF NOT EXISTS idx_health_checks_checked_at ON health_checks (checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_checks_status ON health_checks (status);

-- ============================================================================
-- 3. 验证表创建
-- ============================================================================

SELECT 'Health Checks Table Created' AS info;
SELECT COUNT(*) AS health_checks_count FROM health_checks;