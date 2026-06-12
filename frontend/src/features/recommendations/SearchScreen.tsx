import { useEffect, useMemo, useState } from "react";

import { LoadingStage } from "../../components/LoadingStage";
import { MatchModal } from "../../components/MatchModal";
import { MovieCard } from "../../components/MovieCard";
import { apiClient, getSessionWebSocketUrl } from "../../lib/api";
import { getStartParam, openTelegramShare } from "../../lib/twa";
import type { MovieRecommendation, SessionResponse } from "../../types/api";

type SearchScreenProps = {
  initialInviteReference: string | null;
  isTelegramContainer: boolean;
  userLabel: string;
  userId: number;
};

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

function parseInviteFromTelegramStartParam(): string | null {
  const startParam = getStartParam();
  if (!startParam?.startsWith("session_")) {
    return null;
  }

  return startParam.replace("session_", "");
}

function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

function extractInviteReference(rawValue: string): string | null {
  const value = rawValue.trim();
  if (!value) {
    return null;
  }

  try {
    const url = new URL(value);
    const pathMatch = url.pathname.match(/^\/session\/([^/]+)$/);
    if (pathMatch?.[1]) {
      return pathMatch[1];
    }
    return url.searchParams.get("invite");
  } catch {
    return value;
  }
}

export function SearchScreen({ initialInviteReference, isTelegramContainer, userId, userLabel }: SearchScreenProps) {
  const [mode, setMode] = useState<"solo" | "duo">("solo");
  const [duoFlow, setDuoFlow] = useState<"create" | "join">("create");
  const [preferenceText, setPreferenceText] = useState("");
  const [loading, setLoading] = useState(false);
  const [movies, setMovies] = useState<MovieRecommendation[]>([]);
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [matchMovie, setMatchMovie] = useState<MovieRecommendation | null>(null);
  const [socketStatus, setSocketStatus] = useState<SocketStatus>("idle");
  const [toast, setToast] = useState<string | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [selectedChips, setSelectedChips] = useState<string[]>([]);
  const [isChipsExpanded, setIsChipsExpanded] = useState(false);
  const [joinValue, setJoinValue] = useState(initialInviteReference ?? parseInviteFromTelegramStartParam() ?? "");
  const [resolvedInviteSessionId, setResolvedInviteSessionId] = useState<string | null>(null);
  const [resolvingInvite, setResolvingInvite] = useState(false);

  const effectiveInviteReference = useMemo(
    () => initialInviteReference ?? parseInviteFromTelegramStartParam(),
    [initialInviteReference],
  );

  useEffect(() => {
    if (!toast) {
      return;
    }
    const timer = window.setTimeout(() => setToast(null), 2400);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    const storedSessionId = window.localStorage.getItem(ACTIVE_SESSION_STORAGE_KEY);
    if (!effectiveInviteReference && !storedSessionId) {
      return;
    }

    setMode("duo");
    setDuoFlow("join");
    const inviteReference = effectiveInviteReference ?? storedSessionId;
    if (!inviteReference) {
      return;
    }

    void (async () => {
      try {
        const sessionResponse = isUuid(inviteReference)
          ? await apiClient.getSession(inviteReference)
          : await apiClient.resolveInviteCode(inviteReference);
        setResolvedInviteSessionId(sessionResponse.id);
        setSession(sessionResponse);
        setDuoFlow(sessionResponse.participant_ids.includes(userId) ? "create" : "join");
        setMovies(sessionResponse.movies ?? []);
      } catch (error) {
        if (!effectiveInviteReference) {
          window.localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
        }
        setErrorBanner(error instanceof Error ? error.message : "Не удалось открыть комнату");
      }
    })();
  }, [effectiveInviteReference, userId]);

  useEffect(() => {
    if (!session?.id || mode === "solo") {
      return;
    }

    let websocket: WebSocket | null = null;
    let reconnectTimeout: number | undefined;
    let reconnectAttempts = 0;
    let closedByCleanup = false;

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
          setToast("Подборка для комнаты готова");
        }

        if (parsed.event === "match_found" && parsed.movie) {
          setMatchMovie(parsed.movie);
        }
      };

      websocket.onclose = () => {
        if (closedByCleanup) {
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

      websocket.onerror = () => websocket?.close();
    };

    connect();

    return () => {
      closedByCleanup = true;
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

  async function handleResolveJoinLink(): Promise<void> {
    const inviteReference = extractInviteReference(joinValue);
    if (!inviteReference) {
      setErrorBanner("Введите invite link, UUID комнаты или короткий код");
      return;
    }

    setResolvingInvite(true);
    setErrorBanner(null);
    try {
      const resolvedSession = isUuid(inviteReference)
        ? await apiClient.getSession(inviteReference)
        : await apiClient.resolveInviteCode(inviteReference);
      setResolvedInviteSessionId(resolvedSession.id);
      setSession(resolvedSession);
      setMode("duo");
      setDuoFlow(resolvedSession.participant_ids.includes(userId) ? "create" : "join");
      setMovies(resolvedSession.movies ?? []);
      const nextUrl = new URL(window.location.href);
      nextUrl.pathname = `/session/${resolvedSession.id}`;
      nextUrl.searchParams.delete("invite");
      window.history.replaceState({}, "", nextUrl.toString());
    } catch (error) {
      setErrorBanner(error instanceof Error ? error.message : "Не удалось найти комнату");
    } finally {
      setResolvingInvite(false);
    }
  }

  async function handleSubmit(): Promise<void> {
    setLoading(true);
    setErrorBanner(null);
    try {
      if (mode === "solo") {
        setMovies([]);
        const response = await apiClient.getSoloRecommendations({
          preference_text: buildPromptText(),
          moods: selectedChips,
          hard_filters: null,
        });
        setMovies(response.movies);
        return;
      }

      if (duoFlow === "join") {
        const sessionId = resolvedInviteSessionId ?? session?.id;
        if (!sessionId) {
          setErrorBanner("Сначала откройте комнату по ссылке или коду");
          return;
        }

        const joinedSession = await apiClient.joinSession({
          session_id: sessionId,
          preference_text: buildPromptText(),
          moods: selectedChips,
          hard_filters: null,
        });
        setSession(joinedSession);
        setMovies(joinedSession.movies ?? []);
        window.localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, joinedSession.id);
        setToast(joinedSession.status === "active" ? "Вы присоединились. Подборка готова." : "Вы присоединились. Ждём остальных.");
        return;
      }

      const createdSession = await apiClient.createSession({
        preference_text: buildPromptText(),
        moods: selectedChips,
        hard_filters: null,
      });
      setSession(createdSession);
      setResolvedInviteSessionId(createdSession.id);
      setMovies(createdSession.movies ?? []);
      window.localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, createdSession.id);
      const nextUrl = new URL(window.location.href);
      nextUrl.pathname = `/session/${createdSession.id}`;
      nextUrl.searchParams.delete("invite");
      window.history.replaceState({}, "", nextUrl.toString());
      setToast("Комната создана. Скопируйте ссылку и позовите второго участника.");
    } catch (error) {
      setErrorBanner(error instanceof Error ? error.message : "Произошла непредвиденная ошибка");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(movie: MovieRecommendation): Promise<void> {
    try {
      await apiClient.addToWatchlist({
        tmdb_id: movie.tmdb_id,
        movie,
      });
      setToast("Фильм сохранен");
    } catch {
      setErrorBanner("Не удалось обновить watchlist");
    }
  }

  async function handleFeedback(status: "seen" | "skip_forever", movie: MovieRecommendation): Promise<void> {
    setMovies((current) => current.filter((item) => item.tmdb_id !== movie.tmdb_id));
    try {
      await apiClient.saveFeedback({
        tmdb_id: movie.tmdb_id,
        status,
      });
      setToast(status === "seen" ? "Отмечено как просмотренное" : "Больше не показываем");
    } catch {
      setErrorBanner("Не удалось сохранить обратную связь");
    }
  }

  async function handleSwipe(direction: "left" | "right", movie: MovieRecommendation): Promise<void> {
    setMovies((current) => current.filter((item) => item.tmdb_id !== movie.tmdb_id));
    if (mode !== "solo" && session) {
      try {
        const response = await apiClient.createSwipe({
          session_id: session.id,
          tmdb_id: movie.tmdb_id,
          action: direction === "right" ? "like" : "dislike",
        });
        if (response.matched && response.movie) {
          setMatchMovie(response.movie);
        }
      } catch {
        setErrorBanner("Не удалось синхронизировать свайп");
      }
      return;
    }

    if (direction === "right") {
      await handleSave(movie);
    }
  }

  async function copyInviteLink(): Promise<void> {
    if (!session?.invite_link) {
      return;
    }

    try {
      await navigator.clipboard.writeText(session.invite_link);
      setToast("Ссылка скопирована");
    } catch {
      setErrorBanner("Не удалось скопировать ссылку");
    }
  }

  return (
    <section className="space-y-6 pb-28">
      <header className="grid gap-4 rounded-[2rem] border border-white/10 bg-surface/50 p-5 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-accent">Главная</p>
          <h2 className="mt-2 text-3xl font-bold text-white">Подбор кино для {userLabel}</h2>
          <p className="mt-2 max-w-2xl text-sm text-zinc-300">
            Веб-сценарий начинается здесь: создайте комнату, присоединитесь по ссылке или просто запустите соло-режим без Telegram.
          </p>
        </div>
        <div className="rounded-3xl border border-white/10 bg-black/15 px-4 py-3 text-sm text-zinc-200">
          {isTelegramContainer ? "Telegram container detected" : "Browser-first mode"}
        </div>
      </header>

      <div className="grid gap-4 lg:grid-cols-[0.72fr_1.28fr]">
        <aside className="space-y-4">
          <div className="rounded-[2rem] border border-white/10 bg-surface/70 p-5 shadow-card">
            <p className="text-xs uppercase tracking-[0.25em] text-zinc-500">Сценарий старта</p>
            <div className="mt-4 grid grid-cols-2 gap-3 rounded-3xl border border-white/10 bg-black/15 p-2">
              {(["solo", "duo"] as const).map((item) => (
                <button
                  key={item}
                  className={`rounded-2xl px-4 py-3 text-sm font-medium transition ${
                    mode === item ? "bg-accent text-black" : "text-zinc-400"
                  }`}
                  onClick={() => setMode(item)}
                  type="button"
                >
                  {item === "solo" ? "Соло" : "Комната"}
                </button>
              ))}
            </div>

            {mode === "duo" ? (
              <div className="mt-4 space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <button
                    className={`rounded-2xl px-4 py-3 text-sm ${duoFlow === "create" ? "bg-white text-black" : "border border-white/10 text-zinc-300"}`}
                    onClick={() => setDuoFlow("create")}
                    type="button"
                  >
                    Создать комнату
                  </button>
                  <button
                    className={`rounded-2xl px-4 py-3 text-sm ${duoFlow === "join" ? "bg-white text-black" : "border border-white/10 text-zinc-300"}`}
                    onClick={() => setDuoFlow("join")}
                    type="button"
                  >
                    Войти по ссылке
                  </button>
                </div>

                {duoFlow === "join" ? (
                  <div className="space-y-3">
                    <input
                      className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none placeholder:text-zinc-500"
                      onChange={(event) => setJoinValue(event.target.value)}
                      placeholder="Вставьте invite link, UUID или код комнаты"
                      value={joinValue}
                    />
                    <button
                      className="w-full rounded-2xl border border-white/10 px-4 py-3 text-sm text-white disabled:opacity-60"
                      disabled={resolvingInvite || joinValue.trim().length === 0}
                      onClick={() => void handleResolveJoinLink()}
                      type="button"
                    >
                      {resolvingInvite ? "Ищем комнату..." : "Открыть комнату"}
                    </button>
                  </div>
                ) : (
                  <p className="rounded-3xl border border-white/10 bg-black/15 p-4 text-sm text-zinc-300">
                    Создайте комнату, скопируйте обычную web-ссылку и поделитесь ей где угодно. Telegram share остаётся только дополнительной кнопкой.
                  </p>
                )}
              </div>
            ) : null}
          </div>

          <div className="rounded-[2rem] border border-white/10 bg-surface/70 p-5 shadow-card">
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
              <div className="mt-4 space-y-3 rounded-3xl border border-white/10 bg-black/15 p-4">
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
                            selectedChips.includes(chip) ? "bg-accent text-black" : "border border-white/10 bg-white/5 text-zinc-300"
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
        </aside>

        <div className="space-y-4">
          <div className="space-y-4 rounded-[2rem] border border-white/10 bg-surface/70 p-5 shadow-card">
            <label className="text-sm text-zinc-300" htmlFor="preferenceText">
              Что вы хотите посмотреть сейчас
            </label>
            <textarea
              id="preferenceText"
              className="min-h-36 w-full rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-white outline-none placeholder:text-zinc-500"
              onChange={(event) => setPreferenceText(event.target.value)}
              placeholder='Например: "Люблю `Достать ножи`, хочу умный триллер без хоррора, до двух часов."'
              value={preferenceText}
            />

            <button
              className="w-full rounded-2xl bg-accent px-5 py-4 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
              disabled={loading || preferenceText.trim().length < 3}
              onClick={() => void handleSubmit()}
              type="button"
            >
              {mode === "solo" ? "Запустить веб-подбор" : duoFlow === "join" ? "Присоединиться к комнате" : "Создать комнату"}
            </button>
          </div>

          {session ? (
            <div className="rounded-[2rem] border border-yellow-300/20 bg-yellow-300/10 p-5 text-sm text-yellow-50">
              <p className="font-semibold">Комната активна</p>
              <p className="mt-2 break-all">{session.invite_link ?? "Ссылка-приглашение пока недоступна."}</p>
              <p className="mt-2 text-xs text-yellow-100">
                Код комнаты: {session.invite_code ?? "—"} · {session.participant_ids.length}/{session.max_participants} участников · websocket:{" "}
                {socketStatus}
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <button className="rounded-2xl bg-white px-4 py-3 text-sm font-medium text-black" onClick={() => void copyInviteLink()} type="button">
                  Copy link
                </button>
                {isTelegramContainer && session.invite_link ? (
                  <button
                    className="rounded-2xl border border-white/10 px-4 py-3 text-sm text-white"
                    onClick={() => openTelegramShare(session.invite_link ?? "", "Join my Movielap room")}
                    type="button"
                  >
                    Share via Telegram
                  </button>
                ) : null}
              </div>
            </div>
          ) : null}

          {loading ? <LoadingStage /> : null}
          {errorBanner ? <div className="rounded-3xl border border-red-400/20 bg-red-400/10 p-4 text-sm text-red-100">{errorBanner}</div> : null}

          {!loading && movies.length === 0 ? (
            <div className="rounded-[2rem] border border-white/10 bg-black/15 p-6 text-sm text-zinc-400">
              {mode === "solo"
                ? "Подборка появится здесь после запуска. В обычном вебе это первый экран после входа гостем."
                : session?.status === "waiting"
                  ? "Комната открыта, но подборка стартует после подключения остальных участников."
                  : "Откройте комнату или создайте новую, чтобы начать совместный сценарий."}
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
        </div>
      </div>

      {toast ? (
        <div className="fixed left-1/2 top-6 z-40 -translate-x-1/2 rounded-full bg-white px-4 py-2 text-sm font-medium text-black shadow-lg">
          {toast}
        </div>
      ) : null}

      {matchMovie ? <MatchModal movie={matchMovie} onClose={() => setMatchMovie(null)} /> : null}
    </section>
  );
}
