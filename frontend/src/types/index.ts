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
  lab_name?: string;
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

// Match score range options for filtering
export type MatchScoreRange = 'all' | 'excellent' | 'good' | 'moderate';

export interface MatchScoreRangeOption {
  value: MatchScoreRange;
  label: string;
  description: string;
  minScore?: number;
  maxScore?: number;
}

export const MATCH_SCORE_RANGES: MatchScoreRangeOption[] = [
  { value: 'all', label: 'All Matches', description: 'Show all matching grants' },
  { value: 'excellent', label: 'Excellent (90%+)', description: 'Highest relevance to your profile', minScore: 90 },
  { value: 'good', label: 'Good (75-89%)', description: 'Strong alignment with your focus', minScore: 75, maxScore: 89 },
  { value: 'moderate', label: 'Moderate (50-74%)', description: 'Partial match to your profile', minScore: 50, maxScore: 74 },
];

// Advanced filter types for dashboard
export interface AdvancedGrantFilters {
  agencies?: string[];
  categories?: string[];
  min_amount?: number;
  max_amount?: number;
  deadline_after?: string;
  deadline_before?: string;
  deadline_proximity?: string; // Days until deadline (e.g., "30", "60", "90", "180")
  // Match score filter
  score_range?: MatchScoreRange;
  min_score?: number;
  max_score?: number;
  // Eligibility filters
  career_stages?: string[];
  citizenship?: string[];
  institution_types?: string[];
  postdocs_eligible?: boolean;
  students_eligible?: boolean;
  // Phase 2 filters (require migration)
  geographic_scope?: string;
  // Award details filters
  award_types?: string[];
  award_duration?: string;
  indirect_cost_policy?: string;
  submission_types?: string[];
}

export interface FilterOptionItem {
  value: string;
  label: string;
}

export interface FilterOptions {
  agencies: string[];
  categories: string[];
  sources: string[];
  amount_range: {
    min: number;
    max: number;
  };
  // Predefined options for advanced filters
  career_stages: FilterOptionItem[];
  citizenship_options: FilterOptionItem[];
  institution_types: FilterOptionItem[];
  award_types: FilterOptionItem[];
  award_durations: FilterOptionItem[];
  geographic_scopes: FilterOptionItem[];
  indirect_cost_policies: FilterOptionItem[];
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

// Deadline types - Extended workflow statuses
export type DeadlineStatus =
  | 'not_started'
  | 'drafting'
  | 'internal_review'
  | 'submitted'
  | 'under_review'
  | 'awarded'
  | 'rejected';

export type DeadlinePriority = 'low' | 'medium' | 'high' | 'critical';

export type DeadlineUrgencyLevel = 'none' | 'low' | 'medium' | 'high' | 'critical' | 'overdue';

// Status display configuration
export const DEADLINE_STATUS_CONFIG: Record<DeadlineStatus, { label: string; color: string; bgColor: string; order: number }> = {
  not_started: { label: 'Not Started', color: 'text-gray-600', bgColor: 'bg-gray-100', order: 0 },
  drafting: { label: 'Drafting', color: 'text-blue-600', bgColor: 'bg-blue-100', order: 1 },
  internal_review: { label: 'Internal Review', color: 'text-yellow-600', bgColor: 'bg-yellow-100', order: 2 },
  submitted: { label: 'Submitted', color: 'text-purple-600', bgColor: 'bg-purple-100', order: 3 },
  under_review: { label: 'Under Review', color: 'text-orange-600', bgColor: 'bg-orange-100', order: 4 },
  awarded: { label: 'Awarded', color: 'text-green-600', bgColor: 'bg-green-100', order: 5 },
  rejected: { label: 'Rejected', color: 'text-red-600', bgColor: 'bg-red-100', order: 6 },
};

export const DEADLINE_PRIORITY_CONFIG: Record<DeadlinePriority, { label: string; color: string; bgColor: string }> = {
  low: { label: 'Low', color: 'text-gray-500', bgColor: 'bg-gray-100' },
  medium: { label: 'Medium', color: 'text-blue-500', bgColor: 'bg-blue-100' },
  high: { label: 'High', color: 'text-orange-500', bgColor: 'bg-orange-100' },
  critical: { label: 'Critical', color: 'text-red-500', bgColor: 'bg-red-100' },
};

export interface Deadline {
  id: string;
  user_id: string;
  grant_id?: string;
  title: string;
  description?: string;
  funder?: string;
  mechanism?: string;
  sponsor_deadline: string;
  internal_deadline?: string;
  status: DeadlineStatus;
  priority: DeadlinePriority;
  url?: string;
  notes?: string;
  color: string;
  // Recurring deadline fields
  is_recurring: boolean;
  recurrence_rule?: string;
  parent_deadline_id?: string;
  // Reminder configuration
  reminder_config: number[];
  escalation_sent: boolean;
  // Computed fields
  days_until_deadline: number;
  is_overdue: boolean;
  urgency_level: DeadlineUrgencyLevel;
  status_config: { label: string; color: string; order: number };
  grant?: Grant;
  created_at: string;
  updated_at: string;
}

export interface DeadlineCreate {
  title: string;
  sponsor_deadline: string;
  grant_id?: string;
  description?: string;
  funder?: string;
  mechanism?: string;
  internal_deadline?: string;
  status?: DeadlineStatus;
  priority?: DeadlinePriority;
  url?: string;
  notes?: string;
  color?: string;
  // Recurring fields
  is_recurring?: boolean;
  recurrence_rule?: string;
  // Reminder config
  reminder_config?: number[];
}

export interface DeadlineUpdate extends Partial<DeadlineCreate> {
  status?: DeadlineStatus;
}

export interface DeadlineFilters {
  status?: DeadlineStatus;
  from_date?: string;
  to_date?: string;
  funder?: string;
  search?: string;
  sort?: 'deadline_asc' | 'deadline_desc' | 'created_desc';
}

export interface DeadlineListResponse {
  items: Deadline[];
  total: number;
}

// Status history types
export interface StatusHistoryEntry {
  id: string;
  deadline_id: string;
  previous_status?: string;
  new_status: string;
  changed_by?: string;
  changed_at: string;
  notes?: string;
}

export interface StatusHistoryResponse {
  items: StatusHistoryEntry[];
  total: number;
}

// Status change request
export interface StatusChangeRequest {
  status: DeadlineStatus;
  notes?: string;
}

// Deadline stats
export interface DeadlineStats {
  total: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  overdue: number;
  due_this_week: number;
  due_this_month: number;
  recurring_templates: number;
}

// Recurrence presets
export interface RecurrencePreset {
  key: string;
  label: string;
  rule: string;
}

export interface RecurrencePresetsResponse {
  presets: RecurrencePreset[];
}

// ============================================
// Calendar Integration Types
// ============================================

export type CalendarProvider = 'google' | 'outlook';

export interface CalendarIntegration {
  id: string;
  user_id: string;
  provider: CalendarProvider;
  calendar_id: string;
  sync_enabled: boolean;
  last_synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CalendarIntegrationStatus {
  google: {
    connected: boolean;
    calendar_id?: string;
    sync_enabled?: boolean;
    last_synced_at?: string;
  };
  outlook: {
    connected: boolean;
    calendar_id?: string;
    sync_enabled?: boolean;
    last_synced_at?: string;
  };
}

export interface ReminderSchedule {
  id: string;
  deadline_id: string;
  reminder_type: 'email' | 'push' | 'sms';
  remind_before_minutes: number;
  is_sent: boolean;
  sent_at: string | null;
}

export interface ReminderSettings {
  email_enabled: boolean;
  sms_enabled: boolean;
  default_reminders: number[]; // minutes before deadline
}

// ============================================
// Document Template Types
// ============================================

export interface TemplateCategory {
  id: string;
  name: string;
  description?: string;
  display_order: number;
  template_count?: number;
}

export interface TemplateVariable {
  name: string;
  type: 'text' | 'number' | 'date' | 'select';
  description?: string;
  default?: string;
  options?: string[]; // for select type
  required?: boolean;
}

export interface Template {
  id: string;
  user_id?: string;
  category_id?: string;
  category?: TemplateCategory;
  title: string;
  description?: string;
  content: string;
  variables: TemplateVariable[];
  is_public: boolean;
  is_system: boolean;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

export interface TemplateCreate {
  category_id?: string;
  title: string;
  description?: string;
  content: string;
  variables?: TemplateVariable[];
  is_public?: boolean;
}

export interface TemplateUpdate {
  category_id?: string;
  title?: string;
  description?: string;
  content?: string;
  variables?: TemplateVariable[];
  is_public?: boolean;
}

export interface TemplateListResponse {
  items: Template[];
  total: number;
}

export interface TemplateFilters {
  category_id?: string;
  search?: string;
  is_public?: boolean;
  is_system?: boolean;
}

export interface TemplateRenderRequest {
  template_id: string;
  variables: Record<string, string | number>;
}

export interface TemplateRenderResponse {
  rendered_content: string;
}

// ===== AI Tools Types =====

// Eligibility Check
export type EligibilityStatus = 'eligible' | 'not_eligible' | 'partial' | 'unknown';

export interface EligibilityCriterion {
  criterion: string;
  met: boolean;
  explanation: string;
  confidence: number;
}

export interface EligibilityCheckResponse {
  grant_id: string;
  grant_title: string;
  overall_status: EligibilityStatus;
  overall_confidence: number;
  criteria: EligibilityCriterion[];
  summary: string;
  recommendations: string[];
  missing_info: string[];
  session_id?: string;
  checked_at: string;
}

// Chat
export interface ChatSource {
  document_type: string;
  document_id?: string;
  title: string;
  excerpt: string;
  relevance_score: number;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: ChatSource[];
  created_at: string;
}

export interface ChatSession {
  id: string;
  title: string;
  session_type: string;
  context_grant_id?: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

export interface ChatSessionListItem {
  id: string;
  title: string;
  session_type: string;
  message_count: number;
  last_message_at?: string;
  created_at: string;
}

// Research
export type ResearchStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface ResearchGrantResult {
  id: string;
  title: string;
  funder: string;
  mechanism?: string;
  description?: string;
  deadline?: string;
  amount_min?: number;
  amount_max?: number;
  relevance_score: number;
  match_reasons: string[];
}

export interface ResearchSession {
  id: string;
  query: string;
  status: ResearchStatus;
  results?: ResearchGrantResult[];
  insights?: string;
  grants_found?: number;
  processing_time_ms?: number;
  created_at: string;
  completed_at?: string;
}

// Funding Alerts
export type AlertFrequency = 'daily' | 'weekly' | 'monthly';

// Application Outcome Tracking
export type ApplicationStatus =
  | 'not_applied'
  | 'in_progress'
  | 'submitted'
  | 'awarded'
  | 'rejected'
  | 'withdrawn';

export interface OutcomeUpdate {
  application_status: ApplicationStatus;
  application_submitted_at?: string;
  outcome_received_at?: string;
  award_amount?: number;
  outcome_notes?: string;
}

export const APPLICATION_STATUS_CONFIG: Record<ApplicationStatus, { label: string; color: string; bgColor: string }> = {
  not_applied: { label: 'Not Applied', color: 'text-gray-600', bgColor: 'bg-gray-100' },
  in_progress: { label: 'In Progress', color: 'text-blue-600', bgColor: 'bg-blue-100' },
  submitted: { label: 'Submitted', color: 'text-purple-600', bgColor: 'bg-purple-100' },
  awarded: { label: 'Awarded', color: 'text-emerald-600', bgColor: 'bg-emerald-100' },
  rejected: { label: 'Rejected', color: 'text-red-600', bgColor: 'bg-red-100' },
  withdrawn: { label: 'Withdrawn', color: 'text-orange-600', bgColor: 'bg-orange-100' },
};

export interface FundingAlertPreferences {
  id: string;
  enabled: boolean;
  frequency: AlertFrequency;
  min_match_score: number;
  include_deadlines: boolean;
  include_new_grants: boolean;
  include_insights: boolean;
  preferred_funders?: string[];
  last_sent_at?: string;
}

// ===== Competition & Mechanism Types =====

export type CompetitionLevel = 'low' | 'medium' | 'high' | 'very_high';

export interface MechanismInfo {
  code: string;
  name: string;
  success_rate_overall: number;
  competition_level: CompetitionLevel;
  estimated_applicants_per_cycle: number;
  typical_duration_months: number;
  typical_budget_min: number;
  typical_budget_max: number;
}

export interface CompetitionData {
  competition_score: number; // 0-1
  competition_level: CompetitionLevel;
  estimated_applicants: number;
  factors: string[];
}

export type EffortComplexity = 'simple' | 'moderate' | 'complex';

export interface EffortData {
  hours_estimate?: number;
  weeks_estimate?: string; // e.g., "2-3 weeks"
  complexity: EffortComplexity;
}
