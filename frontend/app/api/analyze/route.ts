import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";

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

    // 3. Optional: Validate the data before sending to Python
    // (We assumed the client does basic validation like occasion, persona, etc.)

    // 4. Forward the exact FormData directly to the Python FastAPI instance
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";
    const pythonEndpoint = `${baseUrl.replace(/\/$/, '')}/analyze`;
    
    console.log("[NextJS Gateway] Forwarding request to AI Core...");
    const aiResponse = await fetch(pythonEndpoint, {
      method: "POST",
      body: formData, // passing raw form data
    });

    if (!aiResponse.ok) {
      let errorText = await aiResponse.text();
      try {
        errorText = JSON.parse(errorText).detail || errorText;
      } catch (e) {}
      console.error("[NextJS Gateway] AI Core Error:", errorText);
      return NextResponse.json(
        { error: "AI Engine Error", details: errorText },
        { status: aiResponse.status }
      );
    }

    // 5. Parse JSON from Python and return it to the frontend
    const aiData = await aiResponse.json();
    return NextResponse.json(aiData);

  } catch (error: any) {
    console.error("[NextJS Gateway] Internal Error:", error);
    return NextResponse.json(
      { error: "Internal Gateway Error", details: error.message },
      { status: 500 }
    );
  }
}
