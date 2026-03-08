"""
FASHR Phase 7 — Background Sync: Update Product Weights
Reads ratings from Supabase, calculates averages, and updates
retrieval_weight / rating_score / rating_count in Pinecone metadata.

Run periodically (e.g., daily via cron, Railway, or GitHub Actions):
  python scripts/update_product_weights.py
"""

import os
import sys
from dotenv import load_dotenv
from pinecone import Pinecone
from supabase import create_client

# Load env from frontend/.env.local
_root = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(_root, "frontend", ".env.local"))

PINECONE_KEY = os.getenv("PINECONE_KEY")
INDEX_NAME = "fashr-products"
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")


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
    if not all([PINECONE_KEY, SUPABASE_URL, SUPABASE_KEY]):
        print("Missing env vars. Ensure PINECONE_KEY, NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY are set.")
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
                }
            )
            updates += 1
            print(f"  ✓ {product_id}: avg={avg:.2f}, count={stats['count']}, weight={weight}")
        except Exception as e:
            print(f"  ✗ {product_id}: {e}")

    print(f"\nDone. Updated {updates}/{len(agg)} products in Pinecone.")


if __name__ == "__main__":
    main()
