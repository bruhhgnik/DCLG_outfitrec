export default function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="relative w-8 h-8">
        <div className="absolute inset-0 border-2 border-gray-200 rounded-full"></div>
        <div className="absolute inset-0 border-2 border-black border-t-transparent rounded-full animate-spin"></div>
      </div>
    </div>
  );
}
