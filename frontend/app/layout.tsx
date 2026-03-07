import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "sonner";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "FashAr | AI-Powered Personal Stylist",
  description: "Eliminate outfit anxiety. Get instant, constructive feedback on what you're wearing.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider
      appearance={{
        layout: {
          socialButtonsVariant: 'iconButton',
        },
        variables: {
          colorPrimary: '#000000',
        }
      }}
    >
      <html lang="en">
        <body className={`${inter.className} min-h-screen bg-gray-50 text-gray-900`}>
          {children}
          <Toaster position="top-center" richColors closeButton />
        </body>
      </html>
    </ClerkProvider>
  );
}
