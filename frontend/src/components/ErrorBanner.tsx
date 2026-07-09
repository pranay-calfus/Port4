interface ErrorBannerProps {
  message: string;
}

export function ErrorBanner({ message }: ErrorBannerProps) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">
      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-600 text-xs font-bold text-white">
        !
      </span>
      <div>
        <p className="text-sm font-semibold">Something went wrong</p>
        <p className="text-sm">{message}</p>
      </div>
    </div>
  );
}
