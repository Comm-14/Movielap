import { useEffect, useState } from "react";

import { BottomTabBar } from "./components/BottomTabBar";
import { SearchScreen } from "./features/recommendations/SearchScreen";
import { WatchlistScreen } from "./features/watchlist/WatchlistScreen";
import { initTelegramApp } from "./lib/twa";

export default function App() {
  const [activeTab, setActiveTab] = useState<"search" | "watchlist">("search");

  useEffect(() => {
    initTelegramApp();
  }, []);

  return (
    <main className="mx-auto min-h-screen max-w-md px-4 pb-24 pt-6 text-white">
      {activeTab === "search" ? <SearchScreen /> : <WatchlistScreen />}
      <BottomTabBar activeTab={activeTab} onChange={setActiveTab} />
    </main>
  );
}
