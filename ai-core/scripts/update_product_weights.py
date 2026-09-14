"""
FASHR — Background sync: turn star ratings into Pinecone retrieval weights.

Reads every rating from Supabase, averages per product, and writes
retrieval_weight / rating_score / rating_count back into the product's Pinecone metadata,
where `query_products` uses them to rerank search results.

Only metadata is touched, so nothing is re-embedded and `chunk_text` is left alone.

Runs on a schedule — see .github/workflows/update-product-weights.yml — or by hand:
  python ai-core/scripts/update_product_weights.py
"""

import sys
from pathlib import Path

# Import app.config for credentials rather than loading .env here. The load_dotenv call
# this replaced pointed at `ai-core/frontend/.env.local`, which does not exist.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import os  # noqa: E402

from pinecone import Pinecone  # noqa: E402
from supabase import create_client  # noqa: E402

from app.config import PINECONE_KEY, PINECONE_INDEX, PINECONE_NAMESPACE  # noqa: E402

INDEX_NAME = PINECONE_INDEX
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")

# Must be the service-role key. RLS is enabled on product_ratings with no policies, so the
# anon key this script used to rely on can no longer read the table at all — it would
# silently return zero rows and report "nothing to update" forever.
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def calculate_weight(avg_rating: float, count: int) -> float:
    """
    Convert average rating (1-5) into a retrieval_weight multiplier.
    - 5.0 avg → 1.25x boost
    - 3.0 avg → 1.0x (neutral)
    - 1.0 avg → 0.75x penalty
    Scale linearly. Low count ratings are damped toward 1.0.
    """
    # Damping: if only 1-2 ratings, pull toward neutral
    damping = min(count / 5.0, 1.0) 
    raw_weight = 0.75 + (avg_rating - 1.0) * 0.125  # Maps 1→0.75, 3→1.0, 5→1.25
    return round(1.0 + (raw_weight - 1.0) * damping, 4)


def main():
    missing = [
        name for name, value in (
            ("PINECONE_KEY", PINECONE_KEY),
            ("SUPABASE_URL", SUPABASE_URL),
            ("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_KEY),
        ) if not value
    ]
    if missing:
        print(f"Missing required settings: {', '.join(missing)}")
        sys.exit(1)

    # 1. Fetch all ratings from Supabase
    print("Fetching ratings from Supabase...")
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    resp = sb.table("product_ratings").select("product_id, rating").execute()
    
    if not resp.data:
        print("No ratings found. Nothing to update.")
        return

    # 2. Aggregate: { product_id: { total: N, count: N } }
    agg = {}
    for row in resp.data:
        pid = row["product_id"]
        if pid not in agg:
            agg[pid] = {"total": 0, "count": 0}
        agg[pid]["total"] += row["rating"]
        agg[pid]["count"] += 1

    print(f"Found ratings for {len(agg)} products.")

    # 3. Update Pinecone metadata
    pc = Pinecone(api_key=PINECONE_KEY)
    index = pc.Index(INDEX_NAME)

    updates = 0
    for product_id, stats in agg.items():
        avg = stats["total"] / stats["count"]
        weight = calculate_weight(avg, stats["count"])

        try:
            index.update(
                id=product_id,
                set_metadata={
                    "rating_score": round(avg, 2),
                    "rating_count": stats["count"],
                    "retrieval_weight": weight,
                },
                # Records are written into this namespace by seed_products.py. Omitting it
                # targets a different namespace, where the update silently does nothing.
                namespace=PINECONE_NAMESPACE,
            )
            updates += 1
            print(f"  ✓ {product_id}: avg={avg:.2f}, count={stats['count']}, weight={weight}")
        except Exception as e:
            print(f"  ✗ {product_id}: {e}")

    print(f"\nDone. Updated {updates}/{len(agg)} products in Pinecone.")


if __name__ == "__main__":
    main()
