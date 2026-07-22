import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { FeedbackMetrics } from "../api/types";
import {
  FEEDBACK_CATEGORY_COLORS,
  FEEDBACK_CATEGORY_ORDER,
  SENTIMENT_COLORS,
  SENTIMENT_ORDER,
  TEAM_COLORS,
  TEAM_ORDER,
} from "../lib/colors";
import { Accordion } from "./ui/Accordion";

const AXIS_COLOR = "#8b929e";

function buildSeries(order: string[], colors: Record<string, string>, counts: Record<string, number>) {
  const total = order.reduce((sum, key) => sum + (counts[key] ?? 0), 0);
  return order.map((key) => ({
    name: key,
    key,
    value: counts[key] ?? 0,
    color: colors[key] ?? "#9ca3af",
    pct: total > 0 ? Math.round(((counts[key] ?? 0) / total) * 100) : 0,
  }));
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
    <Accordion title={title} defaultOpen storageKey={`feedback-chart-${slugify(title)}`}>
      <div style={{ width: "100%", height: series.length * 42 + 30 }}>
        <ResponsiveContainer>
          <BarChart data={series} layout="vertical" margin={{ left: 24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#8b929e33" horizontal={false} />
            <XAxis type="number" allowDecimals={false} stroke={AXIS_COLOR} fontSize={12} />
            <YAxis type="category" dataKey="name" stroke={AXIS_COLOR} fontSize={12} width={140} />
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
      <p className="mt-2 text-xs text-ink-muted">
        {series.map((entry) => `${entry.name}: ${entry.value} (${entry.pct}%)`).join(" · ")}
      </p>
    </Accordion>
  );
}

export function FeedbackMetricCharts({ metrics }: { metrics: FeedbackMetrics }) {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <BarCard
        title="Feedback by Sentiment"
        order={SENTIMENT_ORDER}
        colors={SENTIMENT_COLORS}
        counts={metrics.feedback_per_sentiment}
      />
      <BarCard
        title="Feedback by Category"
        order={FEEDBACK_CATEGORY_ORDER}
        colors={FEEDBACK_CATEGORY_COLORS}
        counts={metrics.feedback_per_category}
      />
      <BarCard
        title="Feedback by Team"
        order={TEAM_ORDER}
        colors={TEAM_COLORS}
        counts={metrics.feedback_per_team}
      />
    </div>
  );
}
