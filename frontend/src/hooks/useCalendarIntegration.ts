import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { calendarIntegrationApi } from '../services/api';
import type { CalendarProvider } from '../types';

export const useCalendarStatus = () => {
  return useQuery({
    queryKey: ['calendar-integration-status'],
    queryFn: calendarIntegrationApi.getStatus,
  });
};

export const useConnectGoogle = () => {
  return useMutation({
    mutationFn: calendarIntegrationApi.connectGoogle,
    onSuccess: (data) => {
      // Redirect to Google OAuth
      window.location.href = data.auth_url;
    },
  });
};

export const useDisconnectCalendar = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (provider: CalendarProvider) => calendarIntegrationApi.disconnect(provider),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar-integration-status'] });
    },
  });
};

export const useToggleSync = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ provider, enabled }: { provider: CalendarProvider; enabled: boolean }) =>
      calendarIntegrationApi.toggleSync(provider, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar-integration-status'] });
    },
  });
};

export const useSyncCalendar = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (provider: CalendarProvider) => calendarIntegrationApi.syncNow(provider),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar-integration-status'] });
    },
  });
};
