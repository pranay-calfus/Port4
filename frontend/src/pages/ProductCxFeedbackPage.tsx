import { FeedbackTable } from "../components/FeedbackTable";

export function ProductCxFeedbackPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6 px-6 py-8">
      <h1 className="text-2xl font-bold text-ink">Feedback</h1>
      <FeedbackTable />
    </div>
  );
}
