export interface Product {
  sku_id: string;
  title: string | null;
  brand: string | null;
  type: string;
  category: string;
  sub_category: string | null;
  primary_color: string | null;
  secondary_colors: string[];
  pattern: string | null;
  material_appearance: string | null;
  fit: string | null;
  gender: string;
  design_elements: string[];
  formality_level: string | null;
  versatility: string | null;
  statement_piece: boolean;
  functional_slot: string;
  style: string | null;
  fashion_aesthetics: string[];
  occasion: string[];
  season: string[];
  formality_score: number;
  image_url: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CompatibleItem {
  sku_id: string;
  score: number;
  product?: Product;
}

export interface CompatibilityResponse {
  source_sku: string;
  slot: string | null;
  compatible_items: CompatibleItem[];
  total_count: number;
}

export interface OutfitRecommendation {
  base_product: Product;
  recommendations: Record<string, CompatibleItem[]>;
  slots_filled: string[];
}

export interface OutfitScoreResponse {
  sku_ids: string[];
  total_score: number;
  pair_scores: Record<string, number>;
  average_score: number;
}

export type FunctionalSlot =
  | "Base Top"
  | "Outerwear"
  | "Primary Bottom"
  | "Secondary Bottom"
  | "Footwear"
  | "Accessory";

// Look Generation Types
export interface LookItem {
  sku_id: string;
  title: string;
  brand: string;
  image_url: string;
  type: string;
  color: string;
  slot: string;
}

export interface Look {
  id: string;
  name: string;
  description: string;
  dimension: string;
  dimension_value: string;
  items: Record<string, LookItem>;
  slots_filled: string[];
}

export interface LooksResponse {
  base_product: Product;
  looks: Look[];
  total_looks: number;
}
