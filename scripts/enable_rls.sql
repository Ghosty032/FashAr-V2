-- ==========================================================================================
-- FASHR — Lock the public anon key out of the application tables
--
-- Run this in the Supabase SQL editor AFTER deploying the service-role change in
-- frontend/lib/supabase-admin.ts. Running it before will break history and ratings,
-- because the routes would still be using the anon key this script revokes.
--
-- WHY THIS WORKS
-- NEXT_PUBLIC_SUPABASE_ANON_KEY is public by construction: the NEXT_PUBLIC_ prefix ships
-- it to every browser. Until now these tables had RLS disabled, so anyone holding that key
-- could read, insert and delete every user's rows straight against the Supabase REST API,
-- completely bypassing the Next.js routes and their user_id filters.
--
-- Enabling RLS with NO policies denies all access to the anon and authenticated roles.
-- The service_role key bypasses RLS entirely, so the API routes keep working unchanged.
-- Authorization now lives exclusively in those routes: verify the Clerk session, then
-- filter by that user's id on every query.
--
-- NOTE: this intentionally does not touch scripts/schema.sql, which describes a different
-- set of tables (users / analyses / ratings) than the ones the code actually uses. That
-- drift is tracked separately — see the Tier 3 review item.
-- ==========================================================================================

alter table public.wardrobe_history enable row level security;
alter table public.product_ratings  enable row level security;

-- No CREATE POLICY statements. That is the point: default-deny for every role except
-- service_role. If you later add direct browser access to Supabase, add scoped policies
-- here rather than turning RLS back off.

-- ==========================================================================================
-- VERIFY
-- rowsecurity should be true for both tables, and each should have zero policies.
-- ==========================================================================================

select tablename, rowsecurity
from pg_tables
where schemaname = 'public'
  and tablename in ('wardrobe_history', 'product_ratings');

select tablename, count(policyname) as policy_count
from pg_policies
where schemaname = 'public'
  and tablename in ('wardrobe_history', 'product_ratings')
group by tablename;

-- ==========================================================================================
-- AFTER RUNNING
-- Rotate the anon key in the Supabase dashboard (Settings -> API). It has been readable by
-- every visitor and was, until this change, effectively an admin credential.
-- ==========================================================================================
