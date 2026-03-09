# FashAr — AI-Powered Personal Stylist

![FashAr Banner](https://img.shields.io/badge/Status-V2.0_Out_Now-indigo?style=for-the-badge) ![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

**Ditch outfit anxiety. Dress with Aura.**

FashAr is a next-generation, AI-driven personal styling application that provides immediate, objective feedback on your daily outfits. By uploading a simple mirror selfie, FashAr's state-of-the-art multimodal vision model analyzes your silhouette, color palette, and proportions in seconds to discover the exact missing piece needed to complete your look.

[**Deployed Demo** (Coming Soon)](#)

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

Create a `.env` file in the `ai-core` directory:
```env
NVIDIA_API_KEY=your_nvidia_api_key
OPENWEATHER_API_KEY=your_openweathermap_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_service_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX=fashar-wardrobe
```

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

Create a `.env.local` file in the `frontend` directory:
```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
CLERK_SECRET_KEY=your_clerk_secret_key
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# Fast API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

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
