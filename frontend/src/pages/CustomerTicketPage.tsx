import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { acceptSolution, getMyTicket, reopenTicket, replyToTicket } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { statusLabel } from "../lib/colors";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ErrorBanner, ErrorMessage, Spinner } from "../components/ui/Feedback";
import { TextAreaField } from "../components/ui/FormField";
import { TicketAiCard } from "../components/TicketAiCard";
import { PriorityHint } from "../components/PriorityHint";
import { ConversationView } from "../components/ConversationView";
import { TicketTimeline } from "../components/TicketTimeline";

export function CustomerTicketPage() {
  const { ticketId } = useParams();
  const id = Number(ticketId);
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [replyText, setReplyText] = useState("");

  const queryKey = ["my-ticket", id];
  const { data: ticket, isLoading, error } = useQuery({
    queryKey,
    queryFn: () => getMyTicket(token!, id),
    enabled: !!token && !Number.isNaN(id),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey });
    queryClient.invalidateQueries({ queryKey: ["my-tickets"] });
  };

  const replyMutation = useMutation({
    mutationFn: (message: string) => replyToTicket(token!, id, message),
    onSuccess: () => {
      setReplyText("");
      invalidate();
    },
  });

  const acceptMutation = useMutation({
    mutationFn: () => acceptSolution(token!, id),
    onSuccess: invalidate,
  });

  const reopenMutation = useMutation({
    mutationFn: () => reopenTicket(token!, id),
    onSuccess: invalidate,
  });

  if (isLoading) return <Spinner label="Loading ticket…" />;
  if (error) return <ErrorBanner message={ErrorMessage(error)} />;
  if (!ticket) return null;

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">
      <Link to="/" className="text-sm text-ink-muted hover:text-ink">
        ← Back to My Tickets
      </Link>

      <Card className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-ink">
            {ticket.ticket_number} — {ticket.title}
          </h1>
          <p className="mt-1 text-sm text-ink-muted">
            Status: <strong className="text-ink">{statusLabel(ticket.status)}</strong> · Priority:{" "}
            <strong className="text-ink">{ticket.priority}</strong> · Department:{" "}
            <strong className="text-ink">{ticket.department}</strong>
          </p>
        </div>

        <TicketAiCard ticket={ticket} />
        <PriorityHint currentPriority={ticket.priority} aiPriority={ticket.ai_priority} />

        <ConversationView messages={ticket.messages} />
        <TicketTimeline activity={ticket.activity} label="🕒 TIMELINE" />

        {ticket.status === "CLOSED" ? (
          <p className="text-sm text-ink-muted">
            This ticket is closed. Please open a new ticket for any further issues.
          </p>
        ) : (
          <div className="space-y-3">
            <TextAreaField
              label="Reply"
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

            {ticket.status === "RESOLVED" && (
              <div className="flex gap-3 pt-2">
                <Button onClick={() => acceptMutation.mutate()} disabled={acceptMutation.isPending}>
                  ✅ Accept Solution
                </Button>
                <Button onClick={() => reopenMutation.mutate()} disabled={reopenMutation.isPending}>
                  ↩️ Reopen (not resolved)
                </Button>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
