import type { MovieRecommendation } from "../types/api";

interface MatchModalProps {
  movie: MovieRecommendation;
  onClose: () => void;
}

export function MatchModal({ movie, onClose }: MatchModalProps) {
  const imageUrl = movie.poster_path
    ? `https://image.tmdb.org/t/p/w500${movie.poster_path}`
    : "https://placehold.co/600x900/221133/f5f5f5?text=Movielap";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 px-5">
      <div className="w-full max-w-sm rounded-[2rem] border border-white/10 bg-surface p-5 shadow-card">
        <div className="space-y-4">
          <div className="rounded-3xl bg-gradient-to-br from-yellow-300/20 via-yellow-200/10 to-fuchsia-500/20 p-4">
            <p className="text-xs uppercase tracking-[0.3em] text-yellow-200">Есть совпадение</p>
            <h2 className="mt-2 text-2xl font-bold text-white">{movie.original_title}</h2>
            <p className="mt-1 text-sm text-zinc-200">{movie.match_summary_ru ?? movie.reason_ru}</p>
          </div>

          <img alt={movie.original_title} className="h-[280px] w-full rounded-3xl object-cover" src={imageUrl} />

          {movie.match_explainer.length > 0 ? (
            <div className="space-y-2">
              {movie.match_explainer.map((item) => (
                <div key={`${movie.tmdb_id}-${item.audience_label}`} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-400">{item.audience_label}</p>
                  <p className="mt-1 text-sm text-white">{item.reason_ru}</p>
                </div>
              ))}
            </div>
          ) : null}

          {movie.streaming_providers.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {movie.streaming_providers.map((provider) => (
                <span key={`${movie.tmdb_id}-${provider.name}`} className="rounded-full bg-yellow-300/15 px-3 py-1 text-xs text-yellow-100">
                  {provider.name}
                </span>
              ))}
            </div>
          ) : null}

          <div className="flex gap-3">
            <button
              className="flex-1 rounded-2xl bg-accent px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
              disabled={!movie.trailer_url}
              onClick={() => movie.trailer_url && window.open(movie.trailer_url, "_blank", "noopener,noreferrer")}
              type="button"
            >
              Трейлер
            </button>
            <button
              className="flex-1 rounded-2xl border border-white/10 px-4 py-3 text-sm font-semibold text-white"
              onClick={onClose}
              type="button"
            >
              Закрыть
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
