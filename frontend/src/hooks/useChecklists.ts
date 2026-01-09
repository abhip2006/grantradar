import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { checklistsApi } from '../services/checklistsApi';
import type {
  ChecklistTemplate,
  ApplicationChecklist,
  CreateChecklistRequest,
  UpdateChecklistItemRequest,
} from '../types/checklists';

// Stale time constants for consistency
const STALE_TIMES = {
  LIST: 5 * 60 * 1000,     // 5 minutes for list queries
  DETAIL: 2 * 60 * 1000,   // 2 minutes for detail queries
  REALTIME: 30 * 1000,     // 30 seconds for real-time data
} as const;

// Query keys for cache management
export const checklistKeys = {
  all: ['checklists'] as const,
  templates: () => [...checklistKeys.all, 'templates'] as const,
  templatesByFunder: (funder: string) => [...checklistKeys.templates(), 'funder', funder] as const,
  template: (id: string) => [...checklistKeys.templates(), 'detail', id] as const,
  card: (cardId: string) => [...checklistKeys.all, 'card', cardId] as const,
  bulkProgress: (cardIds: string[]) => [...checklistKeys.all, 'bulk-progress', cardIds] as const,
};

/**
 * Hook to fetch all available checklist templates
 * @param params - Optional filters (funder, mechanism)
 */
export function useChecklistTemplates(params?: { funder?: string; mechanism?: string }) {
  return useQuery({
    queryKey: checklistKeys.templates(),
    queryFn: () => checklistsApi.getTemplates(params),
    staleTime: STALE_TIMES.LIST,
  });
}

/**
 * Hook to fetch templates for a specific funder
 * @param funder - Funder name (e.g., 'NIH', 'NSF')
 */
export function useChecklistTemplatesByFunder(funder: string) {
  return useQuery({
    queryKey: checklistKeys.templatesByFunder(funder),
    queryFn: () => checklistsApi.getTemplatesByFunder(funder),
    enabled: !!funder,
    staleTime: STALE_TIMES.LIST,
  });
}

/**
 * Hook to fetch a single template by ID
 * @param templateId - Template UUID
 */
export function useChecklistTemplate(templateId: string) {
  return useQuery({
    queryKey: checklistKeys.template(templateId),
    queryFn: () => checklistsApi.getTemplate(templateId),
    enabled: !!templateId,
    staleTime: STALE_TIMES.DETAIL,
  });
}

/**
 * Hook to fetch the checklist for a specific application/card
 * @param cardId - Kanban card UUID
 */
export function useApplicationChecklist(cardId: string) {
  return useQuery({
    queryKey: checklistKeys.card(cardId),
    queryFn: () => checklistsApi.getApplicationChecklist(cardId),
    enabled: !!cardId,
    staleTime: STALE_TIMES.REALTIME,
  });
}

/**
 * Hook to create a new checklist for an application
 */
export function useCreateChecklist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ cardId, data }: { cardId: string; data: CreateChecklistRequest }) =>
      checklistsApi.createChecklist(cardId, data),
    onSuccess: (_, { cardId }) => {
      // Invalidate the application checklist cache (granular)
      queryClient.invalidateQueries({ queryKey: checklistKeys.card(cardId) });
      // Also invalidate bulk progress for any cached queries containing this card
      queryClient.invalidateQueries({ queryKey: [...checklistKeys.all, 'bulk-progress'] });
    },
  });
}

/**
 * Hook to update a checklist item (mark complete/incomplete, add notes)
 */
export function useUpdateChecklistItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      cardId,
      itemId,
      data,
    }: {
      cardId: string;
      itemId: string;
      data: UpdateChecklistItemRequest;
    }) => checklistsApi.updateChecklistItem(cardId, itemId, data),
    onMutate: async ({ cardId, itemId, data }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: checklistKeys.card(cardId) });

      // Snapshot the previous value
      const previousChecklist = queryClient.getQueryData<ApplicationChecklist | null>(
        checklistKeys.card(cardId)
      );

      // Optimistically update the cache
      if (previousChecklist) {
        const updatedItems = previousChecklist.items.map((item) =>
          item.item_id === itemId
            ? {
                ...item,
                completed: data.completed ?? item.completed,
                notes: data.notes ?? item.notes,
                completed_at: data.completed ? new Date().toISOString() : item.completed_at,
              }
            : item
        );

        const completedCount = updatedItems.filter((i) => i.completed).length;

        queryClient.setQueryData<ApplicationChecklist>(checklistKeys.card(cardId), {
          ...previousChecklist,
          items: updatedItems,
          completed_count: completedCount,
          progress_percent: (completedCount / updatedItems.length) * 100,
        });
      }

      return { previousChecklist };
    },
    onError: (_, { cardId }, context) => {
      // Rollback on error
      if (context?.previousChecklist) {
        queryClient.setQueryData(checklistKeys.card(cardId), context.previousChecklist);
      }
    },
    onSettled: (_, __, { cardId }) => {
      // Always refetch after mutation settles (granular invalidation)
      queryClient.invalidateQueries({ queryKey: checklistKeys.card(cardId) });
      // Also invalidate bulk progress for any cached queries containing this card
      queryClient.invalidateQueries({ queryKey: [...checklistKeys.all, 'bulk-progress'] });
    },
  });
}

/**
 * Hook to delete a checklist from an application
 */
export function useDeleteChecklist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (cardId: string) => checklistsApi.deleteChecklist(cardId),
    onSuccess: (_, cardId) => {
      queryClient.setQueryData(checklistKeys.card(cardId), null);
      // Invalidate bulk progress for any cached queries containing this card
      queryClient.invalidateQueries({ queryKey: [...checklistKeys.all, 'bulk-progress'] });
    },
  });
}

/**
 * Hook to reset all items in a checklist
 */
export function useResetChecklist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (cardId: string) => checklistsApi.resetChecklist(cardId),
    onSuccess: (_, cardId) => {
      queryClient.invalidateQueries({ queryKey: checklistKeys.card(cardId) });
      // Invalidate bulk progress for any cached queries containing this card
      queryClient.invalidateQueries({ queryKey: [...checklistKeys.all, 'bulk-progress'] });
    },
  });
}

/**
 * Hook to change the template for an existing checklist
 */
export function useChangeChecklistTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ cardId, templateId }: { cardId: string; templateId: string }) =>
      checklistsApi.changeTemplate(cardId, templateId),
    onSuccess: (_, { cardId }) => {
      queryClient.invalidateQueries({ queryKey: checklistKeys.card(cardId) });
      // Invalidate bulk progress for any cached queries containing this card
      queryClient.invalidateQueries({ queryKey: [...checklistKeys.all, 'bulk-progress'] });
    },
  });
}

/**
 * Hook to fetch progress for multiple cards
 * @param cardIds - Array of kanban card UUIDs
 */
export function useBulkChecklistProgress(cardIds: string[]) {
  return useQuery({
    queryKey: checklistKeys.bulkProgress(cardIds),
    queryFn: () => checklistsApi.getBulkProgress(cardIds),
    enabled: cardIds.length > 0,
    staleTime: STALE_TIMES.REALTIME,
  });
}
