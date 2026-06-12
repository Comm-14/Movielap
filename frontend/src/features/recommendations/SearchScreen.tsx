import { useEffect, useState } from "react";

import { LoadingStage } from "../../components/LoadingStage";
import { MatchModal } from "../../components/MatchModal";
import { MovieCard } from "../../components/MovieCard";
import { apiClient, getSessionWebSocketUrl } from "../../lib/api";
import { getStartParam, getTelegramUser } from "../../lib/twa";
import type { MovieRecommendation, SessionResponse } from "../../types/api";

type SocketStatus = "idle" | "connecting" | "connected" | "reconnecting" | "closed";

const ACTIVE_SESSION_STORAGE_KEY = "movie-match-active-session-id";
const CHIP_GROUPS = [
  {
    title: "Настроение",
    icon: "✨",
    items: [
      "🧘 Расслабить мозг",
      "😭 Поплакать",
      "😂 Посмеяться",
      "😰 Держать в напряжении",
      "❤️ Про любовь",
      "🌤️ Вдохновляющие",
    ],
  },
  {
    title: "Жанры",
    icon: "🎬",
    items: ["💥 Боевик и экшн", "🕵️ Триллер", "🔍 Детектив", "🚀 Фантастика", "🎭 Драма", "😄 Комедия"],
  },
  {
    title: "Детали",
    icon: "🎨",
    items: [
      "🎁 Неожиданный финал",
      "🌌 Красивый визуал",
      "🆕 Свежие новинки",
      "🏆 Золотая классика",
      "📖 На реальных событиях",
      "🧠 Заставляет задуматься",
    ],
  },
  {
    title: "Страны",
    icon: "🌍",
    items: ["🇺🇸 Америка", "🇹🇷 Турция", "🇷🇺 Россия", "🇰🇷 Корейское", "🇬🇧 Британское", "🇫🇷 Французское"],
  },
  {
    title: "Длительность",
    icon: "⏱️",
    items: ["⏳ Короткие (до 1.5 часа)", "🍿 На весь вечер (2-3ч)"],
  },
] as const;
function parseSessionIdFromStartParam(startParam: string | null): string | null {
  if (!startParam?.startsWith("session_")) {
    return null;
  }

  return startParam.replace("session_", "");
}

export function SearchScreen() {
  const telegramUser = getTelegramUser();
  const startSessionId = parseSessionIdFromStartParam(getStartParam());
  const [mode, setMode] = useState<"solo" | "duo">("solo");
  const [preferenceText, setPreferenceText] = useState("");
  const [loading, setLoading] = useState(false);
  const [movies, setMovies] = useState<MovieRecommendation[]>([]);
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [sessionIntent, setSessionIntent] = useState<"create" | "join">(startSessionId ? "join" : "create");
  const [matchMovie, setMatchMovie] = useState<MovieRecommendation | null>(null);
  const [socketStatus, setSocketStatus] = useState<SocketStatus>("idle");
  const [toast, setToast] = useState<string | null>(null);
  const [selectedChips, setSelectedChips] = useState<string[]>([]);
  const [isChipsExpanded, setIsChipsExpanded] = useState(false);

  useEffect(() => {
    if (!toast) {
      return;
    }
    const timer = window.setTimeout(() => setToast(null), 2200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    const restoredSessionId = startSessionId ?? window.localStorage.getItem(ACTIVE_SESSION_STORAGE_KEY);
    if (!restoredSessionId) {
      return;
    }

    setMode("duo");
    if (startSessionId) {
      setSessionIntent("join");
    }

    void (async () => {
      try {
        const restoredSession = await apiClient.getSession(restoredSessionId);
        setSession(restoredSession);
        setMode(restoredSession.type === "duo" ? "duo" : "solo");
        setMovies(restoredSession.movies ?? []);
      } catch {
        window.localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
      }
    })();
  }, [startSessionId]);

  useEffect(() => {
    if (!session?.id || mode === "solo") {
      return;
    }

    let websocket: WebSocket | null = null;
    let reconnectTimeout: number | undefined;
    let reconnectAttempts = 0;
    let isClosedByEffect = false;

    const connect = () => {
      setSocketStatus(reconnectAttempts === 0 ? "connecting" : "reconnecting");
      websocket = new WebSocket(getSessionWebSocketUrl(session.id));

      websocket.onopen = () => {
        reconnectAttempts = 0;
        setSocketStatus("connected");
      };

      websocket.onmessage = (event) => {
        const parsed = JSON.parse(event.data) as { event: string; movies?: MovieRecommendation[]; movie?: MovieRecommendation };
        if (parsed.event === "movies_ready" && parsed.movies) {
          setMovies(parsed.movies);
          setSession((current) => (current ? { ...current, status: "active", movies: parsed.movies } : current));
          window.localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, session.id);
          setToast("Подборка готова");
        }

        if (parsed.event === "match_found" && parsed.movie) {
          setMatchMovie(parsed.movie);
        }
      };

      websocket.onclose = () => {
        if (isClosedByEffect) {
          setSocketStatus("closed");
          return;
        }

        if (reconnectAttempts >= 5) {
          setSocketStatus("closed");
          return;
        }

        reconnectAttempts += 1;
        reconnectTimeout = window.setTimeout(connect, Math.min(5000, reconnectAttempts * 1000));
      };

      websocket.onerror = () => {
        websocket?.close();
      };
    };

    connect();

    return () => {
      isClosedByEffect = true;
      if (reconnectTimeout) {
        window.clearTimeout(reconnectTimeout);
      }
      websocket?.close();
    };
  }, [mode, session?.id]);

  function toggleChip(chip: string): void {
    setSelectedChips((current) => (current.includes(chip) ? current.filter((item) => item !== chip) : [...current, chip]));
  }

  function buildPromptText(): string {
    const chipsText = selectedChips.length > 0 ? `\n\nПодсказки по тегам: ${selectedChips.join(", ")}.` : "";
    return `${preferenceText.trim()}${chipsText}`.trim();
  }

  async function handleSubmit(): Promise<void> {
    setLoading(true);
    try {
      if (mode === "solo") {
        setMovies([]);
        const response = await apiClient.getSoloRecommendations({
          ...telegramUser,
          preference_text: buildPromptText(),
          moods: selectedChips,
          hard_filters: null,
        });
        setMovies(response.movies);
      } else {
        if (sessionIntent === "join" && startSessionId) {
          const joinedSession = await apiClient.joinSession({
            ...telegramUser,
            session_id: startSessionId,
            preference_text: buildPromptText(),
            moods: selectedChips,
            hard_filters: null,
          });
          setSession(joinedSession);
            setMode("duo");
            setMovies(joinedSession.movies ?? []);
            window.localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, joinedSession.id);
            setToast(
              joinedSession.status === "active"
                ? "Вы подключились. Подборка готова."
              : `Вы подключились. Ждем еще: ${joinedSession.max_participants - joinedSession.participant_ids.length}`,
          );
        } else {
          const createdSession = await apiClient.createSession({
            ...telegramUser,
            preference_text: buildPromptText(),
            moods: selectedChips,
            hard_filters: null,
          });
          setSession(createdSession);
          window.localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, createdSession.id);
          setToast("Duo-сессия создана");
        }
      }
    } catch (error) {
      setToast(error instanceof Error ? error.message : "Произошла непредвиденная ошибка");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(movie: MovieRecommendation): Promise<void> {
    try {
      await apiClient.addToWatchlist({
        ...telegramUser,
        tmdb_id: movie.tmdb_id,
        movie,
      });
      setToast("Фильм сохранен");
    } catch {
      setToast("Не удалось обновить список");
    }
  }

  async function handleFeedback(status: "seen" | "skip_forever", movie: MovieRecommendation): Promise<void> {
    setMovies((current) => current.filter((item) => item.tmdb_id !== movie.tmdb_id));
    try {
      await apiClient.saveFeedback({
        ...telegramUser,
        tmdb_id: movie.tmdb_id,
        status,
      });
      setToast(status === "seen" ? "Отмечено как просмотренное" : "Больше не покажем");
    } catch {
      setToast("Не удалось сохранить выбор");
    }
  }

  async function handleSwipe(direction: "left" | "right", movie: MovieRecommendation): Promise<void> {
    setMovies((current) => current.filter((item) => item.tmdb_id !== movie.tmdb_id));
    if (mode !== "solo" && session) {
      try {
        const response = await apiClient.createSwipe({
          ...telegramUser,
          session_id: session.id,
          tmdb_id: movie.tmdb_id,
          action: direction === "right" ? "like" : "dislike",
        });
        if (response.matched && response.movie) {
          setMatchMovie(response.movie);
        }
      } catch {
        setToast("Не удалось синхронизировать свайп");
      }
      return;
    }

    if (direction === "right") {
      await handleSave(movie);
    }
  }

  return (
    <section className="space-y-6 pb-28">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-[0.3em] text-accent">Movielap</p>
        <h1 className="text-3xl font-bold text-white">Выберите настроение, а мы найдем кино</h1>
        <p className="text-sm text-zinc-300">Подбор для одного или для двоих с объяснением, где смотреть и трейлером в один тап.</p>
      </header>

      <div className="grid grid-cols-2 gap-3 rounded-3xl border border-white/10 bg-surface/70 p-2">
        {(["solo", "duo"] as const).map((item) => (
          <button
            key={item}
            className={`rounded-2xl px-4 py-3 text-sm font-medium capitalize transition ${
              mode === item ? "bg-accent text-white" : "text-zinc-400"
            }`}
            onClick={() => {
              setMode(item);
              if (item === "duo" && startSessionId) {
                setSessionIntent("join");
              }
            }}
            type="button"
          >
            {item === "solo" ? "соло" : "дуо"}
          </button>
        ))}
      </div>

      <div className="space-y-4 rounded-3xl border border-white/10 bg-surface/70 p-5 shadow-card">
        <div className="space-y-2">
          <button
            className="flex w-full items-center justify-between rounded-3xl border border-white/10 bg-black/15 px-4 py-4 text-left"
            onClick={() => setIsChipsExpanded((current) => !current)}
            type="button"
          >
            <div>
              <p className="text-xs uppercase tracking-[0.25em] text-zinc-500">Подсказки</p>
              <p className="mt-1 text-sm text-zinc-300">
                {selectedChips.length > 0 ? `Выбрано тегов: ${selectedChips.length}` : "Настроение, жанры, детали, страны и длительность"}
              </p>
            </div>
            <span className="text-lg text-zinc-400">{isChipsExpanded ? "−" : "+"}</span>
          </button>

          {isChipsExpanded ? (
            <div className="space-y-3 rounded-3xl border border-white/10 bg-black/15 p-4">
              {CHIP_GROUPS.map((group) => (
                <div key={group.title} className="space-y-2">
                  <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">
                    {group.icon} {group.title}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {group.items.map((chip) => (
                      <button
                        key={chip}
                        className={`rounded-full px-3 py-2 text-xs transition ${
                          selectedChips.includes(chip) ? "bg-accent text-white" : "border border-white/10 bg-white/5 text-zinc-300"
                        }`}
                        onClick={() => toggleChip(chip)}
                        type="button"
                      >
                        {chip}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <textarea
          className="min-h-32 w-full rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-white outline-none placeholder:text-zinc-500"
          onChange={(event) => setPreferenceText(event.target.value)}
          placeholder={
            'Чего душа просит? Пиши как есть, например: "Люблю Гарри Поттера, хочу красивую сказку на вечер".\nФормула идеального кино: назови 2-3 любимых фильма + настроение + что точно не хочешь'
          }
          value={preferenceText}
        />

        <button
          className="w-full rounded-2xl bg-accent px-5 py-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
          disabled={loading || preferenceText.trim().length < 3}
          onClick={() => void handleSubmit()}
          type="button"
        >
          {mode === "solo"
              ? "Подобрать для меня"
            : sessionIntent === "join"
              ? "Присоединиться к дуо"
              : "Создать дуо-сессию"}
        </button>
      </div>

      {loading ? <LoadingStage /> : null}

      {session ? (
        <div className="rounded-3xl border border-yellow-300/20 bg-fuchsia-500/10 p-5 text-sm text-yellow-50">
          <p className="font-semibold">Дуо-сессия</p>
          <p className="mt-2 break-all">{session.invite_link ?? "Ссылка-приглашение пока недоступна."}</p>
          <p className="mt-3 text-xs text-fuchsia-100">
            {session.participant_ids.length}/{session.max_participants} участников · соединение: {socketStatus} ·{" "}
            {session.movies?.length ? "Подборка восстановлена." : session.status === "active" ? "Все готово." : "Ждем второго человека."}
          </p>
        </div>
      ) : null}

      {movies.length > 0 ? (
        <div className="space-y-4">
          {movies.map((movie) => (
            <MovieCard
              key={movie.tmdb_id}
              movie={movie}
              onFeedback={handleFeedback}
              onSave={handleSave}
              onSwipe={handleSwipe}
            />
          ))}
        </div>
      ) : null}

      {toast ? (
        <div className="fixed left-1/2 top-6 -translate-x-1/2 rounded-full bg-white px-4 py-2 text-sm font-medium text-black shadow-lg">
          {toast}
        </div>
      ) : null}

      {matchMovie ? <MatchModal movie={matchMovie} onClose={() => setMatchMovie(null)} /> : null}
    </section>
  );
}
