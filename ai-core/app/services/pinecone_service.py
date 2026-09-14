"""
FASHR — Pinecone product retrieval.

Uses an index built with **integrated inference**: Pinecone hosts `llama-text-embed-v2`
and embeds text server-side, handling the asymmetry itself (input_type=passage on write,
query on read). Nothing here computes a vector.

This replaced an MD5-based pseudo-embedding whose 1024-dim output contained only 8 distinct
values tiled 128 times, giving retrieval no semantic signal whatsoever. If you ever see a
hand-rolled `_simple_embedding` reappear, that is the bug.
"""

import os
import threading

from pinecone import Pinecone

# Single source of truth for env loading. This module previously called load_dotenv itself
# with three os.path.dirname hops, which from app/services/ resolves to
# `ai-core/frontend/.env.local` — a path that does not exist. It appeared to work only
# because main.py imports app.config first and that populates os.environ as a side effect;
# importing this module on its own left PINECONE_KEY as None.
import app.config  # noqa: F401

PINECONE_KEY = os.getenv("PINECONE_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX", "fashr-products-v2")
NAMESPACE = "__default__"

# How many candidates to pull before reranking. Deliberately wider than the 3 we return, so
# `retrieval_weight` has something to actually reorder.
CANDIDATE_POOL = 20
FINAL_RESULTS = 3

_index = None
_index_lock = threading.Lock()


def _get_index():
    """Cached client. The previous version rebuilt the whole Pinecone client per query."""
    global _index
    if _index is None:
        with _index_lock:
            if _index is None:
                _index = Pinecone(api_key=PINECONE_KEY).Index(INDEX_NAME)
    return _index


def _build_filter(
    gap_type: str,
    gender: str,
    body_types: list[str],
    sizes: list[str],
) -> dict:
    """
    Metadata filter applied server-side by Pinecone.

    body_type and size_range are list-valued metadata, and Pinecone's `$in` matches on list
    overlap, so these belong in the query rather than in a post-filter. Filtering after
    retrieval was starving results: it fetched 5 candidates, then dropped any that missed on
    body type or size, and could easily return nothing.
    """
    conditions: dict = {"gap_type": {"$in": [gap_type]}}

    # "unisex" is not a constraint — it means "show me everything".
    if gender and gender != "unisex":
        conditions["gender_filter"] = {"$in": [gender, "unisex"]}
    if body_types:
        conditions["body_type"] = {"$in": body_types}
    if sizes:
        conditions["size_range"] = {"$in": sizes}

    return conditions


def _hits_to_products(hits: list[dict]) -> list[dict]:
    """Flatten Pinecone hits and apply the rating-derived retrieval weight."""
    products = []
    for hit in hits:
        fields = hit.get("fields", {})
        base_score = hit.get("_score", 0.0)
        weight = fields.get("retrieval_weight", 1.0)

        products.append({
            "product_id": hit.get("_id", ""),
            "title": fields.get("title", ""),
            "brand": fields.get("brand", ""),
            "description": fields.get("description", ""),
            "gap_type": fields.get("gap_type", []),
            "color_family": fields.get("color_family", []),
            "buy_link": fields.get("buy_link", ""),
            "rating_score": fields.get("rating_score", 0),
            "rating_count": fields.get("rating_count", 0),
            "relevance_score": round(base_score * weight, 4),
        })
    return products


def _search(query_text: str, filters: dict) -> list[dict]:
    resp = _get_index().search(
        namespace=NAMESPACE,
        query={"inputs": {"text": query_text}, "top_k": CANDIDATE_POOL, "filter": filters},
    )
    return resp.to_dict().get("result", {}).get("hits", [])


def query_products(
    gap_query: str,
    gap_type: str,
    gender: str = "unisex",
    body_types: list[str] | None = None,
    sizes: list[str] | None = None,
    top_k: int = FINAL_RESULTS,
) -> list[dict]:
    """
    Find products that fill the identified style gap.

    `gap_query` is the critic's natural-language description of the missing piece, e.g.
    "structured navy wool blazer with natural shoulder". It is written as product prose on
    purpose, because that is the register the catalog descriptions are embedded in — feeding
    a metadata-shaped string like "Fashion item for structure gap" matches far worse.

    Blocking call (the Pinecone SDK is sync). Callers on the event loop should wrap it in
    `asyncio.to_thread`.
    """
    body_types = body_types or []
    sizes = sizes or []

    filters = _build_filter(gap_type, gender, body_types, sizes)
    hits = _search(gap_query, filters)

    # If the personal filters over-constrain, fall back to gap + gender rather than showing
    # the user nothing. Better a slightly-off size than an empty recommendations panel.
    if not hits and (body_types or sizes):
        print(
            f"[PINECONE] No matches for body_types={body_types} sizes={sizes}; "
            "relaxing to gap and gender only."
        )
        hits = _search(gap_query, _build_filter(gap_type, gender, [], []))

    products = _hits_to_products(hits)
    products.sort(key=lambda p: p["relevance_score"], reverse=True)
    return products[:top_k]
