import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { escalateChat, sendChatMessage } from "../api/client";
import type { ChatTurn, Priority } from "../api/types";
import { PRIORITIES } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { ErrorBanner, ErrorMessage, SuccessBanner } from "./ui/Feedback";
import { SelectField, TextAreaField } from "./ui/FormField";
import { ChatBubble } from "./ChatBubble";

export function ChatBox() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [history, setHistory] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [priority, setPriority] = useState<Priority>("Medium");
  const [feedbackReceived, setFeedbackReceived] = useState(false);

  const sendMutation = useMutation({
    mutationFn: (message: string) => sendChatMessage(token!, message, history),
    onSuccess: (response) => {
      setHistory(response.history);
      setDraft("");
    },
  });

  const escalateMutation = useMutation({
    mutationFn: () => escalateChat(token!, history, priority),
    onSuccess: (result) => {
      if (result.type === "ticket") {
        navigate(`/tickets/${result.ticket.id}`);
        return;
      }
      setHistory([]);
      setFeedbackReceived(true);
    },
  });

  const hasUserTurn = history.some((turn) => turn.role === "user");

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-ink">Chat with our assistant</h2>
        <p className="mt-1 text-sm text-ink-muted">
          Tell us about an issue or share your feedback - we'll automatically route it to the
          right place, whether that's a support ticket or our Product &amp; CX team.
        </p>
      </div>

      {feedbackReceived && (
        <SuccessBanner message="Thanks for your feedback - our Product & CX team will review it." />
      )}

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
          onChange={(e) => {
            setDraft(e.target.value);
            setFeedbackReceived(false);
          }}
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
              label="If this is a support issue, how urgent is it?"
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
              {escalateMutation.isPending ? "Submitting…" : "Submit"}
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
