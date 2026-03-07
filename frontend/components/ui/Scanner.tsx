"use client";

import { useState } from "react";
import ImageUploadZone from "./ImageUploadZone";
import { ScanLine, Type, ChevronDown } from "lucide-react";
import { toast } from "sonner";

// PRD §5.1.3 — Two-tier occasion system
const OCCASIONS_TIER1 = ["Casual", "Smart Casual", "Business", "Formal", "Event", "Active"] as const;
const STYLE_PERSONAS = ["Minimalist", "Streetwear", "Old Money", "Business Core", "Y2K", "Outdoor / Utilitarian"] as const;

type InputMode = "image" | "text";

export default function Scanner() {
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
      // TODO: Phase 6 — POST to gateway/api/analyze
      toast.info("Analysis engine not connected yet. This will work after Phase 3 & 6.");
    } catch {
      toast.error("Analysis failed. Please try again.");
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
        className="w-full flex items-center justify-center gap-2 bg-black text-white py-3.5 px-6 rounded-xl font-medium hover:bg-gray-900 transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-gray-200"
      >
        <ScanLine className="w-5 h-5" />
        {isAnalyzing ? "Analyzing…" : "Analyze My Outfit"}
      </button>
    </div>
  );
}
