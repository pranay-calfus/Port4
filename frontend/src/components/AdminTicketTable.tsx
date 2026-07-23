import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { adminDeleteTicket, adminListTickets } from "../api/client";
import { PRIORITIES, TICKET_STATUSES, type TicketOut } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { statusLabel } from "../lib/colors";
import { formatDateTime } from "../lib/format";
import { Accordion } from "./ui/Accordion";
import { Button } from "./ui/Button";
import { ErrorBanner, ErrorMessage, Spinner } from "./ui/Feedback";
import { Modal } from "./ui/Modal";

export function AdminTicketTable({ departmentFilter }: { departmentFilter?: string }) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [priority, setPriority] = useState("All");
  const [status, setStatus] = useState("All");
  const [search, setSearch] = useState("");
  const [pendingDelete, setPendingDelete] = useState<TicketOut | null>(null);

  const queryKey = ["admin-tickets", departmentFilter, priority, status, search];
  const { data: tickets, isLoading, error } = useQuery({
    queryKey,
    queryFn: () =>
      adminListTickets(token!, {
        department: departmentFilter,
        priority: priority === "All" ? undefined : priority,
        status_filter: status === "All" ? undefined : status,
        search: search || undefined,
      }),
    enabled: !!token,
  });

  const deleteMutation = useMutation({
    mutationFn: (ticketId: number) => adminDeleteTicket(token!, ticketId),
    onSuccess: () => {
      setPendingDelete(null);
      queryClient.invalidateQueries({ queryKey: ["admin-tickets"] });
    },
  });

  return (
    <div className="space-y-4">
      {departmentFilter && (
        <p className="text-xs text-ink-muted">
          Pinned to <strong>{departmentFilter}</strong> - change the team filter above to switch.
        </p>
      )}
      <Accordion title="Filters" defaultOpen storageKey="admin-ticket-filters">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <label className="mb-1.5 block text-sm text-ink-muted">Priority</label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink"
            >
              <option value="All">All</option>
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-sm text-ink-muted">Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink"
            >
              <option value="All">All</option>
              {TICKET_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {statusLabel(s)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-sm text-ink-muted">Search</label>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Ticket #, title, or description"
              className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-muted"
            />
          </div>
        </div>
      </Accordion>

      {isLoading && <Spinner label="Loading tickets…" />}
      {error && <ErrorBanner message={ErrorMessage(error)} />}

      {tickets && (
        <>
          <p className="text-sm text-ink-muted">{tickets.length} ticket(s)</p>
          {tickets.length === 0 ? (
            <p className="text-sm text-ink-muted">No tickets match this filter.</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-surface-border">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-surface-border text-xs uppercase tracking-wide text-ink-muted">
                  <tr>
                    <th className="px-4 py-3">Ticket</th>
                    <th className="px-4 py-3">Title</th>
                    <th className="px-4 py-3">Team</th>
                    <th className="px-4 py-3">Priority</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Created</th>
                    <th className="px-4 py-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((ticket) => (
                    <tr key={ticket.id} className="border-b border-surface-border last:border-0">
                      <td className="px-4 py-3 text-ink">{ticket.ticket_number}</td>
                      <td className="px-4 py-3 text-ink">{ticket.title}</td>
                      <td className="px-4 py-3 text-ink-muted">{ticket.department}</td>
                      <td className="px-4 py-3 text-ink-muted">{ticket.priority}</td>
                      <td className="px-4 py-3 text-ink-muted">{statusLabel(ticket.status)}</td>
                      <td className="px-4 py-3 whitespace-nowrap text-ink-muted">
                        {formatDateTime(ticket.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          <Link to={`/admin/tickets/${ticket.id}`}>
                            <Button className="px-2 py-1 text-xs">Open</Button>
                          </Link>
                          <Button
                            variant="danger"
                            className="px-2 py-1 text-xs"
                            onClick={() => setPendingDelete(ticket)}
                          >
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {pendingDelete && (
        <Modal title="Delete ticket" onClose={() => setPendingDelete(null)}>
          <p className="text-sm text-ink-muted">
            Permanently delete <strong className="text-ink">{pendingDelete.ticket_number}</strong>?
            This removes its full message history and activity log too. This cannot be undone.
          </p>
          {deleteMutation.isError && <ErrorBanner message={ErrorMessage(deleteMutation.error)} />}
          <div className="mt-4 flex justify-end gap-2">
            <Button onClick={() => setPendingDelete(null)}>Cancel</Button>
            <Button
              variant="danger"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate(pendingDelete.id)}
            >
              Delete Permanently
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}
