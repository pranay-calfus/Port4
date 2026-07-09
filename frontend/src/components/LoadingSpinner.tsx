export function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center gap-3 py-6 text-indigo-600">
      <div
        className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600"
        role="status"
        aria-label="Loading"
      />
      <span className="text-sm font-medium">Routing ticket…</span>
    </div>
  );
}
