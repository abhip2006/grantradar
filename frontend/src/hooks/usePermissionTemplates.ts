import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { permissionTemplatesApi } from '../services/api';
import type { PermissionTemplateCreate, PermissionTemplateUpdate } from '../types/team';
import { teamKeys } from './useTeam';

// Query keys for cache invalidation
export const permissionTemplateKeys = {
  all: ['permissionTemplates'] as const,
  list: () => [...permissionTemplateKeys.all, 'list'] as const,
  defaults: () => [...permissionTemplateKeys.all, 'defaults'] as const,
  detail: (id: string) => [...permissionTemplateKeys.all, 'detail', id] as const,
};

/**
 * Hook to fetch all permission templates for the current user
 */
export function usePermissionTemplates() {
  return useQuery({
    queryKey: permissionTemplateKeys.list(),
    queryFn: () => permissionTemplatesApi.list(),
    staleTime: 60000, // 1 minute - templates don't change often
  });
}

/**
 * Hook to fetch default permission templates
 * These are system-defined templates that can be used as starting points
 */
export function useDefaultTemplates() {
  return useQuery({
    queryKey: permissionTemplateKeys.defaults(),
    queryFn: () => permissionTemplatesApi.getDefaults(),
    staleTime: 300000, // 5 minutes - defaults rarely change
  });
}

/**
 * Hook to fetch a single permission template by ID
 * @param templateId - The ID of the template to fetch
 */
export function usePermissionTemplate(templateId: string) {
  return useQuery({
    queryKey: permissionTemplateKeys.detail(templateId),
    queryFn: () => permissionTemplatesApi.get(templateId),
    enabled: !!templateId,
  });
}

/**
 * Hook to create a new permission template
 */
export function useCreateTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: PermissionTemplateCreate) => permissionTemplatesApi.create(data),
    onSuccess: () => {
      // Invalidate the templates list to refetch
      queryClient.invalidateQueries({ queryKey: permissionTemplateKeys.list() });
    },
  });
}

/**
 * Hook to update an existing permission template
 */
export function useUpdateTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PermissionTemplateUpdate }) =>
      permissionTemplatesApi.update(id, data),
    onSuccess: (_, { id }) => {
      // Invalidate both the list and the specific template detail
      queryClient.invalidateQueries({ queryKey: permissionTemplateKeys.list() });
      queryClient.invalidateQueries({ queryKey: permissionTemplateKeys.detail(id) });
    },
  });
}

/**
 * Hook to delete a permission template
 */
export function useDeleteTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (templateId: string) => permissionTemplatesApi.delete(templateId),
    onSuccess: (_, templateId) => {
      // Invalidate the list and remove the detail from cache
      queryClient.invalidateQueries({ queryKey: permissionTemplateKeys.list() });
      queryClient.removeQueries({ queryKey: permissionTemplateKeys.detail(templateId) });
    },
  });
}

/**
 * Hook to apply a permission template to a team member
 * This will update the team member's permissions based on the template
 */
export function useApplyTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ templateId, memberId }: { templateId: string; memberId: string }) =>
      permissionTemplatesApi.applyToMember(templateId, memberId),
    onSuccess: (_, { memberId }) => {
      // Invalidate team member queries to reflect the new permissions
      queryClient.invalidateQueries({ queryKey: teamKeys.members() });
      queryClient.invalidateQueries({ queryKey: teamKeys.member(memberId) });
      queryClient.invalidateQueries({ queryKey: teamKeys.activities() });
    },
  });
}
