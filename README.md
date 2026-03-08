# FASHR V2 — AI-Powered Personal Stylist

> Eliminate outfit anxiety. Get instant, constructive feedback on what you're wearing and discover the perfect completer piece.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js + Tailwind CSS |
| **Animation** | Framer Motion + GSAP |
| **AI Core** | Python / FastAPI + LangGraph |
| **API Gateway** | Node.js (Express/Fastify) |
| **Core LLM** | NVIDIA NIM Qwen 3.5 |
| **Vector DB** | Pinecone |
| **Relational DB** | Supabase (Postgres) |
| **Auth** | Clerk / NextAuth.js |
| **CI/CD** | GitHub Actions → Vercel + Railway |

## Project Structure

```
FashAr/
├── frontend/          # Next.js app (App Router)
│   ├── app/           # Pages & layouts
│   ├── components/    # React components
│   ├── lib/           # Client utilities
│   └── public/        # Static assets
├── gateway/           # Node.js API gateway
│   └── src/
├── ai-core/           # Python FastAPI + LangGraph
│   ├── app/
│   │   ├── nodes/     # LangGraph nodes (scan, critique, retrieve, respond)
│   │   ├── prompts/   # Qwen prompt templates
│   │   ├── schemas/   # Pydantic models
│   │   └── services/  # Pinecone, weather, link-validation
│   └── tests/
├── scripts/           # Data seeding, cron jobs
├── .env               # API keys (never commit)
└── .gitignore
```

## Getting Started

### Prerequisites

- Node.js 20+
- Python 3.12 (conda venv at `.venv/`)
- API keys for: NVIDIA NIM, Pinecone, Supabase, Clerk, OpenWeatherMap

### Setup

```bash
# 1. Clone the repo
git clone <repo-url> && cd FashAr

# 2. Activate the Python venv
conda activate .venv

# 3. Fill in your API keys
# Edit .env with your actual keys

# 4. Install frontend dependencies (Phase 1+)
cd frontend && npm install

# 5. Install AI core dependencies (Phase 3+)
cd ai-core && pip install -r requirements.txt

# 6. Start the dev servers
# Frontend:  cd frontend && npm run dev
# Gateway:   cd gateway && npm run dev
# AI Core:   cd ai-core && uvicorn app.main:app --reload
```


