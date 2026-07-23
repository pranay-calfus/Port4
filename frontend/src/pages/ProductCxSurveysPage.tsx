import { Link } from "react-router-dom";
import { DateRangeFilter } from "../components/DateRangeFilter";
import { SurveyAnalyticsCharts } from "../components/SurveyAnalyticsCharts";
import { SurveyResponsesTable } from "../components/SurveyResponsesTable";
import { useDateRangeFilter } from "../lib/dateRange";
import { Button } from "../components/ui/Button";

export function ProductCxSurveysPage() {
  const range = useDateRangeFilter();

  return (
    <div className="mx-auto max-w-6xl space-y-8 px-6 py-8">
      <div className="flex items-end justify-between gap-4">
        <h1 className="text-2xl font-bold text-ink">Surveys</h1>
        <Link to="/product-cx/surveys/manage">
          <Button>Manage Surveys</Button>
        </Link>
      </div>
      <DateRangeFilter {...range} />
      <div>
        <h2 className="mb-3 text-lg font-semibold text-ink">Analytics</h2>
        <SurveyAnalyticsCharts dateFrom={range.dateFrom} dateTo={range.dateTo} />
      </div>
      <div>
        <h2 className="mb-3 text-lg font-semibold text-ink">Responses</h2>
        <SurveyResponsesTable defaultDateFrom={range.dateFrom} defaultDateTo={range.dateTo} />
      </div>
    </div>
  );
}
