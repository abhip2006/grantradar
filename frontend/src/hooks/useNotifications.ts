import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notificationsApi } from '../services/api';

// Query keys for cache invalidation
export const notificationKeys = {
  all: ['notifications'] as const,
  list: (unreadOnly?: boolean) => [...notificationKeys.all, 'list', { unreadOnly }] as const,
  unreadCount: () => [...notificationKeys.all, 'unreadCount'] as const,
};

/**
 * Hook to fetch notifications list
 * @param unreadOnly - If true, only fetch unread notifications
 * @param limit - Maximum number of notifications to fetch (default: 50)
 * @param offset - Offset for pagination (default: 0)
 */
export function useNotifications(unreadOnly = false, limit = 50, offset = 0) {
  return useQuery({
    queryKey: [...notificationKeys.list(unreadOnly), { limit, offset }],
    queryFn: () => notificationsApi.list(unreadOnly, limit, offset),
    staleTime: 30000, // 30 seconds
  });
}

/**
 * Hook to fetch unread notification count
 * Useful for displaying badge counts in the UI
 */
export function useUnreadCount() {
  return useQuery({
    queryKey: notificationKeys.unreadCount(),
    queryFn: () => notificationsApi.getUnreadCount(),
    staleTime: 15000, // 15 seconds - refresh more frequently for real-time feel
    refetchInterval: 60000, // Poll every minute for new notifications
  });
}

/**
 * Hook to mark a single notification as read
 */
export function useMarkAsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (notificationId: string) => notificationsApi.markAsRead(notificationId),
    onSuccess: () => {
      // Invalidate both the list and unread count
      queryClient.invalidateQueries({ queryKey: notificationKeys.all });
    },
    // Optimistic update for better UX
    onMutate: async (notificationId: string) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: notificationKeys.all });

      // Snapshot the previous value for unread count
      const previousCount = queryClient.getQueryData<number>(notificationKeys.unreadCount());

      // Optimistically update unread count
      if (previousCount !== undefined && previousCount > 0) {
        queryClient.setQueryData(notificationKeys.unreadCount(), previousCount - 1);
      }

      return { previousCount, notificationId };
    },
    onError: (_err, _notificationId, context) => {
      // Rollback on error
      if (context?.previousCount !== undefined) {
        queryClient.setQueryData(notificationKeys.unreadCount(), context.previousCount);
      }
    },
  });
}

/**
 * Hook to mark all notifications as read
 */
export function useMarkAllAsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => notificationsApi.markAllAsRead(),
    onSuccess: () => {
      // Invalidate all notification queries
      queryClient.invalidateQueries({ queryKey: notificationKeys.all });
    },
    // Optimistic update
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: notificationKeys.all });

      const previousCount = queryClient.getQueryData<number>(notificationKeys.unreadCount());

      // Set unread count to 0 optimistically
      queryClient.setQueryData(notificationKeys.unreadCount(), 0);

      return { previousCount };
    },
    onError: (_err, _variables, context) => {
      // Rollback on error
      if (context?.previousCount !== undefined) {
        queryClient.setQueryData(notificationKeys.unreadCount(), context.previousCount);
      }
    },
  });
}

/**
 * Hook to delete a notification
 */
export function useDeleteNotification() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (notificationId: string) => notificationsApi.delete(notificationId),
    onSuccess: () => {
      // Invalidate all notification queries
      queryClient.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
}
