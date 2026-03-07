import { SignUp } from "@clerk/nextjs";

export default function Page() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50 px-4">
      <div className="w-full max-w-md space-y-8 flex flex-col items-center">
        <div className="text-center">
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900 tracking-tight leading-tight">
            Create your account
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Join FASHR and eliminate outfit anxiety
          </p>
        </div>
        <SignUp routing="path" path="/sign-up" signInUrl="/sign-in" forceRedirectUrl="/onboarding" />
      </div>
    </div>
  );
}
