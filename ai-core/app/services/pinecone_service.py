import os
import hashlib
from pinecone import Pinecone
from dotenv import load_dotenv

# Load env
_parent = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(_parent, "frontend", ".env.local"))

PINECONE_KEY = os.getenv("PINECONE_KEY")
INDEX_NAME = "fashr-products"
EMBEDDING_DIM = 1024


def _get_index():
    pc = Pinecone(api_key=PINECONE_KEY)
    return pc.Index(INDEX_NAME)


def _simple_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """
    Deterministic pseudo-embedding matching the seed script.
    TODO: Replace with real NVIDIA NeMo Embeddings in production.
    """
    h = hashlib.md5(text.encode()).digest()
    vec = []
    for i in range(dim):
        byte_pair = h[(i * 2) % len(h)] ^ h[(i * 2 + 1) % len(h)]
        val = (byte_pair / 127.5) - 1.0
        vec.append(val)
    norm = sum(v ** 2 for v in vec) ** 0.5
    return [v / norm for v in vec]


def query_products(
    gap_type: str,
    gender: str,
    body_types: list[str],
    sizes: list[str],
    color_family: list[str] | None = None,
    top_k: int = 5
) -> list[dict]:
    """
    Query Pinecone for products matching the gap, filtered by user dimensions.
    Returns top_k results sorted by weighted score.
    """
    index = _get_index()

    # Build the query text similar to how we embedded
    query_text = f"Fashion item for {gap_type} gap. Colors: {', '.join(color_family or [])}. For {gender} in sizes {', '.join(sizes)}."
    query_vec = _simple_embedding(query_text)

    # Build metadata filter
    # Pinecone filter syntax: https://docs.pinecone.io/docs/metadata-filtering
    filter_conditions = {
        "gap_type": {"$in": [gap_type]},
    }

    # Gender: match exact or unisex
    if gender and gender != "unisex":
        filter_conditions["gender_filter"] = {"$in": [gender, "unisex"]}

    results = index.query(
        vector=query_vec,
        top_k=top_k,
        include_metadata=True,
        filter=filter_conditions,
    )

    # Post-filter by body_type and size overlap, then apply retrieval_weight
    scored_products = []
    for match in results.get("matches", []):
        meta = match.get("metadata", {})

        # Check body_type overlap
        product_body_types = meta.get("body_type", [])
        if body_types and not any(bt in product_body_types for bt in body_types):
            continue

        # Check size overlap
        product_sizes = meta.get("size_range", [])
        if sizes and not any(s in product_sizes for s in sizes):
            continue

        # Apply retrieval_weight multiplier to the cosine score
        base_score = match.get("score", 0)
        weight = meta.get("retrieval_weight", 1.0)
        weighted_score = base_score * weight

        scored_products.append({
            "product_id": match["id"],
            "title": meta.get("title", ""),
            "brand": meta.get("brand", ""),
            "description": meta.get("description", ""),
            "gap_type": meta.get("gap_type", []),
            "color_family": meta.get("color_family", []),
            "buy_link": meta.get("buy_link", ""),
            "rating_score": meta.get("rating_score", 0),
            "rating_count": meta.get("rating_count", 0),
            "relevance_score": round(weighted_score, 4),
        })

    # Sort by weighted score descending and return top 3
    scored_products.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored_products[:3]
