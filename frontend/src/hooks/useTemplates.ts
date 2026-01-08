import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { templatesApi } from '../services/api';
import type {
  Template,
  TemplateCreate,
  TemplateUpdate,
  TemplateFilters,
  TemplateListResponse,
  TemplateCategory,
} from '../types';

export const useTemplates = (filters?: TemplateFilters) => {
  return useQuery<TemplateListResponse>({
    queryKey: ['templates', filters],
    queryFn: () => templatesApi.getTemplates(filters),
  });
};

export const useTemplate = (id: string) => {
  return useQuery<Template>({
    queryKey: ['template', id],
    queryFn: () => templatesApi.getTemplate(id),
    enabled: !!id,
  });
};

export const useCreateTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TemplateCreate) => templatesApi.createTemplate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
    },
  });
};

export const useUpdateTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TemplateUpdate }) =>
      templatesApi.updateTemplate(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      queryClient.invalidateQueries({ queryKey: ['template', id] });
    },
  });
};

export const useDeleteTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => templatesApi.deleteTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
    },
  });
};

export const useDuplicateTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => templatesApi.duplicateTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
    },
  });
};

export const useRenderTemplate = () => {
  return useMutation({
    mutationFn: ({ id, variables }: { id: string; variables: Record<string, string | number> }) =>
      templatesApi.renderTemplate(id, variables),
  });
};

export const useTemplateCategories = () => {
  return useQuery<TemplateCategory[]>({
    queryKey: ['template-categories'],
    queryFn: templatesApi.getCategories,
  });
};
