import { api } from './api';
import type {
  ReviewWorkflow,
  ReviewWorkflowListResponse,
  ApplicationReview,
  ReviewHistoryResponse,
  ApplicationTeamMember,
  TeamMembersResponse,
  StartReviewRequest,
  SubmitReviewActionRequest,
  AddTeamMemberRequest,
  UpdateTeamMemberRequest,
} from '../types/reviews';

/**
 * API methods for Internal Review Workflow feature.
 *
 * These endpoints map to the backend API as defined in:
 * - GET /api/workflows - List review workflows
 * - POST /api/kanban/{card_id}/review - Start review process
 * - POST /api/kanban/{card_id}/review/action - Submit review action
 * - GET /api/kanban/{card_id}/review/history - Get review history
 * - POST /api/kanban/{card_id}/team - Add team member
 * - GET /api/kanban/{card_id}/team - Get team members
 */
export const reviewsApi = {
  // ============================================
  // Review Workflow Templates
  // ============================================

  /**
   * Get all available review workflow templates
   */
  getWorkflows: async (): Promise<ReviewWorkflowListResponse> => {
    const response = await api.get<ReviewWorkflowListResponse>('/workflows');
    return response.data;
  },

  /**
   * Get a specific workflow by ID
   */
  getWorkflow: async (workflowId: string): Promise<ReviewWorkflow> => {
    const response = await api.get<ReviewWorkflow>(`/workflows/${workflowId}`);
    return response.data;
  },

  // ============================================
  // Application Review Management
  // ============================================

  /**
   * Get the current review status for an application
   */
  getApplicationReview: async (cardId: string): Promise<ApplicationReview | null> => {
    try {
      const response = await api.get<ApplicationReview>(`/kanban/${cardId}/review`);
      return response.data;
    } catch (error: unknown) {
      // If no review exists, return null
      const axiosError = error as { response?: { status?: number } };
      if (axiosError.response?.status === 404) {
        return null;
      }
      throw error;
    }
  },

  /**
   * Start a new review process for an application
   */
  startReview: async (cardId: string, data?: StartReviewRequest): Promise<ApplicationReview> => {
    const response = await api.post<ApplicationReview>(`/kanban/${cardId}/review`, data || {});
    return response.data;
  },

  /**
   * Submit a review action (approve, reject, return, comment)
   */
  submitReviewAction: async (
    cardId: string,
    data: SubmitReviewActionRequest
  ): Promise<ApplicationReview> => {
    const response = await api.post<ApplicationReview>(`/kanban/${cardId}/review/action`, data);
    return response.data;
  },

  /**
   * Get the complete review history for an application
   */
  getReviewHistory: async (cardId: string): Promise<ReviewHistoryResponse> => {
    const response = await api.get<ReviewHistoryResponse>(`/kanban/${cardId}/review/history`);
    return response.data;
  },

  /**
   * Cancel/end the current review process
   */
  cancelReview: async (cardId: string): Promise<void> => {
    await api.delete(`/kanban/${cardId}/review`);
  },

  // ============================================
  // Team Member Management
  // ============================================

  /**
   * Get all team members assigned to an application
   */
  getTeamMembers: async (cardId: string): Promise<TeamMembersResponse> => {
    const response = await api.get<TeamMembersResponse>(`/kanban/${cardId}/team`);
    return response.data;
  },

  /**
   * Add a team member to an application
   */
  addTeamMember: async (
    cardId: string,
    data: AddTeamMemberRequest
  ): Promise<ApplicationTeamMember> => {
    const response = await api.post<ApplicationTeamMember>(`/kanban/${cardId}/team`, data);
    return response.data;
  },

  /**
   * Update a team member's role or permissions
   */
  updateTeamMember: async (
    cardId: string,
    memberId: string,
    data: UpdateTeamMemberRequest
  ): Promise<ApplicationTeamMember> => {
    const response = await api.patch<ApplicationTeamMember>(
      `/kanban/${cardId}/team/${memberId}`,
      data
    );
    return response.data;
  },

  /**
   * Remove a team member from an application
   */
  removeTeamMember: async (cardId: string, memberId: string): Promise<void> => {
    await api.delete(`/kanban/${cardId}/team/${memberId}`);
  },

  // ============================================
  // Utility Methods
  // ============================================

  /**
   * Check if the current user can perform a review action at the current stage
   */
  canUserReview: async (cardId: string): Promise<{ can_review: boolean; reason?: string }> => {
    const response = await api.get<{ can_review: boolean; reason?: string }>(
      `/kanban/${cardId}/review/can-review`
    );
    return response.data;
  },

  /**
   * Get available users who can be added as team members
   */
  getAvailableUsers: async (
    cardId: string,
    params?: { search?: string; limit?: number }
  ): Promise<{ users: Array<{ id: string; email: string; name?: string }> }> => {
    const response = await api.get(`/kanban/${cardId}/team/available-users`, { params });
    return response.data;
  },
};

export default reviewsApi;
