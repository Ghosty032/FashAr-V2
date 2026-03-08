"use client";

import { useState, useEffect } from "react";
import { FinalAnalysis } from "@/lib/types/ai";
import { CheckCircle2, AlertTriangle, RefreshCw, ShoppingBag, Cloud, Sun, CloudRain, Snowflake, Thermometer, Star } from "lucide-react";
import { toast } from "sonner";

export default function Results({ data, onReset }: { data: FinalAnalysis, onReset: () => void }) {
  const { style_score, score_breakdown, narrative_critique, gap_type, color_palette, detected_items, recommended_products, weather } = data;

  // Phase 7: Track ratings per product { [product_id]: rating }
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const [ratingLoading, setRatingLoading] = useState<string | null>(null);

  const handleRate = async (productId: string, rating: number) => {
    // Optimistic update
    setRatings((prev) => ({ ...prev, [productId]: rating }));
    setRatingLoading(productId);

    try {
      const res = await fetch("/api/rate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId, rating }),
      });
      if (!res.ok) throw new Error("Failed to save rating");
      toast.success(`Rated ${rating}★`);
    } catch {
      toast.error("Could not save rating");
      // Revert on failure
      setRatings((prev) => {
        const next = { ...prev };
        delete next[productId];
        return next;
      });
    } finally {
      setRatingLoading(null);
    }
  };

  // Determine score color
  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-yellow-500 bg-yellow-50";
    if (score >= 70) return "text-green-600 bg-green-50";
    if (score >= 40) return "text-orange-500 bg-orange-50";
    return "text-red-500 bg-red-50";
  };

  const getWeatherIcon = (condition: string) => {
    switch (condition) {
      case "rain":
      case "drizzle":
      case "thunderstorm":
        return <CloudRain className="w-8 h-8 text-blue-400" />;
      case "snow":
        return <Snowflake className="w-8 h-8 text-cyan-300" />;
      case "clear":
        return <Sun className="w-8 h-8 text-amber-400" />;
      default:
        return <Cloud className="w-8 h-8 text-gray-400" />;
    }
  };

  const isComplete = style_score >= 90;

  // Phase 8: Animated Score Counter
  const [displayScore, setDisplayScore] = useState(0);
  
  useEffect(() => {
    let start = 0;
    const end = style_score;
    if (start === end) return;
    
    let totalDuration = 1500;
    let incrementTime = (totalDuration / end);
    
    let timer = setInterval(() => {
      start += 1;
      setDisplayScore(start);
      if (start === end) clearInterval(timer);
    }, incrementTime);
    
    return () => clearInterval(timer);
  }, [style_score]);


  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      
      {/* Header / Score Ring */}
      <div className="flex flex-col md:flex-row gap-6">
        
        {/* Style Score Card */}
        <div className={`flex flex-col items-center justify-center p-8 rounded-3xl border border-gray-100 shadow-sm ${getScoreColor(style_score)} w-full md:w-1/3 text-center animate-fade-in-up`}>
          <div className="text-6xl font-black tracking-tighter mb-2 tabular-nums">{displayScore}</div>
          <div className="text-sm font-medium uppercase tracking-widest opacity-80">Style Score</div>
          <div className="mt-4 text-xs font-medium bg-white/50 px-3 py-1 rounded-full border border-black/5 animate-fade-in delay-500">
            {isComplete ? "Outfit Complete" : `Gap: ${gap_type.toUpperCase()}`}
          </div>
        </div>

        {/* Narrative Critique */}
        <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm w-full md:w-2/3 flex flex-col justify-center animate-fade-in-up delay-100">
          <h3 className="text-lg font-bold mb-3 text-gray-900">Expert Critique</h3>
          <p className="text-gray-600 leading-relaxed text-sm">
            {narrative_critique}
          </p>
          
          {/* Breakdown Mini-Grid */}
          <div className="grid grid-cols-2 gap-4 mt-6 pt-6 border-t border-gray-100">
            <div>
              <div className="text-xs text-gray-400 font-medium uppercase tracking-wider mb-1">Color Cohesion</div>
              <div className="text-sm font-semibold">{score_breakdown.color_cohesion}/100</div>
            </div>
            <div>
              <div className="text-xs text-gray-400 font-medium uppercase tracking-wider mb-1">Occasion Fit</div>
              <div className="text-sm font-semibold">{score_breakdown.occasion_appropriateness}/100</div>
            </div>
            <div>
              <div className="text-xs text-gray-400 font-medium uppercase tracking-wider mb-1">Silhouette & Fit</div>
              <div className="text-sm font-semibold">{score_breakdown.silhouette_and_fit}/100</div>
            </div>
            <div>
              <div className="text-xs text-gray-400 font-medium uppercase tracking-wider mb-1">Completeness</div>
              <div className="text-sm font-semibold">{score_breakdown.completeness}/100</div>
            </div>
          </div>
        </div>
      </div>

      {/* Weather + Colors + Detected Items */}
      <div className={`grid grid-cols-1 ${weather ? "md:grid-cols-3" : "md:grid-cols-2"} gap-6`}>
        
        {/* Weather Tile (Phase 5) */}
        {weather && (
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 p-6 rounded-3xl border border-blue-100 shadow-sm flex flex-col items-center justify-center text-center animate-fade-in-up delay-200">
            <div className="mb-3">{getWeatherIcon(weather.condition)}</div>
            <div className="flex items-center gap-1 mb-1">
              <Thermometer className="w-4 h-4 text-gray-500" />
              <span className="text-2xl font-bold text-gray-800">{weather.temp_c}°C</span>
            </div>
            <div className="text-sm font-medium text-gray-600 capitalize">{weather.description}</div>
            <div className="text-xs text-gray-400 mt-1">{weather.city}</div>
            {weather.weather_note && (
              <div className="mt-3 text-[11px] text-blue-600 bg-blue-100/50 px-3 py-1.5 rounded-lg leading-tight">
                {weather.weather_note}
              </div>
            )}
          </div>
        )}

        <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm animate-fade-in-up delay-300">
          <h3 className="text-sm font-bold uppercase tracking-wider text-gray-400 mb-4">Color Palette</h3>
          <div className="flex gap-3">
            {color_palette.map((color, idx) => (
              <div key={idx} className="flex flex-col items-center gap-2">
                <div className="w-12 h-12 rounded-full border border-gray-200 shadow-inner" style={{ backgroundColor: color.hex_code }} />
                <span className="text-[10px] font-medium text-gray-500 truncate max-w-[60px] text-center">{color.name}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm">
          <h3 className="text-sm font-bold uppercase tracking-wider text-gray-400 mb-4">Detected Garments</h3>
          <ul className="space-y-3">
            {detected_items.map((item, idx) => (
              <li key={idx} className="flex items-start justify-between text-sm">
                <div>
                  <span className="font-semibold text-gray-800 capitalize">{item.color} {item.garment_type}</span>
                  <div className="text-xs text-gray-500 capitalize">{item.fit} fit · {item.texture_or_fabric}</div>
                </div>
                {item.confidence_score > 0.8 ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Recommendations (The Closet) — Phase 7: with star ratings */}
      {!isComplete && recommended_products && recommended_products.length > 0 && (
        <div className="bg-white p-6 md:p-8 rounded-3xl border border-gray-100 shadow-sm">
          <div className="mb-6">
            <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <ShoppingBag className="w-5 h-5 text-indigo-500" /> 
              Recommended to fill the gap ({gap_type})
            </h3>
            <p className="text-sm text-gray-500 mt-1">Sourced from your personal catalog vector search.</p>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {recommended_products.map((product) => (
              <div 
                key={product.product_id} 
                className="group p-4 rounded-xl border border-gray-100 bg-gray-50 hover:bg-white hover:shadow-md hover:border-gray-200 transition-all"
              >
                <a href={product.buy_link} target="_blank" rel="noreferrer">
                  <div className="aspect-square bg-gray-200 rounded-lg mb-4 flex items-center justify-center text-gray-400 text-xs overflow-hidden relative">
                    <span className="uppercase tracking-widest font-bold opacity-30">{product.brand}</span>
                  </div>
                  <h4 className="font-semibold text-gray-900 text-sm mb-1 group-hover:text-indigo-600 transition-colors line-clamp-1">{product.title}</h4>
                  <p className="text-xs text-gray-500 line-clamp-2">{product.description}</p>
                  <div className="mt-3 flex items-center justify-between text-xs font-medium">
                    <span className="text-gray-400">{product.brand}</span>
                    <span className="text-indigo-600">View →</span>
                  </div>
                </a>

                {/* Phase 7: Star Rating Widget */}
                <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
                  <div className="flex gap-0.5">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        onClick={() => handleRate(product.product_id, star)}
                        disabled={ratingLoading === product.product_id}
                        className="p-0.5 transition-transform hover:scale-110 disabled:opacity-50"
                        title={`Rate ${star} star${star > 1 ? "s" : ""}`}
                      >
                        <Star
                          className={`w-4 h-4 transition-colors ${
                            (ratings[product.product_id] || 0) >= star
                              ? "text-amber-400 fill-amber-400"
                              : "text-gray-300"
                          }`}
                        />
                      </button>
                    ))}
                  </div>
                  {ratings[product.product_id] && (
                    <span className="text-[10px] text-gray-400 font-medium">
                      {ratings[product.product_id]}★ saved
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Reset */}
      <div className="flex justify-center pt-8">
        <button 
          onClick={onReset}
          className="flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors bg-white px-6 py-2.5 rounded-full border border-gray-200 shadow-sm"
        >
          <RefreshCw className="w-4 h-4" />
          Scan Another Outfit
        </button>
      </div>

    </div>
  );
}

