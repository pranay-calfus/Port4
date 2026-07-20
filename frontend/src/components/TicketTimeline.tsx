import type { ActivityOut } from "../api/types";
import { formatDateTime } from "../lib/format";

export function TicketTimeline({ activity, label = "TIMELINE" }: { activity: ActivityOut[]; label?: string }) {
  return (
    <div>
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-ink-muted">{label}</p>
      <ol className="space-y-4 border-l border-surface-border pl-4">
        {activity.map((entry) => (
          <li key={entry.id} className="relative">
            <span className="absolute -left-[21px] top-1 h-2 w-2 rounded-full bg-ink" />
            <div className="flex items-baseline justify-between gap-4">
              <p className="font-semibold text-ink">{entry.event_type}</p>
              <p className="whitespace-nowrap text-xs text-ink-muted">{formatDateTime(entry.created_at)}</p>
            </div>
            {entry.detail && <p className="text-sm text-ink-muted">{entry.detail}</p>}
          </li>
        ))}
      </ol>
    </div>
  );
}
