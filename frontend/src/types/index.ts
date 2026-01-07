// User types
export interface User {
  id: string;
  email: string;
  name?: string;
  institution?: string;
  phone?: string;
  created_at: string;
  has_profile: boolean;
  // Frontend-specific fields for compatibility
  organization_name?: string;
  organization_type?: string;
  focus_areas?: string[];
}

// Authentication types
export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface SignupData {
  email: string;
  password: string;
  name?: string;
  institution?: string;
  // Frontend-specific fields that map to profile
  organization_name?: string;
  organization_type?: string;
  focus_areas?: string[];
}

// Grant types
export type GrantSource = 'federal' | 'foundation' | 'state' | 'corporate' | 'nih' | 'nsf' | 'grants_gov';
export type GrantStatus = 'active' | 'forecasted' | 'closed' | 'archived';

export interface Grant {
  id: string;
  title: string;
  description?: string;
  source: GrantSource;
  external_id: string;
  agency?: string;
  funder_name?: string;
  amount_min?: number;
  amount_max?: number;
  funding_amount_min?: number;
  funding_amount_max?: number;
  deadline?: string;
  posted_at?: string;
  url?: string;
  eligibility?: Record<string, unknown>;
  categories?: string[];
  focus_areas?: string[];
  created_at?: string;
}

export interface GrantMatch {
  id: string;
  grant_id: string;
  user_id?: string;
  score: number; // 0-100 for display
  match_score?: number; // 0-1 from API
  reasoning?: string;
  predicted_success?: number;
  status: 'new' | 'viewed' | 'saved' | 'dismissed' | 'applied';
  user_action?: string;
  created_at: string;
  grant: Grant;
}

// Dashboard stats
export interface MatchScoreDistribution {
  excellent: number;
  good: number;
  moderate: number;
  low: number;
}

export interface UpcomingDeadline {
  grant_id: string;
  match_id: string;
  grant_title: string;
  deadline: string;
  match_score: number;
  days_remaining: number;
}

export interface RecentMatch {
  match_id: string;
  grant_id: string;
  grant_title: string;
  match_score: number;
  created_at: string;
  grant_agency?: string;
}

export interface DashboardStats {
  total_matches: number;
  saved_grants: number;
  dismissed_grants: number;
  new_matches_today: number;
  new_matches_week: number;
  score_distribution: MatchScoreDistribution;
  average_match_score?: number;
  upcoming_deadlines: UpcomingDeadline[];
  recent_matches: RecentMatch[];
  profile_complete: boolean;
  profile_has_embedding: boolean;
  // Legacy fields for UI compatibility
  new_grants?: number;
  high_matches?: number;
  upcoming_deadline_count?: number;
}

// Notification preferences
export interface NotificationPreferences {
  email_enabled: boolean;
  email_frequency: 'daily' | 'weekly' | 'realtime';
  min_match_score: number;
  notify_on_deadline: boolean;
  deadline_warning_days: number;
}

// API response types
export interface PaginatedResponse<T> {
  items: T[];
  matches?: T[]; // Backend uses 'matches' for match list
  total: number;
  page: number;
  page_size: number;
  per_page?: number;
  has_more: boolean;
}

export interface ApiError {
  error: boolean;
  message: string;
  detail?: string;
  status_code: number;
}

// Calendar types
export interface CalendarLinks {
  grant_id: string;
  grant_title: string;
  deadline: string;
  google_calendar_url: string;
  outlook_calendar_url: string;
  ics_download_url: string;
}

// Profile import types
export interface ImportPreview {
  name?: string;
  institution?: string;
  research_areas: string[];
  methods: string[];
  publications: Array<{
    title: string;
    journal?: string;
    year?: number;
    type?: string;
  }>;
  past_grants: Array<{
    title: string;
    funder?: string;
    amount?: string;
    start_year?: number;
    end_year?: number;
  }>;
  career_stage?: string;
  keywords: string[];
  orcid?: string;
  source: 'orcid' | 'cv';
}
