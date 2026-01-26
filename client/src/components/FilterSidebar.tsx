"use client";

import { useState } from "react";

interface FilterSidebarProps {
  categories: string[];
  brands: string[];
  colors: string[];
  selectedCategory?: string;
  selectedBrand?: string;
  selectedColor?: string;
  selectedSlot?: string;
  onFilterChange: (filters: {
    category?: string;
    brand?: string;
    primary_color?: string;
    functional_slot?: string;
  }) => void;
}

const SLOTS = ["Base Top", "Outerwear", "Primary Bottom", "Secondary Bottom", "Footwear", "Accessory"];

// Priority order for categories - most relevant fashion categories first
const CATEGORY_PRIORITY = [
  "tops",
  "bottoms",
  "outerwear",
  "footwear",
  "accessories",
  "bags",
  "jewelry",
  "eyewear",
];

function sortCategories(categories: string[]): string[] {
  return [...categories].sort((a, b) => {
    const aIndex = CATEGORY_PRIORITY.indexOf(a.toLowerCase());
    const bIndex = CATEGORY_PRIORITY.indexOf(b.toLowerCase());

    // If both are in priority list, sort by priority
    if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
    // If only a is in priority list, a comes first
    if (aIndex !== -1) return -1;
    // If only b is in priority list, b comes first
    if (bIndex !== -1) return 1;
    // Otherwise, alphabetical
    return a.localeCompare(b);
  });
}

export default function FilterSidebar({
  categories,
  brands,
  colors,
  selectedCategory,
  selectedBrand,
  selectedColor,
  selectedSlot,
  onFilterChange,
}: FilterSidebarProps) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    category: true,
    slot: true,
    brand: false,
    color: false,
  });

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const FilterSection = ({
    title,
    section,
    options,
    selected,
    filterKey,
  }: {
    title: string;
    section: string;
    options: string[];
    selected?: string;
    filterKey: string;
  }) => (
    <div className="border-b border-gray-200 py-4">
      <button
        onClick={() => toggleSection(section)}
        className="flex items-center justify-between w-full text-left"
      >
        <span className="text-sm font-medium uppercase tracking-wide">{title}</span>
        <svg
          className={`w-4 h-4 transition-transform ${expandedSections[section] ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {expandedSections[section] && (
        <div className="mt-3 space-y-2 max-h-48 overflow-y-auto">
          <button
            onClick={() => onFilterChange({ [filterKey]: undefined })}
            className={`block text-sm w-full text-left py-1 hover:text-black ${
              !selected ? "font-medium text-black" : "text-gray-500"
            }`}
          >
            All
          </button>
          {options.map((option) => (
            <button
              key={option}
              onClick={() => onFilterChange({ [filterKey]: option })}
              className={`block text-sm w-full text-left py-1 hover:text-black ${
                selected === option ? "font-medium text-black" : "text-gray-500"
              }`}
            >
              {option}
            </button>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <aside className="w-full">
      <h2 className="text-sm font-medium uppercase tracking-wide mb-4">Filters</h2>

      <FilterSection
        title="Category"
        section="category"
        options={sortCategories(categories)}
        selected={selectedCategory}
        filterKey="category"
      />

      <FilterSection
        title="Product Type"
        section="slot"
        options={SLOTS}
        selected={selectedSlot}
        filterKey="functional_slot"
      />

      <FilterSection
        title="Brand"
        section="brand"
        options={brands.slice(0, 20)}
        selected={selectedBrand}
        filterKey="brand"
      />

      <FilterSection
        title="Color"
        section="color"
        options={colors}
        selected={selectedColor}
        filterKey="primary_color"
      />

      {(selectedCategory || selectedBrand || selectedColor || selectedSlot) && (
        <button
          onClick={() =>
            onFilterChange({
              category: undefined,
              brand: undefined,
              primary_color: undefined,
              functional_slot: undefined,
            })
          }
          className="mt-4 w-full py-2 text-sm border border-black hover:bg-black hover:text-white transition-colors"
        >
          Clear All Filters
        </button>
      )}
    </aside>
  );
}
