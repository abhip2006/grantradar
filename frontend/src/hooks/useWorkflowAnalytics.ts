import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workflowAnalyticsApi } from '../services/workflowAnalyticsApi';
import type {
  TimePerStageResponse,
  BottlenecksResponse,
  ApplicationEventsResponse,
  CompletionRatesResponse,
  DeadlineRiskForecastResponse,
  WorkflowAnalyticsSummary,
  TeamProductivityMetrics,
  WorkflowPatternSuccess,
} from '../types/workflowAnalytics';

// Stale time constants for consistency
const STALE_TIMES = {
  LIST: 5 * 60 * 1000,        // 5 minutes for list/analytics queries
  DETAIL: 2 * 60 * 1000,      // 2 minutes for detail queries
  REALTIME: 30 * 1000,        // 30 seconds for real-time data
} as const;

// Query keys for cache management
export const workflowAnalyticsKeys = {
  all: ['workflowAnalytics'] as const,
  timePerStage: (params?: { period_start?: string; period_end?: string; stage?: string }) =>
    [...workflowAnalyticsKeys.all, 'timePerStage', params] as const,
  bottlenecks: (params?: { severity?: string; limit?: number }) =>
    [...workflowAnalyticsKeys.all, 'bottlenecks', params] as const,
  applicationEvents: (cardId: string, params?: { event_type?: string; limit?: number; offset?: number }) =>
    [...workflowAnalyticsKeys.all, 'applicationEvents', cardId, params] as const,
  completionRates: (params?: { period_start?: string; period_end?: string }) =>
    [...workflowAnalyticsKeys.all, 'completionRates', params] as const,
  deadlineRisk: (params?: { days_ahead?: number; min_risk_level?: string }) =>
    [...workflowAnalyticsKeys.all, 'deadlineRisk', params] as const,
  summary: (params?: { period_start?: string; period_end?: string }) =>
    [...workflowAnalyticsKeys.all, 'summary', params] as const,
  teamProductivity: () => [...workflowAnalyticsKeys.all, 'teamProductivity'] as const,
  patternSuccess: () => [...workflowAnalyticsKeys.all, 'patternSuccess'] as const,
};

/**
 * Hook to fetch workflow analytics summary
 */
export function useWorkflowAnalytics(params?: {
  period_start?: string;
  period_end?: string;
}) {
  return useQuery<WorkflowAnalyticsSummary, Error>({
    queryKey: workflowAnalyticsKeys.summary(params),
    queryFn: () => workflowAnalyticsApi.getSummary(params),
    staleTime: STALE_TIMES.LIST,
  });
}

/**
 * Hook to fetch time per stage data
 */
export function useTimePerStage(params?: {
  period_start?: string;
  period_end?: string;
  stage?: string;
}) {
  return useQuery<TimePerStageResponse, Error>({
    queryKey: workflowAnalyticsKeys.timePerStage(params),
    queryFn: () => workflowAnalyticsApi.getTimePerStage(params),
    staleTime: STALE_TIMES.LIST,
  });
}

/**
 * Hook to fetch workflow bottlenecks
 */
export function useBottlenecks(params?: {
  severity?: 'low' | 'medium' | 'high' | 'critical';
  limit?: number;
}) {
  return useQuery<BottlenecksResponse, Error>({
    queryKey: workflowAnalyticsKeys.bottlenecks(params),
    queryFn: () => workflowAnalyticsApi.getBottlenecks(params),
    staleTime: STALE_TIMES.LIST,
  });
}

/**
 * Hook to fetch application events timeline
 */
export function useApplicationEvents(
  cardId: string,
  params?: {
    event_type?: 'stage_enter' | 'stage_exit' | 'action' | 'milestone';
    limit?: number;
    offset?: number;
  }
) {
  return useQuery<ApplicationEventsResponse, Error>({
    queryKey: workflowAnalyticsKeys.applicationEvents(cardId, params),
    queryFn: () => workflowAnalyticsApi.getApplicationEvents(cardId, params),
    enabled: !!cardId,
    staleTime: STALE_TIMES.REALTIME,
  });
}

/**
 * Hook to fetch completion rates
 */
export function useCompletionRates(params?: {
  period_start?: string;
  period_end?: string;
}) {
  return useQuery<CompletionRatesResponse, Error>({
    queryKey: workflowAnalyticsKeys.completionRates(params),
    queryFn: () => workflowAnalyticsApi.getCompletionRates(params),
    staleTime: STALE_TIMES.LIST,
  });
}

/**
 * Hook to fetch deadline risk forecast
 */
export function useDeadlineRiskForecast(params?: {
  days_ahead?: number;
  min_risk_level?: 'low' | 'medium' | 'high' | 'critical';
}) {
  return useQuery<DeadlineRiskForecastResponse, Error>({
    queryKey: workflowAnalyticsKeys.deadlineRisk(params),
    queryFn: () => workflowAnalyticsApi.getDeadlineRiskForecast(params),
    staleTime: STALE_TIMES.DETAIL,
  });
}

/**
 * Hook to fetch team productivity metrics
 */
export function useTeamProductivity() {
  return useQuery<TeamProductivityMetrics, Error>({
    queryKey: workflowAnalyticsKeys.teamProductivity(),
    queryFn: () => workflowAnalyticsApi.getTeamProductivity(),
    staleTime: STALE_TIMES.LIST,
  });
}

/**
 * Hook to fetch workflow pattern success rates
 */
export function useWorkflowPatternSuccess() {
  return useQuery<WorkflowPatternSuccess[], Error>({
    queryKey: workflowAnalyticsKeys.patternSuccess(),
    queryFn: () => workflowAnalyticsApi.getWorkflowPatternSuccess(),
    staleTime: STALE_TIMES.LIST,
  });
}

/**
 * Hook to trigger recalculation of workflow analytics
 */
export function useRecalculateAnalytics() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params?: { period_start?: string; period_end?: string }) =>
      workflowAnalyticsApi.recalculate(params),
    onSuccess: () => {
      // Invalidate all workflow analytics queries
      queryClient.invalidateQueries({ queryKey: workflowAnalyticsKeys.all });
    },
  });
}
