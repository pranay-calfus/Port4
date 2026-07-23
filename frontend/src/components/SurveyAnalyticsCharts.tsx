import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adminListSurveys, adminSurveyAnalytics } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { BRAND_ACCENT } from "../lib/colors";
import { Card, CardLabel } from "./ui/Card";
import { ErrorBanner, ErrorMessage, Spinner } from "./ui/Feedback";

function RatingDistribution({ distribution }: { distribution: Record<string, number> }) {
  const total = Object.values(distribution).reduce((sum, n) => sum + n, 0);
  return (
    <div className="space-y-1.5">
      {[5, 4, 3, 2, 1].map((star) => {
        const count = distribution[String(star)] ?? 0;
        const pct = total > 0 ? Math.round((count / total) * 100) : 0;
        return (
          <div key={star} className="flex items-center gap-2 text-xs text-ink-muted">
            <span className="w-8">{star}★</span>
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
              <div className="h-full bg-brand" style={{ width: `${pct}%` }} />
            </div>
            <span className="w-14 text-right">
              {count} ({pct}%)
            </span>
          </div>
        );
      })}
    </div>
  );
}

export function SurveyAnalyticsCharts({
  dateFrom,
  dateTo,
}: {
  dateFrom?: string;
  dateTo?: string;
}) {
  const { token } = useAuth();
  const [surveyId, setSurveyId] = useState("");

  const { data: surveys } = useQuery({
    queryKey: ["surveys"],
    queryFn: () => adminListSurveys(token!),
    enabled: !!token,
  });

  const { data: analytics, isLoading, error } = useQuery({
    queryKey: ["survey-analytics", surveyId, dateFrom, dateTo],
    queryFn: () => adminSurveyAnalytics(token!, Number(surveyId), { date_from: dateFrom, date_to: dateTo }),
    enabled: !!token && !!surveyId,
  });

  return (
    <div className="space-y-4">
      <div className="max-w-xs">
        <label className="mb-1.5 block text-sm text-ink-muted">Survey</label>
        <select
          value={surveyId}
          onChange={(e) => setSurveyId(e.target.value)}
          className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand focus:border-brand"
        >
          <option value="">Select a survey…</option>
          {surveys?.map((s) => (
            <option key={s.id} value={s.id}>
              {s.title}
            </option>
          ))}
        </select>
      </div>

      {!surveyId && <p className="text-sm text-ink-muted">Pick a survey to see its analytics.</p>}
      {isLoading && <Spinner label="Loading analytics…" />}
      {error && <ErrorBanner message={ErrorMessage(error)} />}

      {analytics && (
        <div className="space-y-4">
          <Card accent={BRAND_ACCENT}>
            <CardLabel>Total Responses</CardLabel>
            <p className="text-3xl font-bold text-ink">{analytics.total_responses}</p>
          </Card>
          {analytics.questions.map((q) => (
            <Card key={q.question_id} className="space-y-3">
              <div>
                <CardLabel>{q.question_text}</CardLabel>
                <p className="text-xs text-ink-muted">{q.response_count} response(s)</p>
              </div>
              {q.question_type === "rating" ? (
                <>
                  <p className="text-2xl font-bold text-ink">
                    {q.average_rating != null ? q.average_rating.toFixed(1) : "—"}{" "}
                    <span className="text-sm font-normal text-ink-muted">avg rating</span>
                  </p>
                  <RatingDistribution distribution={q.rating_distribution} />
                </>
              ) : q.most_common_answers.length > 0 ? (
                <div className="space-y-1.5">
                  <p className="text-xs uppercase tracking-wide text-ink-muted">Most common answers</p>
                  {q.most_common_answers.map((a, i) => (
                    <div key={i} className="flex items-center justify-between text-sm">
                      <span className="text-ink">{a.answer}</span>
                      <span className="text-ink-muted">{a.count}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-ink-muted">No answers yet.</p>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
