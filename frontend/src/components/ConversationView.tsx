import type { MessageOut } from "../api/types";
import { ChatBubble } from "./ChatBubble";

export function ConversationView({ messages }: { messages: MessageOut[] }) {
  return (
    <div>
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-ink-muted">Conversation</p>
      <div className="space-y-3">
        {messages.map((message) => (
          <ChatBubble
            key={message.id}
            isCustomer={message.sender_type === "USER"}
            label={message.sender_type}
            text={message.message}
          />
        ))}
      </div>
    </div>
  );
}
