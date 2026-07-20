import { useState } from "react";
import { ASSIGNED_TEAMS, CATEGORIES, PRIORITIES, type TicketDetailOut } from "../api/types";
import { Button } from "./ui/Button";
import { Card, CardLabel } from "./ui/Card";
import { SelectField } from "./ui/FormField";

const MANUAL_BASELINE_SECONDS = 120;

interface ManualResult {
  seconds: number;
  category: string;
  priority: string;
  team: string;
}

function MatchRow({ label, yours, ai }: { label: string; yours: string; ai: string | null }) {
  const matches = !!ai && yours === ai;
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted">{label}</p>
      <p className="text-ink">
        {matches ? "✔️" : "⤬"} You: <strong>{yours}</strong>
      </p>
      <p className="text-ink-muted">AI: {ai ?? "—"}</p>
    </div>
  );
}

export function ManualRoutingPanel({ ticket }: { ticket: TicketDetailOut }) {
  const [timerStart, setTimerStart] = useState<number | null>(null);
  const [category, setCategory] = useState<string>(CATEGORIES[0]);
  const [priority, setPriority] = useState<string>(PRIORITIES[0]);
  const [team, setTeam] = useState<string>(ASSIGNED_TEAMS[0]);
  const [result, setResult] = useState<ManualResult | null>(null);

  function startTimer() {
    setResult(null);
    setTimerStart(performance.now());
  }

  function submitRouting() {
    if (timerStart == null) return;
    const seconds = (performance.now() - timerStart) / 1000;
    setResult({ seconds, category, priority, team });
    setTimerStart(null);
  }

  function reset() {
    setResult(null);
    setTimerStart(null);
  }

  const manualSeconds = result?.seconds ?? MANUAL_BASELINE_SECONDS;
  const aiSeconds = ticket.ai_processing_ms != null ? ticket.ai_processing_ms / 1000 : null;
  const pctFaster =
    aiSeconds != null && manualSeconds > 0
      ? Math.round(((manualSeconds - aiSeconds) / manualSeconds) * 100)
      : null;

  return (
    <Card className="space-y-4">
      <div>
        <CardLabel>⏱️ Manual Routing (for comparison)</CardLabel>
        <p className="text-sm text-ink-muted">
          Time yourself triaging this ticket the way a support agent would - pick a category, priority,
          and team - then compare that against the AI above.
        </p>
      </div>

      {timerStart == null && !result && <Button onClick={startTimer}>Start Manual Timer</Button>}

      {timerStart != null && (
        <div className="space-y-3">
          <div className="rounded-md border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-sm text-blue-400">
            Timer running...
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <SelectField label="Category" value={category} onChange={(e) => setCategory(e.target.value)}>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </SelectField>
            <SelectField label="Priority" value={priority} onChange={(e) => setPriority(e.target.value)}>
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </SelectField>
            <SelectField label="Team" value={team} onChange={(e) => setTeam(e.target.value)}>
              {ASSIGNED_TEAMS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </SelectField>
          </div>
          <Button variant="primary" onClick={submitRouting}>
            Submit Manual Routing
          </Button>
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="rounded-md border border-green-500/30 bg-green-500/10 px-3 py-2 text-sm text-green-400">
            Manual routing took {result.seconds.toFixed(1)} seconds.
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <MatchRow label="Category" yours={result.category} ai={ticket.ai_category} />
            <MatchRow label="Priority" yours={result.priority} ai={ticket.ai_priority} />
            <MatchRow label="Team" yours={result.team} ai={ticket.department} />
          </div>
          <Button onClick={reset}>Reset Manual Timer</Button>

          {aiSeconds != null && (
            <Card className="space-y-2">
              <CardLabel>Comparison</CardLabel>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div>
                  <p className="text-xs text-ink-muted">Manual time</p>
                  <p className="text-lg font-semibold text-ink">{manualSeconds.toFixed(1)}s</p>
                </div>
                <div>
                  <p className="text-xs text-ink-muted">AI time</p>
                  <p className="text-lg font-semibold text-ink">{aiSeconds.toFixed(2)}s</p>
                </div>
                <div>
                  <p className="text-xs text-ink-muted">Faster than manual</p>
                  <p className="text-lg font-semibold text-ink">{pctFaster}%</p>
                </div>
              </div>
              <p className="text-xs text-ink-muted">
                AI time is measured for this ticket. Based on your measured manual routing time.
              </p>
            </Card>
          )}
        </div>
      )}

      {!result && timerStart == null && (
        <p className="text-xs text-ink-muted">
          No manual timing taken yet this session - comparisons will use a typical ~
          {MANUAL_BASELINE_SECONDS}s manual triage baseline once available.
        </p>
      )}
    </Card>
  );
}
