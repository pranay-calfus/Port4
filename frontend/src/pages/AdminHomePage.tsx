import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adminMetrics } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { AdminTicketTable } from "../components/AdminTicketTable";
import { StatRow } from "../components/StatRow";
import { MetricCharts } from "../components/MetricCharts";
import { Tabs } from "../components/ui/Tabs";
import { ErrorBanner, ErrorMessage, Spinner } from "../components/ui/Feedback";

function DashboardTab({ teamFilter, onTeamChange }: { teamFilter: string; onTeamChange: (v: string) => void }) {
  const { token, identity } = useAuth();
  const isSuperAdmin = identity?.department == null;

  const { data: metrics, isLoading, error } = useQuery({
    queryKey: ["admin-metrics"],
    queryFn: () => adminMetrics(token!),
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

  return (
    <div className="space-y-6">
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
      <StatRow metrics={activeMetrics} />
      <MetricCharts metrics={activeMetrics} showDepartment={isSuperAdmin && teamFilter === "All Teams"} />
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
