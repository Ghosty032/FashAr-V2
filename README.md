# FashAr —Your AI-Powered Personal Stylist

![FashAr Banner](https://img.shields.io/badge/Status-V2.0_Out_Now-indigo?style=for-the-badge) ![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

**Ditch outfit anxiety. Dress with Aura.**

FashAr is a next-generation, AI-driven personal styling application that provides immediate, objective feedback on your daily outfits. By uploading a simple mirror selfie, FashAr's state-of-the-art multimodal vision model analyzes your silhouette, color palette, and proportions in seconds to discover the exact missing piece needed to complete your look.

https://fash-ar-v2.vercel.app/

> **Build status and known issues:** see [PROJECT_STATUS.md](PROJECT_STATUS.md). The AI
> pipeline is currently awaiting a working NVIDIA NIM key and refreshed model IDs.

---

## ✨ Core Features

- 📸 **Instant Expert Critique**
  Upload an outfit photo and a multimodal vision model extracts every garment — type, colour, fabric, fit — then a reasoning model grades it on colour cohesion, occasion appropriateness, silhouette and completeness.

- 🔍 **Find the Gap**
  Missing a jacket? Need better footwear? FashAr identifies the single element holding your outfit back from a perfect 100, as one of six gap types: `structure`, `footwear`, `texture`, `accessory`, `color` or `none`.

- 🛍️ **Smart Completers (RAG)**
  The critic describes the missing piece the way a product listing would — *"structured navy wool blazer with natural shoulder"* — and Pinecone embeds that phrase server-side to search the catalog, filtered by gap type, gender, body type and size, then reranked by community ratings.

- 🌤️ **Context-Aware Styling**
  Live local weather (OpenWeatherMap) suppresses or boosts gap types before retrieval, so you aren't recommended a wool coat at 30 °C.

- 🌗 **Premium UI & Dark Mode**
  A glassmorphism-inspired interface built with Next.js 16, Tailwind CSS 4, and dynamic animations, with class-based dark mode.

---

## 🧠 How the Pipeline Works

A single `/analyze` request runs a three-node LangGraph workflow:

```
scan      Vision model extracts garments + colour palette   -> ScanResult
   |
critique  Reasoning model scores the outfit, names the gap,
          and writes a product-style description of it      -> CritiqueResult
   |
retrieve  Pinecone embeds that description and searches the
          catalog, filtered and reranked                    -> RecommendedProduct[]
```

Retrieval is skipped entirely when the score is ≥ 90 or the gap is `none` — a finished
outfit gets no upsell.

---

## 🔍 Request Lifecycle — what runs, and where

One click of **Analyze My Outfit**, traced through every file it touches.

```
Browser                    Vercel (Node)                 Render (Python)
────────                   ─────────────                 ───────────────
Scanner.tsx
  handleSubmit()  ──POST──▶ app/api/analyze/route.ts
                              auth() ─────────────────▶ Clerk
                              profile lookup ─────────▶ Supabase
                              + X-Gateway-Secret
                                      │
                                      └──────POST──────▶ main.py  analyze_outfit()
                                                           deps.py  gate + rate limit
                                                           weather_service ──▶ OpenWeatherMap
                                                           graph.ainvoke()
                                                             ├─ scan.py ─────▶ NVIDIA NIM
                                                             ├─ critique.py ─▶ NVIDIA NIM
                                                             └─ retrieve.py ─▶ Pinecone
                                      ◀──── FinalAnalysis ────┘
MainApp.tsx ◀── JSON ────────┘
  └─POST /api/history ─────▶ Supabase
```

### 1. The browser builds the request
[`Scanner.tsx:53`](frontend/components/ui/Scanner.tsx#L53) — `handleSubmit()`

Validates input (text mode needs ≥ 6 words), then asks for geolocation at
[line 72](frontend/components/ui/Scanner.tsx#L72) with a 5s timeout. **Denial is not an
error** — it just proceeds without weather. Assembles `FormData` at
[lines 83-95](frontend/components/ui/Scanner.tsx#L83-L95): the image *or* text, occasion
tiers, persona, and coordinates if granted.

Note what it does **not** send: gender, body type, sizes. Those are attached server-side so
the browser cannot spoof them.

### 2. The gateway authenticates and enriches
[`app/api/analyze/route.ts:8`](frontend/app/api/analyze/route.ts#L8) — `POST`

- [L11](frontend/app/api/analyze/route.ts#L11) `auth()` — Clerk session, else 401.
- [L29-39](frontend/app/api/analyze/route.ts#L29-L39) Looks up the user's profile via
  `getSupabaseAdmin()` and sets `gender`, `body_type` and `sizes` onto the FormData. A
  missing profile or unreachable database logs a warning and continues **unfiltered** —
  never fatal.
- [L49](frontend/app/api/analyze/route.ts#L49) Fails closed if `GATEWAY_SECRET` is unset.
- [L60-70](frontend/app/api/analyze/route.ts#L60-L70) Forwards to the AI Core with
  `X-Gateway-Secret` and `X-User-Id`, aborting at 58s.

`Content-Type` is deliberately not set — `fetch` must generate the multipart boundary.

### 3. The AI Core admits the request
[`main.py:49`](ai-core/app/main.py#L49) — `analyze_outfit`

The route's `dependencies=[Depends(enforce_rate_limit)]` runs **before** the handler:
[`deps.py:41`](ai-core/app/deps.py#L41) `verify_gateway` does a constant-time secret
comparison, then [`deps.py:66`](ai-core/app/deps.py#L66) applies a per-user sliding window
(20/hour). The limiter lives here, not in Node, because Render runs one long-lived process
where an in-memory counter actually holds.

Then: image → base64 data URI ([L79](ai-core/app/main.py#L79)), occasion tiers joined,
`body_type`/`sizes` JSON-parsed tolerantly ([L89](ai-core/app/main.py#L89) — malformed
values degrade to `[]` rather than failing), and weather fetched at
[L106](ai-core/app/main.py#L106) only if coordinates arrived.

### 4. The graph runs
[`graph.py:15-23`](ai-core/app/graph.py#L15-L23) — `START → scan → critique → retrieve → END`

Invoked at [`main.py:125`](ai-core/app/main.py#L125) under a 55s ceiling. State flows
through `AgentState` (`schemas/state.py`), which also carries an `error` channel.

### 5. `scan` — what am I wearing?
[`nodes/scan.py:13`](ai-core/app/nodes/scan.py#L13) — `scan_outfit`

Picks `VISION_MODEL` for images, `TEXT_SCAN_MODEL` for text. Makes **one** call via
`ainvoke_with_retry`, then extracts JSON from the raw text with
[`json_utils.extract_json_object`](ai-core/app/json_utils.py) rather than chaining
`JsonOutputParser` — reasoning models narrate before answering, which the parser rejects
outright. Produces `ScanResult`.

On failure it returns an **empty** `ScanResult` plus an `error`, so the critic can still
respond to the stated occasion. A timeout is re-raised rather than swallowed.

### 6. `critique` — how good is it, and what's missing?
[`nodes/critique.py:12`](ai-core/app/nodes/critique.py#L12) — `critique_outfit`

Feeds the scan plus user context to `CRITIC_MODEL`. Returns `CritiqueResult`: four rubric
scores, an overall score, a narrative, a `gap_type` from six literals, and **`gap_query`** —
a product-style phrase like *"structured navy wool blazer with natural shoulder"*. That
field is the hinge between critique and retrieval.

### 7. `retrieve` — find the missing piece
[`nodes/retrieve.py:27`](ai-core/app/nodes/retrieve.py#L27) — `retrieve_products`

Short-circuits when `style_score ≥ 90` or `gap_type == "none"`. Applies weather rules: a
suppressed gap switches to a boosted one, or retrieval is skipped. Calls Pinecone through
`asyncio.to_thread` — the SDK is synchronous and would otherwise block the event loop.

### 8. Vector search
[`services/pinecone_service.py:101`](ai-core/app/services/pinecone_service.py#L101) — `query_products`

Pinecone embeds `gap_query` server-side (integrated inference — nothing here computes a
vector). [`_build_filter`](ai-core/app/services/pinecone_service.py#L43) pushes `gap_type`,
gender, body type and size into the query itself. Fetches 20 candidates, reranks by
`retrieval_weight` (derived from user star ratings), returns 3.

If personal filters match nothing it **relaxes** to gap + gender rather than showing an
empty panel.

### 9. Response assembled
Back in [`main.py:139-170`](ai-core/app/main.py#L139-L170). A recorded `error` becomes a
**502** carrying the real reason. A failed scan with zero detected garments is also 502 —
otherwise the critic's "1/100, no garments present" would reach the user as a real score.
Otherwise a `FinalAnalysis` is returned.

### 10. Render and persist
[`Scanner.tsx:98`](frontend/components/ui/Scanner.tsx#L98) receives the JSON and calls
`onAnalysisComplete(data, { occasion, persona })` — the context is passed separately
because the analysis response never carried it.

[`MainApp.tsx:16`](frontend/components/ui/MainApp.tsx#L16) switches to the results view
**immediately**, then saves to `/api/history` in the background. A failed save logs but does
not block the user from seeing their result. `Results.tsx` renders; each star click POSTs to
`/api/rate`, which eventually feeds `retrieval_weight` back into step 8 via the daily
workflow.

### Where it breaks, and what you'll see

| Symptom | Cause | Where |
| --- | --- | --- |
| `Server misconfigured` | `GATEWAY_SECRET` unset | [route.ts:50](frontend/app/api/analyze/route.ts#L50) |
| `401 Unauthorized` | secret mismatch between Node and Python | [deps.py:41](ai-core/app/deps.py#L41) |
| `429` | 20 analyses/hour exceeded | [deps.py:66](ai-core/app/deps.py#L66) |
| `502` + a real reason | a node recorded an error | [main.py:143](ai-core/app/main.py#L143) |
| `504` | graph exceeded 55s | [main.py:127](ai-core/app/main.py#L127) |
| Empty recommendations | score ≥ 90, gap `none`, or weather suppression | [retrieve.py:27](ai-core/app/nodes/retrieve.py#L27) |

---

## 🛠️ Tech Stack

**Frontend (Web App)**
- **Framework:** Next.js 16 (App Router), React 19
- **Styling:** Tailwind CSS 4 (class-based dark mode)
- **Authentication:** Clerk
- **UI Components:** Sonner (toasts), Lucide React (icons), react-dropzone
- **Deployment:** Vercel

**Backend (AI Engine & API)**
- **Framework:** Python 3.11, FastAPI, Uvicorn
- **Orchestration:** LangGraph — stateful `scan → critique → retrieve` workflow
- **Vision & reasoning:** NVIDIA NIM hosted models. The exact IDs live in
  `ai-core/app/nodes/` — treat the code as the source of truth, since NVIDIA retires
  hosted models regularly.
- **Embeddings:** Pinecone **integrated inference** (`llama-text-embed-v2`, 1024-dim).
  Pinecone hosts the model and embeds text server-side on both write and query, so no
  embedding API key is needed.
- **Databases:**
  - Supabase (PostgreSQL) — outfit history and product ratings
  - Pinecone — product catalog vector search
- **Deployment:** Render

### Security model

The AI Core sits on a public URL but accepts requests only from the Next.js route, which
verifies the Clerk session first and forwards a shared `X-Gateway-Secret`. It applies a
per-user rate limit and layered timeouts. Supabase tables have RLS enabled with no
policies, so the public anon key cannot reach them — the API routes use the service-role
key and filter by user id themselves.

---

## 🚀 Local Development Setup

### 1. Clone the repository
```bash
git clone https://github.com/Ghosty032/FashAr-V2.git
cd FashAr-V2
```

### 2. Backend Setup (AI Core)
Navigate to the backend folder and set up a Python virtual environment:
```bash
cd ai-core
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

In local development the AI Core reads **`frontend/.env.local`** (see `app/config.py`), so
there is no separate `ai-core/.env` to create — configure everything in the frontend file
described in step 3 below. In production, set the same variables in your Render/Railway
dashboard instead.

> Consolidating this into a single, conventionally-named env file is a known cleanup item.

Run the backend server:
```bash
uvicorn app.main:app --reload --port 8000
```

> If port 8000 is already taken (XAMPP/Apache claims it on many Windows setups), run on
> 8001 instead and set `NEXT_PUBLIC_API_URL` to match — that is the port the frontend
> falls back to by default.

### 3. Frontend Setup
Open a new terminal, navigate to the frontend folder, and install dependencies:
```bash
cd frontend
npm install
```

Create a `.env.local` file in the `frontend` directory. Note that the AI Core reads this
same file during local development, so it holds both frontend and backend keys:

```env
# --- Auth ---
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
CLERK_SECRET_KEY=your_clerk_secret_key

# --- Database ---
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
# Server-only. Bypasses RLS, so it must never gain a NEXT_PUBLIC_ prefix.
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# --- AI Core (read by the Python backend in local dev) ---
NVIDIA_NVIM_KEY=your_nvidia_api_key
PINECONE_KEY=your_pinecone_api_key
PINECONE_INDEX=fashr-products-v2
OPENWEATHER_KEY=your_openweathermap_api_key

# --- Gateway ---
NEXT_PUBLIC_API_URL=http://localhost:8000
# Shared secret proving a request to the AI Core came from the Next.js route.
# Must be byte-identical on both sides. Generate one with:
#   python -c "import secrets; print(secrets.token_urlsafe(32))"
GATEWAY_SECRET=your_generated_secret
```

Optional tuning (all have working defaults):

| Variable | Default | Purpose |
| --- | --- | --- |
| `RATE_LIMIT_REQUESTS` | `20` | Analyses allowed per user per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `3600` | Length of that window |
| `LLM_TIMEOUT_SECONDS` | `40` | Ceiling on a single NIM call |
| `ANALYSIS_TIMEOUT_SECONDS` | `55` | Ceiling on the whole LangGraph run |
| `PINECONE_NAMESPACE` | `__default__` | Namespace holding the product records |
| `VISION_MODEL` | see `app/config.py` | Model for the image scan path |
| `TEXT_SCAN_MODEL` | see `app/config.py` | Model for the text-only scan path |
| `CRITIC_MODEL` | see `app/config.py` | Model that scores the outfit |

Model IDs are configuration rather than code because NVIDIA retires hosted models
regularly. To check your key and the configured IDs in one step:

```bash
python ai-core/scripts/check_models.py
```

It separates the two failure modes, which look identical from inside the app but need
completely different fixes: a key with no inference entitlement (nothing you change in the
code will help) versus a model ID that has been retired (it suggests a working replacement
and prints the variable to set).

Never trust `ChatNVIDIA.get_available_models()` — it reads a static table baked into the
library and lists models that no longer exist.

The AI Core prints its configuration at startup and names anything missing. `GET /` reports
the same as `{"status": "degraded", "missing_settings": [...]}`.

Run the frontend development server:
```bash
npm run dev
```

Visit `http://localhost:3000` in your browser.

### 4. Seed the product catalog

Recommendations come from a Pinecone index, which starts empty. Seed it once:

```bash
python scripts/seed_products.py
```

This creates `fashr-products-v2` with the `llama-text-embed-v2` model attached and upserts
the catalog. Pinecone computes the embeddings server-side, so this needs only
`PINECONE_KEY`. Re-running is safe — ids are deterministic, so it overwrites in place.

### 5. Secure the database

Apply [`scripts/enable_rls.sql`](scripts/enable_rls.sql) in the Supabase SQL editor **after**
deploying, not before. It enables Row-Level Security with no policies, which locks the
public anon key out of `wardrobe_history` and `product_ratings` while the service-role key
used by the API routes continues to work. Rotate the anon key afterwards.

For a fresh database, apply [`scripts/schema.sql`](scripts/schema.sql) instead — it creates
all three tables and enables RLS in one pass.

---

## 🧪 Tests

```bash
cd ai-core
pip install -r requirements.txt -r requirements-dev.txt

pytest                  # unit tests — no network, no credentials
pytest -m integration   # live retrieval — needs PINECONE_KEY and a seeded index
```

Integration tests are excluded by default (see `pytest.ini`) so the standard run works on a
clean checkout. Both suites, plus the frontend typecheck and lint, run in CI on every push.

---

## 📸 Screenshots

*(Add screenshots of your application here once deployed! Consider adding the Landing Page, the Scanner interface, and the Results Dashboard)*

---

## 📄 License
This project is licensed under the MIT License.
