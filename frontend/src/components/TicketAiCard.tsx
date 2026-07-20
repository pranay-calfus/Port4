import type { TicketDetailOut } from "../api/types";
import { EMOTION_EMOJI } from "../api/types";
import { EMOTION_COLORS, PRIORITY_COLORS } from "../lib/colors";
import { formatDateTime } from "../lib/format";
import { Badge } from "./ui/Badge";
import { Card, CardLabel } from "./ui/Card";

export function TicketAiCard({ ticket }: { ticket: TicketDetailOut }) {
  if (!ticket.ai_summary) {
    return (
      <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-400">
        AI categorization isn't available for this ticket yet - it needs manual triage.
      </div>
    );
  }

  const priorityColor = PRIORITY_COLORS[ticket.ai_priority as keyof typeof PRIORITY_COLORS] ?? "#9ca3af";
  const emotionColor = EMOTION_COLORS[ticket.ai_emotion as keyof typeof EMOTION_COLORS] ?? "#9ca3af";
  const confidencePct = Math.round((ticket.ai_confidence ?? 0) * 100);
  const isLowConfidence = (ticket.ai_confidence ?? 1) < 0.65;

  return (
    <div className="space-y-3 border-l-2 border-l-green-500 pl-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Card>
          <CardLabel>Category</CardLabel>
          <p className="font-semibold text-ink">{ticket.ai_category}</p>
        </Card>
        <Card>
          <CardLabel>Priority</CardLabel>
          {ticket.ai_priority && <Badge color={priorityColor} label={ticket.ai_priority} />}
        </Card>
        <Card>
          <CardLabel>Emotion</CardLabel>
          {ticket.ai_emotion && (
            <Badge
              color={emotionColor}
              label={`${EMOTION_EMOJI[ticket.ai_emotion as keyof typeof EMOTION_EMOJI] ?? ""} ${ticket.ai_emotion}`}
            />
          )}
        </Card>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Card>
          <CardLabel>Assigned Team</CardLabel>
          <p className="font-semibold text-ink">{ticket.department}</p>
        </Card>
        <Card>
          <CardLabel>Confidence</CardLabel>
          <p className="mb-1.5 font-semibold text-ink">{confidencePct}%</p>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
            <div className="h-full bg-accent" style={{ width: `${confidencePct}%` }} />
          </div>
        </Card>
      </div>
      {isLowConfidence && (
        <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-400">
          Low confidence
        </div>
      )}
      <Card>
        <CardLabel>Reason</CardLabel>
        <p className="text-sm text-ink">{ticket.ai_summary}</p>
      </Card>
      <div className="flex justify-between text-xs text-ink-muted">
        <span>{ticket.ticket_number}</span>
        <span>Created {formatDateTime(ticket.created_at)}</span>
      </div>
    </div>
  );
}
