"use client";

import { useState } from "react";
import Link from "next/link";
import { UserButton, SignInButton, useUser } from "@clerk/nextjs";
import { Sparkles, Camera, Search, ShoppingBag, ArrowRight } from "lucide-react";
import MainApp from "@/components/ui/MainApp";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

export default function Home() {
  const { isLoaded, isSignedIn } = useUser();
  const [isAppOpen, setIsAppOpen] = useState(false);

  // Still rendering loading state to prevent flash, but keep it minimal
  if (!isLoaded) return null;

  return (
    <div className="min-h-screen flex flex-col items-center selection:bg-indigo-100 selection:text-indigo-900 dark:selection:bg-indigo-900 dark:selection:text-indigo-100 bg-gray-50 dark:bg-black overflow-hidden transition-colors duration-300">
      {/* Header */}
      <div className="w-full max-w-5xl flex items-center justify-between px-6 py-6 z-10 bg-white/70 dark:bg-transparent backdrop-blur-md dark:backdrop-blur-none border border-white/40 dark:border-transparent sticky top-0 rounded-b-3xl transition-colors">
        <Link
          href="/"
          onClick={(e) => {
            if (isAppOpen) {
              e.preventDefault();
              setIsAppOpen(false); // Soft reset to landing page
            }
          }}
          className="flex items-center gap-2 group cursor-pointer"
          title="Go to home"
        >
          <div className="bg-black dark:bg-white/10 text-white p-1.5 rounded-lg group-hover:scale-110 transition-transform">
            <Sparkles className="w-5 h-5" />
          </div>
          <span className="text-xl font-bold tracking-tight text-gray-900 dark:text-gray-100">FASHR</span>
        </Link>

        <div className="flex items-center gap-4">
          <ThemeToggle />

          {isSignedIn ? (
            <UserButton appearance={{ elements: { userButtonAvatarBox: "w-10 h-10 shadow-sm border border-gray-200 dark:border-gray-800" } }} />
          ) : (
            <SignInButton mode="modal">
              <button className="text-sm font-medium text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-white/20 transition-all px-4 py-2.5 rounded-xl border border-transparent dark:bg-white/10 dark:border-white/10 shadow-sm dark:shadow-none">Log In</button>
            </SignInButton>
          )}
        </div>
      </div>

      {isAppOpen && isSignedIn ? (
        /* Authenticated & Flow Started: Show the App flow */
        <div className="w-full max-w-4xl px-4 py-8 animate-fade-in">
          <MainApp />
        </div>
      ) : (
        /* Unauthenticated OR Initial Landing View: Show Landing */
        <main className="flex-1 flex flex-col items-center justify-center text-center w-full px-4 relative">

          {/* Background Decor */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-50 dark:bg-indigo-950/20 rounded-full blur-3xl opacity-50 mix-blend-multiply dark:mix-blend-lighten pointer-events-none animate-pulse-border" />

          <div className="relative z-10 max-w-3xl mx-auto py-20">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-100 dark:border-indigo-500/20 text-indigo-700 dark:text-indigo-300 text-xs font-semibold mb-8 animate-fade-in-up">
              <Sparkles className="w-3.5 h-3.5" />
              <span>V2.0 Out Now</span>
            </div>

            <h1 className="text-5xl md:text-7xl font-black tracking-tighter text-gray-900 dark:text-white mb-6 drop-shadow-sm animate-fade-in-up animation-delay-100 leading-tight">
              Ditch outfit anxiety.<br />
              <span className="gradient-text dark:from-indigo-400 dark:via-purple-400 dark:to-pink-400">Dress with Aura.</span>
            </h1>

            <p className="text-lg md:text-xl text-gray-500 dark:text-gray-400 max-w-2xl mx-auto leading-relaxed mb-10 animate-fade-in-up delay-200">
              Get immediate, objective feedback on your outfit and discover the exact missing piece to complete your look. Powered by generative AI.
            </p>

            <div className="animate-fade-in-up delay-300">
              {isSignedIn ? (
                <button
                  onClick={() => setIsAppOpen(true)}
                  className="group relative inline-flex items-center gap-2 bg-black dark:bg-white text-white dark:text-black px-8 py-4 rounded-2xl font-semibold hover:scale-105 active:scale-95 transition-all shadow-[0_8px_30px_rgb(0,0,0,0.12)] hover:shadow-[0_8px_30px_rgb(255,255,255,0.12)] overflow-hidden"
                >
                  <span className="absolute inset-0 bg-white/20 dark:bg-black/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out" />
                  <span className="relative">Start Analyzing</span>
                  <ArrowRight className="w-5 h-5 relative group-hover:translate-x-1 transition-transform" />
                </button>
              ) : (
                <SignInButton mode="modal">
                  <button className="group relative inline-flex items-center gap-2 bg-black dark:bg-white text-white dark:text-black px-8 py-4 rounded-2xl font-semibold hover:scale-105 active:scale-95 transition-all shadow-[0_8px_30px_rgb(0,0,0,0.12)] hover:shadow-[0_8px_30px_rgb(255,255,255,0.12)] overflow-hidden">
                    <span className="absolute inset-0 bg-white/20 dark:bg-black/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out" />
                    <span className="relative">Start Analyzing</span>
                    <ArrowRight className="w-5 h-5 relative group-hover:translate-x-1 transition-transform" />
                  </button>
                </SignInButton>
              )}
            </div>
          </div>

          {/* Feature Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto w-full pb-24 z-10">
            {[
              {
                icon: Camera,
                title: "Instant Critique",
                desc: "Upload a mirror selfie. Our 100B+ parameter vision model analyzes silhouette, palette, and proportions in seconds.",
                delay: "delay-400"
              },
              {
                icon: Search,
                title: "Find the Gap",
                desc: "Missing a jacket? Need better footwear? We identify exactly what's holding your outfit back from a perfect 100.",
                delay: "delay-500"
              },
              {
                icon: ShoppingBag,
                title: "Smart Completers",
                desc: "Get purchasable recommendations tailored to your size, budget, gender, and the current local weather.",
                delay: "delay-600"
              }
            ].map((f, i) => (
              <div key={i} className={`bg-white/80 dark:bg-gray-900/80 backdrop-blur-md p-8 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-[0_4px_20px_rgb(0,0,0,0.03)] hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] hover:-translate-y-1 transition-all text-left animate-fade-in-up ${f.delay}`}>
                <div className="w-12 h-12 rounded-2xl bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 flex items-center justify-center mb-6 text-indigo-600 dark:text-indigo-400">
                  <f.icon className="w-6 h-6" />
                </div>
                <h3 className="font-bold text-xl text-gray-900 dark:text-gray-100 mb-3">{f.title}</h3>
                <p className="text-gray-500 dark:text-gray-400 leading-relaxed text-sm">{f.desc}</p>
              </div>
            ))}
          </div>
        </main>
      )}

      {/* Footer */}
      {!isAppOpen && (
        <footer className="w-full border-t border-gray-100 dark:border-gray-900 py-8 text-center text-sm text-gray-400 z-10 bg-white dark:bg-black transition-colors duration-300">
          <p>© {new Date().getFullYear()} FASHR. Powered by LangGraph and Pinecone.</p>
        </footer>
      )}
    </div>
  );
}

