import { useQuery } from "@tanstack/react-query";
import { feedbackMetrics } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { DateRangeFilter } from "../components/DateRangeFilter";
import { FeedbackMetricCharts } from "../components/FeedbackMetricCharts";
import { ThemeCharts } from "../components/ThemeCharts";
import { useDateRangeFilter } from "../lib/dateRange";
import { Card } from "../components/ui/Card";
import { ErrorBanner, ErrorMessage, Spinner } from "../components/ui/Feedback";

export function ProductCxAnalyticsPage() {
  const { token } = useAuth();
  const range = useDateRangeFilter();

  const { data: metrics, isLoading, error } = useQuery({
    queryKey: ["feedback-metrics", range.dateFrom, range.dateTo],
    queryFn: () => feedbackMetrics(token!, { date_from: range.dateFrom, date_to: range.dateTo }),
    enabled: !!token,
  });

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-6 py-8">
      <h1 className="text-2xl font-bold text-ink">Feedback Analytics</h1>
      <DateRangeFilter {...range} />

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
