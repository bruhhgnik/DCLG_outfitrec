import { Product, PaginatedResponse, OutfitRecommendation, OutfitScoreResponse, LooksResponse } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

console.log("API_BASE:", API_BASE);

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    cache: 'no-store', // Always fetch fresh data
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// Product endpoints
export async function getProducts(params?: {
  page?: number;
  page_size?: number;
  category?: string;
  functional_slot?: string;
  gender?: string;
  brand?: string;
  primary_color?: string;
}): Promise<PaginatedResponse<Product>> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        searchParams.append(key, String(value));
      }
    });
  }
  const query = searchParams.toString();
  return fetchApi<PaginatedResponse<Product>>(`/api/v1/products${query ? `?${query}` : ""}`);
}

export async function getProduct(skuId: string): Promise<Product> {
  return fetchApi<Product>(`/api/v1/products/${skuId}`);
}

export async function searchProducts(query: string, limit = 20): Promise<{ items: Product[]; count: number }> {
  return fetchApi<{ items: Product[]; count: number }>(
    `/api/v1/products/search?q=${encodeURIComponent(query)}&limit=${limit}`
  );
}

export async function getCategories(): Promise<{ categories: string[] }> {
  return fetchApi<{ categories: string[] }>("/api/v1/products/categories");
}

export async function getBrands(): Promise<{ brands: string[] }> {
  return fetchApi<{ brands: string[] }>("/api/v1/products/brands");
}

export async function getColors(): Promise<{ colors: string[] }> {
  return fetchApi<{ colors: string[] }>("/api/v1/products/colors");
}

// Outfit endpoints
export async function generateOutfit(
  baseSku: string,
  options?: {
    slots?: string[];
    min_score?: number;
    limit_per_slot?: number;
  }
): Promise<OutfitRecommendation> {
  const searchParams = new URLSearchParams();
  searchParams.append("base_sku", baseSku);
  if (options?.slots) {
    options.slots.forEach((slot) => searchParams.append("slots", slot));
  }
  if (options?.min_score !== undefined) {
    searchParams.append("min_score", String(options.min_score));
  }
  if (options?.limit_per_slot !== undefined) {
    searchParams.append("limit_per_slot", String(options.limit_per_slot));
  }
  return fetchApi<OutfitRecommendation>(`/api/v1/outfits/generate?${searchParams.toString()}`, {
    method: "POST",
  });
}

export async function scoreOutfit(skuIds: string[]): Promise<OutfitScoreResponse> {
  return fetchApi<OutfitScoreResponse>("/api/v1/outfits/score", {
    method: "POST",
    body: JSON.stringify({ sku_ids: skuIds }),
  });
}

export async function generateLooks(
  baseSku: string,
  numLooks: number = 3
): Promise<LooksResponse> {
  const searchParams = new URLSearchParams();
  searchParams.append("base_sku", baseSku);
  searchParams.append("num_looks", String(numLooks));
  return fetchApi<LooksResponse>(`/api/v1/outfits/generate-looks?${searchParams.toString()}`);
}

// Health check
export async function getHealthStatus(): Promise<{
  status: string;
  database: string;
  compatibility_graph_loaded: boolean;
  graph_products: number;
}> {
  return fetchApi("/api/v1/stats/health");
}

// Site config
export async function getSiteConfig(): Promise<{
  hero_video_url: string;
}> {
  return fetchApi("/api/v1/stats/config");
}
