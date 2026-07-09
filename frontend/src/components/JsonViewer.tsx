interface JsonViewerProps {
  data: unknown;
}

export function JsonViewer({ data }: JsonViewerProps) {
  return (
    <pre className="max-h-80 overflow-auto rounded-xl bg-slate-900 p-4 text-xs leading-relaxed text-emerald-300">
      <code>{JSON.stringify(data, null, 2)}</code>
    </pre>
  );
}
