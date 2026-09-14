import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import { errorMessage } from "@/lib/errors";

/**
 * DELETE /api/history/[id] — Delete a specific history record
 *
 * Service-role client, so the .eq("user_id", userId) below is load-bearing: without it
 * this would delete any row by id regardless of owner.
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
    const supabase = getSupabaseAdmin();
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
  } catch (err: unknown) {
    console.error("[History API] DELETE error:", err);
    return NextResponse.json({ error: errorMessage(err) }, { status: 500 });
  }
}

