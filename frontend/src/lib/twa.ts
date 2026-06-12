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

export function isTelegramWebApp(): boolean {
  const webApp = getWebApp();
  return Boolean(webApp?.initDataUnsafe?.user && webApp?.initData);
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

export function getTelegramInitData(): string | null {
  return getWebApp()?.initData ?? null;
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

export function openTelegramShare(url: string, text: string): void {
  const shareUrl = new URL("https://t.me/share/url");
  shareUrl.searchParams.set("url", url);
  shareUrl.searchParams.set("text", text);
  window.open(shareUrl.toString(), "_blank", "noopener,noreferrer");
}
