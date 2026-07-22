import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { feedbackMetrics } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { FeedbackMetricCharts } from "../components/FeedbackMetricCharts";
import { FeedbackTable } from "../components/FeedbackTable";
import { SurveyAnalyticsCharts } from "../components/SurveyAnalyticsCharts";
import { SurveyResponsesTable } from "../components/SurveyResponsesTable";
import { ThemeCharts } from "../components/ThemeCharts";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ErrorBanner, ErrorMessage, Spinner } from "../components/ui/Feedback";
import { Tabs } from "../components/ui/Tabs";

function DashboardTab() {
  const { token } = useAuth();
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const { data: metrics, isLoading, error } = useQuery({
    queryKey: ["feedback-metrics", dateFrom, dateTo],
    queryFn: () => feedbackMetrics(token!, { date_from: dateFrom || undefined, date_to: dateTo || undefined }),
    enabled: !!token,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label className="mb-1.5 block text-sm text-ink-muted">From</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink"
          />
        </div>
        <div>
          <label className="mb-1.5 block text-sm text-ink-muted">To</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-ink"
          />
        </div>
        {(dateFrom || dateTo) && (
          <Button
            onClick={() => {
              setDateFrom("");
              setDateTo("");
            }}
          >
            Clear Range
          </Button>
        )}
      </div>

      {isLoading && <Spinner label="Loading metrics…" />}
      {error && <ErrorBanner message={ErrorMessage(error)} />}

      {metrics && (
        <>
          <Card>
            <p className="text-sm text-ink-muted">Total Feedback</p>
            <p className="mt-1 text-3xl font-bold text-ink">{metrics.total_feedback}</p>
          </Card>
          <FeedbackMetricCharts metrics={metrics} />
          <ThemeCharts topThemes={metrics.top_themes} trend={metrics.theme_trend} />
        </>
      )}
    </div>
  );
}

function SurveysTab() {
  return (
    <div className="space-y-8">
      <div className="flex justify-end">
        <Link to="/product-cx/surveys">
          <Button>Manage Surveys</Button>
        </Link>
      </div>
      <div>
        <h2 className="mb-3 text-lg font-semibold text-ink">Analytics</h2>
        <SurveyAnalyticsCharts />
      </div>
      <div>
        <h2 className="mb-3 text-lg font-semibold text-ink">Responses</h2>
        <SurveyResponsesTable />
      </div>
    </div>
  );
}

export function ProductCxDashboardPage() {
  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <h1 className="mb-6 text-2xl font-bold text-ink">Product &amp; CX</h1>
      <Tabs
        tabs={[
          { key: "dashboard", label: "Dashboard", content: <DashboardTab /> },
          { key: "feedback", label: "Feedback", content: <FeedbackTable /> },
          { key: "surveys", label: "Surveys", content: <SurveysTab /> },
        ]}
      />
    </div>
  );
}
