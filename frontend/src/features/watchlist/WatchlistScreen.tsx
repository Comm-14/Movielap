import { useEffect, useState } from "react";

import { apiClient } from "../../lib/api";
import { getTelegramUser } from "../../lib/twa";
import type { WatchlistItemResponse } from "../../types/api";

export function WatchlistScreen() {
  const telegramUser = getTelegramUser();
  const [items, setItems] = useState<WatchlistItemResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const response = await apiClient.getWatchlist(telegramUser.telegram_id);
        setItems(response);
      } finally {
        setLoading(false);
      }
    })();
  }, [telegramUser.telegram_id]);

  if (loading) {
    return <div className="rounded-3xl border border-white/10 bg-surface/70 p-6 text-sm text-zinc-400">Загружаем список...</div>;
  }

  if (items.length === 0) {
    return <div className="rounded-3xl border border-white/10 bg-surface/70 p-6 text-sm text-zinc-400">Здесь появятся сохраненные фильмы.</div>;
  }

  return (
    <section className="space-y-3 pb-28">
      {items.map((item) => (
        <article key={item.id} className="overflow-hidden rounded-3xl border border-white/10 bg-surface/70">
          <div className="flex gap-4 p-4">
            <img
              alt={item.original_title ?? `Movie ${item.tmdb_id}`}
              className="h-28 w-20 rounded-2xl object-cover"
              src={
                item.poster_path
                  ? `https://image.tmdb.org/t/p/w500${item.poster_path}`
                  : "https://placehold.co/160x240/221133/f5f5f5?text=Movielap"
              }
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-white">{item.original_title ?? `TMDB #${item.tmdb_id}`}</p>
              <p className="mt-1 text-xs text-zinc-400">
                {item.year ?? "Год неизвестен"} · {item.runtime_minutes ? `${item.runtime_minutes} мин` : "Длительность неизвестна"} · Рейтинг{" "}
                {item.vote_average?.toFixed(1) ?? "N/A"}
              </p>
              {item.match_summary_ru ? <p className="mt-3 text-xs text-white">{item.match_summary_ru}</p> : null}
              {item.reason_ru ? <p className="mt-2 text-xs text-zinc-300">{item.reason_ru}</p> : null}
              {item.genres.length > 0 ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {item.genres.slice(0, 3).map((genre) => (
                    <span key={`${item.id}-${genre}`} className="rounded-full border border-white/10 bg-white/5 px-2 py-1 text-[11px] text-zinc-200">
                      {genre}
                    </span>
                  ))}
                </div>
              ) : null}
              <p className="mt-3 text-[11px] text-zinc-500">Добавлено: {new Date(item.added_at).toLocaleString()}</p>
            </div>
          </div>
        </article>
      ))}
    </section>
  );
}
