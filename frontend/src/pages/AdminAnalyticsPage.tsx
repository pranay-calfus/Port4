import { useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adminMetrics } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { DateRangeFilter } from "../components/DateRangeFilter";
import { StatRow } from "../components/StatRow";
import { MetricCharts } from "../components/MetricCharts";
import { ThemeCharts } from "../components/ThemeCharts";
import { useDateRangeFilter } from "../lib/dateRange";
import { isSuperAdmin } from "../lib/roles";
import { buildDashboardCsv, downloadCsv } from "../lib/exportCsv";
import { downloadBlob, generateDashboardPdf } from "../lib/exportPdf";
import { Button } from "../components/ui/Button";
import { ErrorBanner, ErrorMessage, Spinner } from "../components/ui/Feedback";

export function AdminAnalyticsPage() {
  const { token, identity } = useAuth();
  const superAdmin = isSuperAdmin(identity);
  const [teamFilter, setTeamFilter] = useState("All Teams");
  const range = useDateRangeFilter();
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [exportError, setExportError] = useState("");
  const chartsRef = useRef<HTMLDivElement>(null);

  const { data: metrics, isLoading, error } = useQuery({
    queryKey: ["admin-metrics", range.dateFrom, range.dateTo],
    queryFn: () => adminMetrics(token!, { date_from: range.dateFrom, date_to: range.dateTo }),
    enabled: !!token,
  });

  if (isLoading) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-8">
        <Spinner label="Loading metrics…" />
      </div>
    );
  }
  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-8">
        <ErrorBanner message={ErrorMessage(error)} />
      </div>
    );
  }
  if (!metrics) return null;

  const teams = superAdmin && metrics.by_department ? Object.keys(metrics.by_department).sort() : [];
  const activeMetrics =
    superAdmin && teamFilter !== "All Teams" && metrics.by_department
      ? metrics.by_department[teamFilter]
      : metrics;
  const scopeLabel = superAdmin ? teamFilter : identity?.department ?? "";

  function handleExportCsv() {
    const csv = buildDashboardCsv(activeMetrics, metrics!.date_range, scopeLabel, new Date().toISOString());
    downloadCsv(`ticktrack-dashboard-${Date.now()}.csv`, csv);
  }

  async function handleExportPdf() {
    setExportError("");
    setIsExportingPdf(true);
    try {
      const blob = await generateDashboardPdf(
        activeMetrics,
        metrics!.date_range,
        scopeLabel,
        new Date().toISOString(),
        chartsRef.current
      );
      downloadBlob(`ticktrack-dashboard-${Date.now()}.pdf`, blob);
    } catch (err) {
      setExportError(ErrorMessage(err));
    } finally {
      setIsExportingPdf(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-6 py-8">
      <h1 className="text-2xl font-bold text-ink">Ticket Analytics</h1>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-wrap items-end gap-4">
          {superAdmin && teams.length > 0 && (
            <div className="max-w-xs">
              <label className="mb-1.5 block text-sm text-ink-muted">Team</label>
              <select
                value={teamFilter}
                onChange={(e) => setTeamFilter(e.target.value)}
                className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand focus:border-brand"
              >
                <option value="All Teams">All Teams</option>
                {teams.map((team) => (
                  <option key={team} value={team}>
                    {team}
                  </option>
                ))}
              </select>
            </div>
          )}
          <DateRangeFilter {...range} />
        </div>
        <div className="flex items-end gap-2">
          <Button onClick={handleExportCsv}>Export CSV</Button>
          <Button onClick={handleExportPdf} disabled={isExportingPdf}>
            {isExportingPdf ? "Generating…" : "Export PDF"}
          </Button>
        </div>
      </div>
      {exportError && <ErrorBanner message={exportError} />}
      <StatRow metrics={activeMetrics} />
      <div ref={chartsRef} className="space-y-4">
        <MetricCharts metrics={activeMetrics} showDepartment={superAdmin && teamFilter === "All Teams"} />
        <ThemeCharts topThemes={activeMetrics.top_themes} trend={activeMetrics.theme_trend} />
      </div>
    </div>
  );
}
