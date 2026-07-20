import type { HTMLAttributes } from "react";

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-lg border border-surface-border bg-surface-card p-5 ${className}`}
      {...props}
    />
  );
}

export function CardLabel({ className = "", ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={`mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted ${className}`}
      {...props}
    />
  );
}
