// Workflow Analytics Types
// Based on the Workflow Analytics feature plan from application-workflow-features.md

/**
 * Represents a single workflow event in the application lifecycle
 */
export interface WorkflowEvent {
  id: string;
  kanban_card_id: string;
  event_type: 'stage_enter' | 'stage_exit' | 'action' | 'milestone';
  stage: string;
  metadata?: Record<string, unknown>;
  occurred_at: string;
}

/**
 * Time spent in each stage of the workflow
 */
export interface TimePerStage {
  stage: string;
  stage_label: string;
  avg_days: number;
  min_days: number;
  max_days: number;
  median_days: number;
  count: number;
  color: string;
}

/**
 * Identifies bottlenecks in the workflow process
 */
export interface Bottleneck {
  id: string;
  stage: string;
  stage_label: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  avg_delay_days: number;
  affected_applications: number;
  threshold_days: number;
  description: string;
  recommendation: string;
}

/**
 * Overall workflow analytics data
 */
export interface WorkflowAnalytics {
  id: string;
  user_id: string;
  period_start: string;
  period_end: string;
  metrics: WorkflowMetrics;
  generated_at: string;
}

/**
 * Detailed metrics for workflow analytics
 */
export interface WorkflowMetrics {
  avg_time_per_stage: Record<string, number>;
  bottlenecks: string[];
  completion_rate: number;
  avg_total_cycle_time: number;
  applications_completed: number;
  applications_in_progress: number;
  deadline_success_rate: number;
}

/**
 * API response for time per stage data
 */
export interface TimePerStageResponse {
  stages: TimePerStage[];
  total_applications: number;
  avg_total_cycle_time: number;
  generated_at: string;
}

/**
 * API response for bottleneck analysis
 */
export interface BottlenecksResponse {
  bottlenecks: Bottleneck[];
  total_identified: number;
  critical_count: number;
  generated_at: string;
}

/**
 * API response for application events
 */
export interface ApplicationEventsResponse {
  events: WorkflowEvent[];
  card_id: string;
  total: number;
}

/**
 * Completion rate data per stage
 */
export interface CompletionRateData {
  stage: string;
  stage_label: string;
  started: number;
  completed: number;
  completion_rate: number;
  avg_days_to_complete: number;
}

/**
 * API response for completion rates
 */
export interface CompletionRatesResponse {
  rates: CompletionRateData[];
  overall_completion_rate: number;
  total_started: number;
  total_completed: number;
  generated_at: string;
}

/**
 * Deadline risk forecast for applications
 */
export interface DeadlineRisk {
  card_id: string;
  grant_title: string;
  deadline: string;
  days_remaining: number;
  current_stage: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  risk_score: number; // 0-100
  predicted_completion_date?: string;
  risk_factors: string[];
  recommendation: string;
}

/**
 * API response for deadline risk forecast
 */
export interface DeadlineRiskForecastResponse {
  at_risk: DeadlineRisk[];
  safe: DeadlineRisk[];
  total_applications: number;
  critical_count: number;
  high_risk_count: number;
  medium_risk_count: number;
  generated_at: string;
}

/**
 * Team productivity metrics
 */
export interface TeamProductivityMetrics {
  total_applications_managed: number;
  avg_applications_per_member: number;
  avg_time_to_completion: number;
  top_performers: Array<{
    user_id: string;
    name: string;
    applications_completed: number;
    avg_cycle_time: number;
  }>;
}

/**
 * Success rate by workflow pattern
 */
export interface WorkflowPatternSuccess {
  pattern_name: string;
  description: string;
  applications_using: number;
  success_rate: number;
  avg_cycle_time: number;
}

/**
 * Workflow analytics summary for dashboard
 */
export interface WorkflowAnalyticsSummary {
  total_applications: number;
  avg_cycle_time_days: number;
  bottleneck_count: number;
  at_risk_deadlines: number;
  completion_rate: number;
  deadline_success_rate: number;
  most_problematic_stage?: string;
  fastest_stage?: string;
  slowest_stage?: string;
}
