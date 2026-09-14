/**
 * Extract a human-readable message from an unknown thrown value.
 *
 * `catch` bindings are `unknown` rather than `any` so that reading `.message` off a thrown
 * string, or a rejected promise carrying a plain object, is a compile error instead of
 * `undefined` leaking into a user-facing toast.
 */
export function errorMessage(err: unknown, fallback = "Something went wrong"): string {
  if (err instanceof Error && err.message) return err.message;
  if (typeof err === "string" && err) return err;
  if (err && typeof err === "object" && "message" in err) {
    const message = (err as { message: unknown }).message;
    if (typeof message === "string" && message) return message;
  }
  return fallback;
}

/** True for the DOMException an AbortSignal.timeout() raises. */
export function isTimeoutError(err: unknown): boolean {
  return (
    typeof err === "object" &&
    err !== null &&
    "name" in err &&
    ((err as { name: unknown }).name === "TimeoutError" ||
      (err as { name: unknown }).name === "AbortError")
  );
}
