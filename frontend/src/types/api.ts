export interface AuthUserResponse {
  user_id: number;
  first_name: string;
  username?: string | null;
  auth_provider: string;
  token: string;
}

export interface TelegramSignInRequest {
  init_data_raw: string;
}

export interface GuestAuthRequest {
  name: string;
}

export interface MatchExplainerItem {
  audience_label: string;
  reason_ru: string;
}

export interface StreamingProvider {
  name: string;
}

export interface HardFilters {
  include_genres: string[];
  exclude_genres: string[];
  year_from: number | null;
  year_to: number | null;
  countries: string[];
  min_runtime: number | null;
  max_runtime: number | null;
  min_rating: number | null;
  exclude_keywords: string[];
}

export interface MovieRecommendation {
  tmdb_id: number;
  original_title: string;
  year: number | null;
  poster_path: string | null;
  vote_average: number | null;
  overview: string | null;
  genre_ids: number[];
  genres: string[];
  runtime_minutes: number | null;
  origin_countries: string[];
  reason_ru: string;
  match_summary_ru: string | null;
  match_explainer: MatchExplainerItem[];
  trailer_url: string | null;
  streaming_providers: StreamingProvider[];
}

export interface SoloRecommendationRequest {
  preference_text: string;
  moods: string[];
  hard_filters?: HardFilters | null;
}

export interface RecommendationResponse {
  movies: MovieRecommendation[];
}

export interface SessionCreateRequest {
  preference_text: string;
  moods: string[];
  hard_filters?: HardFilters | null;
  max_participants?: number;
}

export interface SessionJoinRequest {
  session_id: string;
  preference_text: string;
  moods: string[];
  hard_filters?: HardFilters | null;
}

export interface SessionResponse {
  id: string;
  type: "solo" | "duo" | string;
  status: "waiting" | "active" | "completed" | string;
  creator_id: number;
  guest_id: number | null;
  participant_ids: number[];
  max_participants: number;
  invite_link?: string | null;
  invite_code?: string | null;
  created_at: string;
  movies?: MovieRecommendation[] | null;
}

export interface WatchlistAddRequest {
  tmdb_id: number;
  movie?: MovieRecommendation | null;
}

export interface WatchlistItemResponse {
  id: string;
  user_id: number;
  tmdb_id: number;
  added_at: string;
  original_title?: string | null;
  year?: number | null;
  poster_path?: string | null;
  vote_average?: number | null;
  overview?: string | null;
  genre_ids: number[];
  genres: string[];
  runtime_minutes?: number | null;
  origin_countries: string[];
  reason_ru?: string | null;
  match_summary_ru?: string | null;
}

export interface MovieFeedbackRequest {
  tmdb_id: number;
  status: "seen" | "skip_forever";
}

export interface SwipeCreateRequest {
  session_id: string;
  tmdb_id: number;
  action: "like" | "dislike";
}

export interface SwipeResponse {
  matched: boolean;
  movie: MovieRecommendation | null;
}

export interface SessionMoviesReadyEvent {
  event: "movies_ready";
  session_id: string;
  movies: MovieRecommendation[];
}

export interface SessionMatchFoundEvent {
  event: "match_found";
  session_id: string;
  movie: MovieRecommendation;
}

export type SessionSocketEvent = SessionMoviesReadyEvent | SessionMatchFoundEvent;
