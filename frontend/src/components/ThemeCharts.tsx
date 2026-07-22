import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ThemeTrendPoint, TopTheme } from "../api/types";
import { themeColor } from "../lib/colors";
import { Accordion } from "./ui/Accordion";

const AXIS_COLOR = "#8b929e";

function MostCommonThemesChart({ topThemes }: { topThemes: TopTheme[] }) {
  const total = topThemes.reduce((sum, t) => sum + t.count, 0);
  const series = topThemes.map((t) => ({
    name: t.theme,
    value: t.count,
    color: themeColor(t.theme),
    pct: total > 0 ? Math.round((t.count / total) * 100) : 0,
  }));

  return (
    <Accordion title="Most Common Themes" defaultOpen storageKey="chart-most-common-themes">
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
                <Cell key={entry.name} fill={entry.color} />
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

function ThemeFrequencyChart({ topThemes }: { topThemes: TopTheme[] }) {
  const total = topThemes.reduce((sum, t) => sum + t.count, 0);
  const series = topThemes
    .map((t) => ({
      name: t.theme,
      value: t.count,
      color: themeColor(t.theme),
      pct: total > 0 ? Math.round((t.count / total) * 100) : 0,
    }))
    .filter((entry) => entry.value > 0);

  return (
    <Accordion title="Theme Frequency" defaultOpen storageKey="chart-theme-frequency">
      <div style={{ width: "100%", height: 220 }}>
        <ResponsiveContainer>
          <PieChart>
            <Pie data={series} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90}>
              {series.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
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
      <p className="mt-2 text-xs text-ink-muted">
        {series.map((entry) => `${entry.name}: ${entry.value} (${entry.pct}%)`).join(" · ")}
      </p>
    </Accordion>
  );
}

function ThemeTrendChart({ themes, trend }: { themes: string[]; trend: ThemeTrendPoint[] }) {
  const data = trend.map((point) => ({ date: point.date, ...point.counts }));

  return (
    <Accordion title="Trend Over Time" defaultOpen storageKey="chart-theme-trend">
      <div style={{ width: "100%", height: 280 }}>
        <ResponsiveContainer>
          <AreaChart data={data} margin={{ left: 8, right: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#8b929e33" />
            <XAxis dataKey="date" stroke={AXIS_COLOR} fontSize={12} />
            <YAxis allowDecimals={false} stroke={AXIS_COLOR} fontSize={12} />
            <Tooltip contentStyle={{ background: "#111", border: "1px solid #333", fontSize: 12 }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {themes.map((theme) => (
              <Area
                key={theme}
                type="monotone"
                dataKey={theme}
                stackId="themes"
                stroke={themeColor(theme)}
                fill={themeColor(theme)}
                fillOpacity={0.5}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Accordion>
  );
}

export function ThemeCharts({
  topThemes,
  trend,
}: {
  topThemes: TopTheme[];
  trend: ThemeTrendPoint[];
}) {
  if (topThemes.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <MostCommonThemesChart topThemes={topThemes} />
        <ThemeFrequencyChart topThemes={topThemes} />
      </div>
      <ThemeTrendChart themes={topThemes.map((t) => t.theme)} trend={trend} />
    </div>
  );
}
