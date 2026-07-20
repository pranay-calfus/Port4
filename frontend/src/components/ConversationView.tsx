import type { MessageOut } from "../api/types";

export function ConversationView({ messages }: { messages: MessageOut[] }) {
  return (
    <div>
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-ink-muted">Conversation</p>
      <div className="space-y-3">
        {messages.map((message) => {
          const isCustomer = message.sender_type === "USER";
          return (
            <div
              key={message.id}
              className={`rounded-lg border border-surface-border px-4 py-3 ${
                isCustomer ? "" : "bg-white/[0.03]"
              }`}
            >
              <p className="mb-1 text-xs uppercase tracking-wide text-ink-muted">{message.sender_type}</p>
              <p className="whitespace-pre-wrap text-sm text-ink">{message.message}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
