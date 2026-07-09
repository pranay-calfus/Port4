import { TicketRouteResult } from "../types/ticket";

interface ResultCardProps {
  data: TicketRouteResult;
  processingTime: string;
}

const PRIORITY_STYLES: Record<string, string> = {
  High: "bg-red-100 text-red-700 border-red-300",
  Medium: "bg-amber-100 text-amber-700 border-amber-300",
  Low: "bg-emerald-100 text-emerald-700 border-emerald-300"
};

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-800">{value}</p>
    </div>
  );
}

export function ResultCard({ data, processingTime }: ResultCardProps) {
  const priorityClass = PRIORITY_STYLES[data.priority] ?? "bg-slate-100 text-slate-700 border-slate-300";

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field label="Category" value={data.category} />
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Priority</p>
          <span className={`mt-1 inline-block rounded-full border px-3 py-0.5 text-sm font-semibold ${priorityClass}`}>
            {data.priority}
          </span>
        </div>
        <Field label="Assigned Team" value={data.assignedTeam} />
        <Field label="Confidence" value={`${Math.round(data.confidence * 100)}%`} />
      </div>
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Reason</p>
        <p className="mt-1 text-sm text-slate-700">{data.reasoning}</p>
      </div>
      <p className="text-right text-xs text-slate-400">Processed in {processingTime}</p>
    </div>
  );
}
