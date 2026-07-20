import type { TicketDetailOut } from "../api/types";

export function RawJsonBlock({ ticket }: { ticket: TicketDetailOut }) {
  const payload = {
    success: true,
    data: {
      category: ticket.ai_category,
      priority: ticket.ai_priority,
      assignedTeam: ticket.department,
      emotion: ticket.ai_emotion,
      reasoning: ticket.ai_summary,
      confidence: ticket.ai_confidence,
    },
    ticketNumber: ticket.ticket_number,
    status: ticket.status,
  };

  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">
        Raw JSON Response
      </p>
      <pre className="overflow-x-auto rounded-md border border-surface-border bg-black/40 p-4 text-xs text-green-400">
        {JSON.stringify(payload, null, 2)}
      </pre>
    </div>
  );
}
