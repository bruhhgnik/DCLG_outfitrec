"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { Product, CompatibleItem } from "@/types";
import { generateOutfit, scoreOutfit } from "@/lib/api";

interface OutfitBuilderProps {
  baseProduct: Product;
}

const SLOT_ORDER = ["Outerwear", "Base Top", "Primary Bottom", "Secondary Bottom", "Footwear", "Accessory"];
const SLOT_LABELS: Record<string, string> = {
  "Base Top": "Top",
  "Outerwear": "Outerwear",
  "Primary Bottom": "Bottom",
  "Secondary Bottom": "Socks/Layers",
  "Footwear": "Shoes",
  "Accessory": "Accessory",
};

export default function OutfitBuilder({ baseProduct }: OutfitBuilderProps) {
  const [recommendations, setRecommendations] = useState<Record<string, CompatibleItem[]>>({});
  const [selectedItems, setSelectedItems] = useState<Record<string, CompatibleItem | null>>({});
  const [outfitScore, setOutfitScore] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchRecommendations() {
      try {
        setLoading(true);
        const result = await generateOutfit(baseProduct.sku_id, {
          limit_per_slot: 6,
          min_score: 0.5,
        });
        setRecommendations(result.recommendations);

        // Auto-select top item from each slot
        const autoSelected: Record<string, CompatibleItem | null> = {};
        Object.entries(result.recommendations).forEach(([slot, items]) => {
          if (items.length > 0) {
            autoSelected[slot] = items[0];
          }
        });
        setSelectedItems(autoSelected);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load recommendations");
      } finally {
        setLoading(false);
      }
    }

    fetchRecommendations();
  }, [baseProduct.sku_id]);

  // Calculate outfit score when selection changes
  useEffect(() => {
    async function calculateScore() {
      const skuIds = [
        baseProduct.sku_id,
        ...Object.values(selectedItems)
          .filter((item): item is CompatibleItem => item !== null)
          .map((item) => item.sku_id),
      ];

      if (skuIds.length >= 2) {
        try {
          const result = await scoreOutfit(skuIds);
          setOutfitScore(result.average_score);
        } catch {
          setOutfitScore(null);
        }
      } else {
        setOutfitScore(null);
      }
    }

    calculateScore();
  }, [selectedItems, baseProduct.sku_id]);

  const getImageUrl = (item: CompatibleItem) => {
    return item.product?.image_url || "/placeholder.svg";
  };

  const handleSelectItem = (slot: string, item: CompatibleItem | null) => {
    setSelectedItems((prev) => ({ ...prev, [slot]: item }));
  };

  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-48 mb-6"></div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="aspect-square bg-gray-100 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-500">{error}</p>
      </div>
    );
  }

  const availableSlots = SLOT_ORDER.filter(
    (slot) => slot !== baseProduct.functional_slot && recommendations[slot]?.length > 0
  );

  return (
    <div>
      {/* Outfit Score Banner */}
      {outfitScore !== null && (
        <div className="mb-6 p-4 bg-black text-white flex items-center justify-between">
          <span className="text-sm uppercase tracking-wide">Outfit Compatibility Score</span>
          <span className="text-2xl font-bold">{Math.round(outfitScore * 100)}%</span>
        </div>
      )}

      {/* Selected Outfit Overview */}
      <div className="mb-8">
        <h3 className="text-sm font-medium uppercase tracking-wide mb-4">Your Complete Look</h3>
        <div className="flex gap-2 sm:gap-3 overflow-x-auto pb-2">
          {/* Base Product */}
          <div className="flex-shrink-0 w-16 sm:w-20 md:w-24">
            <div className="aspect-square bg-gray-100 relative border-2 border-black rounded">
              <Image
                src={baseProduct.image_url || "/placeholder.svg"}
                alt={baseProduct.title || baseProduct.type}
                fill
                className="object-contain p-1 sm:p-2"
                sizes="96px"
              />
            </div>
            <p className="text-[10px] sm:text-xs text-center mt-1 truncate">Base Item</p>
          </div>

          {/* Selected Items */}
          {availableSlots.map((slot) => {
            const selected = selectedItems[slot];
            return (
              <div key={slot} className="flex-shrink-0 w-16 sm:w-20 md:w-24">
                {selected ? (
                  <Link href={`/product/${selected.sku_id}`}>
                    <div className="aspect-square bg-gray-50 relative border border-gray-200 hover:border-black transition-colors rounded">
                      <Image
                        src={getImageUrl(selected)}
                        alt={selected.product?.title || ""}
                        fill
                        className="object-contain p-1 sm:p-2"
                        sizes="96px"
                      />
                      <div className="absolute bottom-0 right-0 bg-black text-white text-[8px] sm:text-[10px] px-1">
                        {Math.round(selected.score * 100)}%
                      </div>
                    </div>
                  </Link>
                ) : (
                  <div className="aspect-square bg-gray-50 border border-dashed border-gray-300 flex items-center justify-center rounded">
                    <span className="text-gray-400 text-xs">+</span>
                  </div>
                )}
                <p className="text-[10px] sm:text-xs text-center mt-1 truncate text-gray-500">
                  {SLOT_LABELS[slot] || slot}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recommendations by Slot */}
      <div className="space-y-8">
        {availableSlots.map((slot) => {
          const items = recommendations[slot] || [];
          const selected = selectedItems[slot];

          return (
            <div key={slot}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium uppercase tracking-wide">
                  {SLOT_LABELS[slot] || slot}
                </h3>
                {selected && (
                  <button
                    onClick={() => handleSelectItem(slot, null)}
                    className="text-xs text-gray-500 hover:text-black"
                  >
                    Clear
                  </button>
                )}
              </div>

              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2 sm:gap-3">
                {items.map((item) => {
                  const isSelected = selected?.sku_id === item.sku_id;
                  return (
                    <button
                      key={item.sku_id}
                      onClick={() => handleSelectItem(slot, isSelected ? null : item)}
                      className={`group text-left ${isSelected ? "ring-2 ring-black rounded" : ""}`}
                    >
                      <div className="aspect-square bg-gray-50 relative overflow-hidden rounded">
                        <Image
                          src={getImageUrl(item)}
                          alt={item.product?.title || ""}
                          fill
                          className="object-contain p-1 sm:p-2 group-hover:scale-105 transition-transform"
                          sizes="(max-width: 640px) 30vw, (max-width: 1024px) 20vw, 15vw"
                        />
                        <div className="absolute top-0.5 right-0.5 sm:top-1 sm:right-1 bg-black/80 text-white text-[8px] sm:text-[10px] px-1 py-0.5 rounded">
                          {Math.round(item.score * 100)}%
                        </div>
                      </div>
                      <p className="text-[10px] sm:text-xs mt-1 truncate">{item.product?.brand || "Brand"}</p>
                      <p className="text-[9px] sm:text-[10px] text-gray-500 truncate">
                        {item.product?.title || item.product?.type || "Product"}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {availableSlots.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No compatible items found for this product.</p>
        </div>
      )}
    </div>
  );
}
