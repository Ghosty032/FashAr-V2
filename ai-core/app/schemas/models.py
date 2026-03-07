from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# =========================================================================================
# PHASE 3 - AI CORE SCHEMAS
# These schemas define the EXACT JSON structure the AI must return.
# Using Pydantic alongside Langchain's `with_structured_output` ensures the NVIDIA model
# strictly adheres to this format so the frontend doesn't crash.
# =========================================================================================

class DetectedItem(BaseModel):
    garment_type: str = Field(description="e.g., 'jeans', 't-shirt', 'blazer', 'sneakers'")
    color: str = Field(description="Primary color of the item, e.g., 'navy blue', 'white'")
    texture_or_fabric: str = Field(description="Visual texture or fabric type, e.g., 'denim', 'cotton', 'leather'")
    fit: str = Field(description="How the item fits, e.g., 'slim', 'oversized', 'regular'")
    confidence_score: float = Field(description="AI confidence score between 0.0 and 1.0")

class ColorPalette(BaseModel):
    hex_code: str = Field(description="Hexadecimal color string, e.g., '#0F172A'")
    name: str = Field(description="Human readable name of the color")
    harmony_role: Literal["dominant", "secondary", "accent"] = Field(description="The role this color plays in the entire outfit's color harmony")

class ScoreBreakdown(BaseModel):
    color_cohesion: int = Field(description="Score from 1-100 on how well the colors work together")
    occasion_appropriateness: int = Field(description="Score from 1-100 on how well it fits the given occasion")
    silhouette_and_fit: int = Field(description="Score from 1-100 on the proportions and fit")
    completeness: int = Field(description="Score from 1-100 on whether the outfit feels 'finished' or if it's missing something")

class CritiqueResult(BaseModel):
    """The final structured output from the Critic node."""
    style_score: int = Field(description="Final overall style score from 1-100")
    score_breakdown: ScoreBreakdown
    narrative_critique: str = Field(description="A 2-4 sentence constructive, sophisticated fashion critique written in an objective, elevated tone.")
    gap_type: Literal["structure", "footwear", "texture", "accessory", "color", "none"] = Field(description="The primary missing element holding the outfit back. Output 'none' if perfect.")
    
class ScanResult(BaseModel):
    """The structured output from the Vision/Scan node."""
    detected_items: List[DetectedItem]
    color_palette: List[ColorPalette]

class RecommendedProduct(BaseModel):
    """A single product recommendation from Pinecone RAG."""
    product_id: str
    title: str
    brand: str
    description: str
    gap_type: List[str]
    color_family: List[str]
    buy_link: str
    rating_score: float
    rating_count: int
    relevance_score: float

class FinalAnalysis(BaseModel):
    """Combined object to return to the frontend via FastAPI"""
    detected_items: List[DetectedItem]
    color_palette: List[ColorPalette]
    style_score: int
    score_breakdown: ScoreBreakdown
    narrative_critique: str
    gap_type: str
    recommended_products: List[RecommendedProduct] = []
