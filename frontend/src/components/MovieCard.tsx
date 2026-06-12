import TinderCard from "react-tinder-card";

import type { MovieRecommendation } from "../types/api";

interface MovieCardProps {
  movie: MovieRecommendation;
  onSave: (movie: MovieRecommendation) => void;
  onSwipe: (direction: "left" | "right", movie: MovieRecommendation) => void;
  onFeedback: (status: "seen" | "skip_forever", movie: MovieRecommendation) => void;
}

export function MovieCard({ movie, onFeedback, onSave, onSwipe }: MovieCardProps) {
  const imageUrl = movie.poster_path
    ? `https://image.tmdb.org/t/p/w500${movie.poster_path}`
    : "https://placehold.co/600x900/221133/f5f5f5?text=Movielap";

  return (
    <TinderCard
      preventSwipe={["up", "down"]}
      onSwipe={(direction) => {
        if (direction === "left" || direction === "right") {
          onSwipe(direction, movie);
        }
      }}
    >
      <article className="relative overflow-hidden rounded-[2rem] bg-surface shadow-card">
        <div className="relative h-[58vh] w-full">
          <img alt={movie.original_title} className="h-full w-full object-cover" src={imageUrl} />
          <div className="absolute inset-0 bg-gradient-to-t from-black via-black/45 to-transparent" />
          <div className="absolute inset-x-0 bottom-0 space-y-4 p-5">
            <div className="inline-flex max-w-[92%] rounded-2xl bg-white/10 px-4 py-3 text-sm text-white backdrop-blur-md">
              {movie.match_summary_ru ?? movie.reason_ru}
            </div>
            <div className="flex items-end justify-between gap-4">
              <div>
                <h3 className="text-2xl font-bold text-white">{movie.original_title}</h3>
                <p className="text-sm text-zinc-300">
                  {movie.year ?? "Год неизвестен"} · {movie.runtime_minutes ? `${movie.runtime_minutes} мин` : "Длительность неизвестна"} ·{" "}
                  Рейтинг {movie.vote_average?.toFixed(1) ?? "N/A"}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {movie.match_explainer.length > 0 ? (
            <div className="space-y-2">
              <p className="text-xs uppercase tracking-[0.25em] text-accent">Почему это подходит</p>
              {movie.match_explainer.map((item) => (
                <div key={`${movie.tmdb_id}-${item.audience_label}`} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-400">{item.audience_label}</p>
                  <p className="mt-1 text-sm text-white">{item.reason_ru}</p>
                </div>
              ))}
            </div>
          ) : null}

          <div className="flex flex-wrap gap-2 text-xs">
            {movie.genres.slice(0, 4).map((genre) => (
              <span key={genre} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-zinc-200">
                {genre}
              </span>
            ))}
            {movie.origin_countries.slice(0, 2).map((country) => (
              <span key={country} className="rounded-full border border-fuchsia-300/20 bg-fuchsia-300/10 px-3 py-1 text-fuchsia-100">
                {country}
              </span>
            ))}
          </div>

          {movie.streaming_providers.length > 0 ? (
            <div className="space-y-2">
              <p className="text-xs uppercase tracking-[0.25em] text-zinc-500">Где смотреть</p>
              <div className="flex flex-wrap gap-2 text-xs">
                {movie.streaming_providers.map((provider) => (
                  <span key={`${movie.tmdb_id}-${provider.name}`} className="rounded-full bg-yellow-300/15 px-3 py-1 text-yellow-100">
                    {provider.name}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          <div className="grid grid-cols-2 gap-2">
            <button
              className="rounded-2xl border border-white/10 px-4 py-3 text-sm font-semibold text-white"
              onClick={() => onSave(movie)}
              type="button"
            >
              Сохранить
            </button>
            <button
              className="rounded-2xl border border-yellow-300/20 bg-yellow-300/10 px-4 py-3 text-sm font-semibold text-yellow-50"
              onClick={() => onFeedback("seen", movie)}
              type="button"
            >
              Уже видел
            </button>
            <button
              className="rounded-2xl border border-fuchsia-400/20 bg-fuchsia-400/10 px-4 py-3 text-sm font-semibold text-fuchsia-50"
              onClick={() => onFeedback("skip_forever", movie)}
              type="button"
            >
              Скрыть навсегда
            </button>
            <button
              className="rounded-2xl bg-accent px-4 py-3 text-sm font-semibold text-white disabled:opacity-50"
              disabled={!movie.trailer_url}
              onClick={() => movie.trailer_url && window.open(movie.trailer_url, "_blank", "noopener,noreferrer")}
              type="button"
            >
              Трейлер
            </button>
          </div>
        </div>
      </article>
    </TinderCard>
  );
}
