import { useEffect, useState } from "react";

import { BottomTabBar } from "./components/BottomTabBar";
import { SearchScreen } from "./features/recommendations/SearchScreen";
import { WatchlistScreen } from "./features/watchlist/WatchlistScreen";
import { clearStoredAuthSession, getStoredAuthSession, setStoredAuthSession, type StoredAuthSession } from "./lib/auth";
import { apiClient } from "./lib/api";
import { getTelegramInitData, initTelegramApp, isTelegramWebApp } from "./lib/twa";

function readInviteReferenceFromLocation(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  const pathMatch = window.location.pathname.match(/^\/session\/([^/]+)$/);
  if (pathMatch?.[1]) {
    return pathMatch[1];
  }

  const searchParams = new URLSearchParams(window.location.search);
  return searchParams.get("invite");
}

export default function App() {
  const [activeTab, setActiveTab] = useState<"search" | "watchlist">("search");
  const [authSession, setAuthSession] = useState<StoredAuthSession | null>(() => getStoredAuthSession());
  const [guestName, setGuestName] = useState("");
  const [booting, setBooting] = useState(true);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [inviteReference] = useState(() => readInviteReferenceFromLocation());
  const telegramMode = isTelegramWebApp();

  useEffect(() => {
    initTelegramApp();
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const storedSession = getStoredAuthSession();
        if (storedSession) {
          const refreshed = await apiClient.getMe();
          setStoredAuthSession(refreshed);
          setAuthSession(refreshed);
          return;
        }

        if (telegramMode) {
          const initData = getTelegramInitData();
          if (initData) {
            const signedIn = await apiClient.signInWithTelegram({ init_data_raw: initData });
            setStoredAuthSession(signedIn);
            setAuthSession(signedIn);
          }
        }
      } catch (error) {
        clearStoredAuthSession();
        setAuthSession(null);
        setAuthError(error instanceof Error ? error.message : "Не удалось восстановить сессию");
      } finally {
        setBooting(false);
      }
    })();
  }, [telegramMode]);

  async function handleGuestContinue(): Promise<void> {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const signedIn = await apiClient.signInAsGuest({ name: guestName.trim() });
      setStoredAuthSession(signedIn);
      setAuthSession(signedIn);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Не удалось создать гостевой профиль");
    } finally {
      setAuthLoading(false);
      setBooting(false);
    }
  }

  function handleLogout(): void {
    clearStoredAuthSession();
    setAuthSession(null);
    setGuestName("");
    setActiveTab("search");
  }

  if (booting) {
    return (
      <main className="mx-auto flex min-h-screen max-w-6xl items-center px-6 py-12 text-white">
        <div className="rounded-[2rem] border border-white/10 bg-surface/70 p-8 shadow-card">
          <p className="text-sm text-zinc-300">Подготавливаем веб-версию Movielap...</p>
        </div>
      </main>
    );
  }

  if (!authSession) {
    return (
      <main className="mx-auto min-h-screen max-w-6xl px-6 py-8 text-white">
        <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-[2rem] border border-white/10 bg-surface/60 p-8 shadow-card">
            <p className="text-xs uppercase tracking-[0.35em] text-accent">Movielap Web</p>
            <h1 className="mt-4 max-w-xl text-4xl font-bold leading-tight">
              Подбор кино для одного, пары или комнаты без обязательного входа через Telegram.
            </h1>
            <p className="mt-4 max-w-2xl text-base text-zinc-300">
              Открываете сайт, создаёте гостевой профиль, собираете комнату по ссылке и свайпаете до общего мэтча. Telegram Mini App
              остаётся дополнительным контейнером, а не единственным способом попасть внутрь.
            </p>
            <div className="mt-8 grid gap-3 md:grid-cols-3">
              {[
                "1. Создайте временный профиль за несколько секунд.",
                "2. Запустите соло-подбор или откройте комнату для друзей.",
                "3. Делитесь обычной ссылкой и продолжайте с любого устройства.",
              ].map((item) => (
                <div key={item} className="rounded-3xl border border-white/10 bg-black/15 p-4 text-sm text-zinc-200">
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[2rem] border border-white/10 bg-black/20 p-6 shadow-card">
            <h2 className="text-2xl font-semibold text-white">{inviteReference ? "Вход в комнату" : "Начать с гостевого профиля"}</h2>
            <p className="mt-3 text-sm text-zinc-300">
              {inviteReference
                ? "Ссылка-приглашение уже распознана. Нужен только ваш экранный ник, чтобы войти и присоединиться."
                : "Для MVP достаточно локального гостевого профиля. Позже сюда можно добавить email/passwordless flow без переделки UX."}
            </p>

            <label className="mt-6 block text-sm text-zinc-200" htmlFor="guestName">
              Как вас показать в комнате
            </label>
            <input
              id="guestName"
              className="mt-2 w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-base text-white outline-none placeholder:text-zinc-500"
              maxLength={48}
              onChange={(event) => setGuestName(event.target.value)}
              placeholder="Например, Аня или Friday Movie Club"
              value={guestName}
            />

            <button
              className="mt-4 w-full rounded-2xl bg-accent px-5 py-4 text-sm font-semibold text-black disabled:opacity-60"
              disabled={authLoading || guestName.trim().length < 2}
              onClick={() => void handleGuestContinue()}
              type="button"
            >
              {inviteReference ? "Продолжить и войти в комнату" : "Продолжить как гость"}
            </button>

            {telegramMode ? (
              <p className="mt-4 text-xs text-zinc-400">Telegram mode обнаружен. При желании вход через Telegram выполнится автоматически.</p>
            ) : (
              <p className="mt-4 text-xs text-zinc-400">Обычный браузерный режим активен. Telegram нужен только как дополнительная точка входа.</p>
            )}

            {authError ? <p className="mt-4 rounded-2xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-100">{authError}</p> : null}
          </div>
        </section>

        <section className="mt-8 grid gap-4 md:grid-cols-3">
          {[
            ["Главная", "Публичная оболочка с нормальным title, описанием и понятным стартом."],
            ["Комнаты", "Invite links работают как обычные `session/<id>` URL, а Telegram share остаётся опцией."],
            ["Синхронизация", "Один и тот же API и WebSocket используются и в браузере, и внутри Telegram контейнера."],
          ].map(([title, text]) => (
            <article key={title} className="rounded-[1.75rem] border border-white/10 bg-surface/40 p-5">
              <h3 className="text-lg font-semibold text-white">{title}</h3>
              <p className="mt-2 text-sm text-zinc-300">{text}</p>
            </article>
          ))}
        </section>
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-4 pb-24 pt-6 text-white md:px-6">
      <header className="mb-6 flex flex-col gap-4 rounded-[2rem] border border-white/10 bg-surface/55 p-5 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-accent">{telegramMode ? "Movielap · Telegram Container" : "Movielap · Web First"}</p>
          <h1 className="mt-2 text-2xl font-bold text-white">Привет, {authSession.first_name}</h1>
          <p className="mt-1 text-sm text-zinc-300">Сначала веб-сценарий, Telegram only when available.</p>
        </div>
        <button className="rounded-2xl border border-white/10 px-4 py-3 text-sm text-white" onClick={handleLogout} type="button">
          Сменить профиль
        </button>
      </header>

      {activeTab === "search" ? (
        <SearchScreen
          initialInviteReference={inviteReference}
          isTelegramContainer={telegramMode}
          userLabel={authSession.first_name}
          userId={authSession.user_id}
        />
      ) : (
        <WatchlistScreen />
      )}
      <BottomTabBar activeTab={activeTab} onChange={setActiveTab} />
    </main>
  );
}
