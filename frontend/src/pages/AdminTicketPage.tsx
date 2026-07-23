import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  adminAssign,
  adminDeleteTicket,
  adminGetTicket,
  adminListAdmins,
  adminReassign,
  adminReply,
  adminUpdateStatus,
} from "../api/client";
import { DEPARTMENTS, PRIORITIES, TICKET_STATUSES } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { STATUS_COLORS, statusLabel } from "../lib/colors";
import { Accordion } from "../components/ui/Accordion";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ErrorBanner, ErrorMessage, Spinner } from "../components/ui/Feedback";
import { SelectField, TextAreaField } from "../components/ui/FormField";
import { Modal } from "../components/ui/Modal";
import { TicketAiCard } from "../components/TicketAiCard";
import { PriorityHint } from "../components/PriorityHint";
import { ConversationView } from "../components/ConversationView";
import { TicketTimeline } from "../components/TicketTimeline";
import { ManualRoutingPanel } from "../components/ManualRoutingPanel";

export function AdminTicketPage() {
  const { ticketId } = useParams();
  const id = Number(ticketId);
  const { token } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const queryKey = ["admin-ticket", id];
  const { data: ticket, isLoading, error } = useQuery({
    queryKey,
    queryFn: () => adminGetTicket(token!, id),
    enabled: !!token && !Number.isNaN(id),
  });

  const { data: admins } = useQuery({
    queryKey: ["admin-admins"],
    queryFn: () => adminListAdmins(token!),
    enabled: !!token,
  });

  const [statusValue, setStatusValue] = useState("");
  const [departmentValue, setDepartmentValue] = useState("");
  const [priorityValue, setPriorityValue] = useState("");
  const [assigneeValue, setAssigneeValue] = useState("");
  const [replyText, setReplyText] = useState("");
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  useEffect(() => {
    if (!ticket) return;
    setStatusValue(ticket.status);
    setDepartmentValue(ticket.department);
    setPriorityValue(ticket.priority);
    setAssigneeValue(ticket.assigned_admin_id ? String(ticket.assigned_admin_id) : "");
  }, [ticket]);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey });
    queryClient.invalidateQueries({ queryKey: ["admin-tickets"] });
    queryClient.invalidateQueries({ queryKey: ["admin-metrics"] });
  };

  const statusMutation = useMutation({
    mutationFn: () => adminUpdateStatus(token!, id, statusValue),
    onSuccess: invalidate,
  });

  const reassignMutation = useMutation({
    mutationFn: () => adminReassign(token!, id, departmentValue, priorityValue),
    onSuccess: invalidate,
  });

  const assignMutation = useMutation({
    mutationFn: () => adminAssign(token!, id, Number(assigneeValue)),
    onSuccess: invalidate,
  });

  const replyMutation = useMutation({
    mutationFn: (message: string) => adminReply(token!, id, message),
    onSuccess: () => {
      setReplyText("");
      invalidate();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => adminDeleteTicket(token!, id),
    onSuccess: () => navigate("/admin"),
  });

  if (isLoading) return <Spinner label="Loading ticket…" />;
  if (error) return <ErrorBanner message={ErrorMessage(error)} />;
  if (!ticket) return null;

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">
      <Link to="/admin" className="text-sm text-ink-muted hover:text-ink">
        ← Back to Tickets
      </Link>

      <Card accent={STATUS_COLORS[ticket.status]} className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-2xl font-bold text-ink">
            {ticket.ticket_number} — {ticket.title}
          </h1>
          <Button variant="danger" onClick={() => setShowDeleteModal(true)}>
            Delete
          </Button>
        </div>

        <p className="text-sm text-ink-muted">
          Requester: <strong className="text-ink">{ticket.user.name}</strong> ({ticket.user.email}) ·
          Status: <strong className="text-ink">{statusLabel(ticket.status)}</strong> · Priority:{" "}
          <strong className="text-ink">{ticket.priority}</strong> · Department:{" "}
          <strong className="text-ink">{ticket.department}</strong>
        </p>

        <TicketAiCard ticket={ticket} />
        <PriorityHint currentPriority={ticket.priority} aiPriority={ticket.ai_priority} />

        <Accordion title="Manual Routing Comparison" storageKey="manual-routing-panel">
          <ManualRoutingPanel ticket={ticket} />
        </Accordion>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="space-y-2">
            <SelectField
              label="Status"
              value={statusValue}
              onChange={(e) => setStatusValue(e.target.value)}
            >
              {TICKET_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {statusLabel(s)}
                </option>
              ))}
            </SelectField>
            <Button className="w-full" onClick={() => statusMutation.mutate()} disabled={statusMutation.isPending}>
              Update Status
            </Button>
            {statusMutation.isError && <ErrorBanner message={ErrorMessage(statusMutation.error)} />}
          </div>

          <div className="space-y-2">
            <SelectField
              label="Department"
              value={departmentValue}
              onChange={(e) => setDepartmentValue(e.target.value)}
            >
              {DEPARTMENTS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </SelectField>
            <SelectField
              label="Priority"
              value={priorityValue}
              onChange={(e) => setPriorityValue(e.target.value)}
            >
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </SelectField>
            <Button
              className="w-full"
              onClick={() => reassignMutation.mutate()}
              disabled={reassignMutation.isPending}
            >
              Reassign
            </Button>
            {reassignMutation.isError && <ErrorBanner message={ErrorMessage(reassignMutation.error)} />}
          </div>

          {admins && admins.length > 0 && (
            <div className="space-y-2">
              <SelectField
                label="Assign to"
                value={assigneeValue}
                onChange={(e) => setAssigneeValue(e.target.value)}
              >
                <option value="">Select an admin</option>
                {admins.map((admin) => (
                  <option key={admin.id} value={admin.id}>
                    {admin.name} ({admin.department ?? "super-admin"})
                  </option>
                ))}
              </SelectField>
              <Button
                className="w-full"
                disabled={!assigneeValue || assignMutation.isPending}
                onClick={() => assignMutation.mutate()}
              >
                Assign
              </Button>
              {assignMutation.isError && <ErrorBanner message={ErrorMessage(assignMutation.error)} />}
            </div>
          )}
        </div>

        <ConversationView messages={ticket.messages} />
        <Accordion title="Timeline" storageKey="admin-ticket-timeline">
          <TicketTimeline activity={ticket.activity} />
        </Accordion>

        {ticket.status === "CLOSED" ? (
          <p className="text-sm text-ink-muted">This ticket is closed.</p>
        ) : (
          <div className="space-y-3">
            <TextAreaField
              label="Reply to customer"
              rows={3}
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
            />
            <Button
              variant="primary"
              disabled={!replyText.trim() || replyMutation.isPending}
              onClick={() => replyMutation.mutate(replyText.trim())}
            >
              Send Reply
            </Button>
            {replyMutation.isError && <ErrorBanner message={ErrorMessage(replyMutation.error)} />}
          </div>
        )}
      </Card>

      {showDeleteModal && (
        <Modal title="Delete ticket" onClose={() => setShowDeleteModal(false)}>
          <p className="text-sm text-ink-muted">
            Permanently delete <strong className="text-ink">{ticket.ticket_number}</strong>? This
            removes its full message history and activity log too. This cannot be undone.
          </p>
          {deleteMutation.isError && <ErrorBanner message={ErrorMessage(deleteMutation.error)} />}
          <div className="mt-4 flex justify-end gap-2">
            <Button onClick={() => setShowDeleteModal(false)}>Cancel</Button>
            <Button
              variant="danger"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
            >
              Delete Permanently
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}
