import tickets from "@sample-tickets";
import { useEffect, useState } from "react";
import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ResultCard } from "../components/ResultCard";
import { useRouteTicket } from "../hooks/useRouteTicket";
import { SampleTicket } from "../types/ticket";

const sampleTickets = tickets as SampleTicket[];
const AUTOPLAY_DELAY_MS = 6000;

interface DemoPageProps {
  onNavigateHome: () => void;
}

export function DemoPage({ onNavigateHome }: DemoPageProps) {
  const [index, setIndex] = useState(0);
  const [autoPlay, setAutoPlay] = useState(false);
  const { data, loading, error, submit } = useRouteTicket();

  const currentTicket = sampleTickets[index];

  useEffect(() => {
    submit(currentTicket.message);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index]);

  useEffect(() => {
    if (!autoPlay || loading) return;
    const timer = setTimeout(() => {
      setIndex((prev) => (prev + 1) % sampleTickets.length);
    }, AUTOPLAY_DELAY_MS);
    return () => clearTimeout(timer);
  }, [autoPlay, loading, index]);

  function goNext() {
    setIndex((prev) => (prev + 1) % sampleTickets.length);
  }

  function goPrev() {
    setIndex((prev) => (prev - 1 + sampleTickets.length) % sampleTickets.length);
  }

  return (
    <div className="mx-auto w-full max-w-3xl rounded-2xl bg-white p-8 shadow-2xl">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Demo Mode</h1>
          <p className="mt-1 text-sm text-slate-500">
            Ticket {index + 1} of {sampleTickets.length}
          </p>
        </div>
        <button
          type="button"
          onClick={onNavigateHome}
          className="text-sm font-medium text-indigo-600 underline-offset-2 hover:underline"
        >
          ← Back to Router
        </button>
      </header>

      <div className="space-y-4">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
            Input ({currentTicket.categoryLabel})
          </p>
          <p className="mt-1 text-sm text-slate-700">{currentTicket.message}</p>
        </div>

        {loading && <LoadingSpinner />}
        {error && <ErrorBanner message={error} />}
        {data && !loading && <ResultCard data={data.data} processingTime={data.processingTime} />}

        <div className="flex items-center justify-between pt-2">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={goPrev}
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Previous
            </button>
            <button
              type="button"
              onClick={goNext}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
            >
              Next
            </button>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={autoPlay}
              onChange={(event) => setAutoPlay(event.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-400"
            />
            Auto-play
          </label>
        </div>
      </div>
    </div>
  );
}
