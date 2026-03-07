import { UserButton, SignInButton } from "@clerk/nextjs";
import { currentUser } from "@clerk/nextjs/server";
import { Sparkles } from "lucide-react";
import MainApp from "@/components/ui/MainApp";

export default async function Home() {
  const user = await currentUser();

  return (
    <div className="min-h-screen flex flex-col items-center p-8">
      {/* Header */}
      <div className="w-full max-w-2xl flex items-center justify-between mb-10 mt-4">
        <div className="flex items-center gap-2">
          <Sparkles className="w-6 h-6 text-black" />
          <span className="text-xl font-bold tracking-tight">FASHR</span>
        </div>
        {user ? (
          <UserButton appearance={{ elements: { userButtonAvatarBox: "w-10 h-10" } }} />
        ) : null}
      </div>

      {user ? (
        /* Authenticated: Show the App flow */
        <MainApp />
      ) : (
        /* Unauthenticated: Show Landing */
        <div className="flex-1 flex flex-col items-center justify-center text-center">
          <Sparkles className="w-16 h-16 mx-auto mb-4 text-black" />
          <h1 className="text-5xl font-extrabold tracking-tighter text-gray-900 mb-4">
            FASHR
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto leading-relaxed mb-8">
            Your personal AI stylist. Get immediate, objective feedback on your outfit and discover the missing piece to complete your look.
          </p>
          <SignInButton mode="modal">
            <button className="bg-black text-white px-8 py-4 rounded-xl font-medium hover:bg-gray-900 transition-colors shadow-lg shadow-gray-200">
              Get Started Free
            </button>
          </SignInButton>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto mt-16 text-left">
            <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm">
              <h3 className="font-bold text-lg mb-2">Instant Critique</h3>
              <p className="text-gray-600 text-sm">Upload a photo. Our vision model breaks down your silhouette, color palette, and proportions in seconds.</p>
            </div>
            <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm">
              <h3 className="font-bold text-lg mb-2">Find the Gap</h3>
              <p className="text-gray-600 text-sm">Missing a jacket? Need better footwear? We identify exactly what&apos;s holding your outfit back.</p>
            </div>
            <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm">
              <h3 className="font-bold text-lg mb-2">Smart Completers</h3>
              <p className="text-gray-600 text-sm">Get 3 validated, purchasable recommendations tailored to your exact size, gender, and the current weather.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
