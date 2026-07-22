import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { adminMetrics } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { AdminTicketTable } from "../components/AdminTicketTable";
import { StatRow } from "../components/StatRow";
import { MetricCharts } from "../components/MetricCharts";
import { ThemeCharts } from "../components/ThemeCharts";
import { buildDashboardCsv, downloadCsv } from "../lib/exportCsv";
import { downloadBlob, generateDashboardPdf } from "../lib/exportPdf";
import { Button } from "../components/ui/Button";
import { Tabs } from "../components/ui/Tabs";
import { ErrorBanner, ErrorMessage, Spinner } from "../components/ui/Feedback";

function DashboardTab({ teamFilter, onTeamChange }: { teamFilter: string; onTeamChange: (v: string) => void }) {
  const { token, identity } = useAuth();
  const isSuperAdmin = identity?.department == null;
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [exportError, setExportError] = useState("");
  const chartsRef = useRef<HTMLDivElement>(null);

  const { data: metrics, isLoading, error } = useQuery({
    queryKey: ["admin-metrics", dateFrom, dateTo],
    queryFn: () => adminMetrics(token!, { date_from: dateFrom || undefined, date_to: dateTo || undefined }),
    enabled: !!token,
  });

  if (isLoading) return <Spinner label="Loading metrics…" />;
  if (error) return <ErrorBanner message={ErrorMessage(error)} />;
  if (!metrics) return null;

  const teams = isSuperAdmin && metrics.by_department ? Object.keys(metrics.by_department).sort() : [];
  const activeMetrics =
    isSuperAdmin && teamFilter !== "All Teams" && metrics.by_department
      ? metrics.by_department[teamFilter]
      : metrics;
  const scopeLabel = isSuperAdmin ? teamFilter : identity?.department ?? "";

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
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-wrap items-end gap-4">
          {isSuperAdmin && teams.length > 0 && (
            <div className="max-w-xs">
              <label className="mb-1.5 block text-sm text-ink-muted">Team</label>
              <select
                value={teamFilter}
                onChange={(e) => onTeamChange(e.target.value)}
                className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink"
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
          <div>
            <label className="mb-1.5 block text-sm text-ink-muted">From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm text-ink-muted">To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink"
            />
          </div>
          {(dateFrom || dateTo) && (
            <Button
              onClick={() => {
                setDateFrom("");
                setDateTo("");
              }}
            >
              Clear Range
            </Button>
          )}
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
        <MetricCharts metrics={activeMetrics} showDepartment={isSuperAdmin && teamFilter === "All Teams"} />
        <ThemeCharts topThemes={activeMetrics.top_themes} trend={activeMetrics.theme_trend} />
      </div>
    </div>
  );
}

export function AdminHomePage() {
  const { identity } = useAuth();
  const [teamFilter, setTeamFilter] = useState("All Teams");
  const isSuperAdmin = identity?.department == null;

  const departmentFilter = isSuperAdmin
    ? teamFilter !== "All Teams"
      ? teamFilter
      : undefined
    : identity?.department ?? undefined;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      {isSuperAdmin && (
        <div className="mb-4 flex justify-end">
          <Link to="/admin/team">
            <Button>Manage Team</Button>
          </Link>
        </div>
      )}
      <Tabs
        tabs={[
          {
            key: "dashboard",
            label: "Dashboard",
            content: <DashboardTab teamFilter={teamFilter} onTeamChange={setTeamFilter} />,
          },
          {
            key: "tickets",
            label: "Tickets",
            content: <AdminTicketTable departmentFilter={departmentFilter} />,
          },
        ]}
      />
    </div>
  );
}
