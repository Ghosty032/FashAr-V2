export interface DetectedItem {
  garment_type: string;
  color: string;
  texture_or_fabric: string;
  fit: string;
  confidence_score: number;
}

export interface ColorPalette {
  hex_code: string;
  name: string;
  harmony_role: "dominant" | "secondary" | "accent";
}

export interface ScoreBreakdown {
  color_cohesion: number;
  occasion_appropriateness: number;
  silhouette_and_fit: number;
  completeness: number;
}

export interface RecommendedProduct {
  product_id: string;
  title: string;
  brand: string;
  description: string;
  gap_type: string[];
  color_family: string[];
  buy_link: string;
  rating_score: number;
  rating_count: number;
  relevance_score: number;
}

export interface FinalAnalysis {
  detected_items: DetectedItem[];
  color_palette: ColorPalette[];
  style_score: number;
  score_breakdown: ScoreBreakdown;
  narrative_critique: string;
  gap_type: string;
  recommended_products: RecommendedProduct[];
}
