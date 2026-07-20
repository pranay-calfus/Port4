import { useTheme } from "../context/ThemeContext";

export function ThemeToggle() {
  const { themeMode, toggleTheme } = useTheme();
  const isDark = themeMode === "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className="flex h-9 w-9 items-center justify-center rounded-full border border-surface-border text-base hover:bg-white/5"
    >
      {isDark ? "🌤️" : "🌑"}
    </button>
  );
}
