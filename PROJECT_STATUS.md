# FashAr — Project Status

**Last updated:** 2026-09-14

A working snapshot of where this project actually stands: what it does, what is currently
broken, what has been fixed, and what is left. Written to be picked up cold after a break.

> **Status: the text-description path works end to end.** Verified through the UI on
> 2026-09-14 — scan → critique → retrieve → recommendations → saved history. The image
> upload path is wired but has not been exercised with a real photo. One security task
> remains outstanding, see [Current Status](#2-current-status).

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

### NVIDIA NIM — working

A replacement key was added on 2026-09-14 and runs inference. The previous key could list
models but returned 403 on every completion — the signature of exhausted credits, not a
code defect.

**The original model IDs were also all dead.** A batch of NVIDIA hosted models reached
end-of-life on 2026-08-25. Current defaults, verified live:

| Setting | Model | Latency |
| --- | --- | --- |
| `VISION_MODEL` | `meta/llama-3.2-11b-vision-instruct` | 0.3s |
| `TEXT_SCAN_MODEL` | `nvidia/nemotron-3-super-120b-a12b` | 0.6s |
| `CRITIC_MODEL` | `nvidia/nemotron-3-super-120b-a12b` | 0.6s |

The old `llama-3.2-90b-vision` is worth noting: it does not 404, it simply **never
responds** — over 120s in testing, against a 40s timeout. It fails as a hang, not an error.

Run `python ai-core/scripts/check_models.py` after any key or model change. It separates
"key has no entitlement" from "model ID retired", which look identical from inside the app
but need completely different fixes.

> **Two stale-table traps.** `ChatNVIDIA.get_available_models()` reads a static table
> compiled into `langchain-nvidia-ai-endpoints` and lists retired models — only
> `GET https://integrate.api.nvidia.com/v1/models` is authoritative. The same table causes
> startup warnings that a model's "type is unknown" or that it is "not known to support
> tools"; both are false negatives, verified live. See the note in `app/config.py`.

**Expect occasional 503s.** The hosted free tier returns "Service temporarily overloaded"
regularly under load. `app/nim.py` retries these within a shared time budget; permanent
failures (404/410/403) are not retried.

### Supabase — back, but RLS is still not applied

The project resolves again and the REST API answers, so the earlier DNS failure was a
pause, not a deletion. The service-role key is configured locally.

🔴 **`scripts/enable_rls.sql` has never been run.** Verified 2026-09-14: the public anon key
still reads rows out of `wardrobe_history`, including their Clerk `user_id`. That key ships
to every browser. Until the script is applied, anyone who views the deployed site's source
can read, insert or delete every user's history directly against the REST API, bypassing the
routes entirely.

Order matters: deploy `SUPABASE_SERVICE_ROLE_KEY` to Vercel **first**, then run the script,
then rotate the anon key. Running it before the deploy breaks history saves in production.

Two dead tables, `analyses` and `ratings`, survive from the original schema. Nothing reads
them; drop them once confirmed.

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

### 3.6 Tier 5: configuration, tests and automation

**One place reads the environment (item 14).** `app/config.py` loads it once and exposes
typed constants; `deps.py`, both services and both LLM nodes now import from it instead of
calling `os.getenv` themselves. Resolution order is real env vars → `ai-core/.env` →
`frontend/.env.local`, so production keeps working while local setups do not have to move.
Each setting accepts its historical aliases (`NVIDIA_NVIM_KEY` / `NVIDIA_NIM_API_KEY` /
`NVIDIA_API_KEY`, and similar), which avoids a rename across every deployment target at once.

Model IDs moved into config as `VISION_MODEL`, `TEXT_SCAN_MODEL` and `CRITIC_MODEL`.
Given NVIDIA retired three of this project's models on one day, repointing them should not
require a code change.

The service now prints its configuration at startup and names anything missing along with
what it breaks. `GET /` reports the same as `{"status": "degraded", "missing_settings":
[...]}` — never values, since it is public — and deliberately stays 200 so the platform
does not restart-loop a container whose only problem is an absent key.

**Dependencies pinned (item 15).** `requirements.txt` now pins every direct dependency,
adds `httpx` (imported directly by `weather_service` but previously resolving only through
`langsmith`, one upstream change from breaking), and a new `requirements-dev.txt` carries
`pytest`, `pytest-asyncio` and `supabase` so the deployed image does not ship test tooling.

**A real test suite (item 16).** The seven `test_*.py` scratch scripts — no assertions,
live API calls — are gone, replaced by **35 tests** in `ai-core/tests/`:

- `test_gateway.py` — auth, fail-closed behaviour, rate limiting, per-user isolation
- `test_pipeline.py` — profile parsing, malformed input, error reporting, timeouts, and the
  retrieval node's logic with Pinecone stubbed
- `test_retrieval_live.py` — real retrieval quality, marked `integration`

`pytest.ini` excludes integration tests by default, so the standard run needs no
credentials and no network. Run them with `pytest -m integration`. They assert on relative
ordering rather than absolute scores, so a model update does not fail the build for reasons
unrelated to this code.

Also deleted: `frontend/src/` (create-next-app boilerplate the root `app/` shadowed),
`gateway/` (empty), and `lib/supabase.ts` (orphaned by the profile route).

**Automation (item 17).** `.github/workflows/update-product-weights.yml` runs the ratings
sync daily; `ci.yml` runs the test suite, typecheck and lint on every push and PR.

Two bugs surfaced while wiring this up:

- `update_product_weights.py` authenticated with the **anon key**, which RLS now denies. It
  would have reported "no ratings found" forever rather than failing — a silent no-op.
  Switched to the service-role key.
- Its Pinecone update omitted the **namespace**, so it targeted a different namespace than
  the one the records live in and would have updated nothing. Verified against the live
  index that `set_metadata` works and leaves `chunk_text` untouched, so no re-embedding.

**Lint debt cleared as a precondition.** CI runs `npm run lint`, which was failing with 22
pre-existing errors — mostly `catch (err: any)`. A workflow that is red from day one trains
everyone to ignore CI, so these are fixed: new `lib/errors.ts` provides `errorMessage` and
`isTimeoutError`, catch bindings are `unknown`, and `HistoryRecord` now uses the real types
from `lib/types/ai.ts` instead of seven `any` fields. Down to one benign warning about an
`<img>` on a blob preview, where `next/image` would not help.

### 3.7 Verified behaviour

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

Live end-to-end, text path, through the real pipeline:

```
"navy slim jeans, white cotton tee, white canvas sneakers"  (Smart Casual, Minimalist)
   detected  3 garments + palette  #0A1F44 Dark Navy / #FFFFFF White
   score     68, gap=footwear
   gap_query "tan suede desert boots with crepe sole"
   returned  Suede Desert Boots (Clarks) 0.667 · Chelsea Boots (RM Williams) 0.379

"black ribbed turtleneck, grey wool midi skirt, black ankle boots"  (Business, Old Money)
   score     74, gap=structure  — after two 503 retries recovered automatically
   returned  Cropped Double-Breasted Blazer (Zara) 0.433
```

The 0.667 match is the retrieval chain working as designed: the critic described the missing
piece as a product listing would, Pinecone embedded that phrase, and the closest catalog item
came back first.

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
- [ ] **Repoint dead model IDs.** Now a config change, not a code change — set
      `VISION_MODEL`, `TEXT_SCAN_MODEL` and `CRITIC_MODEL` (see `app/config.py`). Verify
      candidates against `GET /v1/models`, never against `get_available_models()`.

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

**Complete.** See [3.7](#36-tier-5-configuration-tests-and-automation).

- [x] **14. Unify environment variables.** `app/config.py` is now the only module that
      loads the environment. Every setting is a typed constant with alias support.
- [x] **15. Pin `requirements.txt`.** All pinned; `httpx` added, `supabase` and test tooling
      split into `requirements-dev.txt`.
- [x] **16. Delete dead weight.** Removed `frontend/src/`, `gateway/`, seven scratch
      scripts and the orphaned `lib/supabase.ts` — and replaced the scratch scripts with a
      real 35-test suite.
- [x] **17. Schedule the feedback loop.** Daily GitHub Actions workflow, plus a fix for the
      auth bug that would have made it silently no-op.

**One leftover, deliberately not touched:** the repository-root `.env` is untracked, so it
is yours to delete locally. Every value in it is a placeholder and it misled this project
once already — recommend removing it.

### UI — deferred by choice

Tracked but explicitly out of scope for now.

- [ ] Loading overlay in `Scanner.tsx` is `absolute inset-0` with no positioned ancestor, so
      it anchors to the viewport rather than the card.
- [ ] `ImageUploadZone` leaks object URLs — picking a second photo replaces `previewUrl`
      without revoking the previous one.
- [ ] Dark mode is half-applied: `ImageUploadZone`, onboarding, sign-in and sign-up have no
      `dark:` variants.
- [ ] Marketing copy overstates the model. `layout.tsx` metadata and `Scanner.tsx` claim
      "122B parameter", `page.tsx` says "100B+". The vision model is actually **11B**, and
      the critic is a 120B MoE with ~12B active. The README and health check were corrected;
      these three were not, and the 122B figure sits in public OpenGraph metadata.

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
