"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-2xl font-light mb-4">Something went wrong</h1>
        <p className="text-gray-600 mb-8">
          {error.message || "An unexpected error occurred"}
        </p>
        <button
          onClick={() => reset()}
          className="inline-block bg-black text-white px-8 py-3 text-sm uppercase tracking-wider hover:bg-gray-900 transition-colors"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}
