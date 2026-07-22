import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { bulkCreateTickets } from "../api/client";
import type { EscalateResponse } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { FEEDBACK_CATEGORY_COLORS, SENTIMENT_COLORS } from "../lib/colors";
import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";
import { Card, CardLabel } from "./ui/Card";
import { ErrorBanner, ErrorMessage, SuccessBanner } from "./ui/Feedback";
import { TicketAiCard } from "./TicketAiCard";

interface Box {
  id: number;
  value: string;
}

export function BulkTicketForm() {
  const { token } = useAuth();
  const [boxes, setBoxes] = useState<Box[]>([{ id: 0, value: "" }]);
  const [nextId, setNextId] = useState(1);
  const [results, setResults] = useState<EscalateResponse[] | null>(null);
  const [formError, setFormError] = useState("");

  const mutation = useMutation({
    mutationFn: (messages: string[]) => bulkCreateTickets(token!, messages),
    onSuccess: (submissions) => {
      setResults(submissions);
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
      setFormError("Enter at least one submission before continuing.");
      return;
    }
    setFormError("");
    mutation.mutate(messages);
  }

  const submitting = mutation.isPending;
  const ticketCount = results?.filter((r) => r.type === "ticket").length ?? 0;
  const feedbackCount = results?.filter((r) => r.type === "feedback").length ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-ink">Submit multiple items at once</h2>
        <p className="mt-1 text-sm text-ink-muted">
          Paste one or more issues or pieces of feedback below - each is classified
          independently, becoming its own support ticket or a piece of feedback for our Product
          &amp; CX team.
        </p>
      </div>

      <Card className="space-y-3">
        {boxes.map((box, index) => (
          <div key={box.id} className="flex items-start gap-2">
            <textarea
              aria-label={`Submission ${index + 1}`}
              placeholder={`Describe issue or feedback ${index + 1}...`}
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
                aria-label="Remove submission box"
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
            aria-label="Add another submission box"
          >
            ➕
          </button>
          <Button variant="primary" onClick={handleSubmit} disabled={submitting}>
            {submitting ? "Submitting…" : "Submit All"}
          </Button>
        </div>
        {formError && <ErrorBanner message={formError} />}
        {mutation.isError && <ErrorBanner message={ErrorMessage(mutation.error)} />}
      </Card>

      {results && results.length > 0 && (
        <div className="space-y-4">
          <SuccessBanner
            message={`Created ${ticketCount} ticket(s) and received ${feedbackCount} piece(s) of feedback.`}
          />
          {results.map((result) =>
            result.type === "ticket" ? (
              <Card key={`ticket-${result.ticket.id}`} className="space-y-4">
                <Link
                  to={`/tickets/${result.ticket.id}`}
                  className="font-semibold text-ink hover:underline"
                >
                  {result.ticket.ticket_number} — {result.ticket.title}
                </Link>
                <TicketAiCard ticket={result.ticket} />
              </Card>
            ) : (
              <Card key={`feedback-${result.feedback.id}`} className="space-y-3">
                <CardLabel>Feedback received</CardLabel>
                <div className="flex flex-wrap gap-2">
                  {result.feedback.sentiment && (
                    <Badge
                      color={SENTIMENT_COLORS[result.feedback.sentiment]}
                      label={result.feedback.sentiment}
                    />
                  )}
                  {result.feedback.category && (
                    <Badge
                      color={FEEDBACK_CATEGORY_COLORS[result.feedback.category]}
                      label={result.feedback.category}
                    />
                  )}
                </div>
                <p className="text-sm text-ink">{result.feedback.ai_summary ?? result.feedback.raw_text}</p>
              </Card>
            )
          )}
          <Button onClick={() => setResults(null)}>Dismiss</Button>
        </div>
      )}
    </div>
  );
}
