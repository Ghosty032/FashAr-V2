"""
Pipeline behaviour: input parsing, failure reporting, and the retrieval node's logic.

All of it runs with the graph and Pinecone stubbed, so no network or API keys are needed.
Live retrieval is covered separately in test_retrieval_live.py.
"""

import asyncio

import pytest

from app.schemas.models import CritiqueResult, ScanResult, ScoreBreakdown

BREAKDOWN = ScoreBreakdown(
    color_cohesion=60, occasion_appropriateness=65, silhouette_and_fit=70, completeness=50
)


def make_critique(score=62, gap="structure", query="tailored navy wool blazer"):
    return CritiqueResult(
        style_score=score,
        score_breakdown=BREAKDOWN,
        narrative_critique="Flat and unfinished.",
        gap_type=gap,
        gap_query=query,
    )


EMPTY_SCAN = ScanResult(detected_items=[], color_palette=[])


class StubGraph:
    """Captures the inputs the endpoint builds, and returns a canned result."""

    def __init__(self, result=None):
        self.captured = {}
        self._result = result or {
            "scan_result": EMPTY_SCAN,
            "critique_result": make_critique(gap="none", query=""),
        }

    async def ainvoke(self, inputs):
        self.captured = inputs
        return self._result


BASE_FORM = {
    "occasion_tier_1": "Casual",
    "style_persona": "Minimalist",
    "text_description": "navy jeans and a white tee",
}


# ==========================================================================================
# Profile fields reaching the graph
# ==========================================================================================

def test_profile_fields_are_parsed(client, auth_headers, monkeypatch):
    """
    gender/body_type/sizes are attached by the Next.js gateway from the saved profile.
    Before this worked, every request defaulted to unisex with no filters, so men were
    recommended women's shoes.
    """
    import app.main as main

    stub = StubGraph()
    monkeypatch.setattr(main, "fashr_graph", stub)

    client.post("/analyze", headers=auth_headers, data={
        **BASE_FORM, "gender": "womens",
        "body_type": '["petite","slim"]', "sizes": '["XS","S"]',
    })

    assert stub.captured["gender"] == "womens"
    assert stub.captured["body_type"] == ["petite", "slim"]
    assert stub.captured["sizes"] == ["XS", "S"]


@pytest.mark.parametrize("bad", ["not-json", '{"oops": 1}', "", "[1, 2, 3]"])
def test_malformed_profile_fields_degrade(client, auth_headers, monkeypatch, bad):
    """A malformed profile field must not fail the whole analysis."""
    import app.main as main

    stub = StubGraph()
    monkeypatch.setattr(main, "fashr_graph", stub)

    resp = client.post("/analyze", headers=auth_headers,
                       data={**BASE_FORM, "body_type": bad, "sizes": bad})

    assert resp.status_code == 200
    assert stub.captured["body_type"] == []
    assert stub.captured["sizes"] == []


def test_requires_image_or_text(client, auth_headers):
    resp = client.post("/analyze", headers=auth_headers, data={
        "occasion_tier_1": "Casual", "style_persona": "Minimalist",
    })
    assert resp.status_code == 400


def test_occasion_tiers_are_combined(client, auth_headers, monkeypatch):
    import app.main as main

    stub = StubGraph()
    monkeypatch.setattr(main, "fashr_graph", stub)

    client.post("/analyze", headers=auth_headers,
                data={**BASE_FORM, "occasion_tier_2": "rooftop bar"})

    assert stub.captured["occasion"] == "Casual - rooftop bar"


# ==========================================================================================
# Failure reporting
# ==========================================================================================

def test_pipeline_error_surfaces_as_502(client, auth_headers, monkeypatch):
    """
    A node that records why it failed must produce that reason, not a generic 500. Every
    backend failure used to look identical from the outside.
    """
    import app.main as main

    monkeypatch.setattr(main, "fashr_graph", StubGraph({
        "scan_result": EMPTY_SCAN,
        "critique_result": None,
        "error": "Critique step failed (ValueError): model refused",
    }))

    resp = client.post("/analyze", headers=auth_headers, data=BASE_FORM)
    assert resp.status_code == 502
    assert "model refused" in resp.json()["detail"]


def test_graph_timeout_returns_504(client, auth_headers, monkeypatch):
    import app.main as main

    class HangingGraph:
        async def ainvoke(self, inputs):
            await asyncio.sleep(30)

    monkeypatch.setattr(main, "fashr_graph", HangingGraph())
    monkeypatch.setattr(main, "ANALYSIS_TIMEOUT_SECONDS", 0.5)

    resp = client.post("/analyze", headers=auth_headers, data=BASE_FORM)
    assert resp.status_code == 504


# ==========================================================================================
# Retrieval node logic (Pinecone stubbed)
# ==========================================================================================

@pytest.mark.asyncio
async def test_high_score_skips_retrieval(monkeypatch):
    """A finished outfit gets no upsell, and costs no vector search."""
    from app.nodes import retrieve as node

    called = False

    def spy(**kwargs):
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(node, "query_products", spy)
    out = await node.retrieve_products({"critique_result": make_critique(score=95)})

    assert out["recommended_products"] == []
    assert called is False


@pytest.mark.asyncio
async def test_gap_none_skips_retrieval(monkeypatch):
    from app.nodes import retrieve as node

    monkeypatch.setattr(node, "query_products", lambda **k: [{"product_id": "x"}])
    out = await node.retrieve_products({"critique_result": make_critique(gap="none")})

    assert out["recommended_products"] == []


@pytest.mark.asyncio
async def test_gap_query_is_used_as_search_text(monkeypatch):
    """The critic's prose description is what gets embedded, not filter-speak."""
    from app.nodes import retrieve as node

    seen = {}

    def spy(**kwargs):
        seen.update(kwargs)
        return []

    monkeypatch.setattr(node, "query_products", spy)
    await node.retrieve_products({
        "critique_result": make_critique(query="structured navy wool blazer"),
        "gender": "mens", "body_type": ["athletic"], "sizes": ["L"],
    })

    assert seen["gap_query"] == "structured navy wool blazer"
    assert seen["gap_type"] == "structure"
    assert seen["gender"] == "mens"
    assert seen["sizes"] == ["L"]


@pytest.mark.asyncio
async def test_missing_gap_query_falls_back_to_prose(monkeypatch):
    """Older results carry no gap_query; the fallback must still be prose, not a filter."""
    from app.nodes import retrieve as node

    seen = {}
    monkeypatch.setattr(node, "query_products", lambda **k: (seen.update(k), [])[1])

    await node.retrieve_products({"critique_result": make_critique(query="")})

    assert seen["gap_query"]
    assert "gap" not in seen["gap_query"].lower()


@pytest.mark.asyncio
async def test_weather_suppression_switches_to_boosted_gap(monkeypatch):
    from app.nodes import retrieve as node

    seen = {}
    monkeypatch.setattr(node, "query_products", lambda **k: (seen.update(k), [])[1])

    await node.retrieve_products({
        "critique_result": make_critique(gap="structure"),
        "weather_context": {
            "suppressed_gap_types": ["structure"],
            "boosted_gap_types": ["footwear"],
        },
    })

    assert seen["gap_type"] == "footwear"


@pytest.mark.asyncio
async def test_weather_suppression_without_alternative_skips(monkeypatch):
    from app.nodes import retrieve as node

    monkeypatch.setattr(node, "query_products", lambda **k: [{"product_id": "x"}])

    out = await node.retrieve_products({
        "critique_result": make_critique(gap="structure"),
        "weather_context": {"suppressed_gap_types": ["structure"], "boosted_gap_types": []},
    })

    assert out["recommended_products"] == []


@pytest.mark.asyncio
async def test_product_without_gap_type_survives_post_filter(monkeypatch):
    """
    Regression: the filter used `all(...)` over the product's gap_type list, and all([]) is
    True, so a product carrying no gap_type at all was silently discarded.
    """
    from app.nodes import retrieve as node

    products = [
        {"product_id": "no_gap", "gap_type": []},
        {"product_id": "only_suppressed", "gap_type": ["structure"]},
        {"product_id": "partly_suppressed", "gap_type": ["structure", "texture"]},
    ]
    monkeypatch.setattr(node, "query_products", lambda **k: list(products))

    out = await node.retrieve_products({
        "critique_result": make_critique(gap="texture"),
        "weather_context": {"suppressed_gap_types": ["structure"], "boosted_gap_types": []},
    })

    kept = {p["product_id"] for p in out["recommended_products"]}
    assert "no_gap" in kept
    assert "partly_suppressed" in kept
    assert "only_suppressed" not in kept


@pytest.mark.asyncio
async def test_retrieval_failure_is_not_fatal(monkeypatch):
    """A vector search outage should cost recommendations, not the whole analysis."""
    from app.nodes import retrieve as node

    def boom(**kwargs):
        raise RuntimeError("pinecone unreachable")

    monkeypatch.setattr(node, "query_products", boom)
    out = await node.retrieve_products({"critique_result": make_critique()})

    assert out["recommended_products"] == []
