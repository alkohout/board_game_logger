-- 009 — Record the token counts behind each AI charge.
--
-- The ledger stored only a final cost, so when the rules questions looked too
-- cheap there was no way to tell a pricing bug from a genuinely cheap
-- question — it had to be reasoned out. Storing the four token buckets makes
-- a charge auditable, and lets any past period be recosted if a rate or a
-- calculation turns out to be wrong.
--
--   ./venv/bin/python migrations/run_sql.py migrations/009_usage_tokens.sql
--
-- Safe to re-run. Existing rows keep NULL counts: they predate this.

BEGIN;

ALTER TABLE ai_usage ADD COLUMN IF NOT EXISTS input_tokens       INTEGER;
ALTER TABLE ai_usage ADD COLUMN IF NOT EXISTS output_tokens      INTEGER;
ALTER TABLE ai_usage ADD COLUMN IF NOT EXISTS cache_write_tokens INTEGER;
ALTER TABLE ai_usage ADD COLUMN IF NOT EXISTS cache_read_tokens  INTEGER;

COMMIT;
