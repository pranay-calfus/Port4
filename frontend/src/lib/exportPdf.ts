import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import html2canvas from "html2canvas";
import type { DepartmentMetrics, DateRange } from "../api/types";

// jspdf-autotable sets this on the doc instance at runtime but doesn't
// expose it in its public type declarations.
type DocWithAutoTable = jsPDF & { lastAutoTable?: { finalY: number } };

const PAGE_MARGIN = 40;

function addBreakdownTable(
  doc: DocWithAutoTable,
  y: number,
  title: string,
  breakdown: Record<string, number>
): number {
  const entries = Object.entries(breakdown);
  if (entries.length === 0) return y;

  autoTable(doc, {
    startY: y,
    head: [[title, "Count"]],
    body: entries.map(([key, count]) => [key, String(count)]),
    theme: "striped",
    styles: { fontSize: 9 },
    headStyles: { fillColor: [51, 65, 85] },
    margin: { left: PAGE_MARGIN, right: PAGE_MARGIN },
  });
  return (doc.lastAutoTable?.finalY ?? y) + 20;
}

export async function generateDashboardPdf(
  metrics: DepartmentMetrics,
  dateRange: DateRange,
  scopeLabel: string,
  exportedAt: string,
  chartsElement: HTMLElement | null
): Promise<Blob> {
  const doc = new jsPDF({ unit: "pt", format: "a4" }) as DocWithAutoTable;
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  let y = PAGE_MARGIN;

  doc.setFontSize(18);
  doc.text("TickTrack Dashboard Report", PAGE_MARGIN, y);
  y += 22;

  doc.setFontSize(10);
  doc.setTextColor(100);
  doc.text(`Scope: ${scopeLabel}`, PAGE_MARGIN, y);
  y += 14;
  doc.text(`Date range: ${dateRange.from ?? "All time"} to ${dateRange.to ?? "All time"}`, PAGE_MARGIN, y);
  y += 14;
  doc.text(`Generated: ${exportedAt}`, PAGE_MARGIN, y);
  y += 20;
  doc.setTextColor(0);

  autoTable(doc, {
    startY: y,
    head: [["Metric", "Value"]],
    body: [
      ["Total Tickets", String(metrics.total_tickets)],
      ["Open Tickets", String(metrics.open_tickets)],
      [
        "Average Resolution (hours)",
        metrics.avg_resolution_hours == null ? "N/A" : metrics.avg_resolution_hours.toFixed(1),
      ],
    ],
    theme: "grid",
    styles: { fontSize: 9 },
    margin: { left: PAGE_MARGIN, right: PAGE_MARGIN },
  });
  y = (doc.lastAutoTable?.finalY ?? y) + 20;

  y = addBreakdownTable(doc, y, "Status", metrics.tickets_per_status);
  y = addBreakdownTable(doc, y, "Priority", metrics.tickets_per_priority);
  y = addBreakdownTable(doc, y, "Category", metrics.tickets_per_category);
  y = addBreakdownTable(doc, y, "Emotion", metrics.tickets_per_emotion);
  if (metrics.tickets_per_department) {
    y = addBreakdownTable(doc, y, "Team", metrics.tickets_per_department);
  }

  if (chartsElement) {
    const canvas = await html2canvas(chartsElement, { scale: 2 });
    const imgData = canvas.toDataURL("image/png");
    const imgWidth = pageWidth - PAGE_MARGIN * 2;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    if (y + imgHeight > pageHeight - PAGE_MARGIN) {
      doc.addPage();
      y = PAGE_MARGIN;
    }
    doc.addImage(imgData, "PNG", PAGE_MARGIN, y, imgWidth, imgHeight);
  }

  return doc.output("blob");
}

export function downloadBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
