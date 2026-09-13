# FashAr —Your AI-Powered Personal Stylist

![FashAr Banner](https://img.shields.io/badge/Status-V2.0_Out_Now-indigo?style=for-the-badge) ![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

**Ditch outfit anxiety. Dress with Aura.**

FashAr is a next-generation, AI-driven personal styling application that provides immediate, objective feedback on your daily outfits. By uploading a simple mirror selfie, FashAr's state-of-the-art multimodal vision model analyzes your silhouette, color palette, and proportions in seconds to discover the exact missing piece needed to complete your look.

https://fash-ar-v2.vercel.app/

---

## ✨ Core Features

- 📸 **Instant Expert Critique**
  Upload an outfit photo, and our AI vision model (NVIDIA NIM Qwen-VL) evaluates it based on color cohesion, occasion appropriateness, and silhouette fit.

- 🔍 **Find the Gap**
  Missing a jacket? Need better footwear? FashAr identifies exactly what is holding your outfit back from a perfect 100 style score.

- 🛍️ **Smart Completers (RAG)**
  Using a Vector Database (Pinecone), FashAr searches your personal virtual closet (or a defined catalog) to recommend real, purchasable items that perfectly fill the identified style gap.

- 🌤️ **Context-Aware Styling**
  Integrates real-time local weather data (OpenWeatherMap) and intelligent persona tracking to ensure recommendations are actually wearable today.

- 🌗 **Premium UI & Dark Mode**
  A sleek, glassmorphism-inspired interface built with Next.js 15, Tailwind CSS 4.0, and dynamic animations, featuring a seamless, automatic dark mode.

---

## 🛠️ Tech Stack

**Frontend (Web App)**
- **Framework:** Next.js 15 (App Router), React 19
- **Styling:** Tailwind CSS 4.0 (Custom class-based Dark Mode)
- **Authentication:** Clerk
- **UI Components:** Sonner (Toast notifications), Lucide React (Icons)
- **Deployment:** Vercel (Planned)

**Backend (AI Engine & API)**
- **Framework:** Python, FastAPI, Uvicorn
- **AI/LLM Routing:** LangGraph (Stateful analysis workflow)
- **Vision Model:** NVIDIA NIM API (Qwen 3.5 VL 72b)
- **Databases:** 
  - Supabase (PostgreSQL) for user data & outfit history
  - Pinecone for Vector Embeddings (RAG closet search)
- **Deployment:** Render / Railway 

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

### Securing the database

Once the app runs, apply [`scripts/enable_rls.sql`](scripts/enable_rls.sql) in the Supabase
SQL editor. It enables Row-Level Security with no policies, which locks the public anon key
out of `wardrobe_history` and `product_ratings` while the service-role key used by the API
routes continues to work. Rotate the anon key afterwards.

Run the frontend development server:
```bash
npm run dev
```

Visit `http://localhost:3000` in your browser.

---

## 📸 Screenshots

*(Add screenshots of your application here once deployed! Consider adding the Landing Page, the Scanner interface, and the Results Dashboard)*

---

## 📄 License
This project is licensed under the MIT License.
