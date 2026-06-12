import type {
  AuthUserResponse,
  GuestAuthRequest,
  MovieFeedbackRequest,
  RecommendationResponse,
  SessionCreateRequest,
  SessionJoinRequest,
  SessionResponse,
  SoloRecommendationRequest,
  SwipeCreateRequest,
  SwipeResponse,
  TelegramSignInRequest,
  WatchlistAddRequest,
  WatchlistItemResponse,
} from "../types/api";
import { getAuthToken } from "./auth";

function resolveApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL;
  if (configured) {
    return configured;
  }

  if (typeof window !== "undefined") {
    return `${window.location.origin}/api`;
  }

  return "http://localhost:8000/api";
}

const API_BASE_URL = resolveApiBaseUrl();

async function request<TResponse, TPayload = undefined>(
  path: string,
  init?: RequestInit & { payload?: TPayload },
): Promise<TResponse> {
  let response: Response;
  try {
    const token = getAuthToken();
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
      body: init?.payload ? JSON.stringify(init.payload) : init?.body,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown network error";
    throw new Error(`Не удается подключиться к API: ${API_BASE_URL}. ${message}`);
  }

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return (await response.json()) as TResponse;
}

async function parseError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload.detail) {
      return payload.detail;
    }
  } catch {
    // Ignore JSON parse failure and fall back to text.
  }

  const errorText = await response.text();
  return errorText || `Request failed with status ${response.status}`;
}

export function getSessionWebSocketUrl(sessionId: string): string {
  const apiUrl = API_BASE_URL.startsWith("http")
    ? new URL(API_BASE_URL)
    : new URL(API_BASE_URL, window.location.origin);
  apiUrl.protocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
  apiUrl.pathname = `/ws/sessions/${sessionId}`;
  return apiUrl.toString();
}

export const apiClient = {
  getMe(): Promise<AuthUserResponse> {
    return request<AuthUserResponse>("/auth/me");
  },
  signInAsGuest(payload: GuestAuthRequest): Promise<AuthUserResponse> {
    return request<AuthUserResponse, GuestAuthRequest>("/auth/guest", {
      method: "POST",
      payload,
    });
  },
  signInWithTelegram(payload: TelegramSignInRequest): Promise<AuthUserResponse> {
    return request<AuthUserResponse, TelegramSignInRequest>("/auth/telegram", {
      method: "POST",
      payload,
    });
  },
  getSession(sessionId: string): Promise<SessionResponse> {
    return request<SessionResponse>(`/sessions/${sessionId}`);
  },
  resolveInviteCode(inviteCode: string): Promise<SessionResponse> {
    return request<SessionResponse>(`/sessions/resolve/${encodeURIComponent(inviteCode)}`);
  },
  getWatchlist(): Promise<WatchlistItemResponse[]> {
    return request<WatchlistItemResponse[]>("/watchlist/me");
  },
  addToWatchlist(payload: WatchlistAddRequest): Promise<WatchlistItemResponse> {
    return request<WatchlistItemResponse, WatchlistAddRequest>("/watchlist/add", {
      method: "POST",
      payload,
    });
  },
  saveFeedback(payload: MovieFeedbackRequest): Promise<{ status: string }> {
    return request<{ status: string }, MovieFeedbackRequest>("/feedback", {
      method: "POST",
      payload,
    });
  },
  getSoloRecommendations(payload: SoloRecommendationRequest): Promise<RecommendationResponse> {
    return request<RecommendationResponse, SoloRecommendationRequest>("/recommendations/solo", {
      method: "POST",
      payload,
    });
  },
  createSession(payload: SessionCreateRequest): Promise<SessionResponse> {
    return request<SessionResponse, SessionCreateRequest>("/sessions/create", {
      method: "POST",
      payload,
    });
  },
  joinSession(payload: SessionJoinRequest): Promise<SessionResponse> {
    return request<SessionResponse, SessionJoinRequest>("/sessions/join", {
      method: "POST",
      payload,
    });
  },
  createSwipe(payload: SwipeCreateRequest): Promise<SwipeResponse> {
    return request<SwipeResponse, SwipeCreateRequest>("/swipe", {
      method: "POST",
      payload,
    });
  },
};
