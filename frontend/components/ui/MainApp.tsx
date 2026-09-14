"use client";

import { useState } from "react";
import Scanner, { type AnalysisContext } from "./Scanner";
import Results from "./Results";
import History from "./History";
import { FinalAnalysis } from "@/lib/types/ai";
import { Clock } from "lucide-react";

type View = "scanner" | "results" | "history";

export default function MainApp() {
  const [view, setView] = useState<View>("scanner");
  const [analysisData, setAnalysisData] = useState<FinalAnalysis | null>(null);

  const handleAnalysisComplete = async (data: FinalAnalysis, context: AnalysisContext) => {
    setAnalysisData(data);
    setView("results");

    // Auto-save to Supabase in background. The occasion and persona come from the Scanner
    // rather than from `data` — the analysis response has never carried them, which is why
    // those columns were always null.
    try {
      const res = await fetch("/api/history", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...data, ...context }),
      });
      if (res.ok) {
        console.log("[MainApp] Analysis saved to history");
      } else {
        console.error("[MainApp] Failed to save history");
      }
    } catch (err) {
      console.error("[MainApp] History save error:", err);
    }
  };

  const handleReset = () => {
    setAnalysisData(null);
    setView("scanner");
  };

  return (
    <div className="w-full">
      {/* History button — show on scanner view */}
      {view === "scanner" && (
        <div className="flex justify-end max-w-2xl mx-auto mb-4">
          <button
            onClick={() => setView("history")}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 transition-colors bg-white px-4 py-2 rounded-full border border-gray-200 shadow-sm dark:bg-gray-900 dark:text-gray-400 dark:hover:text-gray-100 dark:border-gray-800"
          >
            <Clock className="w-4 h-4" />
            History
          </button>
        </div>
      )}

      {view === "scanner" && (
        <Scanner onAnalysisComplete={handleAnalysisComplete} />
      )}
      {view === "results" && analysisData && (
        <Results data={analysisData} onReset={handleReset} />
      )}
      {view === "history" && (
        <History onBack={() => setView("scanner")} />
      )}
    </div>
  );
}

