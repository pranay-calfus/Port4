import { useEffect, useId, useState, type ReactNode } from "react";

const STORAGE_PREFIX = "port4_accordion_";

function readPersisted(storageKey: string | undefined, defaultOpen: boolean): boolean {
  if (!storageKey) return defaultOpen;
  const stored = localStorage.getItem(STORAGE_PREFIX + storageKey);
  return stored === null ? defaultOpen : stored === "open";
}

/** A collapsible section matching Card's visual language. When `storageKey`
 * is given, the expanded/collapsed state persists across visits (see
 * ThemeContext.tsx for the same localStorage read/write convention).
 */
export function Accordion({
  title,
  defaultOpen = false,
  storageKey,
  children,
}: {
  title: ReactNode;
  defaultOpen?: boolean;
  storageKey?: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(() => readPersisted(storageKey, defaultOpen));
  const contentId = useId();

  useEffect(() => {
    if (storageKey) {
      localStorage.setItem(STORAGE_PREFIX + storageKey, open ? "open" : "closed");
    }
  }, [open, storageKey]);

  return (
    <div className="rounded-lg border border-surface-border bg-surface-card">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={contentId}
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between px-5 py-3 text-left"
      >
        <span className="text-xs font-semibold uppercase tracking-wide text-ink-muted">{title}</span>
        <span
          aria-hidden="true"
          className={`text-ink-muted transition-transform ${open ? "rotate-180" : ""}`}
        >
          ▾
        </span>
      </button>
      {open && (
        <div id={contentId} className="border-t border-surface-border px-5 py-4">
          {children}
        </div>
      )}
    </div>
  );
}
