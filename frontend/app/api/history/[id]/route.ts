import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

/**
 * DELETE /api/history/[id] — Delete a specific history record
 */
export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { id } = await params;

    // Only delete if the record belongs to this user
    const { error } = await supabase
      .from("wardrobe_history")
      .delete()
      .eq("id", id)
      .eq("user_id", userId);

    if (error) {
      console.error("[History API] Delete error:", JSON.stringify(error));
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({ success: true });
  } catch (err: any) {
    console.error("[History API] DELETE error:", err);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

