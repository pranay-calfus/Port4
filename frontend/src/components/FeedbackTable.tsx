import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listFeedback } from "../api/client";
import { ASSIGNED_TEAMS, FEEDBACK_CATEGORIES, SENTIMENTS, type FeedbackOut } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { FEEDBACK_CATEGORY_COLORS, SENTIMENT_COLORS, themeColor } from "../lib/colors";
import { formatDateTime } from "../lib/format";
import { Accordion } from "./ui/Accordion";
import { Badge } from "./ui/Badge";
import { Button } from "./ui/Button";
import { ErrorBanner, ErrorMessage, Spinner } from "./ui/Feedback";
import { Modal } from "./ui/Modal";

export function FeedbackTable() {
  const { token } = useAuth();
  const [sentiment, setSentiment] = useState("All");
  const [category, setCategory] = useState("All");
  const [team, setTeam] = useState("All");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [search, setSearch] = useState("");
  const [viewing, setViewing] = useState<FeedbackOut | null>(null);

  const queryKey = ["feedback", sentiment, category, team, dateFrom, dateTo, search];
  const { data: feedback, isLoading, error } = useQuery({
    queryKey,
    queryFn: () =>
      listFeedback(token!, {
        sentiment: sentiment === "All" ? undefined : sentiment,
        category: category === "All" ? undefined : category,
        team: team === "All" ? undefined : team,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        search: search || undefined,
      }),
    enabled: !!token,
  });

  return (
    <div className="space-y-4">
      <Accordion title="Filters" defaultOpen storageKey="feedback-filters">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <div>
            <label className="mb-1.5 block text-sm text-ink-muted">Sentiment</label>
            <select
              value={sentiment}
              onChange={(e) => setSentiment(e.target.value)}
              className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand focus:border-brand"
            >
              <option value="All">All</option>
              {SENTIMENTS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-sm text-ink-muted">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand focus:border-brand"
            >
              <option value="All">All</option>
              {FEEDBACK_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-sm text-ink-muted">Team</label>
            <select
              value={team}
              onChange={(e) => setTeam(e.target.value)}
              className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand focus:border-brand"
            >
              <option value="All">All</option>
              {ASSIGNED_TEAMS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-sm text-ink-muted">From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand focus:border-brand"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm text-ink-muted">To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand focus:border-brand"
            />
          </div>
        </div>
        <div className="mt-4">
          <label className="mb-1.5 block text-sm text-ink-muted">Search</label>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Feedback text or AI summary"
            className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-muted"
          />
        </div>
      </Accordion>

      {isLoading && <Spinner label="Loading feedback…" />}
      {error && <ErrorBanner message={ErrorMessage(error)} />}

      {feedback && (
        <>
          <p className="text-sm text-ink-muted">{feedback.length} item(s)</p>
          {feedback.length === 0 ? (
            <p className="text-sm text-ink-muted">No feedback matches this filter.</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-surface-border">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-surface-border text-xs uppercase tracking-wide text-ink-muted">
                  <tr>
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">User</th>
                    <th className="px-4 py-3">Sentiment</th>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-4 py-3">Team</th>
                    <th className="px-4 py-3">AI Summary</th>
                    <th className="px-4 py-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {feedback.map((item) => (
                    <tr key={item.id} className="border-b border-surface-border last:border-0">
                      <td className="px-4 py-3 whitespace-nowrap text-ink-muted">
                        {formatDateTime(item.created_at)}
                      </td>
                      <td className="px-4 py-3 text-ink-muted">User #{item.user_id}</td>
                      <td className="px-4 py-3">
                        {item.sentiment && (
                          <Badge color={SENTIMENT_COLORS[item.sentiment]} label={item.sentiment} />
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {item.category && (
                          <Badge color={FEEDBACK_CATEGORY_COLORS[item.category]} label={item.category} />
                        )}
                      </td>
                      <td className="px-4 py-3 text-ink-muted">{item.team ?? "—"}</td>
                      <td className="max-w-xs truncate px-4 py-3 text-ink-muted">
                        {item.ai_summary ?? "—"}
                      </td>
                      <td className="px-4 py-3">
                        <Button className="px-2 py-1 text-xs" onClick={() => setViewing(item)}>
                          View
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {viewing && (
        <Modal title="Feedback detail" onClose={() => setViewing(null)}>
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              {viewing.sentiment && (
                <Badge color={SENTIMENT_COLORS[viewing.sentiment]} label={viewing.sentiment} />
              )}
              {viewing.category && (
                <Badge color={FEEDBACK_CATEGORY_COLORS[viewing.category]} label={viewing.category} />
              )}
              {viewing.team && <Badge color="#9ca3af" label={viewing.team} />}
              {viewing.theme && <Badge color={themeColor(viewing.theme)} label={viewing.theme} />}
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-ink-muted">Submitted text</p>
              <p className="mt-1 text-sm text-ink">{viewing.raw_text}</p>
            </div>
            {viewing.ai_summary && (
              <div>
                <p className="text-xs uppercase tracking-wide text-ink-muted">AI summary</p>
                <p className="mt-1 text-sm text-ink">{viewing.ai_summary}</p>
              </div>
            )}
            {viewing.ai_reasoning && (
              <div>
                <p className="text-xs uppercase tracking-wide text-ink-muted">AI reasoning</p>
                <p className="mt-1 text-sm text-ink">{viewing.ai_reasoning}</p>
              </div>
            )}
            {viewing.ai_confidence != null && (
              <div>
                <p className="text-xs uppercase tracking-wide text-ink-muted">
                  Confidence: {Math.round(viewing.ai_confidence * 100)}%
                </p>
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full bg-brand"
                    style={{ width: `${Math.round(viewing.ai_confidence * 100)}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
