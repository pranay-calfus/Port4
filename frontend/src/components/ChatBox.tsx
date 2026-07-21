import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { escalateChat, sendChatMessage } from "../api/client";
import type { ChatTurn, Priority } from "../api/types";
import { PRIORITIES } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { ErrorBanner, ErrorMessage } from "./ui/Feedback";
import { SelectField, TextAreaField } from "./ui/FormField";
import { ChatBubble } from "./ChatBubble";

export function ChatBox() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [history, setHistory] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [priority, setPriority] = useState<Priority>("Medium");

  const sendMutation = useMutation({
    mutationFn: (message: string) => sendChatMessage(token!, message, history),
    onSuccess: (response) => {
      setHistory(response.history);
      setDraft("");
    },
  });

  const escalateMutation = useMutation({
    mutationFn: () => escalateChat(token!, history, priority),
    onSuccess: (ticket) => navigate(`/tickets/${ticket.id}`),
  });

  const hasUserTurn = history.some((turn) => turn.role === "user");

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-ink">Chat with our assistant</h2>
        <p className="mt-1 text-sm text-ink-muted">
          Describe your issue - once you're ready, raise it as a ticket and it'll be routed to the
          right team.
        </p>
      </div>

      <Card className="space-y-4">
        {history.length > 0 && (
          <div className="space-y-3">
            {history.map((turn, index) => (
              <ChatBubble
                key={index}
                isCustomer={turn.role === "user"}
                label={turn.role === "user" ? "You" : "Assistant"}
                text={turn.content}
              />
            ))}
          </div>
        )}

        <TextAreaField
          label="Message"
          rows={3}
          value={draft}
          disabled={sendMutation.isPending}
          onChange={(e) => setDraft(e.target.value)}
        />
        <Button
          variant="primary"
          disabled={!draft.trim() || sendMutation.isPending}
          onClick={() => sendMutation.mutate(draft.trim())}
        >
          {sendMutation.isPending ? "Sending…" : "Send"}
        </Button>
        {sendMutation.isError && <ErrorBanner message={ErrorMessage(sendMutation.error)} />}

        {hasUserTurn && (
          <div className="space-y-3 border-t border-surface-border pt-4">
            <SelectField
              label="How urgent is this?"
              value={priority}
              onChange={(e) => setPriority(e.target.value as Priority)}
            >
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </SelectField>
            <Button
              variant="primary"
              disabled={escalateMutation.isPending}
              onClick={() => escalateMutation.mutate()}
            >
              {escalateMutation.isPending ? "Raising…" : "Raise Ticket"}
            </Button>
            {escalateMutation.isError && (
              <ErrorBanner message={ErrorMessage(escalateMutation.error)} />
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
