"use client";

import { useState } from "react";
import Scanner from "./Scanner";
import Results from "./Results";
import { FinalAnalysis } from "@/lib/types/ai";

export default function MainApp() {
  const [analysisData, setAnalysisData] = useState<FinalAnalysis | null>(null);

  const handleReset = () => {
    setAnalysisData(null);
  };

  return (
    <div className="w-full">
      {!analysisData ? (
        <Scanner onAnalysisComplete={setAnalysisData} />
      ) : (
        <Results data={analysisData} onReset={handleReset} />
      )}
    </div>
  );
}
