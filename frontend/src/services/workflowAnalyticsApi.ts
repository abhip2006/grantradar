import { api } from './api';
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

/**
 * Workflow Analytics API
 * Endpoints for tracking and analyzing grant application workflow efficiency
 */
export const workflowAnalyticsApi = {
  /**
   * Get time spent per stage across all applications
   */
  getTimePerStage: async (params?: {
    period_start?: string;
    period_end?: string;
    stage?: string;
  }): Promise<TimePerStageResponse> => {
    const response = await api.get<TimePerStageResponse>('/workflow-analytics/time-per-stage', {
      params,
    });
    return response.data;
  },

  /**
   * Get identified bottlenecks in the workflow
   */
  getBottlenecks: async (params?: {
    severity?: 'low' | 'medium' | 'high' | 'critical';
    limit?: number;
  }): Promise<BottlenecksResponse> => {
    const response = await api.get<BottlenecksResponse>('/workflow-analytics/bottlenecks', {
      params,
    });
    return response.data;
  },

  /**
   * Get workflow events for a specific application
   */
  getApplicationEvents: async (
    cardId: string,
    params?: {
      event_type?: 'stage_enter' | 'stage_exit' | 'action' | 'milestone';
      limit?: number;
      offset?: number;
    }
  ): Promise<ApplicationEventsResponse> => {
    const response = await api.get<ApplicationEventsResponse>(
      `/workflow-analytics/applications/${cardId}/events`,
      { params }
    );
    return response.data;
  },

  /**
   * Get completion rates per stage
   */
  getCompletionRates: async (params?: {
    period_start?: string;
    period_end?: string;
  }): Promise<CompletionRatesResponse> => {
    const response = await api.get<CompletionRatesResponse>(
      '/workflow-analytics/completion-rates',
      { params }
    );
    return response.data;
  },

  /**
   * Get deadline risk forecast for applications
   */
  getDeadlineRiskForecast: async (params?: {
    days_ahead?: number;
    min_risk_level?: 'low' | 'medium' | 'high' | 'critical';
  }): Promise<DeadlineRiskForecastResponse> => {
    const response = await api.get<DeadlineRiskForecastResponse>(
      '/workflow-analytics/deadline-risk',
      { params }
    );
    return response.data;
  },

  /**
   * Get overall workflow analytics summary
   */
  getSummary: async (params?: {
    period_start?: string;
    period_end?: string;
  }): Promise<WorkflowAnalyticsSummary> => {
    const response = await api.get<WorkflowAnalyticsSummary>(
      '/workflow-analytics/summary',
      { params }
    );
    return response.data;
  },

  /**
   * Get team productivity metrics
   */
  getTeamProductivity: async (): Promise<TeamProductivityMetrics> => {
    const response = await api.get<TeamProductivityMetrics>(
      '/workflow-analytics/team-productivity'
    );
    return response.data;
  },

  /**
   * Get success rate by workflow pattern
   */
  getWorkflowPatternSuccess: async (): Promise<WorkflowPatternSuccess[]> => {
    const response = await api.get<WorkflowPatternSuccess[]>(
      '/workflow-analytics/pattern-success'
    );
    return response.data;
  },

  /**
   * Trigger recalculation of workflow analytics
   */
  recalculate: async (params?: {
    period_start?: string;
    period_end?: string;
  }): Promise<{ status: string; message: string }> => {
    const response = await api.post<{ status: string; message: string }>(
      '/workflow-analytics/recalculate',
      null,
      { params }
    );
    return response.data;
  },
};

export default workflowAnalyticsApi;
