import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listActiveSurveys, submitSurveyResponse } from "../api/client";
import type { AnswerValue, SurveyDetail, SurveyQuestion } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { Button } from "./ui/Button";
import { ErrorBanner, ErrorMessage } from "./ui/Feedback";
import { TextAreaField, TextField } from "./ui/FormField";

function isAnswered(question: SurveyQuestion, value: AnswerValue | undefined): boolean {
  if (value === undefined) return false;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "string") return value.trim().length > 0;
  return true;
}

function QuestionInput({
  question,
  value,
  onChange,
}: {
  question: SurveyQuestion;
  value: AnswerValue | undefined;
  onChange: (value: AnswerValue) => void;
}) {
  switch (question.question_type) {
    case "short_text":
      return (
        <TextField
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Your answer"
        />
      );
    case "long_text":
      return (
        <TextAreaField
          rows={3}
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Your answer"
        />
      );
    case "rating":
      return (
        <div className="flex gap-1.5">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => onChange(n)}
              className={`flex h-9 w-9 items-center justify-center rounded-md border text-sm ${
                value === n
                  ? "border-accent bg-accent text-[color:var(--color-accent-ink)]"
                  : "border-surface-border text-ink-muted hover:text-ink"
              }`}
            >
              {n}
            </button>
          ))}
        </div>
      );
    case "single_choice":
      return (
        <div className="space-y-1.5">
          {(question.options ?? []).map((option) => (
            <label key={option} className="flex items-center gap-2 text-sm text-ink">
              <input
                type="radio"
                name={`question-${question.id}`}
                checked={value === option}
                onChange={() => onChange(option)}
              />
              {option}
            </label>
          ))}
        </div>
      );
    case "multiple_choice": {
      const selected = (value as string[] | undefined) ?? [];
      return (
        <div className="space-y-1.5">
          {(question.options ?? []).map((option) => (
            <label key={option} className="flex items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={selected.includes(option)}
                onChange={(e) =>
                  onChange(
                    e.target.checked ? [...selected, option] : selected.filter((o) => o !== option)
                  )
                }
              />
              {option}
            </label>
          ))}
        </div>
      );
    }
  }
}

function SurveyForm({ survey, onDone }: { survey: SurveyDetail; onDone: () => void }) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [answers, setAnswers] = useState<Record<number, AnswerValue>>({});

  const submitMutation = useMutation({
    mutationFn: () =>
      submitSurveyResponse(
        token!,
        survey.id,
        Object.entries(answers).map(([question_id, value]) => ({
          question_id: Number(question_id),
          value,
        }))
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["active-surveys"] });
      onDone();
    },
  });

  const canSubmit = survey.questions.every(
    (q) => !q.required || isAnswered(q, answers[q.id])
  );

  return (
    <div className="space-y-4">
      <div>
        <p className="font-semibold text-ink">{survey.title}</p>
        {survey.description && <p className="mt-1 text-sm text-ink-muted">{survey.description}</p>}
      </div>
      <div className="max-h-80 space-y-4 overflow-y-auto pr-1">
        {survey.questions.map((q) => (
          <div key={q.id}>
            <p className="mb-1.5 text-sm text-ink">
              {q.question_text}
              {q.required && <span className="text-red-400"> *</span>}
            </p>
            <QuestionInput
              question={q}
              value={answers[q.id]}
              onChange={(value) => setAnswers((prev) => ({ ...prev, [q.id]: value }))}
            />
          </div>
        ))}
      </div>
      {submitMutation.isError && <ErrorBanner message={ErrorMessage(submitMutation.error)} />}
      <div className="flex justify-end gap-2">
        <Button
          variant="primary"
          disabled={!canSubmit || submitMutation.isPending}
          onClick={() => submitMutation.mutate()}
        >
          {submitMutation.isPending ? "Submitting…" : "Submit"}
        </Button>
      </div>
    </div>
  );
}

export function SurveyBubble() {
  const { token } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [index, setIndex] = useState(0);

  const { data: activeSurveys } = useQuery({
    queryKey: ["active-surveys"],
    queryFn: () => listActiveSurveys(token!),
    enabled: !!token,
  });

  if (!activeSurveys || activeSurveys.length === 0) {
    return null;
  }

  const current = activeSurveys[Math.min(index, activeSurveys.length - 1)];

  function handleDone() {
    setIndex(0);
    // The active-surveys list will refetch (and shrink by one) - if
    // nothing else is left the whole widget unmounts on its own via the
    // early-return above; otherwise leave it open on the next survey.
  }

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {isOpen ? (
        <div className="w-80 rounded-lg border border-surface-border bg-surface-card p-4 shadow-lg sm:w-96">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
              Quick survey {activeSurveys.length > 1 ? `(${index + 1}/${activeSurveys.length})` : ""}
            </span>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              aria-label="Minimize survey"
              className="text-ink-muted hover:text-ink"
            >
              ✕
            </button>
          </div>
          <SurveyForm key={current.id} survey={current} onDone={handleDone} />
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          aria-label="Open survey"
          className="relative flex h-14 w-14 items-center justify-center rounded-full bg-accent text-2xl text-[color:var(--color-accent-ink)] shadow-lg hover:opacity-90"
        >
          📋
          {activeSurveys.length > 1 && (
            <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs text-white">
              {activeSurveys.length}
            </span>
          )}
        </button>
      )}
    </div>
  );
}
