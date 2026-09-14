import { NextResponse } from "next/server";
import { auth, currentUser } from "@clerk/nextjs/server";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import { errorMessage } from "@/lib/errors";

/**
 * GET  /api/profile — the signed-in user's style profile, or null if they have none
 * POST /api/profile — create or update it
 *
 * This replaces the browser writing to Supabase directly with a Clerk JWT template. That
 * approach needed a `supabase` JWT template configured in Clerk and RLS policies keyed on
 * auth.uid(), neither of which holds now: RLS is enabled with no policies and the anon key
 * cannot reach these tables at all.
 *
 * Writing server-side also means the profile cannot be spoofed from the client — the id
 * and email come from the verified session, never from the request body.
 */

const GENDERS = ["mens", "womens", "unisex"] as const;
const BODY_TYPES = ["slim", "regular", "athletic", "plus", "petite", "tall"] as const;
const SIZES = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL"] as const;

/** Keep only recognised values, so a malformed body cannot write junk into the filters. */
function clean(values: unknown, allowed: readonly string[]): string[] {
  if (!Array.isArray(values)) return [];
  return [...new Set(values.filter((v): v is string => typeof v === "string" && allowed.includes(v)))];
}

export async function GET() {
  try {
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const supabase = getSupabaseAdmin();
    const { data, error } = await supabase
      .from("users")
      .select("id, email, gender_filter, body_type, size_range, preferred_brands")
      .eq("id", userId)
      .maybeSingle(); // no row is a normal state, not an error

    if (error) {
      console.error("[Profile API] Fetch error:", JSON.stringify(error));
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({ profile: data ?? null });
  } catch (err: unknown) {
    console.error("[Profile API] GET error:", err);
    return NextResponse.json({ error: errorMessage(err) }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json();

    const gender = GENDERS.includes(body.gender_filter) ? body.gender_filter : "unisex";
    const bodyType = clean(body.body_type, BODY_TYPES);
    const sizeRange = clean(body.size_range, SIZES);
    const brands = Array.isArray(body.preferred_brands)
      ? body.preferred_brands.filter((b: unknown) => typeof b === "string" && b.trim()).slice(0, 20)
      : [];

    // Email comes from Clerk, not the request body.
    const user = await currentUser();
    const email = user?.primaryEmailAddress?.emailAddress ?? "";

    const supabase = getSupabaseAdmin();
    const { error } = await supabase.from("users").upsert(
      {
        id: userId,
        email,
        gender_filter: gender,
        body_type: bodyType,
        size_range: sizeRange,
        preferred_brands: brands,
      },
      // Upsert, not insert: both sign-in and sign-up route through onboarding, so a
      // returning user hits this every time. A plain insert raised a duplicate-key error
      // on the TEXT primary key and left them stuck on the form.
      { onConflict: "id" }
    );

    if (error) {
      console.error("[Profile API] Upsert error:", JSON.stringify(error));
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({ success: true });
  } catch (err: unknown) {
    console.error("[Profile API] POST error:", err);
    return NextResponse.json({ error: errorMessage(err) }, { status: 500 });
  }
}
