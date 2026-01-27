"use client";

import { useCallback, useRef, useEffect, Suspense, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQuery, useInfiniteQuery } from "@tanstack/react-query";
import { getProducts, getCategories, getBrands, getColors } from "@/lib/api";
import ProductGrid from "@/components/ProductGrid";
import FilterSidebar from "@/components/FilterSidebar";
import LoadingSpinner from "@/components/LoadingSpinner";

const PAGE_SIZE = 24;

function ProductsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const loaderRef = useRef<HTMLDivElement>(null);
  const [showFilters, setShowFilters] = useState(false);

  const selectedCategory = searchParams.get("category") || undefined;
  const selectedBrand = searchParams.get("brand") || undefined;
  const selectedColor = searchParams.get("color") || undefined;
  const selectedSlot = searchParams.get("slot") || undefined;

  // Fetch filter options with long cache (rarely change)
  const { data: categoriesData, isLoading: categoriesLoading } = useQuery({
    queryKey: ["categories"],
    queryFn: getCategories,
    staleTime: 30 * 60 * 1000, // 30 minutes
  });

  const { data: brandsData, isLoading: brandsLoading } = useQuery({
    queryKey: ["brands"],
    queryFn: getBrands,
    staleTime: 30 * 60 * 1000,
  });

  const { data: colorsData, isLoading: colorsLoading } = useQuery({
    queryKey: ["colors"],
    queryFn: getColors,
    staleTime: 30 * 60 * 1000,
  });

  const filtersLoading = categoriesLoading || brandsLoading || colorsLoading;
  const categories = categoriesData?.categories ?? [];
  const brands = brandsData?.brands ?? [];
  const colors = colorsData?.colors ?? [];

  // Infinite query for products
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
  } = useInfiniteQuery({
    queryKey: ["products", selectedCategory, selectedBrand, selectedColor, selectedSlot],
    queryFn: ({ pageParam = 1 }) =>
      getProducts({
        page: pageParam,
        page_size: PAGE_SIZE,
        category: selectedCategory,
        brand: selectedBrand,
        primary_color: selectedColor,
        functional_slot: selectedSlot,
      }),
    getNextPageParam: (lastPage, allPages) => {
      const totalFetched = allPages.reduce((sum, page) => sum + page.items.length, 0);
      if (lastPage.items.length === PAGE_SIZE && totalFetched < lastPage.total) {
        return allPages.length + 1;
      }
      return undefined;
    },
    initialPageParam: 1,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  // Flatten products from all pages
  const products = data?.pages.flatMap((page) => page.items) ?? [];
  const total = data?.pages[0]?.total ?? 0;

  // Intersection Observer for infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage && !isLoading) {
          fetchNextPage();
        }
      },
      { threshold: 0.1, rootMargin: "100px" }
    );

    if (loaderRef.current) {
      observer.observe(loaderRef.current);
    }

    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, isLoading, fetchNextPage]);

  const updateFilters = useCallback(
    (newFilters: Record<string, string | undefined>) => {
      const params = new URLSearchParams();

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
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
            />
          </svg>
          <span className="text-sm">Filter</span>
          {hasActiveFilters && <span className="w-2 h-2 bg-white rounded-full"></span>}
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
          {isLoading ? (
            <LoadingSpinner />
          ) : (
            <>
              <ProductGrid products={products} />

              {/* Infinite scroll loader */}
              <div ref={loaderRef} className="py-8 flex justify-center">
                {isFetchingNextPage && (
                  <div className="flex items-center gap-2 text-gray-500">
                    <div className="w-5 h-5 border-2 border-gray-300 border-t-black rounded-full animate-spin"></div>
                    <span className="text-sm">Loading more...</span>
                  </div>
                )}
                {!hasNextPage && products.length > 0 && (
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
