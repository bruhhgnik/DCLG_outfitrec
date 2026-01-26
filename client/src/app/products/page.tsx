"use client";

import { useState, useEffect, useCallback, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Product } from "@/types";
import { getProducts, getCategories, getBrands, getColors } from "@/lib/api";
import ProductGrid from "@/components/ProductGrid";
import FilterSidebar from "@/components/FilterSidebar";
import LoadingSpinner from "@/components/LoadingSpinner";

const PAGE_SIZE = 24; // More products per batch for infinite scroll

function ProductsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [products, setProducts] = useState<Product[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [filtersLoading, setFiltersLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(false);

  const [categories, setCategories] = useState<string[]>([]);
  const [brands, setBrands] = useState<string[]>([]);
  const [colors, setColors] = useState<string[]>([]);

  const loaderRef = useRef<HTMLDivElement>(null);

  const selectedCategory = searchParams.get("category") || undefined;
  const selectedBrand = searchParams.get("brand") || undefined;
  const selectedColor = searchParams.get("color") || undefined;
  const selectedSlot = searchParams.get("slot") || undefined;

  // Fetch filter options
  useEffect(() => {
    async function fetchFilters() {
      try {
        const [catRes, brandRes, colorRes] = await Promise.all([
          getCategories(),
          getBrands(),
          getColors(),
        ]);
        setCategories(catRes.categories);
        setBrands(brandRes.brands);
        setColors(colorRes.colors);
      } catch (error) {
        console.error("Failed to fetch filters:", error);
      } finally {
        setFiltersLoading(false);
      }
    }
    fetchFilters();
  }, []);

  // Reset and fetch initial products when filters change
  useEffect(() => {
    async function fetchInitialProducts() {
      setLoading(true);
      setProducts([]);
      setCurrentPage(1);
      setHasMore(true);

      try {
        const response = await getProducts({
          page: 1,
          page_size: PAGE_SIZE,
          category: selectedCategory,
          brand: selectedBrand,
          primary_color: selectedColor,
          functional_slot: selectedSlot,
        });
        setProducts(response.items);
        setTotal(response.total);
        setHasMore(response.items.length === PAGE_SIZE && response.total > PAGE_SIZE);
      } catch (error) {
        console.error("Failed to fetch products:", error);
        setProducts([]);
      } finally {
        setLoading(false);
      }
    }
    fetchInitialProducts();
  }, [selectedCategory, selectedBrand, selectedColor, selectedSlot]);

  // Load more products
  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return;

    setLoadingMore(true);
    const nextPage = currentPage + 1;

    try {
      const response = await getProducts({
        page: nextPage,
        page_size: PAGE_SIZE,
        category: selectedCategory,
        brand: selectedBrand,
        primary_color: selectedColor,
        functional_slot: selectedSlot,
      });

      setProducts((prev) => [...prev, ...response.items]);
      setCurrentPage(nextPage);
      setHasMore(response.items.length === PAGE_SIZE && products.length + response.items.length < response.total);
    } catch (error) {
      console.error("Failed to load more products:", error);
    } finally {
      setLoadingMore(false);
    }
  }, [currentPage, hasMore, loadingMore, selectedCategory, selectedBrand, selectedColor, selectedSlot, products.length]);

  // Intersection Observer for infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore && !loading) {
          loadMore();
        }
      },
      { threshold: 0.1, rootMargin: "100px" }
    );

    if (loaderRef.current) {
      observer.observe(loaderRef.current);
    }

    return () => observer.disconnect();
  }, [hasMore, loadingMore, loading, loadMore]);

  const updateFilters = useCallback(
    (newFilters: Record<string, string | undefined>) => {
      const params = new URLSearchParams();

      // Build new params from current + new filters
      const allFilters = {
        category: selectedCategory,
        brand: selectedBrand,
        color: selectedColor,
        slot: selectedSlot,
        ...Object.fromEntries(
          Object.entries(newFilters).map(([key, value]) => [
            key === "primary_color" ? "color" : key === "functional_slot" ? "slot" : key,
            value,
          ])
        ),
      };

      Object.entries(allFilters).forEach(([key, value]) => {
        if (value) {
          params.set(key, value);
        }
      });

      router.push(`/products?${params.toString()}`);
      window.scrollTo({ top: 0, behavior: "instant" });
    },
    [router, selectedCategory, selectedBrand, selectedColor, selectedSlot]
  );

  const hasActiveFilters = selectedCategory || selectedBrand || selectedColor || selectedSlot;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Page Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-light">
            {selectedCategory || selectedSlot || "All Products"}
          </h1>
          <p className="text-sm text-gray-500 mt-2">
            {total} {total === 1 ? "product" : "products"}
          </p>
        </div>

        {/* Filter Toggle Button */}
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 px-4 py-2 border transition-colors ${
            showFilters || hasActiveFilters
              ? "bg-black text-white border-black"
              : "border-gray-300 hover:border-black"
          }`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
          </svg>
          <span className="text-sm">Filter</span>
          {hasActiveFilters && (
            <span className="w-2 h-2 bg-white rounded-full"></span>
          )}
        </button>
      </div>

      <div className="flex flex-col md:flex-row gap-8">
        {/* Sidebar - Hidden by default */}
        {showFilters && (
          <div className="w-full md:w-56 flex-shrink-0">
            {filtersLoading ? (
              <div className="animate-pulse space-y-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-12 bg-gray-100 rounded"></div>
                ))}
              </div>
            ) : (
              <FilterSidebar
                categories={categories}
                brands={brands}
                colors={colors}
                selectedCategory={selectedCategory}
                selectedBrand={selectedBrand}
                selectedColor={selectedColor}
                selectedSlot={selectedSlot}
                onFilterChange={updateFilters}
              />
            )}
          </div>
        )}

        {/* Product Grid */}
        <div className="flex-1">
          {loading ? (
            <LoadingSpinner />
          ) : (
            <>
              <ProductGrid products={products} />

              {/* Infinite scroll loader */}
              <div ref={loaderRef} className="py-8 flex justify-center">
                {loadingMore && (
                  <div className="flex items-center gap-2 text-gray-500">
                    <div className="w-5 h-5 border-2 border-gray-300 border-t-black rounded-full animate-spin"></div>
                    <span className="text-sm">Loading more...</span>
                  </div>
                )}
                {!hasMore && products.length > 0 && (
                  <p className="text-sm text-gray-400">You&apos;ve seen all {total} products</p>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ProductsPage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <ProductsContent />
    </Suspense>
  );
}
