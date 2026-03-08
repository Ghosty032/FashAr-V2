import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { createClerkSupabaseClient } from "@/lib/supabase";

/**
 * DELETE /api/history/[id] — Delete a specific history record
 */
export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { userId, getToken } = await auth();
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const token = await getToken({ template: "supabase" });
    if (!token) {
      return NextResponse.json({ error: "Auth token unavailable" }, { status: 401 });
    }

    const { id } = await params;
    const supabase = createClerkSupabaseClient(token);

    const { error } = await supabase
      .from("wardrobe_history")
      .delete()
      .eq("id", id);

    if (error) {
      console.error("[History API] Delete error:", error);
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({ success: true });
  } catch (err: any) {
    console.error("[History API] DELETE error:", err);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
