import type { DepartmentMetrics, DateRange } from "../api/types";

function csvCell(value: string | number): string {
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function csvRow(cells: (string | number)[]): string {
  return cells.map(csvCell).join(",");
}

function breakdownRows(title: string, columnLabel: string, breakdown: Record<string, number>): string[] {
  const rows = [csvRow([title]), csvRow([columnLabel, "Count"])];
  for (const [key, count] of Object.entries(breakdown)) {
    rows.push(csvRow([key, count]));
  }
  return rows;
}

export function buildDashboardCsv(
  metrics: DepartmentMetrics,
  dateRange: DateRange,
  scopeLabel: string,
  exportedAt: string
): string {
  const lines: string[] = [
    csvRow(["Dashboard Export"]),
    csvRow(["Scope", scopeLabel]),
    csvRow(["Date Range - From", dateRange.from ?? "All time"]),
    csvRow(["Date Range - To", dateRange.to ?? "All time"]),
    csvRow(["Generated At", exportedAt]),
    "",
    csvRow(["Summary"]),
    csvRow(["Metric", "Value"]),
    csvRow(["Total Tickets", metrics.total_tickets]),
    csvRow(["Open Tickets", metrics.open_tickets]),
    csvRow([
      "Average Resolution (hours)",
      metrics.avg_resolution_hours == null ? "N/A" : metrics.avg_resolution_hours.toFixed(1),
    ]),
    "",
    ...breakdownRows("Status Breakdown", "Status", metrics.tickets_per_status),
    "",
    ...breakdownRows("Priority Breakdown", "Priority", metrics.tickets_per_priority),
    "",
    ...breakdownRows("Category Breakdown", "Category", metrics.tickets_per_category),
    "",
    ...breakdownRows("Emotion Breakdown", "Emotion", metrics.tickets_per_emotion),
  ];

  if (metrics.tickets_per_department) {
    lines.push("", ...breakdownRows("Team Breakdown", "Team", metrics.tickets_per_department));
  }

  return lines.join("\n");
}

export function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
