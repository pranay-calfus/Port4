import tickets from "@sample-tickets";
import { SampleTicket } from "../types/ticket";

const sampleTickets = tickets as SampleTicket[];

interface ExampleDropdownProps {
  onSelect: (message: string) => void;
}

export function ExampleDropdown({ onSelect }: ExampleDropdownProps) {
  return (
    <select
      defaultValue=""
      onChange={(event) => {
        const ticket = sampleTickets.find((t) => t.id === event.target.value);
        if (ticket) onSelect(ticket.message);
      }}
      className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
    >
      <option value="" disabled>
        Load an example ticket…
      </option>
      {sampleTickets.map((ticket) => (
        <option key={ticket.id} value={ticket.id}>
          [{ticket.categoryLabel}] {ticket.title}
        </option>
      ))}
    </select>
  );
}
