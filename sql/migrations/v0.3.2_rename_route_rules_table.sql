-- Model Gateway v0.3.2 Rename prior core route table to model_routes
-- 将旧核心路由表重命名为 model_routes，去除版本化命名

\set ON_ERROR_STOP on

DO $$
DECLARE
  old_table_name TEXT := 'route_rules_' || 'v' || '2';
  old_index_name TEXT := 'idx_route_rules_' || 'v' || '2' || '_enabled';
  old_trigger_name TEXT := 'update_route_rules_' || 'v' || '2' || '_updated_at';
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = old_table_name
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'model_routes'
  ) THEN
    EXECUTE format('ALTER TABLE %I RENAME TO model_routes', old_table_name);
  END IF;

  IF EXISTS (SELECT 1 FROM pg_class WHERE relname = old_index_name)
     AND NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'idx_model_routes_enabled') THEN
    EXECUTE format('ALTER INDEX %I RENAME TO idx_model_routes_enabled', old_index_name);
  END IF;

  IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = old_trigger_name)
     AND EXISTS (
       SELECT 1 FROM information_schema.tables
       WHERE table_schema = 'public' AND table_name = 'model_routes'
     )
     AND NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_model_routes_updated_at') THEN
    EXECUTE format(
      'ALTER TRIGGER %I ON model_routes RENAME TO update_model_routes_updated_at',
      old_trigger_name
    );
  END IF;
END $$;
