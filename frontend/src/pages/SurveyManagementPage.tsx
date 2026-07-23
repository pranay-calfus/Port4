import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  adminCreateSurvey,
  adminDeleteSurvey,
  adminGetSurvey,
  adminListSurveys,
  adminPublishSurvey,
  adminUnpublishSurvey,
  adminUpdateSurvey,
} from "../api/client";
import {
  CHOICE_QUESTION_TYPES,
  QUESTION_TYPES,
  QUESTION_TYPE_LABELS,
  type QuestionType,
  type Survey,
  type SurveyQuestionInput,
} from "../api/types";
import { useAuth } from "../context/AuthContext";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, CardLabel } from "../components/ui/Card";
import { ErrorBanner, ErrorMessage, Spinner, SuccessBanner } from "../components/ui/Feedback";
import { SelectField, TextAreaField, TextField } from "../components/ui/FormField";
import { Modal } from "../components/ui/Modal";

function emptyQuestion(): SurveyQuestionInput {
  return { question_text: "", question_type: "short_text", options: null, required: true };
}

function QuestionEditor({
  question,
  index,
  onChange,
  onRemove,
}: {
  question: SurveyQuestionInput;
  index: number;
  onChange: (q: SurveyQuestionInput) => void;
  onRemove: () => void;
}) {
  const isChoice = CHOICE_QUESTION_TYPES.includes(question.question_type);
  const options = question.options ?? [];

  function setType(question_type: QuestionType) {
    const nowChoice = CHOICE_QUESTION_TYPES.includes(question_type);
    onChange({ ...question, question_type, options: nowChoice ? (options.length ? options : ["", ""]) : null });
  }

  function setOption(i: number, value: string) {
    const next = [...options];
    next[i] = value;
    onChange({ ...question, options: next });
  }

  function addOption() {
    onChange({ ...question, options: [...options, ""] });
  }

  function removeOption(i: number) {
    onChange({ ...question, options: options.filter((_, idx) => idx !== i) });
  }

  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between">
        <CardLabel>Question {index + 1}</CardLabel>
        <Button variant="danger" className="px-2 py-1 text-xs" onClick={onRemove}>
          Remove
        </Button>
      </div>
      <TextField
        label="Question text"
        value={question.question_text}
        onChange={(e) => onChange({ ...question, question_text: e.target.value })}
      />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <SelectField
          label="Type"
          value={question.question_type}
          onChange={(e) => setType(e.target.value as QuestionType)}
        >
          {QUESTION_TYPES.map((t) => (
            <option key={t} value={t}>
              {QUESTION_TYPE_LABELS[t]}
            </option>
          ))}
        </SelectField>
        <label className="flex items-center gap-2 self-end pb-2 text-sm text-ink">
          <input
            type="checkbox"
            checked={question.required}
            onChange={(e) => onChange({ ...question, required: e.target.checked })}
          />
          Required
        </label>
      </div>
      {isChoice && (
        <div className="space-y-2">
          <p className="text-sm text-ink-muted">Options</p>
          {options.map((option, i) => (
            <div key={i} className="flex items-center gap-2">
              <TextField
                value={option}
                onChange={(e) => setOption(i, e.target.value)}
                placeholder={`Option ${i + 1}`}
              />
              {options.length > 2 && (
                <button
                  type="button"
                  onClick={() => removeOption(i)}
                  className="rounded-md border border-surface-border px-2 py-1 text-xs text-ink-muted hover:text-ink"
                >
                  ✕
                </button>
              )}
            </div>
          ))}
          <Button className="px-2 py-1 text-xs" onClick={addOption}>
            + Add option
          </Button>
        </div>
      )}
    </Card>
  );
}

function SurveyForm({
  initialTitle = "",
  initialDescription = "",
  initialQuestions = [emptyQuestion()],
  submitLabel,
  onSubmit,
  onCancel,
  isSubmitting,
  error,
}: {
  initialTitle?: string;
  initialDescription?: string;
  initialQuestions?: SurveyQuestionInput[];
  submitLabel: string;
  onSubmit: (title: string, description: string, questions: SurveyQuestionInput[]) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  error?: unknown;
}) {
  const [title, setTitle] = useState(initialTitle);
  const [description, setDescription] = useState(initialDescription);
  const [questions, setQuestions] = useState<SurveyQuestionInput[]>(initialQuestions);

  function updateQuestion(index: number, q: SurveyQuestionInput) {
    setQuestions((prev) => prev.map((existing, i) => (i === index ? q : existing)));
  }

  function removeQuestion(index: number) {
    setQuestions((prev) => prev.filter((_, i) => i !== index));
  }

  function addQuestion() {
    setQuestions((prev) => [...prev, emptyQuestion()]);
  }

  const canSubmit =
    title.trim().length > 0 &&
    questions.length > 0 &&
    questions.every(
      (q) =>
        q.question_text.trim().length > 0 &&
        (!CHOICE_QUESTION_TYPES.includes(q.question_type) ||
          (q.options ?? []).filter((o) => o.trim()).length >= 2)
    );

  return (
    <div className="space-y-4">
      <TextField label="Survey title" value={title} onChange={(e) => setTitle(e.target.value)} />
      <TextAreaField
        label="Description (optional)"
        rows={2}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <div className="space-y-3">
        {questions.map((q, i) => (
          <QuestionEditor
            key={i}
            question={q}
            index={i}
            onChange={(next) => updateQuestion(i, next)}
            onRemove={() => removeQuestion(i)}
          />
        ))}
        <Button onClick={addQuestion}>+ Add question</Button>
      </div>
      {error != null && <ErrorBanner message={ErrorMessage(error)} />}
      <div className="flex justify-end gap-2">
        <Button onClick={onCancel}>Cancel</Button>
        <Button
          variant="primary"
          disabled={!canSubmit || isSubmitting}
          onClick={() => onSubmit(title.trim(), description.trim(), questions)}
        >
          {isSubmitting ? "Saving…" : submitLabel}
        </Button>
      </div>
    </div>
  );
}

export function SurveyManagementPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"list" | "create" | number>("list");
  const [deleteTarget, setDeleteTarget] = useState<Survey | null>(null);

  const { data: surveys, isLoading, error } = useQuery({
    queryKey: ["surveys"],
    queryFn: () => adminListSurveys(token!),
    enabled: !!token,
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["surveys"] });
    queryClient.invalidateQueries({ queryKey: ["survey"] });
  }

  const createMutation = useMutation({
    mutationFn: (vars: { title: string; description: string; questions: SurveyQuestionInput[] }) =>
      adminCreateSurvey(token!, vars.title, vars.description || null, vars.questions),
    onSuccess: () => {
      invalidate();
      setMode("list");
    },
  });

  const updateMutation = useMutation({
    mutationFn: (vars: {
      id: number;
      title: string;
      description: string;
      questions: SurveyQuestionInput[];
    }) => adminUpdateSurvey(token!, vars.id, vars.title, vars.description || null, vars.questions),
    onSuccess: () => {
      invalidate();
      setMode("list");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminDeleteSurvey(token!, id),
    onSuccess: () => {
      setDeleteTarget(null);
      invalidate();
    },
  });

  const publishMutation = useMutation({
    mutationFn: (survey: Survey) =>
      survey.is_published ? adminUnpublishSurvey(token!, survey.id) : adminPublishSurvey(token!, survey.id),
    onSuccess: invalidate,
  });

  const editingSurveyId = typeof mode === "number" ? mode : null;
  const { data: editingSurvey, isLoading: isLoadingEditingSurvey } = useQuery({
    queryKey: ["survey", editingSurveyId],
    queryFn: () => adminGetSurvey(token!, editingSurveyId!),
    enabled: !!token && editingSurveyId != null,
  });

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-6 py-8">
      <Link to="/product-cx/surveys" className="text-sm text-ink-muted hover:text-ink">
        ← Back to Surveys
      </Link>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-ink">Survey Management</h1>
        {mode === "list" && <Button variant="primary" onClick={() => setMode("create")}>New Survey</Button>}
      </div>

      {mode === "create" && (
        <Card>
          <SurveyForm
            submitLabel="Create Survey"
            isSubmitting={createMutation.isPending}
            error={createMutation.error}
            onCancel={() => setMode("list")}
            onSubmit={(title, description, questions) =>
              createMutation.mutate({ title, description, questions })
            }
          />
        </Card>
      )}

      {typeof mode === "number" && isLoadingEditingSurvey && <Spinner label="Loading survey…" />}
      {typeof mode === "number" && editingSurvey && (
        <Card>
          <SurveyForm
            key={editingSurvey.id}
            submitLabel="Save Changes"
            initialTitle={editingSurvey.title}
            initialDescription={editingSurvey.description ?? ""}
            initialQuestions={editingSurvey.questions.map((q) => ({
              question_text: q.question_text,
              question_type: q.question_type,
              options: q.options,
              required: q.required,
            }))}
            isSubmitting={updateMutation.isPending}
            error={updateMutation.error}
            onCancel={() => setMode("list")}
            onSubmit={(title, description, questions) =>
              updateMutation.mutate({ id: editingSurvey.id, title, description, questions })
            }
          />
        </Card>
      )}

      {mode === "list" && (
        <div className="space-y-3">
          {isLoading && <Spinner label="Loading surveys…" />}
          {error && <ErrorBanner message={ErrorMessage(error)} />}
          {deleteMutation.isSuccess && <SuccessBanner message="Survey deleted." />}
          {surveys && surveys.length === 0 && (
            <p className="text-sm text-ink-muted">No surveys yet - create one to get started.</p>
          )}
          {surveys?.map((survey) => (
            <Card key={survey.id} className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-semibold text-ink">{survey.title}</p>
                  <Badge
                    color={survey.is_published ? "#4ade80" : "#9ca3af"}
                    label={survey.is_published ? "Published" : "Draft"}
                  />
                </div>
                <p className="text-xs text-ink-muted">{survey.response_count} response(s)</p>
              </div>
              <div className="flex gap-2">
                <Button
                  className="px-2 py-1 text-xs"
                  disabled={publishMutation.isPending}
                  onClick={() => publishMutation.mutate(survey)}
                >
                  {survey.is_published ? "Unpublish" : "Publish"}
                </Button>
                <Button className="px-2 py-1 text-xs" onClick={() => setMode(survey.id)}>
                  Edit
                </Button>
                <Button
                  variant="danger"
                  className="px-2 py-1 text-xs"
                  onClick={() => setDeleteTarget(survey)}
                >
                  Delete
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {deleteTarget && (
        <Modal title="Delete survey" onClose={() => setDeleteTarget(null)}>
          <p className="text-sm text-ink-muted">
            Permanently delete <strong className="text-ink">{deleteTarget.title}</strong>? Its
            responses will be removed too. This cannot be undone.
          </p>
          {deleteMutation.isError && <ErrorBanner message={ErrorMessage(deleteMutation.error)} />}
          <div className="mt-4 flex justify-end gap-2">
            <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button
              variant="danger"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate(deleteTarget.id)}
            >
              Delete Permanently
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}
