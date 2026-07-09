const STATS = [
  { label: "Manual Triage", value: "~2 min", accent: "text-slate-600" },
  { label: "AI Routing", value: "~2 sec", accent: "text-indigo-600" },
  { label: "Improvement", value: "~98%", accent: "text-emerald-600" }
];

export function ComparisonSection() {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
      <h3 className="text-sm font-semibold text-slate-700">Manual vs. AI Routing</h3>
      <div className="mt-3 grid grid-cols-3 gap-3 text-center">
        {STATS.map((stat) => (
          <div key={stat.label} className="rounded-lg bg-white p-3 shadow-sm">
            <p className={`text-lg font-bold ${stat.accent}`}>{stat.value}</p>
            <p className="text-xs text-slate-500">{stat.label}</p>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-slate-500">
        A support agent typically reads a ticket, decides its category and priority, and manually assigns it
        to the right team - a process that takes roughly two minutes per ticket. The AI router performs the
        same triage in about two seconds, freeing agents to focus on actually resolving issues instead of
        sorting them.
      </p>
    </div>
  );
}
