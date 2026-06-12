import type { TelegramUserPayload } from "../types/api";

type TelegramWebAppSdk = {
  ready: () => void;
  expand: () => void;
  setBackgroundColor: (color: string) => void;
  setHeaderColor: (color: string) => void;
  initData?: string;
  initDataUnsafe?: {
    user?: {
      id: number;
      first_name: string;
      username?: string;
    };
    start_param?: string;
  };
};

function getWebApp(): TelegramWebAppSdk | null {
  if (typeof window === "undefined") {
    return null;
  }

  const telegram = (window as Window & { Telegram?: { WebApp?: TelegramWebAppSdk } }).Telegram;
  return telegram?.WebApp ?? null;
}

export function initTelegramApp(): void {
  const webApp = getWebApp();
  if (!webApp) {
    return;
  }

  try {
    webApp.ready();
    webApp.expand();
    webApp.setBackgroundColor("#121212");
    webApp.setHeaderColor("#121212");
  } catch (error) {
    console.warn("Telegram WebApp init skipped:", error);
  }
}

export function getTelegramUser(): TelegramUserPayload {
  const webApp = getWebApp();
  const user = webApp?.initDataUnsafe?.user;
  if (!user) {
    return {
      init_data_raw: null,
      telegram_id: 1,
      first_name: "Guest",
      username: null,
    };
  }

  return {
    init_data_raw: webApp?.initData ?? null,
    telegram_id: user.id,
    first_name: user.first_name,
    username: user.username ?? null,
  };
}

export function getStartParam(): string | null {
  const webApp = getWebApp();
  const webAppStartParam = webApp?.initDataUnsafe?.start_param;
  if (webAppStartParam) {
    return webAppStartParam;
  }

  if (typeof window === "undefined") {
    return null;
  }

  const searchParams = new URLSearchParams(window.location.search);
  return searchParams.get("startapp") ?? searchParams.get("tgWebAppStartParam");
}
