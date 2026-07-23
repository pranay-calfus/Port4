import { DATE_RANGE_PRESETS, type DateRangeFilterState } from "../lib/dateRange";
import { SelectField } from "./ui/FormField";

/** The one shared time-range control used across every analytics surface
 * (Support Dashboard, Product & CX Dashboard, Survey Analytics) - pass it
 * a `useDateRangeFilter()` instance and it renders the preset dropdown,
 * plus the two date inputs only when "Custom Range" is selected.
 */
export function DateRangeFilter({
  preset,
  setPreset,
  customFrom,
  setCustomFrom,
  customTo,
  setCustomTo,
}: DateRangeFilterState) {
  return (
    <div className="flex flex-wrap items-end gap-4">
      <div className="max-w-xs">
        <SelectField
          label="Time Range"
          value={preset}
          onChange={(e) => setPreset(e.target.value as DateRangeFilterState["preset"])}
        >
          {DATE_RANGE_PRESETS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </SelectField>
      </div>
      {preset === "custom" && (
        <>
          <div>
            <label className="mb-1.5 block text-sm text-ink-muted">From</label>
            <input
              type="date"
              value={customFrom}
              onChange={(e) => setCustomFrom(e.target.value)}
              className="rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm text-ink-muted">To</label>
            <input
              type="date"
              value={customTo}
              onChange={(e) => setCustomTo(e.target.value)}
              className="rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink"
            />
          </div>
        </>
      )}
    </div>
  );
}
