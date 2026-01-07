import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import type {
  AuthResponse,
  LoginCredentials,
  SignupData,
  User,
  GrantMatch,
  DashboardStats,
  PaginatedResponse,
  NotificationPreferences,
  Grant,
  CalendarLinks,
  ImportPreview
} from '../types';

// API base URL - connects to FastAPI backend
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Create axios instance
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config;

    // If 401 and we have a refresh token, try to refresh
    if (error.response?.status === 401 && originalRequest) {
      const refreshToken = localStorage.getItem('refresh_token');

      if (refreshToken && !originalRequest.url?.includes('/auth/refresh')) {
        try {
          const response = await api.post<AuthResponse>('/auth/refresh', {
            refresh_token: refreshToken
          });

          localStorage.setItem('access_token', response.data.access_token);
          localStorage.setItem('refresh_token', response.data.refresh_token);

          // Retry original request
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`;
          }
          return api(originalRequest);
        } catch {
          // Refresh failed, clear tokens and redirect
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          window.location.href = '/auth';
        }
      } else {
        // No refresh token, clear and redirect
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/auth';
      }
    }
    return Promise.reject(error);
  }
);

// Helper to transform backend match to frontend format
function transformMatch(backendMatch: Record<string, unknown>): GrantMatch {
  const matchScore = (backendMatch.match_score as number) || 0;

  return {
    id: backendMatch.id as string,
    grant_id: backendMatch.grant_id as string,
    user_id: backendMatch.user_id as string | undefined,
    score: Math.round(matchScore * 100), // Convert 0-1 to 0-100
    match_score: matchScore,
    reasoning: backendMatch.reasoning as string | undefined,
    predicted_success: backendMatch.predicted_success as number | undefined,
    status: (backendMatch.user_action as GrantMatch['status']) || 'new',
    user_action: backendMatch.user_action as string | undefined,
    created_at: backendMatch.created_at as string,
    grant: {
      id: backendMatch.grant_id as string,
      title: backendMatch.grant_title as string,
      description: backendMatch.grant_description as string | undefined,
      source: 'federal' as const,
      external_id: '',
      agency: backendMatch.grant_agency as string | undefined,
      funder_name: backendMatch.grant_agency as string | undefined,
      amount_min: backendMatch.grant_amount_min as number | undefined,
      amount_max: backendMatch.grant_amount_max as number | undefined,
      funding_amount_min: backendMatch.grant_amount_min as number | undefined,
      funding_amount_max: backendMatch.grant_amount_max as number | undefined,
      deadline: backendMatch.grant_deadline as string | undefined,
      url: backendMatch.grant_url as string | undefined,
      categories: backendMatch.grant_categories as string[] | undefined,
      focus_areas: backendMatch.grant_categories as string[] || [],
    },
  };
}

// Helper to transform dashboard stats
function transformStats(backendStats: Record<string, unknown>): DashboardStats {
  const scoreDistribution = (backendStats.score_distribution as Record<string, number>) || {};
  const upcomingDeadlines = (backendStats.upcoming_deadlines as unknown[]) || [];

  return {
    total_matches: (backendStats.total_matches as number) || 0,
    saved_grants: (backendStats.saved_grants as number) || 0,
    dismissed_grants: (backendStats.dismissed_grants as number) || 0,
    new_matches_today: (backendStats.new_matches_today as number) || 0,
    new_matches_week: (backendStats.new_matches_week as number) || 0,
    score_distribution: {
      excellent: scoreDistribution.excellent || 0,
      good: scoreDistribution.good || 0,
      moderate: scoreDistribution.moderate || 0,
      low: scoreDistribution.low || 0,
    },
    average_match_score: backendStats.average_match_score as number | undefined,
    upcoming_deadlines: upcomingDeadlines as DashboardStats['upcoming_deadlines'],
    recent_matches: (backendStats.recent_matches as DashboardStats['recent_matches']) || [],
    profile_complete: (backendStats.profile_complete as boolean) || false,
    profile_has_embedding: (backendStats.profile_has_embedding as boolean) || false,
    // Legacy fields for UI compatibility
    new_grants: (backendStats.new_matches_today as number) || 0,
    high_matches: scoreDistribution.excellent || 0,
    upcoming_deadline_count: upcomingDeadlines.length,
  };
}

// Auth API
export const authApi = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    // Backend expects JSON body, not form-encoded
    const response = await api.post<AuthResponse>('/auth/login', {
      email: credentials.email,
      password: credentials.password,
    });
    return response.data;
  },

  signup: async (data: SignupData): Promise<AuthResponse> => {
    // Map frontend signup data to backend format
    const response = await api.post<AuthResponse>('/auth/register', {
      email: data.email,
      password: data.password,
      name: data.organization_name || data.name,
      institution: data.institution,
    });
    return response.data;
  },

  refreshToken: async (refreshToken: string): Promise<AuthResponse> => {
    const response = await api.post<AuthResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get<User>('/auth/me');
    const user = response.data;

    // Map backend user to frontend format
    return {
      ...user,
      organization_name: user.name || user.institution,
      organization_type: user.institution ? 'Research Institution' : undefined,
      focus_areas: [],
    };
  },

  logout: (): void => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  },
};

// Grants API
export const grantsApi = {
  // List grants (public endpoint)
  listGrants: async (params: {
    page?: number;
    page_size?: number;
    source?: string;
    category?: string;
    min_amount?: number;
    max_amount?: number;
    active_only?: boolean;
  } = {}): Promise<PaginatedResponse<Grant>> => {
    const response = await api.get('/grants', { params });
    const data = response.data;

    return {
      items: data.grants || [],
      total: data.total,
      page: data.page,
      page_size: data.page_size,
      has_more: data.has_more,
    };
  },

  // Search grants
  searchGrants: async (query: string, limit: number = 20): Promise<PaginatedResponse<Grant>> => {
    const response = await api.get('/grants/search', {
      params: { q: query, limit },
    });
    const data = response.data;

    return {
      items: data.grants || [],
      total: data.total,
      page: 1,
      page_size: limit,
      has_more: data.has_more,
    };
  },

  // Get single grant
  getGrant: async (grantId: string): Promise<Grant> => {
    const response = await api.get(`/grants/${grantId}`);
    return response.data;
  },

  // Get user's matches
  getMatches: async (params: {
    page?: number;
    per_page?: number;
    source?: string;
    status?: string;
    min_score?: number;
  } = {}): Promise<PaginatedResponse<GrantMatch>> => {
    const response = await api.get('/matches', {
      params: {
        page: params.page || 1,
        page_size: params.per_page || 20,
        min_score: params.min_score ? params.min_score / 100 : undefined, // Convert to 0-1
        user_action: params.status,
        exclude_dismissed: params.status !== 'dismissed',
      },
    });

    const data = response.data;
    const matches = (data.matches || []).map(transformMatch);

    return {
      items: matches,
      matches: matches,
      total: data.total,
      page: data.page,
      page_size: data.page_size,
      has_more: data.has_more,
    };
  },

  // Get single match
  getMatch: async (matchId: string): Promise<GrantMatch> => {
    const response = await api.get(`/matches/${matchId}`);
    return transformMatch(response.data);
  },

  // Update match status (save/dismiss)
  updateMatchStatus: async (
    matchId: string,
    status: 'viewed' | 'saved' | 'dismissed' | 'applied'
  ): Promise<GrantMatch> => {
    const response = await api.post(`/matches/${matchId}/action`, {
      action: status,
    });
    return transformMatch(response.data);
  },

  // Submit match feedback
  submitFeedback: async (
    matchId: string,
    feedback: {
      relevance_rating: number;
      would_apply: boolean;
      feedback_text?: string;
      match_quality_issues?: string[];
    }
  ): Promise<GrantMatch> => {
    const response = await api.post(`/matches/${matchId}/feedback`, feedback);
    return transformMatch(response.data);
  },

  // Get dashboard stats
  getDashboardStats: async (): Promise<DashboardStats> => {
    const response = await api.get('/stats');
    return transformStats(response.data);
  },
};

// User/Profile API
export const userApi = {
  updateProfile: async (data: Partial<User>): Promise<User> => {
    const response = await api.patch<User>('/profile', {
      research_areas: data.focus_areas,
      // Map other fields as needed
    });
    return response.data;
  },

  getProfile: async (): Promise<Record<string, unknown>> => {
    const response = await api.get('/profile');
    return response.data;
  },

  getNotificationPreferences: async (): Promise<NotificationPreferences> => {
    const response = await api.get<NotificationPreferences>('/users/me/notifications');
    return response.data;
  },

  updateNotificationPreferences: async (
    prefs: Partial<NotificationPreferences>
  ): Promise<NotificationPreferences> => {
    const response = await api.patch<NotificationPreferences>('/users/me/notifications', prefs);
    return response.data;
  },
};

// Calendar API
export const calendarApi = {
  // Get calendar links for a grant
  getCalendarLinks: async (grantId: string): Promise<CalendarLinks> => {
    const response = await api.get<CalendarLinks>(`/calendar/grant/${grantId}/links`);
    return response.data;
  },

  // Export saved grants as ICS file
  exportCalendar: async (savedOnly: boolean = true, daysAhead: number = 365): Promise<Blob> => {
    const response = await api.get('/calendar/export', {
      params: { saved_only: savedOnly, days_ahead: daysAhead },
      responseType: 'blob',
    });
    return response.data;
  },

  // Get ICS for a single grant
  getGrantIcs: async (grantId: string): Promise<Blob> => {
    const response = await api.get(`/calendar/grant/${grantId}/ics`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

// Profile Import API
export const profileImportApi = {
  // Import profile from ORCID
  importFromOrcid: async (orcid: string): Promise<ImportPreview> => {
    const response = await api.post<ImportPreview>('/profile/import/orcid', { orcid });
    return response.data;
  },

  // Import profile from CV
  importFromCv: async (file: File): Promise<ImportPreview> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post<ImportPreview>('/profile/import/cv', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
};

export default api;
