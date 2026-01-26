"use client";

import { useRouter } from "next/navigation";
import Image from "next/image";
import { useCart } from "@/context/CartContext";

export default function CartPage() {
  const router = useRouter();
  const { items, removeItem, clearCart } = useCart();

  const handleBack = () => {
    router.back();
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Back Button */}
      <button
        onClick={handleBack}
        className="mb-8 px-6 py-3 bg-black text-white text-sm font-medium hover:bg-gray-800 transition-colors flex items-center gap-2"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back
      </button>

      {/* Page Title */}
      <h1 className="text-2xl font-bold mb-8">Your Cart</h1>

      {items.length === 0 ? (
        <div className="text-center py-16">
          <svg
            className="w-16 h-16 mx-auto mb-4 text-gray-300"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"
            />
          </svg>
          <p className="text-gray-500 text-sm">Your cart is empty</p>
          <p className="text-gray-400 text-xs mt-2">
            Add items from curated looks to get started
          </p>
        </div>
      ) : (
        <>
          {/* Cart Items */}
          <div className="space-y-4">
            {items.map((item) => (
              <div
                key={item.sku_id}
                className="flex gap-4 p-4 border border-gray-200 rounded-lg"
              >
                {/* Item Image */}
                <div className="w-20 h-20 sm:w-24 sm:h-24 bg-gray-50 rounded relative flex-shrink-0">
                  <Image
                    src={item.image_url || "/placeholder.svg"}
                    alt={item.title}
                    fill
                    className="object-contain p-2"
                    sizes="96px"
                  />
                </div>

                {/* Item Details */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium line-clamp-2">{item.title}</p>
                  <p className="text-xs text-gray-500 mt-1">{item.brand}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    From: {item.lookName}
                  </p>
                </div>

                {/* Remove Button */}
                <button
                  onClick={() => removeItem(item.sku_id)}
                  className="p-2 text-gray-400 hover:text-black transition-colors self-start"
                  aria-label="Remove item"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
            ))}
          </div>

          {/* Cart Summary */}
          <div className="mt-8 pt-6 border-t border-gray-200">
            <div className="flex justify-between items-center mb-4">
              <span className="text-sm text-gray-600">Total Items</span>
              <span className="text-sm font-medium">{items.length}</span>
            </div>
            <button
              onClick={clearCart}
              className="w-full py-3 border border-gray-300 text-sm font-medium hover:bg-gray-50 transition-colors"
            >
              Clear Cart
            </button>
          </div>
        </>
      )}
    </div>
  );
}
