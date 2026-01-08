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
  CalendarMonthResponse,
  UpcomingDeadlinesResponse,
  ImportPreview,
  CompareResponse,
  SimilarGrantsResponse,
  PipelineResponse,
  PipelineItem,
  PipelineItemCreate,
  PipelineItemUpdate,
  PipelineStats,
  ApplicationStage,
  SavedSearch,
  SavedSearchCreate,
  SavedSearchUpdate,
  SavedSearchList,
  FunderListResponse,
  FunderInsightsResponse,
  FunderGrantsResponse,
  SuccessRatesResponse,
  FundingTrendsResponse,
  PipelineMetricsResponse,
  CategoryBreakdownResponse,
  AnalyticsSummaryResponse,
  ForecastUpcomingResponse,
  SeasonalTrendResponse,
  RecommendationsResponse,
  Deadline,
  DeadlineCreate,
  DeadlineUpdate,
  DeadlineFilters,
  DeadlineListResponse,
  CalendarProvider,
  CalendarIntegration,
  CalendarIntegrationStatus,
  Template,
  TemplateCreate,
  TemplateUpdate,
  TemplateFilters,
  TemplateListResponse,
  TemplateRenderResponse,
  TemplateCategory,
  EligibilityCheckResponse,
  ChatSession,
  ChatSessionListItem,
  ChatMessage,
  ResearchSession,
  ResearchGrantResult,
  FundingAlertPreferences,
  AlertFrequency,
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

  // Compare multiple grants
  compareGrants: async (grantIds: string[]): Promise<CompareResponse> => {
    const response = await api.post<CompareResponse>('/grants/compare', {
      grant_ids: grantIds,
    });
    return response.data;
  },

  // Get similar grants
  getSimilarGrants: async (
    grantId: string,
    params: { limit?: number; min_score?: number } = {}
  ): Promise<SimilarGrantsResponse> => {
    const response = await api.get<SimilarGrantsResponse>(`/grants/${grantId}/similar`, {
      params: {
        limit: params.limit || 10,
        min_score: params.min_score || 20,
      },
    });
    return response.data;
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

  // Get deadlines for a specific month
  getMonthDeadlines: async (
    year: number,
    month: number,
    params: { include_saved?: boolean; include_pipeline?: boolean } = {}
  ): Promise<CalendarMonthResponse> => {
    const response = await api.get<CalendarMonthResponse>(`/calendar/month/${year}/${month}`, {
      params: {
        include_saved: params.include_saved ?? true,
        include_pipeline: params.include_pipeline ?? true,
      },
    });
    return response.data;
  },

  // Get upcoming deadlines
  getUpcomingDeadlines: async (
    params: { days?: number; include_saved?: boolean; include_pipeline?: boolean } = {}
  ): Promise<UpcomingDeadlinesResponse> => {
    const response = await api.get<UpcomingDeadlinesResponse>('/calendar/upcoming', {
      params: {
        days: params.days ?? 30,
        include_saved: params.include_saved ?? true,
        include_pipeline: params.include_pipeline ?? true,
      },
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

// Pipeline API - Application tracking through stages
export const pipelineApi = {
  // Get all pipeline items grouped by stage
  getPipeline: async (): Promise<PipelineResponse> => {
    const response = await api.get<PipelineResponse>('/pipeline');
    return response.data;
  },

  // Get pipeline statistics
  getStats: async (): Promise<PipelineStats> => {
    const response = await api.get<PipelineStats>('/pipeline/stats');
    return response.data;
  },

  // Add grant to pipeline
  addToPipeline: async (data: PipelineItemCreate): Promise<PipelineItem> => {
    const response = await api.post<PipelineItem>('/pipeline', data);
    return response.data;
  },

  // Get single pipeline item
  getItem: async (itemId: string): Promise<PipelineItem> => {
    const response = await api.get<PipelineItem>(`/pipeline/${itemId}`);
    return response.data;
  },

  // Update pipeline item
  updateItem: async (itemId: string, data: PipelineItemUpdate): Promise<PipelineItem> => {
    const response = await api.put<PipelineItem>(`/pipeline/${itemId}`, data);
    return response.data;
  },

  // Move item to new stage
  moveItem: async (itemId: string, stage: ApplicationStage): Promise<PipelineItem> => {
    const response = await api.put<PipelineItem>(`/pipeline/${itemId}/move`, { stage });
    return response.data;
  },

  // Remove from pipeline
  removeFromPipeline: async (itemId: string): Promise<void> => {
    await api.delete(`/pipeline/${itemId}`);
  },

  // Check if grant is in pipeline
  getByGrantId: async (grantId: string): Promise<PipelineItem | null> => {
    const response = await api.get<PipelineItem | null>(`/pipeline/grant/${grantId}`);
    return response.data;
  },
};

// Saved Searches API
export const savedSearchesApi = {
  // Get all saved searches
  list: async (): Promise<SavedSearchList> => {
    const response = await api.get<SavedSearchList>('/saved-searches');
    return response.data;
  },

  // Get a single saved search
  get: async (savedSearchId: string): Promise<SavedSearch> => {
    const response = await api.get<SavedSearch>(`/saved-searches/${savedSearchId}`);
    return response.data;
  },

  // Create a new saved search
  create: async (data: SavedSearchCreate): Promise<SavedSearch> => {
    const response = await api.post<SavedSearch>('/saved-searches', data);
    return response.data;
  },

  // Update a saved search
  update: async (savedSearchId: string, data: SavedSearchUpdate): Promise<SavedSearch> => {
    const response = await api.put<SavedSearch>(`/saved-searches/${savedSearchId}`, data);
    return response.data;
  },

  // Delete a saved search
  delete: async (savedSearchId: string): Promise<void> => {
    await api.delete(`/saved-searches/${savedSearchId}`);
  },

  // Apply saved search and get matching results
  apply: async (
    savedSearchId: string,
    params: { page?: number; page_size?: number } = {}
  ): Promise<PaginatedResponse<GrantMatch>> => {
    const response = await api.post(`/saved-searches/${savedSearchId}/apply`, null, {
      params: {
        page: params.page || 1,
        page_size: params.page_size || 20,
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
};

// Funder Insights API
export const funderInsightsApi = {
  // List all funders with summary stats
  listFunders: async (params: {
    search?: string;
    limit?: number;
    offset?: number;
  } = {}): Promise<FunderListResponse> => {
    const response = await api.get<FunderListResponse>('/funders', {
      params: {
        search: params.search,
        limit: params.limit || 50,
        offset: params.offset || 0,
      },
    });
    return response.data;
  },

  // Get top funders by grant count or funding amount
  getTopFunders: async (params: {
    sort_by?: 'grant_count' | 'funding_amount';
    limit?: number;
  } = {}): Promise<FunderListResponse> => {
    const response = await api.get<FunderListResponse>('/funders/top', {
      params: {
        sort_by: params.sort_by || 'grant_count',
        limit: params.limit || 10,
      },
    });
    return response.data;
  },

  // Get detailed insights for a specific funder
  getFunderInsights: async (funderName: string): Promise<FunderInsightsResponse> => {
    const encodedName = encodeURIComponent(funderName);
    const response = await api.get<FunderInsightsResponse>(`/funders/${encodedName}/insights`);
    return response.data;
  },

  // Get grants from a specific funder
  getFunderGrants: async (
    funderName: string,
    params: { page?: number; page_size?: number; active_only?: boolean } = {}
  ): Promise<FunderGrantsResponse> => {
    const encodedName = encodeURIComponent(funderName);
    const response = await api.get<FunderGrantsResponse>(`/funders/${encodedName}/grants`, {
      params: {
        page: params.page || 1,
        page_size: params.page_size || 20,
        active_only: params.active_only || false,
      },
    });
    return response.data;
  },
};

// Analytics API - Success rates, funding trends, pipeline metrics
export const analyticsApi = {
  // Get success rates by stage, category, and funder
  getSuccessRates: async (): Promise<SuccessRatesResponse> => {
    const response = await api.get<SuccessRatesResponse>('/analytics/success-rates');
    return response.data;
  },

  // Get funding trends over time
  getFundingTrends: async (params: {
    period?: 'monthly' | 'quarterly' | 'yearly';
    months?: number;
  } = {}): Promise<FundingTrendsResponse> => {
    const response = await api.get<FundingTrendsResponse>('/analytics/funding-trends', {
      params: {
        period: params.period || 'monthly',
        months: params.months || 12,
      },
    });
    return response.data;
  },

  // Get pipeline conversion metrics
  getPipelineMetrics: async (): Promise<PipelineMetricsResponse> => {
    const response = await api.get<PipelineMetricsResponse>('/analytics/pipeline-metrics');
    return response.data;
  },

  // Get category breakdown
  getCategoryBreakdown: async (): Promise<CategoryBreakdownResponse> => {
    const response = await api.get<CategoryBreakdownResponse>('/analytics/category-breakdown');
    return response.data;
  },

  // Get analytics summary (dashboard stats)
  getSummary: async (): Promise<AnalyticsSummaryResponse> => {
    const response = await api.get<AnalyticsSummaryResponse>('/analytics/summary');
    return response.data;
  },
};

// Forecast API - Predict upcoming grant opportunities
export const forecastApi = {
  // Get upcoming grant forecasts based on historical patterns
  getUpcoming: async (params: {
    lookahead_months?: number;
    limit?: number;
  } = {}): Promise<ForecastUpcomingResponse> => {
    const response = await api.get<ForecastUpcomingResponse>('/forecast/upcoming', {
      params: {
        lookahead_months: params.lookahead_months || 6,
        limit: params.limit || 20,
      },
    });
    return response.data;
  },

  // Get seasonal grant availability trends
  getSeasonal: async (): Promise<SeasonalTrendResponse> => {
    const response = await api.get<SeasonalTrendResponse>('/forecast/seasonal');
    return response.data;
  },

  // Get personalized recommendations based on profile match
  getRecommendations: async (params: {
    limit?: number;
  } = {}): Promise<RecommendationsResponse> => {
    const response = await api.get<RecommendationsResponse>('/forecast/recommendations', {
      params: {
        limit: params.limit || 10,
      },
    });
    return response.data;
  },
};

// Deadlines API - Custom deadline management
export const deadlinesApi = {
  // Get all deadlines with optional filters
  getDeadlines: async (params?: DeadlineFilters): Promise<DeadlineListResponse> => {
    const response = await api.get<DeadlineListResponse>('/deadlines', { params });
    return response.data;
  },

  // Get a single deadline by ID
  getDeadline: async (id: string): Promise<Deadline> => {
    const response = await api.get<Deadline>(`/deadlines/${id}`);
    return response.data;
  },

  // Create a new deadline
  createDeadline: async (data: DeadlineCreate): Promise<Deadline> => {
    const response = await api.post<Deadline>('/deadlines', data);
    return response.data;
  },

  // Update an existing deadline
  updateDeadline: async (id: string, data: DeadlineUpdate): Promise<Deadline> => {
    const response = await api.patch<Deadline>(`/deadlines/${id}`, data);
    return response.data;
  },

  // Delete a deadline
  deleteDeadline: async (id: string): Promise<void> => {
    await api.delete(`/deadlines/${id}`);
  },

  // Create deadline from a saved grant
  linkGrant: async (grantId: string): Promise<Deadline> => {
    const response = await api.post<Deadline>('/deadlines/link-grant', { grant_id: grantId });
    return response.data;
  },

  // Export deadlines as ICS calendar file
  exportIcs: async (): Promise<Blob> => {
    const response = await api.get('/deadlines/export.ics', {
      responseType: 'blob',
    });
    return response.data;
  },
};

// ============================================
// Calendar Integration API
// ============================================

export const calendarIntegrationApi = {
  // Get integration status for all providers
  getStatus: async (): Promise<CalendarIntegrationStatus> => {
    const response = await api.get<CalendarIntegrationStatus>('/integrations/calendar/status');
    return response.data;
  },

  // Initiate OAuth flow - returns redirect URL
  connectGoogle: async (): Promise<{ auth_url: string }> => {
    const response = await api.post<{ auth_url: string }>('/integrations/calendar/google/connect');
    return response.data;
  },

  // Handle OAuth callback
  handleGoogleCallback: async (code: string, state: string): Promise<CalendarIntegration> => {
    const response = await api.post<CalendarIntegration>('/integrations/calendar/google/callback', { code, state });
    return response.data;
  },

  // Disconnect calendar
  disconnect: async (provider: CalendarProvider): Promise<void> => {
    await api.delete(`/integrations/calendar/${provider}`);
  },

  // Toggle sync
  toggleSync: async (provider: CalendarProvider, enabled: boolean): Promise<CalendarIntegration> => {
    const response = await api.patch<CalendarIntegration>(`/integrations/calendar/${provider}`, { sync_enabled: enabled });
    return response.data;
  },

  // Force sync
  syncNow: async (provider: CalendarProvider): Promise<{ synced_count: number }> => {
    const response = await api.post<{ synced_count: number }>(`/integrations/calendar/${provider}/sync`);
    return response.data;
  },
};

// ============================================
// Templates API
// ============================================

export const templatesApi = {
  // List templates with filters
  getTemplates: async (params?: TemplateFilters): Promise<TemplateListResponse> => {
    const response = await api.get<TemplateListResponse>('/templates', { params });
    return response.data;
  },

  // Get single template
  getTemplate: async (id: string): Promise<Template> => {
    const response = await api.get<Template>(`/templates/${id}`);
    return response.data;
  },

  // Create template
  createTemplate: async (data: TemplateCreate): Promise<Template> => {
    const response = await api.post<Template>('/templates', data);
    return response.data;
  },

  // Update template
  updateTemplate: async (id: string, data: TemplateUpdate): Promise<Template> => {
    const response = await api.patch<Template>(`/templates/${id}`, data);
    return response.data;
  },

  // Delete template
  deleteTemplate: async (id: string): Promise<void> => {
    await api.delete(`/templates/${id}`);
  },

  // Duplicate template
  duplicateTemplate: async (id: string): Promise<Template> => {
    const response = await api.post<Template>(`/templates/${id}/duplicate`);
    return response.data;
  },

  // Render template with variables
  renderTemplate: async (id: string, variables: Record<string, string | number>): Promise<TemplateRenderResponse> => {
    const response = await api.post<TemplateRenderResponse>(`/templates/${id}/render`, { variables });
    return response.data;
  },

  // Get categories
  getCategories: async (): Promise<TemplateCategory[]> => {
    const response = await api.get<TemplateCategory[]>('/templates/categories');
    return response.data;
  },
};

// ===== AI Tools API =====

// Eligibility API
export const eligibilityApi = {
  checkEligibility: async (grantId: string, additionalContext?: string) => {
    const response = await api.post<EligibilityCheckResponse>('/eligibility/check', {
      grant_id: grantId,
      additional_context: additionalContext,
    });
    return response.data;
  },

  followUp: async (sessionId: string, message: string) => {
    const response = await api.post('/eligibility/follow-up', {
      session_id: sessionId,
      message,
    });
    return response.data;
  },

  getSessions: async () => {
    const response = await api.get('/eligibility/sessions');
    return response.data;
  },
};

// Chat API
export const chatApi = {
  createSession: async (data: { title?: string; session_type?: string; context_grant_id?: string }) => {
    const response = await api.post<ChatSession>('/chat/sessions', data);
    return response.data;
  },

  getSessions: async (limit = 50) => {
    const response = await api.get<ChatSessionListItem[]>('/chat/sessions', { params: { limit } });
    return response.data;
  },

  getSession: async (sessionId: string) => {
    const response = await api.get<ChatSession>(`/chat/sessions/${sessionId}`);
    return response.data;
  },

  sendMessage: async (sessionId: string, content: string) => {
    const response = await api.post<ChatMessage>(`/chat/sessions/${sessionId}/messages`, { content });
    return response.data;
  },

  deleteSession: async (sessionId: string) => {
    await api.delete(`/chat/sessions/${sessionId}`);
  },
};

// Research API
export const researchApi = {
  createSession: async (query: string) => {
    const response = await api.post<ResearchSession>('/research/sessions', { query });
    return response.data;
  },

  getSessions: async (limit = 20) => {
    const response = await api.get<ResearchSession[]>('/research/sessions', { params: { limit } });
    return response.data;
  },

  getSession: async (sessionId: string) => {
    const response = await api.get<ResearchSession>(`/research/sessions/${sessionId}`);
    return response.data;
  },

  quickSearch: async (query: string, maxResults = 10) => {
    const response = await api.post<ResearchGrantResult[]>('/research/quick-search', {
      query,
      max_results: maxResults,
    });
    return response.data;
  },

  deleteSession: async (sessionId: string) => {
    await api.delete(`/research/sessions/${sessionId}`);
  },
};

// Funding Alerts API
export const alertsApi = {
  getPreferences: async () => {
    const response = await api.get<FundingAlertPreferences>('/alerts/preferences');
    return response.data;
  },

  updatePreferences: async (data: Partial<FundingAlertPreferences>) => {
    const response = await api.put<FundingAlertPreferences>('/alerts/preferences', data);
    return response.data;
  },

  preview: async () => {
    const response = await api.get('/alerts/preview');
    return response.data;
  },

  sendNow: async () => {
    const response = await api.post('/alerts/send-now');
    return response.data;
  },
};

export default api;
