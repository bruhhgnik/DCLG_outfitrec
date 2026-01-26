"use client";

import { useState, useEffect, useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import { Product, Look, LooksResponse } from "@/types";
import { generateLooks } from "@/lib/api";

interface LooksSectionProps {
  baseProduct: Product;
}

export default function LooksSection({ baseProduct }: LooksSectionProps) {
  const [looks, setLooks] = useState<Look[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function fetchLooks() {
      try {
        setLoading(true);
        setError(null);
        const result: LooksResponse = await generateLooks(baseProduct.sku_id, 10);
        setLooks(result.looks);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load looks");
      } finally {
        setLoading(false);
      }
    }

    fetchLooks();
  }, [baseProduct.sku_id]);

  const scrollLeft = () => {
    if (scrollContainerRef.current) {
      const scrollAmount = window.innerWidth < 640 ? 300 : 450;
      scrollContainerRef.current.scrollBy({ left: -scrollAmount, behavior: "smooth" });
    }
  };

  const scrollRight = () => {
    if (scrollContainerRef.current) {
      const scrollAmount = window.innerWidth < 640 ? 300 : 450;
      scrollContainerRef.current.scrollBy({ left: scrollAmount, behavior: "smooth" });
    }
  };

  // Get items excluding the base product, ordered by slot
  // Order: Bottom → Footwear → Outerwear → Accessory
  const getOutfitItems = (look: Look) => {
    const slotOrder = ["primary bottom", "footwear", "outerwear", "base top", "accessory"];
    const items: Array<{ slot: string; item: Look["items"][string] }> = [];

    for (const slot of slotOrder) {
      if (look.items[slot] && look.items[slot].sku_id !== baseProduct.sku_id) {
        items.push({ slot, item: look.items[slot] });
      }
    }
    return items;
  };

  if (loading) {
    return (
      <div className="mt-8 sm:mt-10">
        <div className="flex items-center justify-between mb-4 sm:mb-5">
          <div>
            <h2 className="text-lg sm:text-xl font-semibold">Curated For You</h2>
            <p className="text-gray-500 text-xs sm:text-sm">Finest Trends. Curated Brands</p>
          </div>
        </div>
        <div className="flex gap-3 overflow-hidden">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex-shrink-0 w-[280px] sm:w-[420px] lg:w-[520px] h-[320px] sm:h-[380px] bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error || looks.length === 0) {
    return null;
  }

  return (
    <div className="mt-8 sm:mt-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 sm:mb-5">
        <div>
          <h2 className="text-lg sm:text-xl font-semibold">Curated For You</h2>
          <p className="text-gray-500 text-xs sm:text-sm">Finest Trends. Curated Brands</p>
        </div>
        <div className="flex gap-1.5 sm:gap-2">
          <button
            onClick={scrollLeft}
            className="w-8 h-8 sm:w-9 sm:h-9 flex items-center justify-center border border-gray-300 rounded hover:bg-gray-50 transition-colors"
          >
            <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button
            onClick={scrollRight}
            className="w-8 h-8 sm:w-9 sm:h-9 flex items-center justify-center border border-gray-300 rounded hover:bg-gray-50 transition-colors"
          >
            <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>

      {/* Scrollable Looks Container */}
      <div
        ref={scrollContainerRef}
        className="flex gap-3 sm:gap-4 overflow-x-auto scrollbar-hide pb-4 -mx-4 px-4"
        style={{ scrollSnapType: "x mandatory" }}
      >
        {looks.map((look, index) => {
          const outfitItems = getOutfitItems(look);

          return (
            <div
              key={look.id}
              className="flex-shrink-0 w-[280px] sm:w-[420px] lg:w-[520px] bg-white border border-gray-200 rounded-lg p-3 sm:p-4 lg:p-5"
              style={{ scrollSnapAlign: "start" }}
            >
              {/* Look Header */}
              <h3 className="text-sm sm:text-base font-medium mb-3 sm:mb-4">Look {index + 1}</h3>

              <div className="flex gap-3 sm:gap-4 lg:gap-5">
                {/* Left: Base Product Image */}
                <div className="w-[100px] sm:w-[160px] lg:w-[200px] flex-shrink-0">
                  <div className="relative bg-gray-100 rounded-lg aspect-[3/4]">
                    {/* Pin Icon */}
                    <button className="absolute top-2 right-2 z-10 w-6 h-6 sm:w-7 sm:h-7 bg-gray-800 hover:bg-black rounded-full flex items-center justify-center transition-colors">
                      <svg className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                      </svg>
                    </button>
                    <Image
                      src={baseProduct.image_url || "/placeholder.svg"}
                      alt={baseProduct.title || baseProduct.type}
                      fill
                      className="object-contain p-2 sm:p-3"
                      sizes="(max-width: 640px) 100px, (max-width: 1024px) 160px, 200px"
                    />
                  </div>
                  <p className="mt-2 text-[10px] sm:text-xs text-gray-700 line-clamp-2">
                    {baseProduct.title || baseProduct.type}
                  </p>
                </div>

                {/* Right: Outfit Items List */}
                <div className="flex-1 space-y-2 sm:space-y-2.5 overflow-y-auto max-h-[200px] sm:max-h-[280px] lg:max-h-[300px]">
                  {outfitItems.map(({ item }) => (
                    <Link
                      key={item.sku_id}
                      href={`/product/${item.sku_id}`}
                      className="flex gap-2 sm:gap-3 group"
                    >
                      {/* Item Thumbnail */}
                      <div className="w-[48px] h-[48px] sm:w-[56px] sm:h-[56px] lg:w-[64px] lg:h-[64px] flex-shrink-0 bg-gray-50 rounded border border-gray-100 relative overflow-hidden">
                        <Image
                          src={item.image_url || "/placeholder.svg"}
                          alt={item.title}
                          fill
                          className="object-contain p-1 group-hover:scale-105 transition-transform"
                          sizes="64px"
                        />
                      </div>
                      {/* Item Info */}
                      <div className="flex-1 min-w-0 py-0.5">
                        <p className="text-[11px] sm:text-xs lg:text-sm font-medium text-gray-900 line-clamp-2 group-hover:underline leading-tight">
                          {item.title}
                        </p>
                        <p className="text-[10px] sm:text-xs text-gray-500 mt-0.5">{item.brand}</p>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Custom scrollbar hide style */}
      <style jsx>{`
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
        .scrollbar-hide {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
      `}</style>
    </div>
  );
}
