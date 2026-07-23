import type { ReactNode } from "react";

export function Modal({
  title,
  children,
  onClose,
  maxWidthClassName = "max-w-md",
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  /** Overrides the default max-w-md - e.g. "max-w-2xl" for content-heavy
   * detail views (see WeeklyReportDetail's usage). */
  maxWidthClassName?: string;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className={`max-h-[85vh] w-full overflow-y-auto rounded-lg border border-surface-border bg-surface-card p-6 ${maxWidthClassName}`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <h2 className="mb-3 text-lg font-semibold text-ink">{title}</h2>
        {children}
      </div>
    </div>
  );
}
