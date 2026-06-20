-- PostgreSQL Row-Level Security (RLS) for finance-db
-- Run ONCE against finance-db after Alembic creates all tables.
-- Prevents cross-user data access even if SQL injection succeeds.
--
-- How it works:
--   1. FastAPI middleware sets `app.user_id` session variable at request start.
--   2. Each RLS policy checks `user_id = current_setting('app.user_id')::int`.
--   3. Rows not matching the policy are invisible — SELECT returns nothing,
--      UPDATE/DELETE silently affects 0 rows, INSERT raises a policy violation.
--
-- To apply:
--   docker exec -it finance-db psql -U finance_service -d finance_db -f /rls/finance_rls.sql

-- ── Enable RLS on all user-owned tables ───────────────────────────────────────

ALTER TABLE expenses         ENABLE ROW LEVEL SECURITY;
ALTER TABLE expenses         FORCE ROW LEVEL SECURITY;

ALTER TABLE savings_goals    ENABLE ROW LEVEL SECURITY;
ALTER TABLE savings_goals    FORCE ROW LEVEL SECURITY;

ALTER TABLE budgets           ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgets           FORCE ROW LEVEL SECURITY;

ALTER TABLE spending_limits  ENABLE ROW LEVEL SECURITY;
ALTER TABLE spending_limits  FORCE ROW LEVEL SECURITY;

ALTER TABLE zakat_records    ENABLE ROW LEVEL SECURITY;
ALTER TABLE zakat_records    FORCE ROW LEVEL SECURITY;

ALTER TABLE qurbani_records  ENABLE ROW LEVEL SECURITY;
ALTER TABLE qurbani_records  FORCE ROW LEVEL SECURITY;

ALTER TABLE cash_savings     ENABLE ROW LEVEL SECURITY;
ALTER TABLE cash_savings     FORCE ROW LEVEL SECURITY;

ALTER TABLE assets           ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets           FORCE ROW LEVEL SECURITY;

ALTER TABLE liabilities      ENABLE ROW LEVEL SECURITY;
ALTER TABLE liabilities      FORCE ROW LEVEL SECURITY;

ALTER TABLE sadaqah_records  ENABLE ROW LEVEL SECURITY;
ALTER TABLE sadaqah_records  FORCE ROW LEVEL SECURITY;

ALTER TABLE hajj_umrah_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE hajj_umrah_plans FORCE ROW LEVEL SECURITY;

-- ── User isolation policies ───────────────────────────────────────────────────
-- current_setting('app.user_id', true) uses the "missing_ok" flag so it returns
-- NULL instead of raising an error when the variable is not set (e.g. during
-- schema migrations run outside a request context).

CREATE POLICY user_isolation ON expenses
  USING (user_id = current_setting('app.user_id', true)::int)
  WITH CHECK (user_id = current_setting('app.user_id', true)::int);

CREATE POLICY user_isolation ON savings_goals
  USING (user_id = current_setting('app.user_id', true)::int)
  WITH CHECK (user_id = current_setting('app.user_id', true)::int);

CREATE POLICY user_isolation ON budgets
  USING (user_id = current_setting('app.user_id', true)::int)
  WITH CHECK (user_id = current_setting('app.user_id', true)::int);

CREATE POLICY user_isolation ON spending_limits
  USING (user_id = current_setting('app.user_id', true)::int)
  WITH CHECK (user_id = current_setting('app.user_id', true)::int);

CREATE POLICY user_isolation ON zakat_records
  USING (user_id = current_setting('app.user_id', true)::int)
  WITH CHECK (user_id = current_setting('app.user_id', true)::int);

CREATE POLICY user_isolation ON qurbani_records
  USING (user_id = current_setting('app.user_id', true)::int)
  WITH CHECK (user_id = current_setting('app.user_id', true)::int);

CREATE POLICY user_isolation ON cash_savings
  USING (user_id = current_setting('app.user_id', true)::int)
  WITH CHECK (user_id = current_setting('app.user_id', true)::int);

CREATE POLICY user_isolation ON assets
  USING (user_id = current_setting('app.user_id', true)::int)
  WITH CHECK (user_id = current_setting('app.user_id', true)::int);

CREATE POLICY user_isolation ON liabilities
  USING (user_id = current_setting('app.user_id', true)::int)
  WITH CHECK (user_id = current_setting('app.user_id', true)::int);

CREATE POLICY user_isolation ON sadaqah_records
  USING (user_id = current_setting('app.user_id', true)::int)
  WITH CHECK (user_id = current_setting('app.user_id', true)::int);

CREATE POLICY user_isolation ON hajj_umrah_plans
  USING (user_id = current_setting('app.user_id', true)::int)
  WITH CHECK (user_id = current_setting('app.user_id', true)::int);

-- ── Admin bypass role (optional — for admin tooling / data migrations) ────────
-- Create a role that bypasses RLS:
--   CREATE ROLE finance_admin BYPASSRLS;
--   GRANT finance_admin TO finance_service;
-- Migrations: run with SET ROLE finance_admin; before DDL statements.
