import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { deadlinesApi } from '../services/api';
import type {
  Deadline,
  DeadlineCreate,
  DeadlineUpdate,
  DeadlineFilters,
  DeadlineListResponse,
} from '../types';

export const useDeadlines = (filters?: DeadlineFilters) => {
  return useQuery<DeadlineListResponse>({
    queryKey: ['deadlines', filters],
    queryFn: () => deadlinesApi.getDeadlines(filters),
  });
};

export const useDeadline = (id: string) => {
  return useQuery<Deadline>({
    queryKey: ['deadline', id],
    queryFn: () => deadlinesApi.getDeadline(id),
    enabled: !!id,
  });
};

export const useCreateDeadline = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: DeadlineCreate) => deadlinesApi.createDeadline(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deadlines'] });
    },
  });
};

export const useUpdateDeadline = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DeadlineUpdate }) =>
      deadlinesApi.updateDeadline(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['deadlines'] });
      queryClient.invalidateQueries({ queryKey: ['deadline', id] });
    },
  });
};

export const useDeleteDeadline = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deadlinesApi.deleteDeadline(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deadlines'] });
    },
  });
};

export const useLinkGrant = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (grantId: string) => deadlinesApi.linkGrant(grantId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deadlines'] });
    },
  });
};

export const useExportDeadlinesIcs = () => {
  return useMutation({
    mutationFn: () => deadlinesApi.exportIcs(),
    onSuccess: (blob) => {
      // Create download link for the ICS file
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'deadlines.ics';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
  });
};

export const useChangeDeadlineStatus = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, status, notes }: { id: string; status: string; notes?: string }) =>
      deadlinesApi.changeStatus(id, status as import('../types').DeadlineStatus, notes),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['deadlines'] });
      queryClient.invalidateQueries({ queryKey: ['deadline', id] });
    },
  });
};

export const useDeadlineStats = () => {
  return useQuery({
    queryKey: ['deadline-stats'],
    queryFn: () => deadlinesApi.getStats(),
  });
};

export const useDeadlineStatusHistory = (id: string) => {
  return useQuery({
    queryKey: ['deadline-history', id],
    queryFn: () => deadlinesApi.getStatusHistory(id),
    enabled: !!id,
  });
};
