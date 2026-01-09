import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { reviewsApi } from '../services/reviewsApi';
import type {
  StartReviewRequest,
  SubmitReviewActionRequest,
  AddTeamMemberRequest,
  UpdateTeamMemberRequest,
} from '../types/reviews';

// Stale time constants for consistency
const STALE_TIMES = {
  LIST: 5 * 60 * 1000,     // 5 minutes for list queries
  DETAIL: 2 * 60 * 1000,   // 2 minutes for detail queries
  REALTIME: 30 * 1000,     // 30 seconds for real-time data
} as const;

// Query keys for cache management
export const reviewKeys = {
  all: ['reviews'] as const,
  workflows: () => [...reviewKeys.all, 'workflows'] as const,
  workflow: (workflowId: string) => [...reviewKeys.all, 'workflow', workflowId] as const,
  applicationReview: (cardId: string) => [...reviewKeys.all, 'application', cardId] as const,
  reviewHistory: (cardId: string) => [...reviewKeys.all, 'history', cardId] as const,
  teamMembers: (cardId: string) => [...reviewKeys.all, 'team', cardId] as const,
  canReview: (cardId: string) => [...reviewKeys.all, 'canReview', cardId] as const,
  availableUsers: (cardId: string) => [...reviewKeys.all, 'availableUsers', cardId] as const,
};

// ============================================
// Review Workflow Hooks
// ============================================

/**
 * Fetch all available review workflow templates
 */
export function useReviewWorkflows() {
  return useQuery({
    queryKey: reviewKeys.workflows(),
    queryFn: () => reviewsApi.getWorkflows(),
    staleTime: STALE_TIMES.LIST,
  });
}

/**
 * Fetch a specific workflow by ID
 */
export function useReviewWorkflow(workflowId: string) {
  return useQuery({
    queryKey: reviewKeys.workflow(workflowId),
    queryFn: () => reviewsApi.getWorkflow(workflowId),
    enabled: !!workflowId,
    staleTime: STALE_TIMES.DETAIL,
  });
}

// ============================================
// Application Review Hooks
// ============================================

/**
 * Fetch the current review status for an application
 */
export function useApplicationReview(cardId: string) {
  return useQuery({
    queryKey: reviewKeys.applicationReview(cardId),
    queryFn: () => reviewsApi.getApplicationReview(cardId),
    enabled: !!cardId,
    staleTime: STALE_TIMES.REALTIME,
  });
}

/**
 * Start a new review process for an application
 */
export function useStartReview() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ cardId, data }: { cardId: string; data?: StartReviewRequest }) =>
      reviewsApi.startReview(cardId, data),
    onSuccess: (_, { cardId }) => {
      // Invalidate the application review query
      queryClient.invalidateQueries({ queryKey: reviewKeys.applicationReview(cardId) });
      // Also invalidate review history
      queryClient.invalidateQueries({ queryKey: reviewKeys.reviewHistory(cardId) });
    },
  });
}

/**
 * Submit a review action (approve, reject, return, comment)
 */
export function useSubmitReviewAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ cardId, data }: { cardId: string; data: SubmitReviewActionRequest }) =>
      reviewsApi.submitReviewAction(cardId, data),
    onSuccess: (_, { cardId }) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: reviewKeys.applicationReview(cardId) });
      queryClient.invalidateQueries({ queryKey: reviewKeys.reviewHistory(cardId) });
      queryClient.invalidateQueries({ queryKey: reviewKeys.canReview(cardId) });
    },
  });
}

/**
 * Fetch the review history for an application
 */
export function useReviewHistory(cardId: string) {
  return useQuery({
    queryKey: reviewKeys.reviewHistory(cardId),
    queryFn: () => reviewsApi.getReviewHistory(cardId),
    enabled: !!cardId,
    staleTime: STALE_TIMES.REALTIME,
  });
}

/**
 * Cancel/end the current review process
 */
export function useCancelReview() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (cardId: string) => reviewsApi.cancelReview(cardId),
    onSuccess: (_, cardId) => {
      queryClient.invalidateQueries({ queryKey: reviewKeys.applicationReview(cardId) });
      queryClient.invalidateQueries({ queryKey: reviewKeys.reviewHistory(cardId) });
    },
  });
}

/**
 * Check if the current user can perform a review action
 */
export function useCanUserReview(cardId: string) {
  return useQuery({
    queryKey: reviewKeys.canReview(cardId),
    queryFn: () => reviewsApi.canUserReview(cardId),
    enabled: !!cardId,
    staleTime: STALE_TIMES.REALTIME,
  });
}

// ============================================
// Team Member Hooks
// ============================================

/**
 * Fetch team members for an application
 */
export function useTeamMembers(cardId: string) {
  return useQuery({
    queryKey: reviewKeys.teamMembers(cardId),
    queryFn: () => reviewsApi.getTeamMembers(cardId),
    enabled: !!cardId,
    staleTime: STALE_TIMES.REALTIME,
  });
}

/**
 * Add a team member to an application
 */
export function useAddTeamMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ cardId, data }: { cardId: string; data: AddTeamMemberRequest }) =>
      reviewsApi.addTeamMember(cardId, data),
    onSuccess: (_, { cardId }) => {
      queryClient.invalidateQueries({ queryKey: reviewKeys.teamMembers(cardId) });
      queryClient.invalidateQueries({ queryKey: reviewKeys.availableUsers(cardId) });
    },
  });
}

/**
 * Update a team member's role or permissions
 */
export function useUpdateTeamMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      cardId,
      memberId,
      data,
    }: {
      cardId: string;
      memberId: string;
      data: UpdateTeamMemberRequest;
    }) => reviewsApi.updateTeamMember(cardId, memberId, data),
    onSuccess: (_, { cardId }) => {
      queryClient.invalidateQueries({ queryKey: reviewKeys.teamMembers(cardId) });
    },
  });
}

/**
 * Remove a team member from an application
 */
export function useRemoveTeamMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ cardId, memberId }: { cardId: string; memberId: string }) =>
      reviewsApi.removeTeamMember(cardId, memberId),
    onSuccess: (_, { cardId }) => {
      queryClient.invalidateQueries({ queryKey: reviewKeys.teamMembers(cardId) });
      queryClient.invalidateQueries({ queryKey: reviewKeys.availableUsers(cardId) });
    },
  });
}

/**
 * Get available users who can be added as team members
 */
export function useAvailableUsers(cardId: string, params?: { search?: string; limit?: number }) {
  return useQuery({
    queryKey: [...reviewKeys.availableUsers(cardId), params] as const,
    queryFn: () => reviewsApi.getAvailableUsers(cardId, params),
    enabled: !!cardId,
    staleTime: STALE_TIMES.DETAIL,
  });
}
