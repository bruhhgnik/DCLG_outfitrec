import Link from "next/link";
import { getProducts } from "@/lib/api";
import ProductGrid from "@/components/ProductGrid";
import HeroVideo from "@/components/HeroVideo";
import { Product } from "@/types";

// Categories to display on homepage
const CATEGORIES = [
  { name: "Tops", slug: "tops", filter: "tops" },
  { name: "Bottoms", slug: "bottoms", filter: "bottoms" },
  { name: "Footwear", slug: "footwear", filter: "footwear" },
  { name: "Accessories", slug: "accessories", filter: "accessories" },
];

async function getProductsByCategory(category: string): Promise<Product[]> {
  try {
    console.log(`Fetching products for category: ${category}`);
    const response = await getProducts({ page: 1, page_size: 4, category });
    console.log(`Got ${response.items.length} products for ${category}`);
    return response.items;
  } catch (error) {
    console.error(`Error fetching ${category}:`, error);
    return [];
  }
}

export default async function HomePage() {
  // Fetch products for each category in parallel
  const categoryProducts = await Promise.all(
    CATEGORIES.map(async (cat) => ({
      ...cat,
      products: await getProductsByCategory(cat.filter),
    }))
  );

  return (
    <div>
      {/* Hero Section with Video */}
      <HeroVideo />

      {/* How It Works */}
      <section className="max-w-7xl mx-auto px-4 sm:px-8 lg:px-16 xl:px-24 py-12">
        <h2 className="text-2xl font-light text-center mb-10">How It Works</h2>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="text-center">
            <div className="w-14 h-14 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
              <span className="text-xl font-light">1</span>
            </div>
            <h3 className="font-medium mb-2">Choose a Piece</h3>
            <p className="text-sm text-gray-600">
              Select any item from our curated collection
            </p>
          </div>
          <div className="text-center">
            <div className="w-14 h-14 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
              <span className="text-xl font-light">2</span>
            </div>
            <h3 className="font-medium mb-2">Get AI Recommendations</h3>
            <p className="text-sm text-gray-600">
              Our AI finds perfect matching items
            </p>
          </div>
          <div className="text-center">
            <div className="w-14 h-14 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
              <span className="text-xl font-light">3</span>
            </div>
            <h3 className="font-medium mb-2">Build Your Outfit</h3>
            <p className="text-sm text-gray-600">
              Mix and match to create your complete look
            </p>
          </div>
        </div>
      </section>

      {/* Products by Category */}
      {categoryProducts.map((category) => (
        <section key={category.slug} className="max-w-7xl mx-auto px-4 sm:px-8 lg:px-16 xl:px-24 py-10 border-t border-gray-200">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-light">{category.name}</h2>
            <Link
              href={`/products?category=${category.filter}`}
              className="text-sm underline hover:no-underline"
            >
              View All {category.name}
            </Link>
          </div>
          {category.products.length > 0 ? (
            <ProductGrid products={category.products} />
          ) : (
            <p className="text-center text-gray-500 py-8">
              No {category.name.toLowerCase()} available
            </p>
          )}
        </section>
      ))}

      {/* Category Cards */}
      <section className="max-w-7xl mx-auto px-4 sm:px-8 lg:px-16 xl:px-24 py-12 border-t border-gray-200">
        <h2 className="text-2xl font-light text-center mb-10">Shop by Category</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {CATEGORIES.map((cat) => (
            <Link
              key={cat.slug}
              href={`/products?category=${cat.filter}`}
              className="group relative aspect-square bg-gray-100 flex items-center justify-center hover:bg-gray-200 transition-colors"
            >
              <span className="text-lg font-medium uppercase tracking-wide">{cat.name}</span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
