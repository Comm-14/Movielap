interface BottomTabBarProps {
  activeTab: "search" | "watchlist";
  onChange: (tab: "search" | "watchlist") => void;
}

export function BottomTabBar({ activeTab, onChange }: BottomTabBarProps) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 border-t border-white/10 bg-surface/90 px-4 py-3 backdrop-blur-xl">
      <div className="mx-auto flex max-w-md gap-3">
        {[
          { id: "search", label: "Подбор" },
          { id: "watchlist", label: "Список" },
        ].map((tab) => (
          <button
            key={tab.id}
            className={`flex-1 rounded-2xl px-4 py-3 text-sm font-medium transition ${
              activeTab === tab.id ? "bg-accent text-white" : "bg-white/5 text-muted"
            }`}
            onClick={() => onChange(tab.id as "search" | "watchlist")}
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>
    </nav>
  );
}
