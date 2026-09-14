"use client";

import { useState, useEffect } from "react";
import { useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { errorMessage } from "@/lib/errors";

export default function Onboarding() {
  const { user } = useUser();
  const router = useRouter();

  const [gender, setGender] = useState("unisex");
  const [bodyType, setBodyType] = useState<string[]>([]);
  const [sizeRange, setSizeRange] = useState<string[]>([]);
  const [brands, setBrands] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  // Sign-in and sign-up both redirect here, so most visits are returning users. Load any
  // existing profile and prefill, rather than presenting an empty form they must redo.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/profile");
        if (!res.ok) return;
        const { profile } = await res.json();
        if (cancelled || !profile) return;
        setGender(profile.gender_filter ?? "unisex");
        setBodyType(profile.body_type ?? []);
        setSizeRange(profile.size_range ?? []);
        setBrands((profile.preferred_brands ?? []).join(", "));
      } catch {
        // A failed prefill is not worth blocking the form over.
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const bodyTypeOptions = ["slim", "regular", "athletic", "plus", "petite", "tall"];
  const sizeOptions = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL"];

  const toggleArrayItem = (item: string, currentArray: string[], setFunction: (val: string[]) => void) => {
    if (currentArray.includes(item)) {
      setFunction(currentArray.filter(i => i !== item));
    } else {
      setFunction([...currentArray, item]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    setIsSubmitting(true);
    setError("");

    try {
      // Saved server-side, where the Clerk session is verified. The id and email are taken
      // from that session, so they are not sent from here.
      const brandArray = brands.split(',').map(b => b.trim()).filter(b => b !== '');

      const res = await fetch("/api/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          gender_filter: gender,
          body_type: bodyType,
          size_range: sizeRange,
          preferred_brands: brandArray,
        }),
      });

      if (!res.ok) {
        const { error: msg } = await res.json().catch(() => ({ error: "" }));
        throw new Error(msg || "Failed to save profile.");
      }

      router.push("/");
    } catch (err: unknown) {
      console.error(err);
      setError(errorMessage(err, "Failed to save profile. Please try again."));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-xl mx-auto bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
        <div className="text-center mb-10">
          <h2 className="text-3xl font-bold tracking-tight text-gray-900">Build Your Style Profile</h2>
          <p className="mt-2 text-sm text-gray-500">
            Tell us about your sizing to ensure accurate product recommendations.
          </p>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 text-red-700 p-4 rounded-md text-sm border border-red-100">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          
          {/* Gender Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-3">Recommendation Focus</label>
            <div className="grid grid-cols-3 gap-3">
              {['mens', 'womens', 'unisex'].map((g) => (
                <button
                  type="button"
                  key={g}
                  onClick={() => setGender(g)}
                  className={`py-2 px-4 rounded-lg text-sm font-medium capitalize border transition-all ${
                    gender === g 
                    ? 'bg-black text-white border-black ring-2 ring-black ring-offset-1' 
                    : 'bg-white text-gray-700 border-gray-200 hover:border-gray-300'
                  }`}
                >
                  {g}
                </button>
              ))}
            </div>
          </div>

          {/* Body Type */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-3">Body Type (Select all that apply)</label>
            <div className="flex flex-wrap gap-2">
              {bodyTypeOptions.map((type) => (
                <button
                  type="button"
                  key={type}
                  onClick={() => toggleArrayItem(type, bodyType, setBodyType)}
                  className={`py-1.5 px-4 rounded-full text-sm font-medium capitalize border transition-all ${
                    bodyType.includes(type)
                    ? 'bg-black text-white border-black'
                    : 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>

          {/* Size Range */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-3">Typical Size Range</label>
            <div className="flex flex-wrap gap-2">
              {sizeOptions.map((size) => (
                <button
                  type="button"
                  key={size}
                  onClick={() => toggleArrayItem(size, sizeRange, setSizeRange)}
                  className={`py-1.5 px-4 rounded-full text-sm font-medium border transition-all ${
                    sizeRange.includes(size)
                    ? 'bg-black text-white border-black'
                    : 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100'
                  }`}
                >
                  {size}
                </button>
              ))}
            </div>
          </div>

          {/* Preferred Brands */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">Preferred Brands (Optional)</label>
            <p className="text-xs text-gray-500 mb-3">Comma separated (e.g., Uniqlo, Carhartt, COS)</p>
            <input
              type="text"
              value={brands}
              onChange={(e) => setBrands(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-black focus:ring-black sm:text-sm p-3 border"
              placeholder="Your favorite brands..."
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || isSubmitting || sizeRange.length === 0 || bodyType.length === 0}
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-black hover:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-black disabled:opacity-50 transition-colors"
          >
            {isLoading ? "Loading…" : isSubmitting ? "Saving Profile..." : "Complete Setup"}
          </button>
        </form>
      </div>
    </div>
  );
}
