import type { Metadata, Viewport } from "next";
import { Space_Mono } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";
import { CartProvider } from "@/context/CartContext";

const spaceMono = Space_Mono({
  weight: ["400", "700"],
  subsets: ["latin"],
  display: "swap",
});

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Culture Studio | AI-Powered Style Recommendations",
    template: "%s | Culture Studio",
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
  authors: [{ name: "Culture Studio" }],
  creator: "Culture Studio",
  publisher: "Culture Studio",
  openGraph: {
    type: "website",
    locale: "en_US",
    url: SITE_URL,
    siteName: "Culture Studio",
    title: "Culture Studio | AI-Powered Style Recommendations",
    description:
      "Discover perfectly coordinated outfits with AI-powered recommendations. Get personalized style suggestions and complete looks for any occasion.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Culture Studio - AI-Powered Fashion",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Culture Studio | AI-Powered Style Recommendations",
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
      <body className={`${spaceMono.className} antialiased min-h-screen uppercase`}>
        <CartProvider>
          <Header />
          <main className="sm:px-8 lg:px-16 xl:px-24">{children}</main>
          <footer className="border-t border-gray-200 mt-16 py-8">
            <div className="px-4 sm:px-8 lg:px-16 xl:px-24 text-center text-sm text-gray-500">
              <p>Culture Studio - AI-Powered Fashion Recommendations</p>
            </div>
          </footer>
        </CartProvider>
      </body>
    </html>
  );
}
