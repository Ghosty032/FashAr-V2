import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * Server-only Supabase client.
 *
 * This uses the service-role key, which bypasses Row-Level Security. That is deliberate
 * and it is what makes the lockdown in scripts/enable_rls.sql safe: RLS is enabled with
 * no policies on the app tables, so the public anon key (which ships to every browser
 * via its NEXT_PUBLIC_ prefix) can no longer read or write them at all.
 *
 * The consequence is that every query here is unrestricted, so authorization is entirely
 * the caller's job: verify the Clerk session first, then filter by that user's id on
 * every single read, write and delete. There is no second line of defence behind this.
 *
 * NEVER import this from a client component — it would leak the key into the bundle.
 */
let cached: SupabaseClient | null = null;

export function getSupabaseAdmin(): SupabaseClient {
  if (cached) return cached;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  // Built lazily rather than at module scope so a missing variable surfaces as a clear
  // runtime error on the one route that needs it, instead of failing the whole build.
  if (!url || !serviceRoleKey) {
    throw new Error(
      "Supabase is not configured: NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must both be set."
    );
  }

  cached = createClient(url, serviceRoleKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  return cached;
}
