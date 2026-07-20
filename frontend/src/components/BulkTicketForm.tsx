import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { bulkCreateTickets } from "../api/client";
import type { TicketDetailOut } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { ErrorBanner, ErrorMessage, SuccessBanner } from "./ui/Feedback";
import { TicketAiCard } from "./TicketAiCard";
import { RawJsonBlock } from "./RawJsonBlock";

interface Box {
  id: number;
  value: string;
}

export function BulkTicketForm() {
  const { token } = useAuth();
  const [boxes, setBoxes] = useState<Box[]>([{ id: 0, value: "" }]);
  const [nextId, setNextId] = useState(1);
  const [createdTickets, setCreatedTickets] = useState<TicketDetailOut[] | null>(null);
  const [formError, setFormError] = useState("");

  const mutation = useMutation({
    mutationFn: (messages: string[]) => bulkCreateTickets(token!, messages),
    onSuccess: (tickets) => {
      setCreatedTickets(tickets);
      setBoxes([{ id: nextId, value: "" }]);
      setNextId((prev) => prev + 1);
    },
  });

  function updateBox(id: number, value: string) {
    setBoxes((prev) => prev.map((box) => (box.id === id ? { ...box, value } : box)));
  }

  function addBox() {
    setBoxes((prev) => [...prev, { id: nextId, value: "" }]);
    setNextId((prev) => prev + 1);
  }

  function removeBox(id: number) {
    setBoxes((prev) => prev.filter((box) => box.id !== id));
  }

  function handleSubmit() {
    const messages = boxes.map((box) => box.value.trim()).filter(Boolean);
    if (messages.length === 0) {
      setFormError("Enter at least one ticket description before routing.");
      return;
    }
    setFormError("");
    mutation.mutate(messages);
  }

  const submitting = mutation.isPending;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-ink">Describe your issue(s)</h2>
        <p className="mt-1 text-sm text-ink-muted">
          Paste one or more issues below - each becomes its own ticket, classified independently and
          routed to the right team.
        </p>
      </div>

      <Card className="space-y-3">
        {boxes.map((box, index) => (
          <div key={box.id} className="flex items-start gap-2">
            <textarea
              aria-label={`Ticket ${index + 1}`}
              placeholder={`Describe issue ${index + 1}...`}
              value={box.value}
              disabled={submitting}
              onChange={(e) => updateBox(box.id, e.target.value)}
              rows={3}
              className="w-full flex-1 resize-y rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-muted focus:outline-none focus:ring-1 focus:ring-accent"
            />
            {boxes.length > 1 && !submitting && (
              <button
                type="button"
                onClick={() => removeBox(box.id)}
                className="rounded-md border border-surface-border px-2 py-1 text-xs text-ink-muted hover:text-ink"
                aria-label="Remove ticket box"
              >
                ✕
              </button>
            )}
          </div>
        ))}
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={addBox}
            disabled={submitting}
            className="flex h-8 w-8 items-center justify-center rounded-md border border-surface-border text-ink-muted hover:text-ink"
            aria-label="Add another ticket box"
          >
            ➕
          </button>
          <Button variant="primary" onClick={handleSubmit} disabled={submitting}>
            {submitting ? "Routing…" : "Route All Tickets"}
          </Button>
        </div>
        {formError && <ErrorBanner message={formError} />}
        {mutation.isError && <ErrorBanner message={ErrorMessage(mutation.error)} />}
      </Card>

      {createdTickets && createdTickets.length > 0 && (
        <div className="space-y-4">
          <SuccessBanner message={`Created ${createdTickets.length} ticket(s).`} />
          {createdTickets.map((ticket) => (
            <Card key={ticket.id} className="space-y-4">
              <div className="flex items-center justify-between">
                <Link to={`/tickets/${ticket.id}`} className="font-semibold text-ink hover:underline">
                  {ticket.ticket_number} — {ticket.title}
                </Link>
              </div>
              <TicketAiCard ticket={ticket} />
              <RawJsonBlock ticket={ticket} />
            </Card>
          ))}
          <Button onClick={() => setCreatedTickets(null)}>Dismiss</Button>
        </div>
      )}
    </div>
  );
}
