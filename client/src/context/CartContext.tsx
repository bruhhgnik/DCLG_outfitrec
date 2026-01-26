"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";
import { LookItem } from "@/types";

export interface CartItem extends LookItem {
  lookId: string;
  lookName: string;
}

interface CartContextType {
  items: CartItem[];
  addLookToCart: (lookId: string, lookName: string, items: LookItem[]) => void;
  removeItem: (skuId: string) => void;
  clearCart: () => void;
  itemCount: number;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);

  const addLookToCart = useCallback((lookId: string, lookName: string, lookItems: LookItem[]) => {
    setItems((prev) => {
      // Convert look items to cart items
      const newItems: CartItem[] = lookItems.map((item) => ({
        ...item,
        lookId,
        lookName,
      }));

      // Filter out duplicates (same sku_id)
      const existingSkuIds = new Set(prev.map((item) => item.sku_id));
      const uniqueNewItems = newItems.filter((item) => !existingSkuIds.has(item.sku_id));

      return [...prev, ...uniqueNewItems];
    });
  }, []);

  const removeItem = useCallback((skuId: string) => {
    setItems((prev) => prev.filter((item) => item.sku_id !== skuId));
  }, []);

  const clearCart = useCallback(() => {
    setItems([]);
  }, []);

  return (
    <CartContext.Provider
      value={{
        items,
        addLookToCart,
        removeItem,
        clearCart,
        itemCount: items.length,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context = useContext(CartContext);
  if (context === undefined) {
    throw new Error("useCart must be used within a CartProvider");
  }
  return context;
}
