import { useState } from "react";
import { ClearButton } from "../components/ClearButton";
import { ComparisonSection } from "../components/ComparisonSection";
import { CopyButton } from "../components/CopyButton";
import { ErrorBanner } from "../components/ErrorBanner";
import { ExampleDropdown } from "../components/ExampleDropdown";
import { JsonViewer } from "../components/JsonViewer";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ResultCard } from "../components/ResultCard";
import { TicketInputForm } from "../components/TicketInputForm";
import { useRouteTicket } from "../hooks/useRouteTicket";

interface HomePageProps {
  onNavigateToDemo: () => void;
}

export function HomePage({ onNavigateToDemo }: HomePageProps) {
  const [message, setMessage] = useState("");
  const { data, loading, error, submit, clear } = useRouteTicket();

  function handleSubmit() {
    if (!message.trim()) return;
    submit(message);
  }

  function handleClear() {
    setMessage("");
    clear();
  }

  return (
    <div className="mx-auto w-full max-w-3xl rounded-2xl bg-white p-8 shadow-2xl">
      <header className="mb-6 text-center">
        <h1 className="text-2xl font-bold text-slate-800">Smart Support Ticket Router</h1>
        <p className="mt-1 text-sm text-slate-500">
          Paste a customer message and get an instant category, priority, and team assignment.
        </p>
      </header>

      <div className="space-y-4">
        <ExampleDropdown onSelect={setMessage} />
        <TicketInputForm value={message} onChange={setMessage} onSubmit={handleSubmit} loading={loading} />

        {loading && <LoadingSpinner />}
        {error && <ErrorBanner message={error} />}

        {data && !loading && (
          <div className="space-y-3">
            <ResultCard data={data.data} processingTime={data.processingTime} />
            <JsonViewer data={data} />
            <div className="flex gap-2">
              <CopyButton text={JSON.stringify(data, null, 2)} />
              <ClearButton onClick={handleClear} />
            </div>
          </div>
        )}

        <ComparisonSection />

        <div className="pt-2 text-center">
          <button
            type="button"
            onClick={onNavigateToDemo}
            className="text-sm font-medium text-indigo-600 underline-offset-2 hover:underline"
          >
            Open Demo Mode →
          </button>
        </div>
      </div>
    </div>
  );
}
