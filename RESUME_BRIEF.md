# FashAr V2 — Resume Project Brief

Here are a few variations of bullet points you can use for your resume, tailored to highlight different strengths (Full-Stack Engineering, AI Integration, or Product/UX). 

You can mix and match these directly into your resume's "Projects" or "Experience" section.

---

### Option 1: AI & Data Engineering Focus (Heavy Tech)
**FashAr — AI-Powered Personal Stylist** | *Next.js, Python, FastAPI, NVIDIA NIM, Pinecone, Supabase, LangGraph*
- Architected a multimodal AI styling engine using **Python**, **FastAPI**, and **LangGraph**, orchestrating a 72B parameter vision model (NVIDIA Qwen-VL) to analyze user selfies for color cohesion, fit, and occasion appropriateness in under 5 seconds.
- Implemented a Retrieval-Augmented Generation (RAG) pipeline leveraging **Pinecone Vector Database**, searching a live curated catalog to generate instantly shoppable, high-accuracy clothing recommendations to complete user outfits.
- Designed a continuous learning loop utilizing **Supabase PostgreSQL** and background Python chron-jobs that dynamically adjusted Pinecone retrieval weights based on a custom 5-star user rating system, directly improving recommendation relevancy.
- Integrated external APIs including **OpenWeatherMap** to ensure outfit recommendations were context-aware (e.g., suggesting waterproof layers natively during local rain logic).

### Option 2: Full-Stack & Frontend Polish Focus (UX/UI)
**FashAr — AI-Powered Personal Stylist** | *React, Next.js 15, Tailwind CSS 4.0, Clerk, FastAPI*
- Developed a high-performance, single-page web application using **Next.js 15** and **React 19**, featuring a sleek glassmorphism UI, complex CSS keyframe animations, and seamless dark mode support via Tailwind CSS 4.0.
- Engineered a robust, scalable microservices architecture by decoupling a React frontend from a **FastAPI** Python backend, managing secure cross-origin resource sharing (CORS) and asynchronous state transitions.
- Integrated **Clerk Authentication** to manage stateless user sessions, allowing personalized tracking of past wardrobe analyses and favorite shoppable items via secure connection to a **Supabase** backend.
- Optimized client-side image processing, including automated base64 compression and pre-upload resizing, reducing AI API payload times by 40% while preserving critical visual data for the vision model.

---

### Key Action Verbs & Metrics to Remember:
If an interviewer asks you about this project, lean into these specific quantifiable facts:

* **Speed & Scale:** "Leveraged a 72B parameter vision model (Qwen 3.5 VL) accessed via NVIDIA NIM to process complex image data, achieving sub-5-second analysis times."
* **Advanced Architecture:** "Used LangGraph to move beyond simple chat-bot logic, creating a deterministic, state-based workflow where the AI strictly had to analyze the image, classify the missing gap, and search the vector DB sequentially."
* **Data Loop:** "Built a background sync script (`update_product_weights.py`) that aggregated user star ratings from Supabase and pushed updated score weights into Pinecone, ensuring the RAG pipeline surfaced the highest-rated clothing first."
* **Modern Stack:** "Utilized the absolute cutting edge of the React ecosystem, specifically Next.js 15 App Router and the brand-new Tailwind CSS v4.0 alpha for class-based dark variants."
