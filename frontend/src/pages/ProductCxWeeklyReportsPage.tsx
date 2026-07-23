import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { generateWeeklyReport, getLatestWeeklyReport, listWeeklyReports } from "../api/client";
import type { WeeklyReport } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { WeeklyReportDetail } from "../components/WeeklyReportDetail";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ErrorBanner, ErrorMessage, Spinner } from "../components/ui/Feedback";
import { Modal } from "../components/ui/Modal";
import { WEEKLY_REPORT_SOURCE_COLORS, WEEKLY_REPORT_SOURCE_LABELS } from "../lib/colors";
import { formatDate, formatDateTime } from "../lib/format";

export function ProductCxWeeklyReportsPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [viewing, setViewing] = useState<WeeklyReport | null>(null);

  const latestQuery = useQuery({
    queryKey: ["weekly-report-latest"],
    queryFn: () => getLatestWeeklyReport(token!),
    enabled: !!token,
  });

  const historyQuery = useQuery({
    queryKey: ["weekly-report-history"],
    queryFn: () => listWeeklyReports(token!),
    enabled: !!token,
  });

  const generateMutation = useMutation({
    mutationFn: () => generateWeeklyReport(token!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["weekly-report-latest"] });
      queryClient.invalidateQueries({ queryKey: ["weekly-report-history"] });
    },
  });

  const latest = latestQuery.data ?? null;
  // The history table reads as "past reports" - the one already shown
  // above under "Latest Report" is excluded so nothing appears twice.
  const history = (historyQuery.data ?? []).filter((r) => r.id !== latest?.id);

  return (
    <div className="mx-auto max-w-6xl space-y-8 px-6 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">Weekly Reports</h1>
          <p className="mt-1 text-sm text-ink-muted">
            AI-generated executive summaries of customer feedback, refreshed automatically every
            Monday for the previous week - or generate one now for the trailing 7 days.
          </p>
        </div>
        <Button
          variant="primary"
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
        >
          {generateMutation.isPending ? "Generating…" : "Generate Report"}
        </Button>
      </div>

      {generateMutation.isError && <ErrorBanner message={ErrorMessage(generateMutation.error)} />}

      <div>
        <h2 className="mb-3 text-lg font-semibold text-ink">Latest Report</h2>
        {latestQuery.isLoading && <Spinner label="Loading latest report…" />}
        {latestQuery.error && <ErrorBanner message={ErrorMessage(latestQuery.error)} />}
        {!latestQuery.isLoading && !latestQuery.error && latest === null && (
          <Card>
            <p className="text-sm text-ink-muted">
              No weekly report has been generated yet. Click "Generate Report" above to create the
              first one, or wait for the next scheduled Monday run.
            </p>
          </Card>
        )}
        {latest && (
          <Card>
            <WeeklyReportDetail report={latest} />
          </Card>
        )}
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold text-ink">Report History</h2>
        {historyQuery.isLoading && <Spinner label="Loading report history…" />}
        {historyQuery.error && <ErrorBanner message={ErrorMessage(historyQuery.error)} />}
        {!historyQuery.isLoading && !historyQuery.error && history.length === 0 && (
          <p className="text-sm text-ink-muted">No past reports yet.</p>
        )}
        {history.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-surface-border">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-surface-border text-xs uppercase tracking-wide text-ink-muted">
                <tr>
                  <th className="px-4 py-3">Period</th>
                  <th className="px-4 py-3">Generated</th>
                  <th className="px-4 py-3">Source</th>
                  <th className="px-4 py-3">Feedback Analyzed</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {history.map((report) => (
                  <tr key={report.id} className="border-b border-surface-border last:border-0">
                    <td className="px-4 py-3 whitespace-nowrap text-ink">
                      {formatDate(report.period_start)} – {formatDate(report.period_end)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-ink-muted">
                      {formatDateTime(report.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        color={WEEKLY_REPORT_SOURCE_COLORS[report.generated_by]}
                        label={WEEKLY_REPORT_SOURCE_LABELS[report.generated_by]}
                      />
                    </td>
                    <td className="px-4 py-3 text-ink-muted">{report.total_feedback}</td>
                    <td className="px-4 py-3">
                      <Button className="px-2 py-1 text-xs" onClick={() => setViewing(report)}>
                        View
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {viewing && (
        <Modal title="Weekly report" onClose={() => setViewing(null)} maxWidthClassName="max-w-2xl">
          <WeeklyReportDetail report={viewing} />
        </Modal>
      )}
    </div>
  );
}
