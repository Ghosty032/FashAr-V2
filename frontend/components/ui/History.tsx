"use client";

import { useState, useEffect } from "react";
import { Clock, Trash2, ChevronDown, ChevronUp, RefreshCw, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { errorMessage } from "@/lib/errors";
import type {
  ColorPalette,
  DetectedItem,
  RecommendedProduct,
  ScoreBreakdown,
  WeatherInfo,
} from "@/lib/types/ai";

interface HistoryRecord {
  id: string;
  style_score: number;
  score_breakdown: ScoreBreakdown | null;
  narrative_critique: string;
  gap_type: string;
  detected_items: DetectedItem[] | null;
  color_palette: ColorPalette[] | null;
  recommended_products: RecommendedProduct[] | null;
  weather: WeatherInfo | null;
  occasion: string | null;
  persona: string | null;
  created_at: string;
}

export default function History({ onBack }: { onBack: () => void }) {
  const [records, setRecords] = useState<HistoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/history");
      if (!res.ok) throw new Error("Failed to fetch history");
      const data = await res.json();
      setRecords(data);
    } catch (err: unknown) {
      toast.error(errorMessage(err, "Could not load history"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      const res = await fetch(`/api/history/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete");
      setRecords((prev) => prev.filter((r) => r.id !== id));
      toast.success("Record deleted");
    } catch (err: unknown) {
      toast.error(errorMessage(err, "Delete failed"));
    } finally {
      setDeletingId(null);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-500/10 border-yellow-200 dark:border-yellow-500/20";
    if (score >= 70) return "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-500/10 border-green-200 dark:border-green-500/20";
    if (score >= 40) return "text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-500/10 border-orange-200 dark:border-orange-500/20";
    return "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/20";
  };

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="w-full max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </button>
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100">Wardrobe History</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">{records.length} past analyses</p>
          </div>
        </div>
        <button
          onClick={fetchHistory}
          className="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          title="Refresh"
        >
          <RefreshCw className={`w-5 h-5 text-gray-500 dark:text-gray-400 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="text-center py-16 text-gray-400 dark:text-gray-500">
          <RefreshCw className="w-8 h-8 mx-auto animate-spin mb-3" />
          Loading history…
        </div>
      )}

      {/* Empty State */}
      {!loading && records.length === 0 && (
        <div className="text-center py-16 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-sm transition-colors">
          <Clock className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-700 mb-4" />
          <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-1">No analyses yet</h3>
          <p className="text-sm text-gray-400 dark:text-gray-500">Your outfit history will appear here after your first scan.</p>
        </div>
      )}

      {/* Records */}
      {!loading && records.map((record) => (
        <div
          key={record.id}
          className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm overflow-hidden transition-all hover:shadow-md dark:hover:border-gray-700"
        >
          {/* Card Header */}
          <div
            className="flex items-center gap-4 p-5 cursor-pointer"
            onClick={() => setExpandedId(expandedId === record.id ? null : record.id)}
          >
            {/* Score Badge */}
            <div className={`w-14 h-14 rounded-xl flex items-center justify-center font-black text-xl border ${getScoreColor(record.style_score)}`}>
              {record.style_score}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-sm font-semibold text-gray-800 dark:text-gray-200 capitalize">
                  Gap: {record.gap_type}
                </span>
                {record.occasion && (
                  <span className="text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 px-2 py-0.5 rounded-full font-medium">
                    {record.occasion}
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-400 dark:text-gray-500 truncate">{record.narrative_critique}</p>
              <div className="text-[10px] text-gray-400 dark:text-gray-500 mt-1 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {formatDate(record.created_at)}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(record.id);
                }}
                disabled={deletingId === record.id}
                className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 dark:text-gray-500 hover:text-red-500 transition-colors disabled:opacity-50"
                title="Delete"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              {expandedId === record.id ? (
                <ChevronUp className="w-4 h-4 text-gray-400 dark:text-gray-500" />
              ) : (
                <ChevronDown className="w-4 h-4 text-gray-400 dark:text-gray-500" />
              )}
            </div>
          </div>

          {/* Expanded Details */}
          {expandedId === record.id && (
            <div className="border-t border-gray-100 dark:border-gray-800 p-5 bg-gray-50/50 dark:bg-gray-950/50 space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
              {/* Critique */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">Expert Critique</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{record.narrative_critique}</p>
              </div>

              {/* Score Breakdown */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(record.score_breakdown || {}).map(([key, value]) => (
                  <div key={key} className="bg-white dark:bg-gray-900 p-3 rounded-xl border border-gray-100 dark:border-gray-800">
                    <div className="text-[10px] text-gray-400 dark:text-gray-500 font-medium uppercase tracking-wider mb-1">
                      {key.replace(/_/g, " ")}
                    </div>
                    <div className="text-sm font-bold text-gray-800 dark:text-gray-200">{value as number}/100</div>
                  </div>
                ))}
              </div>

              {/* Detected Items */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">Detected Items</h4>
                <div className="flex flex-wrap gap-2">
                  {(record.detected_items || []).map((item, idx) => (
                    <span key={idx} className="text-xs bg-white dark:bg-gray-900 px-3 py-1.5 rounded-full border border-gray-200 dark:border-gray-800 capitalize dark:text-gray-300">
                      {item.color} {item.garment_type}
                    </span>
                  ))}
                </div>
              </div>

              {/* Colors */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">Colors</h4>
                <div className="flex gap-2">
                  {(record.color_palette || []).map((c, idx) => (
                    <div key={idx} className="w-8 h-8 rounded-full border border-gray-200 dark:border-gray-700 shadow-inner" style={{ backgroundColor: c.hex_code }} title={c.name} />
                  ))}
                </div>
              </div>

              {/* Weather */}
              {record.weather && (
                <div className="text-xs text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 px-3 py-2 rounded-lg border border-blue-100 dark:border-blue-900/30">
                  📍 {record.weather.city} — {record.weather.temp_c}°C, {record.weather.description}
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
