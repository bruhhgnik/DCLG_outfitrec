import type { Metadata, Viewport } from "next";
import "./globals.css";
import Header from "@/components/Header";
import { CartProvider } from "@/context/CartContext";
import QueryProvider from "@/providers/QueryProvider";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Outfit Studio | AI-Powered Style Recommendations",
    template: "%s | Outfit Studio",
  },
  description:
    "Discover perfectly coordinated outfits with AI-powered recommendations. Get personalized style suggestions and complete looks for any occasion.",
  keywords: [
    "outfit recommendations",
    "AI fashion",
    "style guide",
    "outfit builder",
    "fashion AI",
    "wardrobe coordinator",
    "outfit ideas",
    "fashion recommendations",
  ],
  authors: [{ name: "Outfit Studio" }],
  creator: "Outfit Studio",
  publisher: "Outfit Studio",
  openGraph: {
    type: "website",
    locale: "en_US",
    url: SITE_URL,
    siteName: "Outfit Studio",
    title: "Outfit Studio | AI-Powered Style Recommendations",
    description:
      "Discover perfectly coordinated outfits with AI-powered recommendations. Get personalized style suggestions and complete looks for any occasion.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Outfit Studio - AI-Powered Fashion",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Outfit Studio | AI-Powered Style Recommendations",
    description:
      "Discover perfectly coordinated outfits with AI-powered recommendations.",
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  verification: {
    // Add your verification codes here
    // google: "your-google-verification-code",
    // yandex: "your-yandex-verification-code",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#ffffff",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap" rel="stylesheet" />
      </head>
      <body className="antialiased min-h-screen uppercase" style={{ fontFamily: "'Inter', sans-serif" }}>
        <QueryProvider>
          <CartProvider>
            <Header />
            <main>{children}</main>
            <footer className="border-t border-gray-200 mt-16 py-8">
              <div className="px-4 sm:px-8 lg:px-16 xl:px-24 text-center text-sm text-gray-500">
                <p>Outfit Studio - AI-Powered Fashion Recommendations</p>
              </div>
            </footer>
          </CartProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
