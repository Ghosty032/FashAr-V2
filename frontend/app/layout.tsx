import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "sonner";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const viewport: Viewport = {
  themeColor: "#ffffff",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export const metadata: Metadata = {
  title: "FashAr | AI-Powered Personal Stylist",
  description: "Ditch outfit anxiety. Get immediate, objective feedback on your outfit and discover the exact missing piece to complete your look running on a 122B parameter vision model.",
  keywords: ["AI Stylist", "Fashion AI", "Outfit Checker", "Personal Styling", "Generative AI Fashion"],
  authors: [{ name: "FashAr Team" }],
  openGraph: {
    title: "FashAr | AI-Powered Personal Stylist",
    description: "Upload a mirror selfie. Our 100B+ parameter vision model analyzes silhouette, palette, and proportions in seconds.",
    url: "https://fashar.app",
    siteName: "FashAr",
    images: [
      {
        url: "/og-image.jpg", // Placeholder - user can add actual image later
        width: 1200,
        height: 630,
        alt: "FashAr - AI Personal Stylist",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "FashAr | AI-Powered Personal Stylist",
    description: "Get immediate, objective feedback on your outfit and discover the exact missing piece to complete your look.",
    images: ["/og-image.jpg"],
  },
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
        elements: {
          formButtonPrimary: "dark:!bg-white dark:!text-black dark:hover:!bg-gray-200 transition-colors",
        },
        variables: {
          colorPrimary: '#000000',
        }
      }}
    >
      <html lang="en" suppressHydrationWarning>
        <body className={`${inter.className} min-h-screen bg-gray-50 dark:bg-black text-gray-900 dark:text-gray-100 transition-colors duration-300`}>
          <ThemeProvider
            attribute="class"
            defaultTheme="system"
            enableSystem
            disableTransitionOnChange
          >
            {children}
            <Toaster position="top-center" richColors closeButton theme="system" />
          </ThemeProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}
