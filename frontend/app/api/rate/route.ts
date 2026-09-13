import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { getSupabaseAdmin } from "@/lib/supabase-admin";

/**
 * POST /api/rate — Upsert a product rating (1-5 stars)
 * Body: { product_id: string, rating: number }
 *
 * Service-role client. user_id comes from the verified Clerk session, never from the
 * request body, so a caller cannot write a rating on someone else's behalf.
 */

export async function POST(request: Request) {
  try {
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { product_id, rating } = await request.json();

    if (!product_id || !rating || rating < 1 || rating > 5) {
      return NextResponse.json({ error: "Invalid product_id or rating (1-5)" }, { status: 400 });
    }

    console.log(`[Rate API] User ${userId} rated product ${product_id}: ${rating}★`);

    // Upsert: if this user already rated this product, update; otherwise insert
    const supabase = getSupabaseAdmin();
    const { error } = await supabase
      .from("product_ratings")
      .upsert(
        { product_id, user_id: userId, rating },
        { onConflict: "product_id,user_id" }
      );

    if (error) {
      console.error("[Rate API] Upsert error:", JSON.stringify(error));
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({ success: true, product_id, rating });
  } catch (err: any) {
    console.error("[Rate API] Error:", err);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
