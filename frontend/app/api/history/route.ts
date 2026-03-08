import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { createClerkSupabaseClient } from "@/lib/supabase";

/**
 * POST /api/history — Save a new analysis record
 * GET  /api/history — Fetch all records for the authenticated user
 */

export async function POST(request: Request) {
  try {
    const { userId, getToken } = await auth();
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const token = await getToken({ template: "supabase" });
    if (!token) {
      return NextResponse.json({ error: "Auth token unavailable" }, { status: 401 });
    }

    const body = await request.json();
    const supabase = createClerkSupabaseClient(token);

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
      console.error("[History API] Insert error:", error);
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({ success: true });
  } catch (err: any) {
    console.error("[History API] POST error:", err);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function GET() {
  try {
    const { userId, getToken } = await auth();
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const token = await getToken({ template: "supabase" });
    if (!token) {
      return NextResponse.json({ error: "Auth token unavailable" }, { status: 401 });
    }

    const supabase = createClerkSupabaseClient(token);

    const { data, error } = await supabase
      .from("wardrobe_history")
      .select("*")
      .order("created_at", { ascending: false });

    if (error) {
      console.error("[History API] Fetch error:", error);
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json(data);
  } catch (err: any) {
    console.error("[History API] GET error:", err);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
