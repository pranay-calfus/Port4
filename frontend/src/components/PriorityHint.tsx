export function PriorityHint({
  currentPriority,
  aiPriority,
}: {
  currentPriority: string;
  aiPriority: string | null;
}) {
  if (!aiPriority || aiPriority === currentPriority) return null;

  return (
    <div className="rounded-md border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-sm text-blue-400">
      You set priority to <strong>{currentPriority}</strong> - the AI suggested{" "}
      <strong>{aiPriority}</strong> for this ticket.
    </div>
  );
}
