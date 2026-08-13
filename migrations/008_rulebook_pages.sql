-- 008 — Record how many pages each rulebook has.
--
-- Sending a book as page images costs roughly 2,500 tokens a page, so with a
-- page count the app can tell you what a question will cost *before* you ask
-- for images, instead of finding out afterwards.
--
--   ./venv/bin/python migrations/run_sql.py migrations/008_rulebook_pages.sql
--   ./venv/bin/python migrations/006_extract_rulebook_text.py   # fills it in
--
-- Safe to re-run.

BEGIN;

ALTER TABLE rulebooks ADD COLUMN IF NOT EXISTS page_count INTEGER;

COMMIT;
