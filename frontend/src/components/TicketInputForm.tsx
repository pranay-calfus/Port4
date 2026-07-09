import { FormEvent } from "react";

const MAX_LENGTH = 8000;

interface TicketInputFormProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
}

export function TicketInputForm({ value, onChange, onSubmit, loading }: TicketInputFormProps) {
  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  const trimmedEmpty = value.trim().length === 0;

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Paste a customer support message here…"
        rows={6}
        maxLength={MAX_LENGTH}
        className="w-full resize-none rounded-xl border border-slate-300 p-3 text-sm text-slate-800 shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
      />
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-400">
          {value.length} / {MAX_LENGTH} characters
        </span>
        <button
          type="submit"
          disabled={trimmedEmpty || loading}
          className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white shadow transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          Route Ticket
        </button>
      </div>
    </form>
  );
}
