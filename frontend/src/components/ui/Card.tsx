import type { HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Optional accent color (any valid CSS color - a hex from lib/colors.ts's
   * HUES/theme-color maps, or BRAND_ACCENT) for a subtle left border plus a
   * faint background tint, so a card can carry a meaning (a status, a
   * team, a source) at a glance. Omit for a plain neutral card - most cards
   * should stay plain; reserve this for the handful that genuinely benefit
   * (stat tiles, a record's own status color, ...). */
  accent?: string;
}

export function Card({ className = "", accent, style, ...props }: CardProps) {
  const accentStyle = accent
    ? {
        borderLeftColor: accent,
        borderLeftWidth: "3px",
        backgroundColor: `color-mix(in srgb, ${accent} 7%, var(--color-card))`,
        ...style,
      }
    : style;
  return (
    <div
      className={`rounded-lg border border-surface-border bg-surface-card p-5 ${className}`}
      style={accentStyle}
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
