# FashAr — Project Status

**Last updated:** 2026-09-14

A working snapshot of where this project actually stands: what it does, what is currently
broken, what has been fixed, and what is left. Written to be picked up cold after a break.

> **Read this first:** the application does not run end-to-end right now. Two external
> services are down, and neither is a code problem. See [Current Status](#2-current-status).

---

## 1. What FashAr Is

Upload a mirror selfie (or describe an outfit in text), get an objective style critique plus
product recommendations that fill the identified gap.

### Architecture

```
Browser (Next.js 16, React 19)
   |
   |  multipart/form-data
   v
/api/analyze  (Next.js route, Vercel)       <-- verifies Clerk session, adds gateway secret
   |
   |  HTTP + X-Gateway-Secret + X-User-Id
   v
FastAPI "AI Core" (Render)
   |
   +-- LangGraph:  scan  ->  critique  ->  retrieve
   |                |           |             |
   |                |           |             +-- Pinecone (product vector search)
   |                |           +-- NVIDIA NIM (reasoning model, scores + gap)
   |                +-- NVIDIA NIM (vision model, garment + colour extraction)
   |
   +-- OpenWeatherMap (suppress/boost recommendations by weather)

Supabase (Postgres)  <-- history + ratings, written only by Next.js routes
Clerk                <-- auth
```

### Repository layout

| Path | Contents |
| --- | --- |
| `ai-core/app/graph.py` | LangGraph wiring: `START -> scan -> critique -> retrieve -> END` |
| `ai-core/app/nodes/` | The three pipeline nodes |
| `ai-core/app/services/` | Pinecone and OpenWeatherMap clients |
| `ai-core/app/schemas/` | Pydantic models (`models.py`) and graph state (`state.py`) |
| `ai-core/app/deps.py` | Gateway auth + rate limiting **(new)** |
| `frontend/app/api/` | Route handlers: analyze, history, rate |
| `frontend/components/ui/` | Scanner, Results, History, ImageUploadZone |
| `scripts/seed_products.py` | Seeds ~47 products into Pinecone |
| `scripts/enable_rls.sql` | Locks the public anon key out of Supabase **(new)** |
| `scripts/schema.sql` | Canonical schema — reconstructed from code usage, see [3.5](#35-tier-3--4-data-layer-and-failure-visibility) |
| `frontend/app/api/profile/` | Style profile read/write, service-role **(new)** |

---

## 2. Current Status

Verified 2026-09-14. Re-check with the commands in each section.

### NVIDIA NIM — key authenticates, inference forbidden

The API key can list models but cannot run anything:

```
GET  /v1/models            -> 200, 82 models returned
POST /v1/chat/completions  -> 403 {"detail":"Authorization failed"}
POST /v1/embeddings        -> 403 {"detail":"Authorization failed"}
```

Every model tested returns 403 on inference, including models that *are* in the live
catalog. A key that authenticates for listing but fails every inference call points to
exhausted credits or a revoked entitlement — not a code defect.

**Separately, the model IDs in the code are dead.** A large batch of NVIDIA hosted models
reached end-of-life on **2026-08-25**:

| Model ID                             | Used by                      | Status       |
| ------------------------------------ | ---------------------------- | ------------ |
| `meta/llama-3.2-90b-vision-instruct` | `nodes/scan.py` (image path) | 403          |
| `meta/llama-3.1-70b-instruct`        | `nodes/scan.py` (text path)  | **410 Gone** |
| `meta/llama-3.1-405b-instruct`       | `nodes/critique.py`          | 404          |

Both problems must be fixed: a new key alone will not help while the IDs point at retired
models.

> **Trap:** `ChatNVIDIA.get_available_models()` reads a static table compiled into
> `langchain-nvidia-ai-endpoints`. It cheerfully lists all three dead models. Only
> `GET https://integrate.api.nvidia.com/v1/models` reflects reality.

### Supabase — project not resolving

`rxwhuubdyygwhughkunu.supabase.co` fails DNS resolution, while `github.com` and
`api.nvidia.com` resolve from the same shell. That is a paused or deleted free-tier project
(Supabase pauses inactive free projects and their hostnames stop resolving).

History and ratings are therefore non-functional in production.

### Pinecone — healthy

The only fully working external service, and now the source of embeddings too.

```
index:   fashr-products-v2      <- live, integrated inference
model:   llama-text-embed-v2    <- Pinecone-hosted, 1024 dims, 2048-token window
dim:     1024, metric cosine
vectors: 47
SDK:     pinecone 7.3.0

index:   fashr-products         <- OLD, MD5 pseudo-embeddings. Kept for rollback only.
```

The old index is deliberately left in place so the change is reversible. Delete it once
`fashr-products-v2` has been exercised in production.

### Configuration

`frontend/.env.local` holds the real credentials and is the file the Python backend also
reads in local development (see `ai-core/app/config.py`).

The repository-root `.env` is an **abandoned template — every value in it is a
placeholder.** It is a leftover from an earlier gateway-based architecture (note its
`GATEWAY_PORT` / `AI_CORE_URL` keys and the empty `gateway/src/`). Do not copy values from
it. It should be deleted.

**Missing and required** (added by the Tier 1 work, not yet configured anywhere):

- `SUPABASE_SERVICE_ROLE_KEY` — from the Supabase dashboard, Settings → API → `service_role`
- `GATEWAY_SECRET` — generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`

Both are needed in `frontend/.env.local`, in Vercel, and (for `GATEWAY_SECRET`) in Render.
Until `GATEWAY_SECRET` is set, `/analyze` returns 500 — that is the intended fail-closed
behaviour, not a bug.

---

## 3. Changes Already Made

Shipped in commits `b9df338` and `60517f0`, pushed to `origin/main`.

These were **unit-tested but never integration-tested**, because the external services were
already down when they were written. The logic is verified; the wiring is not.

### 3.1 Supabase: service-role key + RLS lockdown

**Problem.** All three API routes built their Supabase client from
`NEXT_PUBLIC_SUPABASE_ANON_KEY`. The `NEXT_PUBLIC_` prefix ships that key to every browser.
Because the routes worked, RLS had to be disabled — meaning anyone holding that public key
could read, insert and delete **every user's** rows straight against the Supabase REST API,
bypassing the routes and their `user_id` filters entirely.

**Fix.** New `frontend/lib/supabase-admin.ts` exposes `getSupabaseAdmin()`, a lazily
constructed service-role client. All three routes now use it. Built lazily on purpose, so a
missing variable fails one request with a clear message instead of breaking the Vercel build.

`scripts/enable_rls.sql` enables RLS on `wardrobe_history` and `product_ratings` with **no
policies**. Service-role bypasses RLS, so the routes keep working while the anon key loses
all access.

**Consequence to remember:** there is now no database-level safety net. Authorization lives
entirely in the route handlers — verify the Clerk session, then filter by that user's id on
every single query.

### 3.2 AI Core: gateway authentication, CORS removed

**Problem.** `/analyze` was unauthenticated on a public Render URL with
`allow_origins=["*"]`. Anyone who found the hostname could drain the NVIDIA and
OpenWeather quotas. (`allow_origins=["*"]` together with `allow_credentials=True` is also
invalid per the CORS spec and rejected by browsers.)

**Fix.** New `ai-core/app/deps.py`:

- `verify_gateway` — constant-time comparison of the `X-Gateway-Secret` header. Fails
  **closed**: an unset `GATEWAY_SECRET` returns 500, never an open door.
- The Next.js route sends that secret plus `X-User-Id` from the verified Clerk session.

The CORS middleware was **deleted outright**. Nothing in a browser calls this service — the
Next.js route proxies every request server-side, and server-to-server calls are not subject
to CORS. Re-adding it would only weaken the gateway check.

### 3.3 Rate limiting and timeouts

**Rate limit.** Per-user sliding window, default 20 analyses/hour, in `deps.py`. It lives in
FastAPI rather than the Next.js route deliberately: Render runs one long-lived process where
an in-process counter actually holds, whereas Vercel would reset it on every cold start.

**Timeouts.** `ChatNVIDIA` has **no `timeout` parameter**, and because its `model_config`
sets `extra="ignore"`, passing `timeout=45` is *silently dropped* rather than raising. The
nodes therefore use `asyncio.wait_for`; the library's async path runs on `aiohttp`, so
cancellation reaches the in-flight request. Layers nest, tightest first:

```
LLM_TIMEOUT (40s per call) < ANALYSIS_TIMEOUT (55s whole graph)
  < gateway fetch abort (58s) < Vercel maxDuration (60s)
```

**One related fix pulled forward.** `scan.py` previously swallowed every exception into an
empty `ScanResult`, which would have turned a timeout into "no garments detected" and handed
the user a confident score for a call that never completed. `TimeoutError` now propagates to
a 504.

### 3.4 Tier 2: the RAG now actually retrieves

**Problem.** Both `pinecone_service.py` and `seed_products.py` built "embeddings" by
expanding a 16-byte MD5 digest to 1024 floats. Measured: 8 distinct values tiled 128 times,
and a one-character input change dropped cosine similarity to 0.19. Ranking was noise — the
only real signal was the `gap_type` metadata filter.

**Fix.** New index `fashr-products-v2` created with `create_index_for_model`, embedding
model `llama-text-embed-v2` attached. The API surface changed with it:

| Before | After |
| --- | --- |
| `pc.create_index(dimension=1024)` | `pc.create_index_for_model(embed={...})` |
| `index.upsert(vectors=[{values}])` | `index.upsert_records(namespace, records)` |
| `index.query(vector=[...])` | `index.search(query={"inputs": {"text": ...}})` |

Response shape is `resp.to_dict()["result"]["hits"]`, each hit carrying `_id`, `_score` and
`fields`. The response object is a `SearchRecordsResponse`, not a dict — `.keys()` fails on it.

**Query quality (item 5).** `CritiqueResult` gained a `gap_query` field: the critic now
describes the missing piece as a product listing would ("structured navy wool blazer with
natural shoulder") instead of the old filter-speak ("Fashion item for structure gap").
Catalog text is embedded in the same register, and `gap_type` is deliberately excluded from
the embedded text since it is applied as a hard filter. `retrieve.py` generates a prose
fallback when `gap_query` is absent or the weather rules swapped the gap out.

The critic prompt previously instructed the model to output `'contrast'` or "a fundamental
swap", neither of which the `gap_type` Literal accepts — the resulting validation error
discarded the entire critique. That is fixed here rather than in Tier 4, because it would
have taken `gap_query` down with it. The prompt now enumerates all six accepted values.

**Filtering (item 6).** `body_type` and `size_range` moved into the Pinecone query filter
(`$in` matches on list overlap), the candidate pool widened from 5 to 20, and
`retrieval_weight` reranks down to 3. Added graceful relaxation: if personal filters return
nothing, it retries on gap + gender rather than showing an empty panel.

**Item 8.** `retrieve_products` is now `async` and calls Pinecone via `asyncio.to_thread`,
so the blocking SDK no longer stalls the event loop. The suppression post-filter no longer
discards products with an empty `gap_type` list (`all([])` is `True`).

**Latent bug found and fixed along the way.** `pinecone_service.py` and `weather_service.py`
both called `load_dotenv` with three `dirname` hops, which from `app/services/` resolves to
`ai-core/frontend/.env.local` — a path that does not exist. They appeared to work only
because `main.py` imports `app.config` first and that populates `os.environ` as a side
effect. Imported standalone, both had no key at all. Both now defer to `app.config`.

### 3.5 Tier 3 + 4: data layer and failure visibility

**Failures now carry a reason (item 13).** `AgentState` gained an `error` channel. `scan.py`
still degrades to an empty result so the critic can respond to the stated occasion, but it
records why; `critique.py` no longer returns a bare `{}`. `main.py` surfaces whichever
reason a node recorded as a **502** rather than a generic 500, and logs when a run
completed with a degraded step. Previously every backend failure looked identical from the
outside, which is what made deploy debugging painful.

**`schema.sql` rewritten (item 9).** It now describes `users`, `wardrobe_history` and
`product_ratings` — the tables the code actually uses — with the unique constraint that
`POST /api/rate`'s `ON CONFLICT` depends on, an index matching the history query, and
`updated_at` triggers. Two judgement calls worth knowing:

- **No foreign keys on `user_id`.** An FK to `users` would make saving history fail for
  anyone without a profile row, turning a profile gap into silent data loss. Clerk is the
  identity source of truth. Add FKs only once every signed-in user is guaranteed a profile.
- **Ratings are not anonymous, and the file now says so.** The superseded schema claimed
  "completely anonymous" while the code stored `user_id` (it must, for the per-user upsert).
  The code's behaviour is recorded as the truth; making them genuinely anonymous is a
  deliberate change, not a cleanup.

**Profile moved server-side (item 10).** New `/api/profile` with GET and POST, using the
service-role client and an **upsert**. The browser no longer talks to Supabase directly —
that path needed a Clerk `supabase` JWT template plus `auth.uid()` RLS policies, neither of
which applies now. Onboarding prefills from the existing profile instead of presenting an
empty form to returning users. `lib/supabase.ts` is deleted as orphaned.

This also fixes the dead end where every returning sign-in hit a duplicate-key error: both
sign-in and sign-up redirect to `/onboarding`, and the old code did a plain `.insert()` on
a TEXT primary key.

**Profile wired into retrieval (item 7).** The analyze route looks the profile up and sets
`gender`, `body_type` and `sizes` on the forwarded FormData. Deliberately server-side: the
client cannot spoof its own sizing, and `Scanner.tsx` need not know the fields exist. A
missing profile or unreachable Supabase logs a warning and proceeds unfiltered.

**Occasion and persona persisted (item 11).** `Scanner` passes an `AnalysisContext` to
`MainApp`, which merges it into the history POST. Both columns were previously always null
because the analysis response never carried those fields.

### 3.6 Verified behaviour

Tier 1 — gateway, rate limiting, timeouts:

```
health, no auth        -> 200      analyze, no secret    -> 401
analyze, wrong secret  -> 401      analyze, near-miss    -> 401
analyze, good secret   -> 422      (auth passed, body rejected, no NIM call)

rate limit, cap 3      -> [422, 422, 429, 429, 429]
Retry-After            -> 3600     different user -> 422 (per-user buckets)

GATEWAY_SECRET unset   -> 500      (fail-closed)
hung graph, 1s deadline-> 504
```

Tier 2 — retrieval, against the live index:

```
"structured navy wool blazer with natural shoulder"
   0.651 Italian Wool Unstructured Blazer   0.440 Relaxed Corduroy Blazer
"soft chunky knit to add tactile warmth"
   0.342 Mohair Blend Oversized Sweater     0.303 Cashmere V-Neck Sweater

gender=womens, gap=footwear -> mules, ankle boots, unisex sneakers
                               (men's Chelsea/desert boots correctly excluded)
over-constrained filters    -> relaxes to gap+gender, returns 3 (was 0)
score >= 90                 -> retrieval skipped
weather suppression         -> structure swapped to boosted footwear
empty gap_type product      -> survives post-filter (was silently dropped)
missing gap_query           -> prose fallback, still returns 3
```

Tier 3 + 4 — failure visibility and profile filtering:

```
critique failure        -> {"error": "Critique step failed (Exception): ..."}  (was {})
that reason over HTTP   -> 502 with the real reason  (was a generic 500)
sizes forwarded         -> gender=womens body_type=['petite'] sizes=['S','M']
malformed profile field -> 200, treated as empty  (does not fail the analysis)

size filter narrows results, against the live index:
   unfiltered  -> Cropped Double-Breasted Blazer, Tailored Trench, Oversized Linen Shacket
   XS + petite -> Cropped Double-Breasted Blazer
```

`tsc --noEmit` passes clean. Tier 1 gate tests re-run green after every later change.

---

## 4. Decisions Made

**Embeddings will come from Pinecone integrated inference**, not NVIDIA.

Pinecone hosts the embedding model and embeds text server-side at both upsert and query
time, so embeddings stop depending on NVIDIA entirely — useful given how volatile that
catalog has proven. Verified available on this account:

| Model | Dims | Max sequence |
| --- | --- | --- |
| `llama-text-embed-v2` | 1024 | 2048 |
| `multilingual-e5-large` | 1024 | 507 |

`llama-text-embed-v2` is the pick: 1024 dims matches the current index, and the 2048-token
window comfortably fits a product description.

**This still requires recreating the index.** The embedding model must be attached at
creation via `create_index_for_model`; it cannot be bolted onto the existing plain index.
Recreation is cheap here — all 47 vectors come from `scripts/seed_products.py`.

The API surface changes with it (confirmed present in Pinecone SDK 7.3.0):

| Today | After |
| --- | --- |
| `pc.create_index(dimension=1024, ...)` | `pc.create_index_for_model(embed={...})` |
| `index.upsert(vectors=[{values: [...]}])` | `index.upsert_records(namespace, records)` |
| `index.query(vector=[...], filter=...)` | `index.search(query={"inputs": {"text": ...}})` |

An NVIDIA key is still required for `scan` and `critique`.

---

## 5. Remaining Work

Item numbers are stable references used throughout this document.

### Blocked on external services

- [ ] **Restore Supabase.** Un-pause the project, or create a new one and apply
      `scripts/schema.sql`, then update `NEXT_PUBLIC_SUPABASE_URL`. No longer blocks any
      code item — history, ratings and the profile are all written and degrade gracefully
      while it is down — but nothing touching the database is integration-tested until it
      returns.
- [ ] **Obtain a working NVIDIA key.** Blocks all end-to-end testing of scan and critique.
- [ ] **Repoint dead model IDs** in `scan.py` and `critique.py` to models that exist. Verify
      against `GET /v1/models`, never against `get_available_models()`.

### Tier 2 — Make the RAG an actual RAG

**Complete.** See [3.4](#34-tier-2-the-rag-now-actually-retrieves) and
[3.6](#35-tier-3--4-data-layer-and-failure-visibility).

- [x] **4. Replace the MD5 pseudo-embeddings.** Pinecone integrated inference.
- [x] **5. Give the retriever something worth embedding.** `gap_query` on `CritiqueResult`.
- [x] **6. Filter server-side, rerank over more candidates.** Plus filter relaxation.
- [x] **7. Pass the user profile through.** The analyze route now reads the profile
      server-side and forwards gender, body type and sizes. Degrades to unfiltered
      recommendations if the profile is missing or Supabase is unreachable.
- [x] **8. Weather post-filter bug + blocking node.**

### Tier 3 — Data layer

**Complete**, though items 9 and 10 are only *integration*-tested once Supabase returns.

- [x] **9. Rewrite `scripts/schema.sql`.** Now describes the tables the code actually uses.
      Reconstructed from code usage rather than dumped, since the project was unreachable —
      diff against `supabase db dump --schema public` when it is back.
- [x] **10. Make the profile readable; fix the onboarding insert.** New `/api/profile`
      route (GET + POST, service-role, upsert). Onboarding posts to it instead of writing
      to Supabase from the browser, and prefills from the existing profile.
- [x] **11. Persist occasion and persona.** Scanner now passes them to `MainApp`, which
      merges them into the history POST.

### Tier 4 — Pipeline correctness

**Complete.**

- [x] **12. Align the critic prompt with the schema.** Done during Tier 2 — a validation
      failure here discards the whole critique, including `gap_query`.
- [x] **13. Stop swallowing pipeline failures.** `AgentState` gained an `error` channel;
      nodes record why they failed and `main.py` returns it as a 502 instead of a generic 500.

### Tier 5 — Configuration and hygiene

- [ ] **14. Unify environment variables.** Three files independently call
      `load_dotenv(frontend/.env.local)` by walking up to a sibling directory that does not
      exist on Render. It works in production only because the platform injects real env
      vars — local dev is the broken case. Consolidate into `config.py`, reconcile the
      names, make the Pinecone index name an env var, and fix the port drift (README says
      8000, the analyze route falls back to 8001).

- [ ] **15. Pin `requirements.txt`.** No version pins at all, and it is missing `httpx`
      (imported directly by `weather_service`, currently resolving only transitively through
      `langsmith`) and `supabase` (needed by `update_product_weights.py`). Commit `0c114e9`
      was already a dependency-conflict deploy fix.

- [ ] **16. Delete dead weight.** `frontend/src/app/` is untouched create-next-app
      boilerplate (root `app/` wins, so it is inert). Six `ai-core/test_*.py` scratch scripts
      with no assertions sit at the package root while `ai-core/tests/` is empty. Plus the
      empty `gateway/src/` and the placeholder root `.env`.

- [ ] **17. Schedule the feedback loop.** `update_product_weights.py` is written but never
      runs, so `retrieval_weight` sits at its seeded value and collected star ratings feed
      nothing. Once item 9 settles the table name, wire it to a scheduled job.

### UI — deferred by choice

Tracked but explicitly out of scope for now.

- [ ] Loading overlay in `Scanner.tsx` is `absolute inset-0` with no positioned ancestor, so
      it anchors to the viewport rather than the card.
- [ ] `ImageUploadZone` leaks object URLs — picking a second photo replaces `previewUrl`
      without revoking the previous one.
- [ ] Dark mode is half-applied: `ImageUploadZone`, onboarding, sign-in and sign-up have no
      `dark:` variants.
- [ ] Marketing copy claims a "122B parameter" model (`layout.tsx` metadata, `Scanner.tsx`)
      and "100B+" (`page.tsx`); the README says Qwen 3.5 VL 72b; the health check says Llama
      3.2 Vision; the code used a 90B model. None of these agree, and the 122B figure is in
      public OpenGraph metadata.

---

## 6. Suggested Order

1. **Restore service.** New NVIDIA key, un-pause Supabase, repoint the dead model IDs. Until
   this is done nothing can be tested end-to-end.
2. **Configure Tier 1.** Add `GATEWAY_SECRET` and `SUPABASE_SERVICE_ROLE_KEY` everywhere,
   deploy both sides, *then* run `scripts/enable_rls.sql` (running it before the deploy
   breaks history), then rotate the anon key.
3. **Items 4 + 5 + 6 together.** These are really one change split across three files.
   Fixing 4 alone will *look* like it fixed retrieval because results start varying
   sensibly, but without 5 it is still matching filter-speak against product prose.
4. **Items 12 and 13**, so failures stop being invisible.
5. **Items 9 → 10 → 7** as one chain — the profile plumbing only pays off once the schema is
   truthful and the profile is readable.
6. **Tier 5**, then the UI backlog.
