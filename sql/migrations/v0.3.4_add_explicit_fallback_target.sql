-- Add an explicit fallback model target and reject orphan model records.
\set ON_ERROR_STOP on

BEGIN;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM models WHERE provider_id IS NULL) THEN
    RAISE EXCEPTION
      'cannot enforce models.provider_id: orphan models exist';
  END IF;
END
$$;

ALTER TABLE models
  ALTER COLUMN provider_id SET NOT NULL;

ALTER TABLE route_rules
  ADD COLUMN IF NOT EXISTS fallback_model_key VARCHAR(128);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'route_rules_fallback_model_key_fkey'
  ) THEN
    ALTER TABLE route_rules
      ADD CONSTRAINT route_rules_fallback_model_key_fkey
      FOREIGN KEY (fallback_model_key)
      REFERENCES models(model_key)
      NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'route_rules_fallback_target_pair_check'
  ) THEN
    ALTER TABLE route_rules
      ADD CONSTRAINT route_rules_fallback_target_pair_check
      CHECK (
        (fallback_provider IS NULL AND fallback_model_key IS NULL)
        OR
        (fallback_provider IS NOT NULL AND fallback_model_key IS NOT NULL)
      )
      NOT VALID;
  END IF;
END
$$;

COMMIT;
