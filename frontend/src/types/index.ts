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

// Grant comparison types
export interface ComparisonGrant {
  id: string;
  title: string;
  agency?: string;
  source: GrantSource;
  amount_min?: number;
  amount_max?: number;
  deadline?: string;
  url?: string;
  categories?: string[];
  eligibility?: Record<string, unknown>;
  description?: string;
  match_score?: number; // 0-1 scale
}

export interface CompareResponse {
  grants: ComparisonGrant[];
  comparison_id?: string;
}

// Similar grants types
export interface SimilarGrant extends Grant {
  similarity_score: number; // 0-100
  similarity_reasons: string[];
}

export interface SimilarGrantsResponse {
  similar_grants: SimilarGrant[];
  source_grant_id: string;
  total: number;
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

// Pipeline types
export type ApplicationStage = 'researching' | 'writing' | 'submitted' | 'awarded' | 'rejected';

export interface PipelineGrantSummary {
  id: string;
  title: string;
  agency?: string;
  deadline?: string;
  amount_min?: number;
  amount_max?: number;
  url?: string;
}

export interface PipelineItem {
  id: string;
  user_id: string;
  grant_id: string;
  match_id?: string;
  stage: ApplicationStage;
  notes?: string;
  target_date?: string;
  created_at: string;
  updated_at: string;
  grant: PipelineGrantSummary;
  days_until_deadline?: number;
  days_until_target?: number;
}

export interface PipelineStageGroup {
  stage: ApplicationStage;
  items: PipelineItem[];
  count: number;
}

export interface PipelineResponse {
  stages: PipelineStageGroup[];
  total: number;
}

export interface PipelineStats {
  total: number;
  by_stage: Record<string, number>;
  upcoming_deadlines: number;
  past_deadlines: number;
}

export interface PipelineItemCreate {
  grant_id: string;
  match_id?: string;
  stage?: ApplicationStage;
  notes?: string;
  target_date?: string;
}

export interface PipelineItemUpdate {
  stage?: ApplicationStage;
  notes?: string;
  target_date?: string;
}

// Saved search types
export interface SavedSearchFilters {
  search_query?: string;
  source?: string;
  min_score?: number;
  max_score?: number;
  min_amount?: number;
  max_amount?: number;
  categories?: string[];
  show_saved_only?: boolean;
  active_only?: boolean;
}

export interface SavedSearch {
  id: string;
  name: string;
  filters: SavedSearchFilters;
  alert_enabled: boolean;
  created_at: string;
  last_alerted_at?: string;
}

export interface SavedSearchCreate {
  name: string;
  filters: SavedSearchFilters;
  alert_enabled?: boolean;
}

export interface SavedSearchUpdate {
  name?: string;
  filters?: SavedSearchFilters;
  alert_enabled?: boolean;
}

export interface SavedSearchList {
  saved_searches: SavedSearch[];
  total: number;
}

// Funder Insights types
export interface FunderSummary {
  funder_name: string;
  total_grants: number;
  avg_amount_min?: number;
  avg_amount_max?: number;
  focus_areas: string[];
  active_grants: number;
}

export interface FunderListResponse {
  funders: FunderSummary[];
  total: number;
}

export interface DeadlineMonth {
  month: number;
  month_name: string;
  grant_count: number;
}

export interface UserApplication {
  grant_id: string;
  grant_title: string;
  stage: string;
  applied_at?: string;
}

export interface UserFunderHistory {
  total_applications: number;
  awarded_count: number;
  rejected_count: number;
  pending_count: number;
  success_rate?: number;
  applications: UserApplication[];
}

export interface FunderInsightsResponse {
  funder_name: string;
  total_grants: number;
  active_grants: number;
  avg_amount_min?: number;
  avg_amount_max?: number;
  min_amount?: number;
  max_amount?: number;
  focus_areas: string[];
  focus_area_counts: Record<string, number>;
  deadline_months: DeadlineMonth[];
  typical_deadline_months: string[];
  user_history?: UserFunderHistory;
}

export interface FunderGrant {
  id: string;
  title: string;
  description?: string;
  amount_min?: number;
  amount_max?: number;
  deadline?: string;
  posted_at?: string;
  categories?: string[];
  url?: string;
  is_active: boolean;
}

export interface FunderGrantsResponse {
  funder_name: string;
  grants: FunderGrant[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// Calendar View types
export type CalendarEventType = 'saved' | 'pipeline';
export type UrgencyLevel = 'critical' | 'warning' | 'normal';

export interface CalendarEvent {
  grant_id: string;
  title: string;
  deadline: string;
  event_type: CalendarEventType;
  stage?: string;
  urgency: UrgencyLevel;
  days_until_deadline: number;
  agency?: string;
  amount_max?: number;
  url?: string;
  match_id?: string;
  pipeline_item_id?: string;
}

export interface CalendarDay {
  date: string;
  events: CalendarEvent[];
  count: number;
}

export interface CalendarDeadlinesResponse {
  events: CalendarEvent[];
  total: number;
  start_date: string;
  end_date: string;
}

export interface CalendarMonthResponse {
  year: number;
  month: number;
  days: CalendarDay[];
  total_events: number;
}

export interface CalendarUpcomingDeadline {
  grant_id: string;
  title: string;
  deadline: string;
  days_until_deadline: number;
  urgency: UrgencyLevel;
  event_type: CalendarEventType;
  stage?: string;
  agency?: string;
  amount_max?: number;
}

export interface UpcomingDeadlinesResponse {
  deadlines: CalendarUpcomingDeadline[];
  total: number;
  critical_count: number;
  warning_count: number;
}

// Analytics types
export interface SuccessRateByCategory {
  category: string;
  total: number;
  submitted: number;
  awarded: number;
  rejected: number;
  success_rate: number;
}

export interface SuccessRateByFunder {
  funder: string;
  total: number;
  submitted: number;
  awarded: number;
  rejected: number;
  success_rate: number;
}

export interface SuccessRateByStage {
  stage: string;
  count: number;
}

export interface SuccessRatesResponse {
  total_applications: number;
  overall_success_rate: number;
  by_stage: SuccessRateByStage[];
  by_category: SuccessRateByCategory[];
  by_funder: SuccessRateByFunder[];
}

export interface FundingDataPoint {
  period: string;
  applied_amount: number;
  awarded_amount: number;
  applied_count: number;
  awarded_count: number;
}

export interface FundingTrendsResponse {
  data_points: FundingDataPoint[];
  total_applied_amount: number;
  total_awarded_amount: number;
  total_applied_count: number;
  total_awarded_count: number;
  period_type: string;
}

export interface PipelineStageMetric {
  stage: string;
  count: number;
  conversion_rate?: number;
  avg_days_in_stage?: number;
}

export interface PipelineMetricsResponse {
  stages: PipelineStageMetric[];
  total_in_pipeline: number;
  overall_conversion_rate: number;
  avg_time_to_award?: number;
}

export interface CategoryBreakdownItem {
  category: string;
  total: number;
  researching: number;
  writing: number;
  submitted: number;
  awarded: number;
  rejected: number;
  success_rate: number;
  avg_funding_amount?: number;
}

export interface CategoryBreakdownResponse {
  categories: CategoryBreakdownItem[];
  total_categories: number;
}

export interface AnalyticsSummaryResponse {
  total_applications: number;
  total_in_pipeline: number;
  total_submitted: number;
  total_awarded: number;
  total_rejected: number;
  overall_success_rate: number;
  total_funding_applied: number;
  total_funding_awarded: number;
  avg_funding_per_award?: number;
  pipeline_conversion_rate: number;
  top_funder?: string;
  top_category?: string;
}

// Forecast types
export type RecurrencePattern = 'annual' | 'biannual' | 'quarterly' | 'monthly' | 'unknown';

export interface ForecastGrant {
  id?: string;
  funder_name: string;
  predicted_open_date: string;
  confidence: number; // 0-1
  historical_amount_min?: number;
  historical_amount_max?: number;
  focus_areas: string[];
  title?: string;
  historical_deadline_month?: number;
  recurrence_pattern: RecurrencePattern;
  last_seen_date?: string;
  source?: string;
  match_score?: number; // 0-1
  reasoning?: string;
}

export interface ForecastUpcomingResponse {
  forecasts: ForecastGrant[];
  total: number;
  generated_at: string;
  lookahead_months: number;
}

export interface SeasonalTrend {
  month: number;
  month_name: string;
  grant_count: number;
  avg_amount?: number;
  top_categories: string[];
  top_funders: string[];
}

export interface SeasonalTrendResponse {
  trends: SeasonalTrend[];
  year_total: number;
  peak_months: number[];
  generated_at: string;
}

export interface RecommendationGrant {
  grant: ForecastGrant;
  match_score: number; // 0-1
  match_reasons: string[];
  profile_overlap: string[];
}

export interface RecommendationsResponse {
  recommendations: RecommendationGrant[];
  total: number;
  profile_complete: boolean;
  generated_at: string;
}
