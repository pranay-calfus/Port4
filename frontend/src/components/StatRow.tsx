import type { DepartmentMetrics } from "../api/types";
import { Card } from "./ui/Card";

export function StatRow({ metrics }: { metrics: DepartmentMetrics }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <Card>
        <p className="text-sm text-ink-muted">Open Tickets</p>
        <p className="mt-1 text-3xl font-bold text-ink">{metrics.open_tickets}</p>
      </Card>
      <Card>
        <p className="text-sm text-ink-muted">Total Tickets</p>
        <p className="mt-1 text-3xl font-bold text-ink">{metrics.total_tickets}</p>
      </Card>
      <Card>
        <p className="text-sm text-ink-muted">Avg Resolution Time</p>
        <p className="mt-1 text-3xl font-bold text-ink">
          {metrics.avg_resolution_hours != null ? `${metrics.avg_resolution_hours.toFixed(1)}h` : "—"}
        </p>
      </Card>
    </div>
  );
}
