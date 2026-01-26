"use client";

import Link from "next/link";
import Image from "next/image";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Product } from "@/types";
import { searchProducts } from "@/lib/api";
import { useCart } from "@/context/CartContext";

export default function Header() {
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchResults, setSearchResults] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { itemCount } = useCart();

  // Debounced search as user types
  useEffect(() => {
    if (!searchQuery.trim() || searchQuery.length < 2) {
      setSearchResults([]);
      return;
    }

    const debounceTimer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const response = await searchProducts(searchQuery, 6);
        setSearchResults(response.items);
      } catch (error) {
        console.error("Search failed:", error);
        setSearchResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 300);

    return () => clearTimeout(debounceTimer);
  }, [searchQuery]);

  // Close search when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setIsSearchOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
      setIsSearchOpen(false);
      setSearchQuery("");
      setSearchResults([]);
    }
  };

  const handleResultClick = (skuId: string) => {
    router.push(`/product/${skuId}`);
    setIsSearchOpen(false);
    setSearchQuery("");
    setSearchResults([]);
  };

  const closeSearch = () => {
    setIsSearchOpen(false);
    setSearchQuery("");
    setSearchResults([]);
  };

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-gray-200">
      <div className="px-4 sm:px-8 lg:px-16 xl:px-24">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="text-xl font-bold tracking-tight">
            CULTURE STUDIO
          </Link>

          {/* Search & Actions */}
          <div className="flex items-center space-x-2" ref={searchRef}>
            {isSearchOpen ? (
              <div className="relative">
                <form onSubmit={handleSearch} className="flex items-center">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search products..."
                    className="w-64 px-3 py-2 text-sm border border-gray-300 focus:outline-none focus:border-black rounded-l"
                    autoFocus
                  />
                  <button
                    type="submit"
                    className="px-3 py-2 bg-black text-white text-sm hover:bg-gray-800"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    onClick={closeSearch}
                    className="ml-2 p-2 text-gray-500 hover:text-black"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </form>

                {/* Search Results Dropdown */}
                {(searchResults.length > 0 || isLoading) && searchQuery.length >= 2 && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 shadow-lg rounded-lg overflow-hidden z-50 max-h-96 overflow-y-auto">
                    {isLoading ? (
                      <div className="p-4 text-center text-gray-500 text-sm">
                        Searching...
                      </div>
                    ) : (
                      <>
                        {searchResults.map((product) => (
                          <button
                            key={product.sku_id}
                            onClick={() => handleResultClick(product.sku_id)}
                            className="w-full flex items-center gap-3 p-3 hover:bg-gray-50 transition-colors text-left border-b border-gray-100 last:border-0"
                          >
                            <div className="w-12 h-12 bg-gray-100 relative flex-shrink-0 rounded">
                              <Image
                                src={product.image_url || "/placeholder.svg"}
                                alt={product.title || product.type}
                                fill
                                className="object-contain p-1"
                                sizes="48px"
                              />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-xs text-gray-500 uppercase">{product.brand}</p>
                              <p className="text-sm font-medium truncate">{product.title || product.type}</p>
                              <p className="text-xs text-gray-400">{product.category}</p>
                            </div>
                          </button>
                        ))}
                        {searchResults.length > 0 && (
                          <button
                            onClick={handleSearch}
                            className="w-full p-3 text-sm text-center text-gray-600 hover:bg-gray-50 hover:text-black font-medium"
                          >
                            View all results for &quot;{searchQuery}&quot;
                          </button>
                        )}
                      </>
                    )}
                  </div>
                )}

                {/* No results message */}
                {!isLoading && searchQuery.length >= 2 && searchResults.length === 0 && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 shadow-lg rounded-lg p-4 text-center text-gray-500 text-sm">
                    No products found for &quot;{searchQuery}&quot;
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={() => setIsSearchOpen(true)}
                className="p-2 hover:bg-gray-100 rounded-full"
                aria-label="Search"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </button>
            )}

            {/* Cart Icon */}
            <Link
              href="/cart"
              className="p-2 hover:bg-gray-100 rounded-full relative"
              aria-label="Cart"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"
                />
              </svg>
              {itemCount > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-black text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                  {itemCount > 99 ? "99+" : itemCount}
                </span>
              )}
            </Link>
          </div>
        </div>
      </div>

    </header>
  );
}
