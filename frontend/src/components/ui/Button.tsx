import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

const base =
  "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed";

const variants: Record<Variant, string> = {
  primary: "bg-accent text-[color:var(--color-accent-ink)] hover:opacity-90",
  secondary: "border border-surface-border text-ink hover:bg-white/5",
  danger: "bg-red-500 text-white hover:bg-red-600",
  ghost: "text-ink-muted hover:text-ink",
};

export function Button({ variant = "secondary", className = "", ...props }: ButtonProps) {
  return <button className={`${base} ${variants[variant]} ${className}`} {...props} />;
}
