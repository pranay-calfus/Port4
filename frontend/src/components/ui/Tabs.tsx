import { useState, type ReactNode } from "react";

interface Tab {
  key: string;
  label: string;
  content: ReactNode;
}

export function Tabs({ tabs, defaultKey }: { tabs: Tab[]; defaultKey?: string }) {
  const [active, setActive] = useState(defaultKey ?? tabs[0]?.key);
  const activeTab = tabs.find((tab) => tab.key === active) ?? tabs[0];

  return (
    <div>
      <div className="mb-6 flex gap-6 border-b border-surface-border">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActive(tab.key)}
            className={`-mb-px border-b-2 px-1 pb-3 text-sm font-medium transition-colors ${
              tab.key === activeTab?.key
                ? "border-brand text-ink"
                : "border-transparent text-ink-muted hover:text-ink"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {activeTab?.content}
    </div>
  );
}
