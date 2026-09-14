"""
Live retrieval against the real Pinecone index.

Marked `integration` and skipped automatically when PINECONE_KEY is absent, so the default
`pytest` run stays offline:

    pytest                      # unit tests only
    pytest -m integration       # these too, needs PINECONE_KEY and a seeded index

These assert on *relative* ordering rather than absolute scores. Embedding models get
updated, and a test that pins a similarity score to 3 decimal places would fail for reasons
that have nothing to do with this codebase.
"""

import pytest

from app.config import PINECONE_KEY

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not PINECONE_KEY, reason="PINECONE_KEY not configured"),
]


def _titles(results):
    return [r["title"] for r in results]


def test_semantic_match_beats_unrelated():
    """
    The core guarantee the old MD5 pseudo-embeddings could not provide: a blazer query
    ranks blazers above everything else in the same gap.
    """
    from app.services.pinecone_service import query_products

    results = query_products(
        gap_query="structured navy wool blazer with natural shoulder for layering",
        gap_type="structure",
    )

    assert results, "expected matches — is the index seeded?"
    assert "blazer" in results[0]["title"].lower()
    # Scores must be ordered and meaningful, not noise.
    scores = [r["relevance_score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] > 0


def test_knitwear_query_returns_knitwear():
    from app.services.pinecone_service import query_products

    results = query_products(
        gap_query="soft chunky knit to add tactile warmth to a flat outfit",
        gap_type="texture",
    )

    joined = " ".join(_titles(results)).lower()
    assert any(word in joined for word in ("sweater", "knit", "cardigan", "turtleneck"))


def test_gender_filter_excludes_other_gender():
    """
    Regression: gender was only applied when != 'unisex', and nothing ever set it, so men
    were being recommended women's mules.
    """
    from app.services.pinecone_service import query_products

    womens = query_products(
        gap_query="elegant heeled shoes", gap_type="footwear", gender="womens"
    )

    assert womens
    # These are men's-only items in the seeded catalog.
    joined = " ".join(_titles(womens)).lower()
    assert "chelsea boots in brown suede" not in joined
    assert "desert boots" not in joined


def test_over_constrained_filters_relax_rather_than_return_nothing():
    """
    Previously filtering happened after retrieval over a pool of 5, so a narrow size could
    leave the user with an empty recommendations panel.
    """
    from app.services.pinecone_service import query_products

    results = query_products(
        gap_query="tailored wool blazer",
        gap_type="structure",
        gender="mens",
        body_types=["petite"],   # no men's blazer in the catalog is tagged petite
        sizes=["XXS"],
    )

    assert results, "expected the relaxation path to return something"


def test_size_filter_narrows_results():
    from app.services.pinecone_service import query_products

    kwargs = dict(gap_query="tailored wool blazer", gap_type="structure", gender="womens")
    unfiltered = query_products(**kwargs)
    filtered = query_products(**kwargs, body_types=["petite"], sizes=["XS"])

    assert len(filtered) <= len(unfiltered)
    assert set(_titles(filtered)).issubset(set(_titles(unfiltered)))


def test_results_carry_every_field_the_api_returns():
    """query_products output is fed straight into RecommendedProduct."""
    from app.schemas.models import RecommendedProduct
    from app.services.pinecone_service import query_products

    results = query_products(gap_query="leather belt", gap_type="accessory")

    assert results
    for row in results:
        RecommendedProduct(**row)  # raises if a field is missing or mistyped
