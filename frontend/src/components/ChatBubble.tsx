export function ChatBubble({
  isCustomer,
  label,
  text,
}: {
  isCustomer: boolean;
  label: string;
  text: string;
}) {
  return (
    <div
      className={`rounded-lg border border-surface-border px-4 py-3 ${
        isCustomer ? "" : "bg-white/[0.03]"
      }`}
      style={
        isCustomer
          ? undefined
          : { borderLeftColor: "var(--color-brand)", borderLeftWidth: "3px" }
      }
    >
      <p className="mb-1 text-xs uppercase tracking-wide text-ink-muted">{label}</p>
      <p className="whitespace-pre-wrap text-sm text-ink">{text}</p>
    </div>
  );
}
