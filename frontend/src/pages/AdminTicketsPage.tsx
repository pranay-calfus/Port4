import { useState } from "react";
import { AdminTicketTable } from "../components/AdminTicketTable";
import { useAuth } from "../context/AuthContext";
import { ASSIGNED_TEAMS } from "../api/types";
import { isSuperAdmin } from "../lib/roles";

export function AdminTicketsPage() {
  const { identity } = useAuth();
  const superAdmin = isSuperAdmin(identity);
  const [teamFilter, setTeamFilter] = useState("All Teams");

  const departmentFilter = superAdmin
    ? teamFilter !== "All Teams"
      ? teamFilter
      : undefined
    : identity?.department ?? undefined;

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-6 py-8">
      <h1 className="text-2xl font-bold text-ink">Tickets</h1>
      {superAdmin && (
        <div className="max-w-xs">
          <label className="mb-1.5 block text-sm text-ink-muted">Team</label>
          <select
            value={teamFilter}
            onChange={(e) => setTeamFilter(e.target.value)}
            className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink"
          >
            <option value="All Teams">All Teams</option>
            {ASSIGNED_TEAMS.map((team) => (
              <option key={team} value={team}>
                {team}
              </option>
            ))}
          </select>
        </div>
      )}
      <AdminTicketTable departmentFilter={departmentFilter} />
    </div>
  );
}
