"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Product } from "@/types";
import { searchProducts } from "@/lib/api";
import ProductGrid from "@/components/ProductGrid";
import LoadingSpinner from "@/components/LoadingSpinner";

function SearchContent() {
  const searchParams = useSearchParams();
  const query = searchParams.get("q") || "";

  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [count, setCount] = useState(0);

  useEffect(() => {
    async function search() {
      if (!query.trim()) {
        setProducts([]);
        setCount(0);
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const response = await searchProducts(query, 50);
        setProducts(response.items);
        setCount(response.count);
      } catch (error) {
        console.error("Search failed:", error);
        setProducts([]);
        setCount(0);
      } finally {
        setLoading(false);
      }
    }

    search();
  }, [query]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-light">
          {query ? `Search: "${query}"` : "Search"}
        </h1>
        {!loading && query && (
          <p className="text-sm text-gray-500 mt-2">
            {count} {count === 1 ? "result" : "results"} found
          </p>
        )}
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : !query.trim() ? (
        <div className="text-center py-16">
          <p className="text-gray-500">Enter a search term to find products</p>
        </div>
      ) : products.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-gray-500">No products found for &quot;{query}&quot;</p>
          <p className="text-sm text-gray-400 mt-2">
            Try a different search term or browse our categories
          </p>
        </div>
      ) : (
        <ProductGrid products={products} />
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <SearchContent />
    </Suspense>
  );
}
