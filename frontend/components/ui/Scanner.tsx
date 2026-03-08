"use client";

import { useState } from "react";
import ImageUploadZone from "./ImageUploadZone";
import { ScanLine, Type, ChevronDown } from "lucide-react";
import { toast } from "sonner";
import { FinalAnalysis } from "@/lib/types/ai";

// PRD §5.1.3 — Two-tier occasion system
const OCCASIONS_TIER1 = ["Casual", "Smart Casual", "Business", "Formal", "Event", "Active"] as const;
const STYLE_PERSONAS = ["Minimalist", "Streetwear", "Old Money", "Business Core", "Y2K", "Outdoor / Utilitarian"] as const;

type InputMode = "image" | "text";

interface ScannerProps {
  onAnalysisComplete: (data: FinalAnalysis) => void;
}

export default function Scanner({ onAnalysisComplete }: ScannerProps) {
  // Input state
  const [mode, setMode] = useState<InputMode>("image");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [textDescription, setTextDescription] = useState("");

  // Context modifiers
  const [occasionTier1, setOccasionTier1] = useState<string>(OCCASIONS_TIER1[0]);
  const [occasionTier2, setOccasionTier2] = useState("");
  const [persona, setPersona] = useState<string>(STYLE_PERSONAS[0]);

  // Submit state
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleImageReady = (file: File, url: string) => {
    setImageFile(file);
    setPreviewUrl(url);
  };

  const handleClearImage = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setImageFile(null);
    setPreviewUrl(null);
  };

  const canSubmit = mode === "image" ? !!imageFile : textDescription.trim().length > 0;

  const handleSubmit = async () => {
    if (!canSubmit) return;

    // Text validation: PRD §5.1.2 — need >= 3 garment descriptors
    if (mode === "text") {
      const words = textDescription.trim().split(/\s+/);
      if (words.length < 6) {
        toast.error("Please provide a more detailed description (e.g., 'dark navy slim jeans with a white oversized linen shirt').");
        return;
      }
    }

    setIsAnalyzing(true);
    try {
      // Phase 5: Capture geolocation (non-blocking — skip if denied)
      let latitude: number | null = null;
      let longitude: number | null = null;
      try {
        const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
        });
        latitude = pos.coords.latitude;
        longitude = pos.coords.longitude;
      } catch {
        console.log("[Scanner] Geolocation denied or unavailable, proceeding without weather.");
      }

      // Build FormData exactly matching FastAPI expectations
      const formData = new FormData();
      if (mode === "image" && imageFile) {
        formData.append("image", imageFile);
      } else if (mode === "text") {
        formData.append("text_description", textDescription);
      }

      formData.append("occasion_tier_1", occasionTier1);
      if (occasionTier2.trim()) formData.append("occasion_tier_2", occasionTier2.trim());
      formData.append("style_persona", persona);

      // Phase 5: Append coordinates if available
      if (latitude !== null && longitude !== null) {
        formData.append("latitude", latitude.toString());
        formData.append("longitude", longitude.toString());
      }

      const response = await fetch("/api/analyze", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || errorData.details || "Failed to analyze outfit");
      }

      const data: FinalAnalysis = await response.json();
      toast.success("Analysis complete!");
      handleClearImage(); // clean up memory
      onAnalysisComplete(data);
      
    } catch (error: any) {
      toast.error(error.message || "Analysis failed. Please try again.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">
      {/* Mode Tabs */}
      <div className="flex bg-gray-100 rounded-xl p-1">
        <button
          onClick={() => setMode("image")}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-medium transition-all
            ${mode === "image" ? "bg-white text-black shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
        >
          <ScanLine className="w-4 h-4" />
          Photo
        </button>
        <button
          onClick={() => setMode("text")}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-medium transition-all
            ${mode === "text" ? "bg-white text-black shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
        >
          <Type className="w-4 h-4" />
          Describe
        </button>
      </div>

      {/* Input Area */}
      {mode === "image" ? (
        <ImageUploadZone
          onImageReady={handleImageReady}
          onClear={handleClearImage}
          previewUrl={previewUrl}
        />
      ) : (
        <textarea
          value={textDescription}
          onChange={(e) => setTextDescription(e.target.value)}
          rows={4}
          placeholder="Describe your outfit in detail… e.g., 'Wearing dark navy slim-fit jeans, a white oversized linen shirt untucked, and brown leather Chelsea boots.'"
          className="w-full rounded-2xl border border-gray-200 bg-white p-4 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-black/10 focus:border-gray-300 resize-none"
        />
      )}

      {/* Context Modifiers */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Occasion Tier 1 */}
        <div>
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">Occasion</label>
          <div className="relative">
            <select
              value={occasionTier1}
              onChange={(e) => setOccasionTier1(e.target.value)}
              className="w-full appearance-none rounded-xl border border-gray-200 bg-white py-2.5 pl-4 pr-10 text-sm font-medium text-gray-800 focus:outline-none focus:ring-2 focus:ring-black/10"
            >
              {OCCASIONS_TIER1.map((o) => (
                <option key={o} value={o}>{o}</option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          </div>
        </div>

        {/* Style Persona */}
        <div>
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">Style Persona</label>
          <div className="relative">
            <select
              value={persona}
              onChange={(e) => setPersona(e.target.value)}
              className="w-full appearance-none rounded-xl border border-gray-200 bg-white py-2.5 pl-4 pr-10 text-sm font-medium text-gray-800 focus:outline-none focus:ring-2 focus:ring-black/10"
            >
              {STYLE_PERSONAS.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Occasion Tier 2 — Contextual Detail */}
      <div>
        <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">Context Detail <span className="text-gray-400">(optional)</span></label>
        <input
          type="text"
          value={occasionTier2}
          onChange={(e) => setOccasionTier2(e.target.value)}
          placeholder="e.g., rooftop bar, law firm interview, outdoor wedding…"
          className="w-full rounded-xl border border-gray-200 bg-white py-2.5 px-4 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-black/10"
        />
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!canSubmit || isAnalyzing}
        className="w-full flex items-center justify-center gap-2 bg-gray-900 text-white py-4 px-6 rounded-2xl font-semibold hover:bg-black transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-[0_8px_30px_rgb(0,0,0,0.12)] hover:shadow-[0_8px_30px_rgb(0,0,0,0.2)] hover:-translate-y-0.5 active:translate-y-0"
      >
        <ScanLine className="w-5 h-5" />
        Analyze My Outfit
      </button>

      {/* Phase 8: Premium Loading Overlay */}
      {isAnalyzing && (
        <div className="absolute inset-0 z-50 glass-card rounded-3xl flex flex-col items-center justify-center animate-fade-in">
          <div className="relative flex items-center justify-center w-20 h-20 mb-6">
            {/* Spinning gradient ring */}
            <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-indigo-500 border-r-indigo-500 animate-spin" />
            <div className="absolute inset-2 rounded-full border-4 border-transparent border-b-violet-500 border-l-violet-500 animate-spin-slow" />
            <ScanLine className="w-8 h-8 text-gray-900 animate-pulse" />
          </div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">Analyzing Outfit</h3>
          <p className="text-sm text-gray-500 animate-pulse text-center px-6">
            Running 122B parameter vision model...<br/>
            Evaluating silhouette, gap, and colors.
          </p>
        </div>
      )}
    </div>
  );
}
