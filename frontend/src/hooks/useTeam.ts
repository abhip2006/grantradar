import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { teamApi } from '../services/api';
import type {
  TeamInviteRequest,
  TeamMemberUpdate,
  TeamActivityFilters,
  BulkInviteRequest,
} from '../types/team';

// Query keys for cache invalidation
export const teamKeys = {
  all: ['team'] as const,
  members: () => [...teamKeys.all, 'members'] as const,
  member: (id: string) => [...teamKeys.all, 'member', id] as const,
  activities: (filters?: TeamActivityFilters) => [...teamKeys.all, 'activities', filters] as const,
  stats: () => [...teamKeys.all, 'stats'] as const,
};

// Get all team members
export function useTeamMembers() {
  return useQuery({
    queryKey: teamKeys.members(),
    queryFn: () => teamApi.getMembers(),
    staleTime: 30000, // 30 seconds
  });
}

// Get a single team member
export function useTeamMember(memberId: string) {
  return useQuery({
    queryKey: teamKeys.member(memberId),
    queryFn: () => teamApi.getMember(memberId),
    enabled: !!memberId,
  });
}

// Get team statistics
export function useTeamStats() {
  return useQuery({
    queryKey: teamKeys.stats(),
    queryFn: () => teamApi.getStats(),
    staleTime: 60000, // 1 minute
  });
}

// Get team activity feed
export function useTeamActivities(filters?: TeamActivityFilters) {
  return useQuery({
    queryKey: teamKeys.activities(filters),
    queryFn: () => teamApi.getActivities(filters),
    staleTime: 30000, // 30 seconds
  });
}

// Invite a new team member
export function useInviteMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TeamInviteRequest) => teamApi.inviteMember(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: teamKeys.members() });
      queryClient.invalidateQueries({ queryKey: teamKeys.stats() });
      queryClient.invalidateQueries({ queryKey: teamKeys.activities() });
    },
  });
}

// Resend invitation email
export function useResendInvitation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (memberId: string) => teamApi.resendInvitation(memberId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: teamKeys.members() });
    },
  });
}

// Cancel a pending invitation
export function useCancelInvitation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (memberId: string) => teamApi.cancelInvitation(memberId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: teamKeys.members() });
      queryClient.invalidateQueries({ queryKey: teamKeys.stats() });
      queryClient.invalidateQueries({ queryKey: teamKeys.activities() });
    },
  });
}

// Update team member role/permissions
export function useUpdateMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ memberId, data }: { memberId: string; data: TeamMemberUpdate }) =>
      teamApi.updateMember(memberId, data),
    onSuccess: (_, { memberId }) => {
      queryClient.invalidateQueries({ queryKey: teamKeys.member(memberId) });
      queryClient.invalidateQueries({ queryKey: teamKeys.members() });
      queryClient.invalidateQueries({ queryKey: teamKeys.activities() });
    },
  });
}

// Remove a team member
export function useRemoveMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (memberId: string) => teamApi.removeMember(memberId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: teamKeys.members() });
      queryClient.invalidateQueries({ queryKey: teamKeys.stats() });
      queryClient.invalidateQueries({ queryKey: teamKeys.activities() });
    },
  });
}

// Accept invitation (for invitation accept page)
export function useAcceptInvitation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (token: string) => teamApi.acceptInvitation(token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: teamKeys.all });
    },
  });
}

// Decline invitation (for invitation decline page)
export function useDeclineInvitation() {
  return useMutation({
    mutationFn: ({ token, reason }: { token: string; reason?: string }) =>
      teamApi.declineInvitation(token, reason),
  });
}

// Bulk invite multiple team members
export function useBulkInvite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: BulkInviteRequest) => teamApi.bulkInvite(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: teamKeys.members() });
      queryClient.invalidateQueries({ queryKey: teamKeys.stats() });
      queryClient.invalidateQueries({ queryKey: teamKeys.activities() });
    },
  });
}

// Search team members with optional query
export function useSearchMembers(query: string, includePending = true) {
  return useQuery({
    queryKey: [...teamKeys.members(), 'search', query, { includePending }],
    queryFn: () => teamApi.searchMembers(query, includePending),
    enabled: query.length > 0, // Only search when there's a query
    staleTime: 30000, // 30 seconds
  });
}
