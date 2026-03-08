import { UserButton, SignInButton } from "@clerk/nextjs";
import { currentUser } from "@clerk/nextjs/server";
import { Sparkles, Camera, Search, ShoppingBag, ArrowRight } from "lucide-react";
import MainApp from "@/components/ui/MainApp";

export default async function Home() {
  const user = await currentUser();

  return (
    <div className="min-h-screen flex flex-col items-center selection:bg-indigo-100 selection:text-indigo-900 bg-gray-50 overflow-hidden">
      {/* Header */}
      <div className="w-full max-w-5xl flex items-center justify-between px-6 py-6 z-10 glass-card sticky top-0 rounded-b-3xl">
        <div className="flex items-center gap-2 group cursor-default">
          <div className="bg-black text-white p-1.5 rounded-lg group-hover:scale-110 transition-transform">
            <Sparkles className="w-5 h-5" />
          </div>
          <span className="text-xl font-bold tracking-tight">FASHR</span>
        </div>
        {user ? (
          <UserButton appearance={{ elements: { userButtonAvatarBox: "w-10 h-10 shadow-sm border border-gray-200" } }} />
        ) : (
          <SignInButton mode="modal">
            <button className="text-sm font-medium hover:text-indigo-600 transition-colors">Log In</button>
          </SignInButton>
        )}
      </div>

      {user ? (
        /* Authenticated: Show the App flow */
        <div className="w-full max-w-4xl px-4 py-8 animate-fade-in">
          <MainApp />
        </div>
      ) : (
        /* Unauthenticated: Show Landing */
        <main className="flex-1 flex flex-col items-center justify-center text-center w-full px-4 relative">
          
          {/* Background Decor */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-50 rounded-full blur-3xl opacity-50 mix-blend-multiply pointer-events-none animate-pulse-border" />
          
          <div className="relative z-10 max-w-3xl mx-auto py-20">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-semibold mb-8 animate-fade-in-up">
              <Sparkles className="w-3.5 h-3.5" />
              <span>V2.0 Now Live</span>
            </div>
            
            <h1 className="text-5xl md:text-7xl font-black tracking-tighter text-gray-900 mb-6 drop-shadow-sm animate-fade-in-up animation-delay-100 leading-tight">
              Ditch outfit anxiety.<br/>
              <span className="gradient-text">Dress with data.</span>
            </h1>
            
            <p className="text-lg md:text-xl text-gray-500 max-w-2xl mx-auto leading-relaxed mb-10 animate-fade-in-up delay-200">
              Get immediate, objective feedback on your outfit and discover the exact missing piece to complete your look. Powered by generative AI.
            </p>
            
            <div className="animate-fade-in-up delay-300">
              <SignInButton mode="modal">
                <button className="group relative inline-flex items-center gap-2 bg-black text-white px-8 py-4 rounded-2xl font-semibold hover:scale-105 active:scale-95 transition-all shadow-[0_8px_30px_rgb(0,0,0,0.12)] hover:shadow-[0_8px_30px_rgb(0,0,0,0.2)] overflow-hidden">
                  <span className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out" />
                  <span className="relative">Analyze My Outfit Free</span>
                  <ArrowRight className="w-5 h-5 relative group-hover:translate-x-1 transition-transform" />
                </button>
              </SignInButton>
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
              <div key={i} className={`bg-white/80 backdrop-blur-md p-8 rounded-3xl border border-gray-100 shadow-[0_4px_20px_rgb(0,0,0,0.03)] hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] hover:-translate-y-1 transition-all text-left animate-fade-in-up ${f.delay}`}>
                <div className="w-12 h-12 rounded-2xl bg-gray-50 border border-gray-100 flex items-center justify-center mb-6 text-indigo-600">
                  <f.icon className="w-6 h-6" />
                </div>
                <h3 className="font-bold text-xl text-gray-900 mb-3">{f.title}</h3>
                <p className="text-gray-500 leading-relaxed text-sm">{f.desc}</p>
              </div>
            ))}
          </div>
        </main>
      )}

      {/* Footer */}
      {!user && (
        <footer className="w-full border-t border-gray-100 py-8 text-center text-sm text-gray-400 z-10 bg-white">
          <p>© {new Date().getFullYear()} FASHR. Built with LangGraph, Next.js, and Pinecone.</p>
        </footer>
      )}
    </div>
  );
}

