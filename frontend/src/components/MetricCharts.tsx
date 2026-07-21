import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DepartmentMetrics } from "../api/types";
import {
  EMOTION_COLORS,
  EMOTION_ORDER,
  PRIORITY_COLORS,
  PRIORITY_ORDER,
  STATUS_COLORS,
  STATUS_ORDER,
  TEAM_COLORS,
  TEAM_ORDER,
  statusLabel,
} from "../lib/colors";
import { Accordion } from "./ui/Accordion";

const AXIS_COLOR = "#8b929e";

function buildSeries(order: string[], colors: Record<string, string>, counts: Record<string, number>) {
  const total = order.reduce((sum, key) => sum + (counts[key] ?? 0), 0);
  return order.map((key) => ({
    name: statusLabel(key),
    key,
    value: counts[key] ?? 0,
    color: colors[key] ?? "#9ca3af",
    pct: total > 0 ? Math.round(((counts[key] ?? 0) / total) * 100) : 0,
  }));
}

function CaptionLine({ series }: { series: ReturnType<typeof buildSeries> }) {
  return (
    <p className="mt-2 text-xs text-ink-muted">
      {series.map((entry) => `${entry.name}: ${entry.value} (${entry.pct}%)`).join(" · ")}
    </p>
  );
}

function slugify(title: string): string {
  return title.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

function BarCard({
  title,
  order,
  colors,
  counts,
}: {
  title: string;
  order: string[];
  colors: Record<string, string>;
  counts: Record<string, number>;
}) {
  const series = buildSeries(order, colors, counts);
  return (
    <Accordion title={title} defaultOpen storageKey={`chart-${slugify(title)}`}>
      <div style={{ width: "100%", height: series.length * 42 + 30 }}>
        <ResponsiveContainer>
          <BarChart data={series} layout="vertical" margin={{ left: 24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#8b929e33" horizontal={false} />
            <XAxis type="number" allowDecimals={false} stroke={AXIS_COLOR} fontSize={12} />
            <YAxis type="category" dataKey="name" stroke={AXIS_COLOR} fontSize={12} width={110} />
            <Tooltip
              formatter={(value: number, _name, item) => [
                `${value} (${item.payload.pct}%)`,
                item.payload.name,
              ]}
              contentStyle={{ background: "#111", border: "1px solid #333", fontSize: 12 }}
            />
            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
              {series.map((entry) => (
                <Cell key={entry.key} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <CaptionLine series={series} />
    </Accordion>
  );
}

function PieCard({
  title,
  order,
  colors,
  counts,
}: {
  title: string;
  order: string[];
  colors: Record<string, string>;
  counts: Record<string, number>;
}) {
  const series = buildSeries(order, colors, counts).filter((entry) => entry.value > 0);
  return (
    <Accordion title={title} defaultOpen storageKey={`chart-${slugify(title)}`}>
      <div style={{ width: "100%", height: 220 }}>
        <ResponsiveContainer>
          <PieChart>
            <Pie data={series} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90}>
              {series.map((entry) => (
                <Cell key={entry.key} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number, _name, item) => [
                `${value} (${item.payload.pct}%)`,
                item.payload.name,
              ]}
              contentStyle={{ background: "#111", border: "1px solid #333", fontSize: 12 }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <CaptionLine series={buildSeries(order, colors, counts)} />
    </Accordion>
  );
}

export function MetricCharts({
  metrics,
  showDepartment,
}: {
  metrics: DepartmentMetrics;
  showDepartment: boolean;
}) {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <BarCard
        title="Tickets by Status"
        order={STATUS_ORDER}
        colors={STATUS_COLORS}
        counts={metrics.tickets_per_status}
      />
      <PieCard
        title="Tickets by Priority"
        order={PRIORITY_ORDER}
        colors={PRIORITY_COLORS}
        counts={metrics.tickets_per_priority}
      />
      <BarCard
        title="Tickets by Emotion"
        order={EMOTION_ORDER}
        colors={EMOTION_COLORS}
        counts={metrics.tickets_per_emotion}
      />
      {showDepartment && metrics.tickets_per_department && (
        <BarCard
          title="Tickets by Team"
          order={TEAM_ORDER}
          colors={TEAM_COLORS}
          counts={metrics.tickets_per_department}
        />
      )}
    </div>
  );
}
