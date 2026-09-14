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
