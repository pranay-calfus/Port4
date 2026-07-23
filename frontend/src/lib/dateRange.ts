import { useState } from "react";

export type DateRangePreset = "today" | "7d" | "30d" | "90d" | "6m" | "1y" | "custom";

export const DATE_RANGE_PRESETS: { value: DateRangePreset; label: string }[] = [
  { value: "today", label: "Today" },
  { value: "7d", label: "Last 7 Days" },
  { value: "30d", label: "Last 30 Days" },
  { value: "90d", label: "Last 90 Days" },
  { value: "6m", label: "Last 6 Months" },
  { value: "1y", label: "Last Year" },
  { value: "custom", label: "Custom Range" },
];

function toDateStr(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/** Resolves a preset into concrete "YYYY-MM-DD" from/to strings, anchored
 * on `today` (overridable for tests). `to` is always today; `from` is
 * today minus the preset's span, inclusive - "7d" spans today and the 6
 * days before it, matching how a customer would read "last 7 days".
 */
export function resolvePresetRange(
  preset: Exclude<DateRangePreset, "custom">,
  today: Date = new Date()
): { from: string; to: string } {
  const to = toDateStr(today);
  const from = new Date(today);
  switch (preset) {
    case "today":
      break;
    case "7d":
      from.setDate(from.getDate() - 6);
      break;
    case "30d":
      from.setDate(from.getDate() - 29);
      break;
    case "90d":
      from.setDate(from.getDate() - 89);
      break;
    case "6m":
      from.setMonth(from.getMonth() - 6);
      break;
    case "1y":
      from.setFullYear(from.getFullYear() - 1);
      break;
  }
  return { from: toDateStr(from), to };
}

export interface DateRangeFilterState {
  preset: DateRangePreset;
  setPreset: (preset: DateRangePreset) => void;
  customFrom: string;
  setCustomFrom: (value: string) => void;
  customTo: string;
  setCustomTo: (value: string) => void;
  /** Resolved concrete "YYYY-MM-DD" bounds - what every query should use. */
  dateFrom: string | undefined;
  dateTo: string | undefined;
}

/** The single source of truth for "what time range is this dashboard tab
 * showing right now" - every chart/card/table on a tab reads `dateFrom`/
 * `dateTo` from one instance of this hook, so they all move together.
 * Defaults to "Last 30 Days" rather than unbounded, per the requirement
 * that a range is always selected; picking "Custom Range" and leaving
 * both fields blank still resolves to unbounded, preserving the
 * dashboards' previous all-time default for anyone who wants it.
 */
export function useDateRangeFilter(defaultPreset: DateRangePreset = "30d"): DateRangeFilterState {
  const [preset, setPreset] = useState<DateRangePreset>(defaultPreset);
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");

  const resolved = preset === "custom" ? { from: customFrom, to: customTo } : resolvePresetRange(preset);

  return {
    preset,
    setPreset,
    customFrom,
    setCustomFrom,
    customTo,
    setCustomTo,
    dateFrom: resolved.from || undefined,
    dateTo: resolved.to || undefined,
  };
}
