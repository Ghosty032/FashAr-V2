import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { getSupabaseAdmin } from "@/lib/supabase-admin";

export const maxDuration = 60; // Allow 60s for AI to respond if on Vercel Pro

export async function POST(request: Request) {
  try {
    // 1. Authenticate the user (optional check here, but good practice)
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // 2. Parse the incoming multipart form data from the client
    const formData = await request.formData();

    // 3. Attach the user's saved style profile.
    //
    // Done here rather than in the browser on purpose: the client cannot spoof its own
    // gender or sizing, and Scanner.tsx does not need to know these fields exist. Without
    // this the AI Core always fell back to gender="unisex" with no body type or sizes,
    // which disabled the product filters entirely — men were getting women's shoes.
    //
    // A missing or unreachable profile is not fatal: the analysis still runs, just with
    // unfiltered recommendations.
    try {
      const supabase = getSupabaseAdmin();
      const { data: profile } = await supabase
        .from("users")
        .select("gender_filter, body_type, size_range")
        .eq("id", userId)
        .maybeSingle();

      if (profile) {
        formData.set("gender", profile.gender_filter ?? "unisex");
        formData.set("body_type", JSON.stringify(profile.body_type ?? []));
        formData.set("sizes", JSON.stringify(profile.size_range ?? []));
      }
    } catch (profileErr) {
      console.warn("[NextJS Gateway] Profile lookup failed, continuing unfiltered:", profileErr);
    }

    // 4. Forward the exact FormData directly to the Python FastAPI instance
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";
    const pythonEndpoint = `${baseUrl.replace(/\/$/, '')}/analyze`;

    const gatewaySecret = process.env.GATEWAY_SECRET;
    if (!gatewaySecret) {
      // Fail closed rather than sending an unauthenticated request the AI Core will reject.
      console.error("[NextJS Gateway] GATEWAY_SECRET is not set.");
      return NextResponse.json(
        { error: "Server misconfigured", details: "GATEWAY_SECRET is not set." },
        { status: 500 }
      );
    }

    console.log("[NextJS Gateway] Forwarding request to AI Core...");
    const aiResponse = await fetch(pythonEndpoint, {
      method: "POST",
      body: formData, // passing raw form data
      headers: {
        // Proves to the AI Core that this call came from us and not from someone who
        // found the Render hostname. Deliberately no Content-Type here — fetch has to
        // set it itself so the multipart boundary matches the body.
        "x-gateway-secret": gatewaySecret,
        // The AI Core rate-limits per user. This is only trustworthy because the secret
        // above proves the caller; it comes from the verified Clerk session, not the client.
        "x-user-id": userId,
      },
      // Sits just inside maxDuration (60s) and just outside the AI Core's own 55s graph
      // deadline, so a hung upstream surfaces as an error instead of a platform timeout.
      signal: AbortSignal.timeout(58_000),
    });

    if (!aiResponse.ok) {
      let errorText = await aiResponse.text();
      try {
        errorText = JSON.parse(errorText).detail || errorText;
      } catch (e) {}
      console.error("[NextJS Gateway] AI Core Error:", errorText);

      // Pass Retry-After through on a 429 so the client can tell the user when to retry.
      const headers = new Headers();
      const retryAfter = aiResponse.headers.get("retry-after");
      if (retryAfter) headers.set("Retry-After", retryAfter);

      return NextResponse.json(
        { error: "AI Engine Error", details: errorText },
        { status: aiResponse.status, headers }
      );
    }

    // 5. Parse JSON from Python and return it to the frontend
    const aiData = await aiResponse.json();
    return NextResponse.json(aiData);

  } catch (error: any) {
    // AbortSignal.timeout rejects with a TimeoutError DOMException.
    if (error?.name === "TimeoutError" || error?.name === "AbortError") {
      console.error("[NextJS Gateway] AI Core timed out.");
      return NextResponse.json(
        { error: "AI Engine Timeout", details: "The AI Core did not respond in time. Please try again." },
        { status: 504 }
      );
    }

    console.error("[NextJS Gateway] Internal Error:", error);
    return NextResponse.json(
      { error: "Internal Gateway Error", details: error.message },
      { status: 500 }
    );
  }
}
