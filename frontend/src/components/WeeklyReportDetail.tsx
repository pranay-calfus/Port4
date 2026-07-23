import type { WeeklyReport } from "../api/types";
import {
  SENTIMENT_COLORS,
  WEEKLY_REPORT_SOURCE_COLORS,
  WEEKLY_REPORT_SOURCE_LABELS,
  themeColor,
} from "../lib/colors";
import { formatDate, formatDateTime } from "../lib/format";
import { Badge } from "./ui/Badge";
import { CardLabel } from "./ui/Card";

const FALLBACK_SENTIMENT_COLOR = "#9ca3af";

function ReportSection({ title, items, emptyLabel }: { title: string; items: string[]; emptyLabel: string }) {
  return (
    <div>
      <CardLabel className="mb-1">{title}</CardLabel>
      {items.length === 0 ? (
        <p className="text-sm text-ink-muted">{emptyLabel}</p>
      ) : (
        <ul className="list-disc space-y-1 pl-5 text-sm text-ink">
          {items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Full detail for one generated weekly report - shared between the
 * "Latest Report" section (rendered inline) and the history list's "View"
 * modal (see ProductCxWeeklyReportsPage), so both render identically.
 */
export function WeeklyReportDetail({ report }: { report: WeeklyReport }) {
  const sentimentEntries = Object.entries(report.sentiment_breakdown).filter(
    ([, v]) => v.count > 0
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-lg font-semibold text-ink">
            {formatDate(report.period_start)} – {formatDate(report.period_end)}
          </p>
          <p className="text-xs text-ink-muted">
            Generated {formatDateTime(report.created_at)}
            {report.model_used && <> · {report.model_used}</>}
          </p>
        </div>
        <Badge
          color={WEEKLY_REPORT_SOURCE_COLORS[report.generated_by]}
          label={WEEKLY_REPORT_SOURCE_LABELS[report.generated_by]}
        />
      </div>

      <div className="flex flex-wrap gap-6">
        <div>
          <CardLabel className="mb-1">Feedback Analyzed</CardLabel>
          <p className="text-2xl font-bold text-ink">{report.total_feedback}</p>
        </div>
        {sentimentEntries.length > 0 && (
          <div>
            <CardLabel className="mb-1">Sentiment Mix</CardLabel>
            <div className="flex flex-wrap gap-2">
              {sentimentEntries.map(([sentiment, v]) => (
                <Badge
                  key={sentiment}
                  color={
                    SENTIMENT_COLORS[sentiment as keyof typeof SENTIMENT_COLORS] ??
                    FALLBACK_SENTIMENT_COLOR
                  }
                  label={`${sentiment} ${v.pct}% (${v.count})`}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {report.top_themes.length > 0 && (
        <div>
          <CardLabel className="mb-1">Top Themes</CardLabel>
          <div className="flex flex-wrap gap-2">
            {report.top_themes.map((t) => (
              <Badge key={t.theme} color={themeColor(t.theme)} label={`${t.theme} (${t.count})`} />
            ))}
          </div>
        </div>
      )}

      <div>
        <CardLabel className="mb-1">Overview</CardLabel>
        <p className="text-sm text-ink">{report.overview}</p>
      </div>

      <div>
        <CardLabel className="mb-1">Overall Sentiment</CardLabel>
        <p className="text-sm text-ink">{report.overall_sentiment}</p>
      </div>

      <ReportSection
        title="Key Insights"
        items={report.key_insights}
        emptyLabel="No insights for this period."
      />
      <ReportSection title="Risks" items={report.risks} emptyLabel="No risks flagged this period." />
      <ReportSection
        title="Recommendations"
        items={report.recommendations}
        emptyLabel="No recommendations for this period."
      />
      <ReportSection
        title="Positive Highlights"
        items={report.positive_highlights}
        emptyLabel="No specific highlights this period."
      />
    </div>
  );
}
