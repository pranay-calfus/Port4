import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adminGetSurvey, adminListSurveyResponses, adminListSurveys } from "../api/client";
import type { SurveyResponse } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { formatDateTime } from "../lib/format";
import { Accordion } from "./ui/Accordion";
import { Button } from "./ui/Button";
import { ErrorBanner, ErrorMessage, Spinner } from "./ui/Feedback";
import { Modal } from "./ui/Modal";

export function SurveyResponsesTable({
  defaultDateFrom,
  defaultDateTo,
}: {
  defaultDateFrom?: string;
  defaultDateTo?: string;
}) {
  const { token } = useAuth();
  const [surveyId, setSurveyId] = useState("");
  // Seeded from the Surveys tab's shared time-range control, but stays
  // independently adjustable here - this table's date fields are a
  // row-level refinement of the shared range, not a duplicate of it.
  const [dateFrom, setDateFrom] = useState(defaultDateFrom ?? "");
  const [dateTo, setDateTo] = useState(defaultDateTo ?? "");
  const [rating, setRating] = useState("");
  const [questionId, setQuestionId] = useState("");
  const [userSearch, setUserSearch] = useState("");
  const [viewing, setViewing] = useState<SurveyResponse | null>(null);

  const { data: surveys } = useQuery({
    queryKey: ["surveys"],
    queryFn: () => adminListSurveys(token!),
    enabled: !!token,
  });

  const { data: selectedSurveyDetail } = useQuery({
    queryKey: ["survey", surveyId ? Number(surveyId) : null],
    queryFn: () => adminGetSurvey(token!, Number(surveyId)),
    enabled: !!token && !!surveyId,
  });

  const questionLabels = useMemo(() => {
    const labels: Record<number, string> = {};
    selectedSurveyDetail?.questions.forEach((q) => {
      labels[q.id] = q.question_text;
    });
    return labels;
  }, [selectedSurveyDetail]);

  const queryKey = ["survey-responses", surveyId, dateFrom, dateTo, rating, questionId];
  const { data: responses, isLoading, error } = useQuery({
    queryKey,
    queryFn: () =>
      adminListSurveyResponses(token!, {
        survey_id: surveyId ? Number(surveyId) : undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        rating: rating ? Number(rating) : undefined,
        question_id: questionId ? Number(questionId) : undefined,
      }),
    enabled: !!token,
  });

  const filteredResponses = useMemo(() => {
    if (!responses) return responses;
    const needle = userSearch.trim().toLowerCase();
    if (!needle) return responses;
    return responses.filter(
      (r) => r.user.name.toLowerCase().includes(needle) || r.user.email.toLowerCase().includes(needle)
    );
  }, [responses, userSearch]);

  function answerSummary(response: SurveyResponse) {
    return response.answers
      .map((a) => (Array.isArray(a.value) ? a.value.join(", ") : String(a.value)))
      .join(" · ");
  }

  return (
    <div className="space-y-4">
      <Accordion title="Filters" defaultOpen storageKey="survey-response-filters">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <div>
            <label className="mb-1.5 block text-sm text-ink-muted">Survey</label>
            <select
              value={surveyId}
              onChange={(e) => {
                setSurveyId(e.target.value);
                setQuestionId("");
              }}
              className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand focus:border-brand"
            >
              <option value="">All</option>
              {surveys?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.title}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-sm text-ink-muted">Question</label>
            <select
              value={questionId}
              onChange={(e) => setQuestionId(e.target.value)}
              disabled={!selectedSurveyDetail}
              className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink disabled:opacity-50"
            >
              <option value="">All</option>
              {selectedSurveyDetail?.questions.map((q) => (
                <option key={q.id} value={q.id}>
                  {q.question_text}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-sm text-ink-muted">Rating</label>
            <select
              value={rating}
              onChange={(e) => setRating(e.target.value)}
              className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand focus:border-brand"
            >
              <option value="">All</option>
              {[1, 2, 3, 4, 5].map((r) => (
                <option key={r} value={r}>
                  {r}
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
          <label className="mb-1.5 block text-sm text-ink-muted">User</label>
          <input
            value={userSearch}
            onChange={(e) => setUserSearch(e.target.value)}
            placeholder="Name or email"
            className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-muted"
          />
        </div>
      </Accordion>

      {isLoading && <Spinner label="Loading responses…" />}
      {error && <ErrorBanner message={ErrorMessage(error)} />}

      {filteredResponses && (
        <>
          <p className="text-sm text-ink-muted">{filteredResponses.length} response(s)</p>
          {filteredResponses.length === 0 ? (
            <p className="text-sm text-ink-muted">No responses match this filter.</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-surface-border">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-surface-border text-xs uppercase tracking-wide text-ink-muted">
                  <tr>
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">User</th>
                    <th className="px-4 py-3">Answers</th>
                    <th className="px-4 py-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredResponses.map((r) => (
                    <tr key={r.id} className="border-b border-surface-border last:border-0">
                      <td className="px-4 py-3 whitespace-nowrap text-ink-muted">
                        {formatDateTime(r.submitted_at)}
                      </td>
                      <td className="px-4 py-3 text-ink-muted">{r.user.name}</td>
                      <td className="max-w-md truncate px-4 py-3 text-ink-muted">
                        {answerSummary(r)}
                      </td>
                      <td className="px-4 py-3">
                        <Button className="px-2 py-1 text-xs" onClick={() => setViewing(r)}>
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
        <Modal title="Survey response" onClose={() => setViewing(null)}>
          <div className="space-y-3">
            <p className="text-xs text-ink-muted">
              {viewing.user.name} ({viewing.user.email}) · {formatDateTime(viewing.submitted_at)}
            </p>
            {viewing.answers.map((a) => (
              <div key={a.id}>
                <p className="text-xs uppercase tracking-wide text-ink-muted">
                  {questionLabels[a.question_id] ?? `Question #${a.question_id}`}
                </p>
                <p className="mt-1 text-sm text-ink">
                  {Array.isArray(a.value) ? a.value.join(", ") : String(a.value)}
                </p>
              </div>
            ))}
          </div>
        </Modal>
      )}
    </div>
  );
}
