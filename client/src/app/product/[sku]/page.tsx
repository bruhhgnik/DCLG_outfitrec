import { notFound } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { Metadata } from "next";
import { getProduct } from "@/lib/api";
import LooksSection from "@/components/LooksSection";

interface ProductPageProps {
  params: Promise<{ sku: string }>;
}

// Dynamic metadata for SEO
export async function generateMetadata({ params }: ProductPageProps): Promise<Metadata> {
  const { sku } = await params;

  try {
    const product = await getProduct(sku);
    const title = product.title || product.type;
    const brand = product.brand || "Unknown Brand";
    const description = `Shop ${title} by ${brand}. ${product.category} in ${product.primary_color || "various colors"}. Perfect for ${product.occasion?.slice(0, 2).join(", ") || "everyday wear"}. Free styling recommendations included.`;

    return {
      title: `${title} | ${brand} | Outfit Studio`,
      description,
      keywords: [
        product.type,
        product.category,
        brand,
        product.primary_color,
        ...(product.fashion_aesthetics || []),
        ...(product.occasion || []),
      ].filter(Boolean).join(", "),
      openGraph: {
        title: `${title} by ${brand}`,
        description,
        type: "website",
        images: product.image_url ? [
          {
            url: product.image_url,
            width: 800,
            height: 800,
            alt: title,
          }
        ] : [],
      },
      twitter: {
        card: "summary_large_image",
        title: `${title} by ${brand}`,
        description,
        images: product.image_url ? [product.image_url] : [],
      },
      robots: {
        index: true,
        follow: true,
      },
    };
  } catch {
    return {
      title: "Product Not Found | Outfit Studio",
      description: "The requested product could not be found.",
    };
  }
}

// JSON-LD structured data for rich snippets
function ProductJsonLd({ product }: { product: any }) {
  const structuredData = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.title || product.type,
    description: `${product.type} by ${product.brand || "Unknown Brand"} in ${product.primary_color || "various colors"}`,
    image: product.image_url,
    brand: {
      "@type": "Brand",
      name: product.brand || "Unknown Brand",
    },
    color: product.primary_color,
    category: product.category,
    audience: {
      "@type": "PeopleAudience",
      suggestedGender: product.gender?.toLowerCase(),
    },
    additionalProperty: [
      {
        "@type": "PropertyValue",
        name: "Style",
        value: product.fashion_aesthetics?.join(", "),
      },
      {
        "@type": "PropertyValue",
        name: "Occasion",
        value: product.occasion?.join(", "),
      },
      {
        "@type": "PropertyValue",
        name: "Season",
        value: product.season?.join(", "),
      },
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
    />
  );
}

export default async function ProductPage({ params }: ProductPageProps) {
  const { sku } = await params;

  let product;
  try {
    product = await getProduct(sku);
  } catch {
    notFound();
  }

  const imageUrl = product.image_url || "/placeholder.svg";

  // Breadcrumb structured data
  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "Home",
        item: process.env.NEXT_PUBLIC_SITE_URL || "https://example.com",
      },
      {
        "@type": "ListItem",
        position: 2,
        name: "Products",
        item: `${process.env.NEXT_PUBLIC_SITE_URL || "https://example.com"}/products`,
      },
      {
        "@type": "ListItem",
        position: 3,
        name: product.title || product.type,
        item: `${process.env.NEXT_PUBLIC_SITE_URL || "https://example.com"}/product/${sku}`,
      },
    ],
  };

  return (
    <>
      {/* Structured Data */}
      <ProductJsonLd product={product} />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }}
      />

      <div className="max-w-6xl mx-auto px-3 sm:px-4 py-4 sm:py-6">
        {/* Breadcrumb */}
        <nav className="text-xs sm:text-sm text-gray-500 mb-4 sm:mb-6" aria-label="Breadcrumb">
          <Link href="/" className="hover:text-black">
            Home
          </Link>
          <span className="mx-1.5 sm:mx-2">/</span>
          <Link href="/products" className="hover:text-black">
            Products
          </Link>
          <span className="mx-1.5 sm:mx-2">/</span>
          <span className="text-black line-clamp-1">{product.title || product.type}</span>
        </nav>

      {/* Product Details */}
      <div className="flex flex-col md:flex-row gap-4 sm:gap-6 lg:gap-8 mb-8 sm:mb-12">
        {/* Image */}
        <div className="w-full md:w-2/5 lg:w-1/2 flex-shrink-0">
          <div className="aspect-square max-h-[40vh] sm:max-h-[45vh] md:max-h-[50vh] bg-gray-50 relative mx-auto rounded-lg overflow-hidden">
            <Image
              src={imageUrl}
              alt={product.title || product.type}
              fill
              className="object-contain p-3 sm:p-4 md:p-6"
              priority
              sizes="(max-width: 768px) 100vw, 40vw"
            />
          </div>
        </div>

        {/* Info */}
        <div className="w-full md:w-3/5 lg:w-1/2 flex flex-col">
          <p className="text-xs sm:text-sm text-gray-500 uppercase tracking-wide mb-1 sm:mb-2">
            {product.brand || "Unknown Brand"}
          </p>
          <h1 className="text-lg sm:text-xl lg:text-2xl font-light mb-3 sm:mb-4">
            {product.title || product.type}
          </h1>

          {/* Quick Details */}
          <div className="space-y-2 sm:space-y-2.5 py-3 sm:py-4 border-t border-b border-gray-200 text-xs sm:text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Category</span>
              <span>{product.category}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Type</span>
              <span>{product.functional_slot}</span>
            </div>
            {product.primary_color && (
              <div className="flex justify-between">
                <span className="text-gray-500">Color</span>
                <span className="flex items-center gap-1.5 sm:gap-2">
                  <span
                    className="w-3 h-3 sm:w-4 sm:h-4 rounded-full border border-gray-200"
                    style={{ backgroundColor: product.primary_color.toLowerCase() }}
                  />
                  {product.primary_color}
                </span>
              </div>
            )}
            {product.style && (
              <div className="flex justify-between">
                <span className="text-gray-500">Style</span>
                <span>{product.style}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-500">Gender</span>
              <span>{product.gender}</span>
            </div>
            {product.formality_level && (
              <div className="flex justify-between">
                <span className="text-gray-500">Formality</span>
                <span>{product.formality_level}</span>
              </div>
            )}
          </div>

          {/* Tags */}
          <div className="mt-3 sm:mt-4">
            {product.occasion.length > 0 && (
              <div className="mb-3">
                <p className="text-[10px] sm:text-xs text-gray-500 uppercase tracking-wide mb-1.5 sm:mb-2">Occasion</p>
                <div className="flex flex-wrap gap-1.5 sm:gap-2">
                  {product.occasion.map((occ) => (
                    <span
                      key={occ}
                      className="px-2 sm:px-2.5 py-0.5 sm:py-1 text-[10px] sm:text-xs border border-gray-200 rounded-full"
                    >
                      {occ}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {product.season.length > 0 && (
              <div className="mb-3">
                <p className="text-[10px] sm:text-xs text-gray-500 uppercase tracking-wide mb-1.5 sm:mb-2">Season</p>
                <div className="flex flex-wrap gap-1.5 sm:gap-2">
                  {product.season.map((s) => (
                    <span
                      key={s}
                      className="px-2 sm:px-2.5 py-0.5 sm:py-1 text-[10px] sm:text-xs border border-gray-200 rounded-full"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {product.fashion_aesthetics.length > 0 && (
              <div>
                <p className="text-[10px] sm:text-xs text-gray-500 uppercase tracking-wide mb-1.5 sm:mb-2">Aesthetics</p>
                <div className="flex flex-wrap gap-1.5 sm:gap-2">
                  {product.fashion_aesthetics.map((aesthetic) => (
                    <span
                      key={aesthetic}
                      className="px-2 sm:px-2.5 py-0.5 sm:py-1 text-[10px] sm:text-xs bg-gray-100 rounded-full"
                    >
                      {aesthetic}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

        {/* Curated Looks Section */}
        <section className="border-t border-gray-200 pt-4 sm:pt-6">
          <LooksSection baseProduct={product} />
        </section>
      </div>
    </>
  );
}
