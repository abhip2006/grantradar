import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { kanbanApi } from '../services/api';
import type {
  KanbanFilters,
  ReorderRequest,
  CardUpdate,
  SubtaskCreate,
  SubtaskUpdate,
  FieldDefinitionCreate,
  FieldDefinitionUpdate,
  TeamInvite,
} from '../types/kanban';

// Keys for cache invalidation
export const kanbanKeys = {
  all: ['kanban'] as const,
  board: (filters?: KanbanFilters) => [...kanbanKeys.all, 'board', filters] as const,
  subtasks: (appId: string) => [...kanbanKeys.all, 'subtasks', appId] as const,
  activities: (appId: string) => [...kanbanKeys.all, 'activities', appId] as const,
  attachments: (appId: string) => [...kanbanKeys.all, 'attachments', appId] as const,
  fields: () => [...kanbanKeys.all, 'fields'] as const,
  team: () => [...kanbanKeys.all, 'team'] as const,
};

// Board hook
export function useKanbanBoard(filters?: KanbanFilters) {
  return useQuery({
    queryKey: kanbanKeys.board(filters),
    queryFn: () => kanbanApi.getBoard(filters),
    staleTime: 30000, // 30 seconds
  });
}

// Reorder mutation
export function useReorderCard() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ReorderRequest) => kanbanApi.reorderCard(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: kanbanKeys.all });
    },
  });
}

// Update card mutation
export function useUpdateCard() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ appId, data }: { appId: string; data: CardUpdate }) =>
      kanbanApi.updateCard(appId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: kanbanKeys.all });
    },
  });
}

// Subtasks hooks
export function useSubtasks(appId: string) {
  return useQuery({
    queryKey: kanbanKeys.subtasks(appId),
    queryFn: () => kanbanApi.getSubtasks(appId),
    enabled: !!appId,
  });
}

export function useCreateSubtask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ appId, data }: { appId: string; data: SubtaskCreate }) =>
      kanbanApi.createSubtask(appId, data),
    onSuccess: (_, { appId }) => {
      queryClient.invalidateQueries({ queryKey: kanbanKeys.subtasks(appId) });
      queryClient.invalidateQueries({ queryKey: kanbanKeys.board() });
    },
  });
}

export function useUpdateSubtask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ subtaskId, data }: { subtaskId: string; data: SubtaskUpdate }) =>
      kanbanApi.updateSubtask(subtaskId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: kanbanKeys.all });
    },
  });
}

export function useDeleteSubtask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (subtaskId: string) => kanbanApi.deleteSubtask(subtaskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: kanbanKeys.all });
    },
  });
}

// Activities hooks
export function useActivities(appId: string, limit = 50) {
  return useQuery({
    queryKey: kanbanKeys.activities(appId),
    queryFn: () => kanbanApi.getActivities(appId, limit),
    enabled: !!appId,
  });
}

export function useAddComment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ appId, content }: { appId: string; content: string }) =>
      kanbanApi.addComment(appId, content),
    onSuccess: (_, { appId }) => {
      queryClient.invalidateQueries({ queryKey: kanbanKeys.activities(appId) });
    },
  });
}

// Attachments hooks
export function useAttachments(appId: string) {
  return useQuery({
    queryKey: kanbanKeys.attachments(appId),
    queryFn: () => kanbanApi.getAttachments(appId),
    enabled: !!appId,
  });
}

export function useUploadAttachment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ appId, file, metadata }: { appId: string; file: File; metadata?: { description?: string; category?: string } }) =>
      kanbanApi.uploadAttachment(appId, file, metadata),
    onSuccess: (_, { appId }) => {
      queryClient.invalidateQueries({ queryKey: kanbanKeys.attachments(appId) });
      queryClient.invalidateQueries({ queryKey: kanbanKeys.board() });
    },
  });
}

export function useDeleteAttachment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (attachmentId: string) => kanbanApi.deleteAttachment(attachmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: kanbanKeys.all });
    },
  });
}

// Custom fields hooks
export function useFieldDefinitions() {
  return useQuery({
    queryKey: kanbanKeys.fields(),
    queryFn: () => kanbanApi.getFieldDefinitions(),
  });
}

export function useCreateFieldDefinition() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: FieldDefinitionCreate) => kanbanApi.createFieldDefinition(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: kanbanKeys.fields() });
    },
  });
}

export function useUpdateFieldDefinition() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ fieldId, data }: { fieldId: string; data: FieldDefinitionUpdate }) =>
      kanbanApi.updateFieldDefinition(fieldId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: kanbanKeys.fields() });
    },
  });
}

export function useDeleteFieldDefinition() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (fieldId: string) => kanbanApi.deleteFieldDefinition(fieldId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: kanbanKeys.all });
    },
  });
}

export function useUpdateCardFields() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ appId, fields }: { appId: string; fields: Record<string, any> }) =>
      kanbanApi.updateCardFields(appId, fields),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: kanbanKeys.all });
    },
  });
}

// Team hooks
export function useTeamMembers() {
  return useQuery({
    queryKey: kanbanKeys.team(),
    queryFn: () => kanbanApi.getTeamMembers(),
  });
}

export function useInviteTeamMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TeamInvite) => kanbanApi.inviteTeamMember(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: kanbanKeys.team() });
    },
  });
}

export function useRemoveTeamMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (memberId: string) => kanbanApi.removeTeamMember(memberId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: kanbanKeys.team() });
    },
  });
}

export function useUpdateAssignees() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ appId, userIds }: { appId: string; userIds: string[] }) =>
      kanbanApi.updateAssignees(appId, userIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: kanbanKeys.all });
    },
  });
}
