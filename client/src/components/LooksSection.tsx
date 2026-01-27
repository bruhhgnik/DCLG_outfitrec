"use client";

import { useState, useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Product, Look, LookItem } from "@/types";
import { generateLooks } from "@/lib/api";
import { useCart } from "@/context/CartContext";

interface LooksSectionProps {
  baseProduct: Product;
}

export default function LooksSection({ baseProduct }: LooksSectionProps) {
  const [animatingLook, setAnimatingLook] = useState<{ id: string; count: number } | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const { addLookToCart } = useCart();

  const {
    data,
    isLoading: loading,
    error,
  } = useQuery({
    queryKey: ["looks", baseProduct.sku_id],
    queryFn: () => generateLooks(baseProduct.sku_id, 10),
    staleTime: 5 * 60 * 1000, // Cache looks for 5 minutes
  });

  const looks = data?.looks ?? [];

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

  // Get all items in a look for adding to cart
  const getAllLookItems = (look: Look): LookItem[] => {
    return Object.values(look.items);
  };

  const handleGetThisLook = (look: Look, lookIndex: number) => {
    const allItems = getAllLookItems(look);

    // Trigger animation
    setAnimatingLook({ id: look.id, count: allItems.length });

    // Add items to cart
    addLookToCart(look.id, `Look ${lookIndex + 1}`, allItems);

    // Clear animation after 800ms
    setTimeout(() => {
      setAnimatingLook(null);
    }, 800);
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
            <div key={i} className="flex-shrink-0 w-[280px] sm:w-[420px] lg:w-[520px] min-h-[280px] sm:min-h-[320px] bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error || (!loading && looks.length === 0)) {
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
          const isAnimating = animatingLook?.id === look.id;

          return (
            <div
              key={look.id}
              className="flex-shrink-0 w-[280px] sm:w-[420px] lg:w-[520px] bg-white border border-gray-200 rounded-lg p-3 sm:p-4 lg:p-5 relative"
              style={{ scrollSnapAlign: "start" }}
            >
              {/* Look Header */}
              <h3 className="text-sm sm:text-base font-medium mb-3 sm:mb-4">Look {index + 1}</h3>

              {/* Content wrapper with blur effect */}
              <div className={`transition-all duration-200 ${isAnimating ? "blur-sm" : ""}`}>
                <div className="flex gap-3 sm:gap-4 lg:gap-5 items-start">
                  {/* Left: Base Product Image */}
                  <div className="w-[100px] sm:w-[140px] lg:w-[160px] flex-shrink-0">
                    <div className="relative bg-gray-100 rounded-lg aspect-[3/4] overflow-hidden">
                      <Image
                        src={baseProduct.image_url || "/placeholder.svg"}
                        alt={baseProduct.title || baseProduct.type}
                        fill
                        className="object-contain p-2 sm:p-3"
                        sizes="(max-width: 640px) 100px, (max-width: 1024px) 140px, 160px"
                      />
                    </div>
                    <p className="mt-2 text-[10px] sm:text-xs text-gray-700 line-clamp-2">
                      {baseProduct.title || baseProduct.type}
                    </p>
                  </div>

                  {/* Right: Outfit Items List */}
                  <div className="flex-1 space-y-2 sm:space-y-2.5">
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

              {/* Added to Cart Overlay */}
              {isAnimating && (
                <div className="absolute inset-0 flex items-center justify-center bg-white/60 animate-fade-in">
                  <div className="bg-black text-white px-4 py-2 rounded text-sm font-medium animate-scale-in">
                    {animatingLook.count} items added to cart
                  </div>
                </div>
              )}

              {/* Get This Look Button */}
              <button
                onClick={() => handleGetThisLook(look, index)}
                disabled={isAnimating}
                className="w-full mt-4 py-2.5 sm:py-3 bg-black text-white text-xs sm:text-sm font-medium hover:bg-gray-800 transition-colors disabled:opacity-50"
              >
                Get This Look
              </button>
            </div>
          );
        })}
      </div>

      {/* Custom scrollbar hide style and animations */}
      <style jsx>{`
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
        .scrollbar-hide {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        @keyframes fade-in {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }
        @keyframes scale-in {
          from {
            opacity: 0;
            transform: scale(0.9);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }
        .animate-fade-in {
          animation: fade-in 0.2s ease-out forwards;
        }
        .animate-scale-in {
          animation: scale-in 0.2s ease-out forwards;
        }
      `}</style>
    </div>
  );
}
