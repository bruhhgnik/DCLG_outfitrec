"use client";

import Link from "next/link";
import Image from "next/image";
import { Product } from "@/types";
import { useState } from "react";

interface ProductCardProps {
  product: Product;
  showScore?: number;
}

export default function ProductCard({ product, showScore }: ProductCardProps) {
  const [imageError, setImageError] = useState(false);

  // Get image URL (now stored as full URL in database)
  const getImageUrl = () => {
    if (imageError || !product.image_url) {
      return "/placeholder.svg";
    }
    return product.image_url;
  };

  return (
    <Link href={`/product/${product.sku_id}`} className="group block">
      <div className="relative aspect-square bg-gray-50 overflow-hidden rounded">
        <Image
          src={getImageUrl()}
          alt={product.title || product.type}
          fill
          className="object-contain p-2 sm:p-4 group-hover:scale-105 transition-transform duration-300"
          onError={() => setImageError(true)}
          sizes="(max-width: 640px) 45vw, (max-width: 1024px) 30vw, 23vw"
        />
        {showScore !== undefined && (
          <div className="absolute top-2 right-2 bg-black text-white text-xs px-2 py-1 font-medium">
            {Math.round(showScore * 100)}% Match
          </div>
        )}
      </div>
      <div className="mt-3 space-y-1">
        <p className="text-xs text-gray-500 uppercase tracking-wide">{product.brand || "Unknown Brand"}</p>
        <h3 className="text-sm font-medium truncate">{product.title || product.type}</h3>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span>{product.primary_color || "Multi"}</span>
          <span>•</span>
          <span>{product.functional_slot}</span>
        </div>
      </div>
    </Link>
  );
}
