-- ==========================================================================================
-- FASHR — Supabase schema
--
-- This file is the canonical definition of the database the application actually uses.
--
-- PROVENANCE: reconstructed from the columns the code reads and writes, because the
-- Supabase project was unreachable when this was written. If the live project comes back,
-- diff this against `supabase db dump --schema public` before trusting it.
--
-- It replaces an earlier version that described three tables (`analyses`, and a `ratings`
-- table with no user_id) which the application has never used. That file could not have
-- recreated a working database, and its RLS policies keyed on auth.uid(), which is NULL
-- for every request this app makes.
--
-- IDs ARE CLERK IDS. Authentication is Clerk, not Supabase Auth, so every user identifier
-- here is the Clerk user id as TEXT (e.g. 'user_2abc...'). That is also why no policy in
-- this file references auth.uid() — it would always be NULL.
--
-- Safe to run against an existing database: every statement is guarded.
-- ==========================================================================================


-- ==========================================================================================
-- USERS — style profile captured during onboarding
-- Written by: frontend/app/onboarding/page.tsx
-- Read by:    the analyze route, to filter product recommendations
-- ==========================================================================================
create table if not exists public.users (
    -- Clerk user id, not a UUID.
    id                text primary key,
    email             text not null,

    -- Dimensions used to filter Pinecone results.
    gender_filter     text not null default 'unisex'
                      check (gender_filter in ('mens', 'womens', 'unisex')),
    body_type         text[] not null default '{}',
    size_range        text[] not null default '{}',
    preferred_brands  text[] not null default '{}',

    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now()
);

-- Plain TEXT with a CHECK rather than a Postgres ENUM: the value set is still enforced,
-- but adding a new option later is an ALTER of the constraint instead of a type migration.


-- ==========================================================================================
-- WARDROBE_HISTORY — one row per completed analysis
-- Written by: POST /api/history      Read by: GET /api/history      Deleted by: DELETE /api/history/[id]
-- ==========================================================================================
create table if not exists public.wardrobe_history (
    id                    uuid primary key default gen_random_uuid(),

    -- Clerk user id. Deliberately NOT a foreign key to public.users: Clerk is the source
    -- of truth for identity, and history is written immediately after an analysis. An FK
    -- here would make saving history fail for anyone who has not completed onboarding,
    -- turning a profile gap into silent data loss. Add one only once every signed-in user
    -- is guaranteed a profile row, and pair it with ON DELETE CASCADE for erasure requests.
    user_id               text not null,

    -- AI output
    style_score           integer not null check (style_score between 0 and 100),
    score_breakdown       jsonb   not null default '{}'::jsonb,
    narrative_critique    text    not null default '',
    gap_type              text,
    detected_items        jsonb   not null default '[]'::jsonb,
    color_palette         jsonb   not null default '[]'::jsonb,
    recommended_products  jsonb   not null default '[]'::jsonb,

    -- Request context. Both are nullable because they were not persisted before the fix
    -- for item 11, so existing rows will have NULLs here.
    weather               jsonb,
    occasion              text,
    persona               text,

    created_at            timestamptz not null default now()
);

-- GET /api/history filters by user_id and orders by created_at desc — index accordingly.
create index if not exists wardrobe_history_user_created_idx
    on public.wardrobe_history (user_id, created_at desc);


-- ==========================================================================================
-- PRODUCT_RATINGS — 1-5 star feedback, aggregated into Pinecone retrieval_weight
-- Written by: POST /api/rate
-- Read by:    ai-core/scripts/update_product_weights.py
--
-- PRIVACY NOTE: these ratings are NOT anonymous. user_id is stored, because the upsert
-- uses ON CONFLICT (product_id, user_id) so a user can revise their own rating. The
-- superseded schema claimed ratings were "completely anonymous" while the code stored the
-- user id regardless. The code's behaviour is recorded here as the truth. If anonymity is
-- actually wanted, that is a deliberate change: drop user_id and find another way to make
-- a rating idempotent per person.
-- ==========================================================================================
create table if not exists public.product_ratings (
    id          uuid primary key default gen_random_uuid(),

    -- Pinecone vector id, e.g. 'prod_000_italian_wool_unstructured_blaz'. Not a FK —
    -- the product catalog lives in Pinecone, not Postgres.
    product_id  text not null,
    -- Clerk user id, not an FK — same reasoning as wardrobe_history.user_id above.
    user_id     text not null,

    rating      integer not null check (rating between 1 and 5),

    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now(),

    -- Required by the ON CONFLICT target in POST /api/rate. Without this exact
    -- constraint the upsert fails at runtime.
    constraint product_ratings_product_user_key unique (product_id, user_id)
);

create index if not exists product_ratings_product_idx
    on public.product_ratings (product_id);


-- ==========================================================================================
-- KEEP updated_at HONEST
-- ==========================================================================================
create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists users_touch_updated_at on public.users;
create trigger users_touch_updated_at
    before update on public.users
    for each row execute function public.touch_updated_at();

drop trigger if exists product_ratings_touch_updated_at on public.product_ratings;
create trigger product_ratings_touch_updated_at
    before update on public.product_ratings
    for each row execute function public.touch_updated_at();


-- ==========================================================================================
-- ROW LEVEL SECURITY
--
-- RLS is enabled with NO policies, which denies the anon and authenticated roles entirely.
-- That is intentional. The public anon key ships to every browser via its NEXT_PUBLIC_
-- prefix, so it must not be able to reach these tables.
--
-- The API routes use the service-role key, which bypasses RLS. Authorization therefore
-- lives exclusively in those route handlers: verify the Clerk session, then filter by that
-- user's id on every query. There is no database-level safety net behind them.
--
-- Do NOT write auth.uid() policies here. Authentication is Clerk, so auth.uid() is NULL
-- on every request and such policies would deny everything.
--
-- scripts/enable_rls.sql applies just this section to an already-existing database.
-- ==========================================================================================
alter table public.users            enable row level security;
alter table public.wardrobe_history enable row level security;
alter table public.product_ratings  enable row level security;


-- ==========================================================================================
-- VERIFY
-- Expect rowsecurity = true and zero policies on all three tables.
-- ==========================================================================================
select tablename, rowsecurity
from pg_tables
where schemaname = 'public'
  and tablename in ('users', 'wardrobe_history', 'product_ratings');

select tablename, count(policyname) as policy_count
from pg_policies
where schemaname = 'public'
  and tablename in ('users', 'wardrobe_history', 'product_ratings')
group by tablename;
