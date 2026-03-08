import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { createClient } from "@supabase/supabase-js";

/**
 * POST /api/history — Save a new analysis record
 * GET  /api/history — Fetch all records for the authenticated user
 * 
 * Uses the Supabase service-level client with explicit user_id filtering
 * since Clerk JWT → Supabase RLS can be tricky to configure correctly.
 */

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export async function POST(request: Request) {
  try {
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json();
    console.log("[History API] Saving analysis for user:", userId);

    const { error } = await supabase.from("wardrobe_history").insert({
      user_id: userId,
      style_score: body.style_score,
      score_breakdown: body.score_breakdown,
      narrative_critique: body.narrative_critique,
      gap_type: body.gap_type,
      detected_items: body.detected_items,
      color_palette: body.color_palette,
      recommended_products: body.recommended_products || [],
      weather: body.weather || null,
      occasion: body.occasion || null,
      persona: body.persona || null,
    });

    if (error) {
      console.error("[History API] Insert error:", JSON.stringify(error));
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    console.log("[History API] Saved successfully");
    return NextResponse.json({ success: true });
  } catch (err: any) {
    console.error("[History API] POST error:", err);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function GET() {
  try {
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    console.log("[History API] Fetching history for user:", userId);

    const { data, error } = await supabase
      .from("wardrobe_history")
      .select("*")
      .eq("user_id", userId)
      .order("created_at", { ascending: false });

    if (error) {
      console.error("[History API] Fetch error:", JSON.stringify(error));
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    console.log(`[History API] Found ${data?.length || 0} records`);
    return NextResponse.json(data);
  } catch (err: any) {
    console.error("[History API] GET error:", err);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

