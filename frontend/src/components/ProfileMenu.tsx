import { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { initials } from "../lib/initials";
import { Button } from "./ui/Button";

export function ProfileMenu() {
  const { identity, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  if (!identity) return null;

  const scopeLabel =
    identity.role === "ADMIN"
      ? identity.department
        ? `Scope: ${identity.department}`
        : "Scope: All departments (super-admin)"
      : "Customer account";

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-sm font-semibold text-[color:var(--color-accent-ink)]"
      >
        {initials(identity.name)}
      </button>
      {open && (
        <div className="absolute right-0 top-11 z-40 w-64 rounded-lg border border-surface-border bg-surface-card p-4 shadow-xl">
          <p className="font-semibold text-ink">{identity.name}</p>
          <p className="text-xs text-ink-muted">{identity.email}</p>
          <p className="mt-1 text-xs text-ink-muted">{scopeLabel}</p>
          <hr className="my-3 border-surface-border" />
          <Button variant="primary" className="w-full" onClick={logout}>
            Log Out
          </Button>
        </div>
      )}
    </div>
  );
}
