import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listMyTickets } from "../api/client";
import { TICKET_STATUSES } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { STATUS_COLORS, statusLabel } from "../lib/colors";
import { Badge } from "./ui/Badge";
import { Card } from "./ui/Card";
import { ErrorBanner, ErrorMessage, Spinner } from "./ui/Feedback";

export function TicketList() {
  const { token } = useAuth();
  const [statusFilter, setStatusFilter] = useState("All");

  const { data: tickets, isLoading, error } = useQuery({
    queryKey: ["my-tickets"],
    queryFn: () => listMyTickets(token!),
    enabled: !!token,
  });

  if (isLoading) return <Spinner label="Loading tickets…" />;
  if (error) return <ErrorBanner message={ErrorMessage(error)} />;

  const filtered = (tickets ?? []).filter(
    (ticket) => statusFilter === "All" || ticket.status === statusFilter
  );

  return (
    <Card className="space-y-4">
      <div className="max-w-xs">
        <label className="mb-1.5 block text-sm text-ink-muted">Filter by status</label>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand focus:border-brand"
        >
          <option value="All">All</option>
          {TICKET_STATUSES.map((status) => (
            <option key={status} value={status}>
              {statusLabel(status)}
            </option>
          ))}
        </select>
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-ink-muted">No tickets match this filter.</p>
      ) : (
        <div className="space-y-2">
          {filtered.map((ticket) => (
            <Link
              key={ticket.id}
              to={`/tickets/${ticket.id}`}
              className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-surface-border px-4 py-3 text-sm text-ink transition-colors hover:bg-white/5"
              style={{ borderLeftColor: STATUS_COLORS[ticket.status], borderLeftWidth: "3px" }}
            >
              <span>
                {ticket.ticket_number} · {ticket.title} · {ticket.priority} priority
              </span>
              <Badge color={STATUS_COLORS[ticket.status]} label={statusLabel(ticket.status)} />
            </Link>
          ))}
        </div>
      )}
    </Card>
  );
}
