"use client";

import { useState, useEffect } from "react";
import { Clock, Trash2, ChevronDown, ChevronUp, RefreshCw, ArrowLeft } from "lucide-react";
import { toast } from "sonner";

interface HistoryRecord {
  id: string;
  style_score: number;
  score_breakdown: any;
  narrative_critique: string;
  gap_type: string;
  detected_items: any[];
  color_palette: any[];
  recommended_products: any[];
  weather: any;
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
    } catch (err: any) {
      toast.error(err.message || "Could not load history");
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
    } catch (err: any) {
      toast.error(err.message || "Delete failed");
    } finally {
      setDeletingId(null);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-yellow-500 bg-yellow-50 border-yellow-200";
    if (score >= 70) return "text-green-600 bg-green-50 border-green-200";
    if (score >= 40) return "text-orange-500 bg-orange-50 border-orange-200";
    return "text-red-500 bg-red-50 border-red-200";
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
            className="p-2 rounded-xl hover:bg-gray-100 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-600" />
          </button>
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-gray-900">Wardrobe History</h2>
            <p className="text-sm text-gray-500">{records.length} past analyses</p>
          </div>
        </div>
        <button
          onClick={fetchHistory}
          className="p-2 rounded-xl hover:bg-gray-100 transition-colors"
          title="Refresh"
        >
          <RefreshCw className={`w-5 h-5 text-gray-500 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="text-center py-16 text-gray-400">
          <RefreshCw className="w-8 h-8 mx-auto animate-spin mb-3" />
          Loading history…
        </div>
      )}

      {/* Empty State */}
      {!loading && records.length === 0 && (
        <div className="text-center py-16 bg-white rounded-3xl border border-gray-100 shadow-sm">
          <Clock className="w-12 h-12 mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-semibold text-gray-700 mb-1">No analyses yet</h3>
          <p className="text-sm text-gray-400">Your outfit history will appear here after your first scan.</p>
        </div>
      )}

      {/* Records */}
      {!loading && records.map((record) => (
        <div
          key={record.id}
          className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden transition-all hover:shadow-md"
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
                <span className="text-sm font-semibold text-gray-800 capitalize">
                  Gap: {record.gap_type}
                </span>
                {record.occasion && (
                  <span className="text-[10px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full font-medium">
                    {record.occasion}
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-400 truncate">{record.narrative_critique}</p>
              <div className="text-[10px] text-gray-400 mt-1 flex items-center gap-1">
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
                className="p-2 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors disabled:opacity-50"
                title="Delete"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              {expandedId === record.id ? (
                <ChevronUp className="w-4 h-4 text-gray-400" />
              ) : (
                <ChevronDown className="w-4 h-4 text-gray-400" />
              )}
            </div>
          </div>

          {/* Expanded Details */}
          {expandedId === record.id && (
            <div className="border-t border-gray-100 p-5 bg-gray-50/50 space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
              {/* Critique */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">Expert Critique</h4>
                <p className="text-sm text-gray-600 leading-relaxed">{record.narrative_critique}</p>
              </div>

              {/* Score Breakdown */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(record.score_breakdown || {}).map(([key, value]) => (
                  <div key={key} className="bg-white p-3 rounded-xl border border-gray-100">
                    <div className="text-[10px] text-gray-400 font-medium uppercase tracking-wider mb-1">
                      {key.replace(/_/g, " ")}
                    </div>
                    <div className="text-sm font-bold text-gray-800">{value as number}/100</div>
                  </div>
                ))}
              </div>

              {/* Detected Items */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">Detected Items</h4>
                <div className="flex flex-wrap gap-2">
                  {(record.detected_items || []).map((item: any, idx: number) => (
                    <span key={idx} className="text-xs bg-white px-3 py-1.5 rounded-full border border-gray-200 capitalize">
                      {item.color} {item.garment_type}
                    </span>
                  ))}
                </div>
              </div>

              {/* Colors */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">Colors</h4>
                <div className="flex gap-2">
                  {(record.color_palette || []).map((c: any, idx: number) => (
                    <div key={idx} className="w-8 h-8 rounded-full border border-gray-200 shadow-inner" style={{ backgroundColor: c.hex_code }} title={c.name} />
                  ))}
                </div>
              </div>

              {/* Weather */}
              {record.weather && (
                <div className="text-xs text-blue-600 bg-blue-50 px-3 py-2 rounded-lg border border-blue-100">
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
