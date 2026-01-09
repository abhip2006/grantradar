import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { componentsApi, versionsApi } from '../services/componentsApi';
import type {
  DocumentComponent,
  DocumentComponentCreate,
  DocumentComponentUpdate,
  DocumentComponentListResponse,
  DocumentComponentFilters,
  ComponentCategory,
  ComponentUsageResponse,
  DocumentVersion,
  DocumentVersionCreate,
  DocumentVersionListResponse,
  VersionDiffResult,
  InsertComponentRequest,
  InsertComponentResponse,
} from '../types/components';

// Stale time constants for consistency
const STALE_TIMES = {
  LIST: 5 * 60 * 1000,     // 5 minutes for list queries
  DETAIL: 2 * 60 * 1000,   // 2 minutes for detail queries
  REALTIME: 30 * 1000,     // 30 seconds for real-time data
} as const;

// Query keys for cache management
export const componentKeys = {
  all: ['components'] as const,
  list: (filters?: DocumentComponentFilters) => [...componentKeys.all, 'list', filters] as const,
  search: (filters: DocumentComponentFilters) => [...componentKeys.all, 'search', filters] as const,
  detail: (id: string) => [...componentKeys.all, 'detail', id] as const,
  versions: (componentId: string) => [...componentKeys.all, 'versions', componentId] as const,
  usage: (componentId: string) => [...componentKeys.all, 'usage', componentId] as const,
} as const;

export const documentVersionKeys = {
  all: ['document-versions'] as const,
  list: (kanbanCardId: string, section?: string) => [...documentVersionKeys.all, 'list', kanbanCardId, section] as const,
  detail: (versionId: string) => [...documentVersionKeys.all, 'detail', versionId] as const,
} as const;

// ============================================
// Document Components Hooks
// ============================================

/**
 * Hook to fetch document components with optional category filter
 */
export const useDocumentComponents = (category?: ComponentCategory) => {
  const filters: DocumentComponentFilters = {};
  if (category) {
    filters.category = category;
  }

  return useQuery<DocumentComponentListResponse>({
    queryKey: componentKeys.list(filters),
    queryFn: () => componentsApi.getComponents(filters),
    staleTime: STALE_TIMES.LIST,
  });
};

/**
 * Hook to fetch a single document component by ID
 */
export const useDocumentComponent = (id: string) => {
  return useQuery<DocumentComponent>({
    queryKey: componentKeys.detail(id),
    queryFn: () => componentsApi.getComponent(id),
    enabled: !!id,
    staleTime: STALE_TIMES.DETAIL,
  });
};

/**
 * Hook to search document components
 */
export const useSearchComponents = (filters: DocumentComponentFilters) => {
  return useQuery<DocumentComponentListResponse>({
    queryKey: componentKeys.search(filters),
    queryFn: () => componentsApi.getComponents(filters),
    enabled: !!filters.search || !!filters.category,
    staleTime: STALE_TIMES.LIST,
  });
};

/**
 * Hook to create a new document component
 */
export const useCreateComponent = () => {
  const queryClient = useQueryClient();

  return useMutation<DocumentComponent, Error, DocumentComponentCreate>({
    mutationFn: (data) => componentsApi.createComponent(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
    },
  });
};

/**
 * Hook to update an existing document component
 */
export const useUpdateComponent = () => {
  const queryClient = useQueryClient();

  return useMutation<DocumentComponent, Error, { id: string; data: DocumentComponentUpdate }>({
    mutationFn: ({ id, data }) => componentsApi.updateComponent(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
      queryClient.invalidateQueries({ queryKey: componentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: componentKeys.versions(id) });
    },
  });
};

/**
 * Hook to delete a document component
 */
export const useDeleteComponent = () => {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (id) => componentsApi.deleteComponent(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
    },
  });
};

/**
 * Hook to get version history for a component
 */
export const useComponentVersions = (componentId: string) => {
  return useQuery<DocumentVersion[]>({
    queryKey: componentKeys.versions(componentId),
    queryFn: () => componentsApi.getComponentVersions(componentId),
    enabled: !!componentId,
    staleTime: STALE_TIMES.DETAIL,
  });
};

/**
 * Hook to restore a previous version of a component
 */
export const useRestoreComponentVersion = () => {
  const queryClient = useQueryClient();

  return useMutation<DocumentComponent, Error, { id: string; versionNumber: number }>({
    mutationFn: ({ id, versionNumber }) => componentsApi.restoreVersion(id, versionNumber),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
      queryClient.invalidateQueries({ queryKey: componentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: componentKeys.versions(id) });
    },
  });
};

/**
 * Hook to get component usage history
 */
export const useComponentUsage = (componentId: string) => {
  return useQuery<ComponentUsageResponse>({
    queryKey: componentKeys.usage(componentId),
    queryFn: () => componentsApi.getComponentUsage(componentId),
    enabled: !!componentId,
    staleTime: STALE_TIMES.LIST,
  });
};

/**
 * Hook to duplicate a component
 */
export const useDuplicateComponent = () => {
  const queryClient = useQueryClient();

  return useMutation<DocumentComponent, Error, { id: string; newName?: string }>({
    mutationFn: ({ id, newName }) => componentsApi.duplicateComponent(id, newName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: componentKeys.all });
    },
  });
};

/**
 * Hook to insert a component into a document
 */
export const useInsertComponent = () => {
  const queryClient = useQueryClient();

  return useMutation<InsertComponentResponse, Error, InsertComponentRequest>({
    mutationFn: (data) => componentsApi.insertComponent(data),
    onSuccess: (_, { component_id, kanban_card_id }) => {
      queryClient.invalidateQueries({ queryKey: componentKeys.usage(component_id) });
      queryClient.invalidateQueries({ queryKey: ['kanban-card', kanban_card_id] });
    },
  });
};

// ============================================
// Document Versions Hooks
// ============================================

/**
 * Hook to fetch document versions for a kanban card
 */
export const useDocumentVersions = (kanbanCardId: string, section?: string) => {
  return useQuery<DocumentVersionListResponse>({
    queryKey: documentVersionKeys.list(kanbanCardId, section),
    queryFn: () => versionsApi.getVersions(kanbanCardId, section),
    enabled: !!kanbanCardId,
    staleTime: STALE_TIMES.LIST,
  });
};

/**
 * Hook to fetch a single document version
 */
export const useDocumentVersion = (versionId: string) => {
  return useQuery<DocumentVersion>({
    queryKey: documentVersionKeys.detail(versionId),
    queryFn: () => versionsApi.getVersion(versionId),
    enabled: !!versionId,
    staleTime: STALE_TIMES.DETAIL,
  });
};

/**
 * Hook to create a new document version
 */
export const useCreateVersion = () => {
  const queryClient = useQueryClient();

  return useMutation<DocumentVersion, Error, DocumentVersionCreate>({
    mutationFn: (data) => versionsApi.createVersion(data),
    onSuccess: (_, { kanban_card_id }) => {
      queryClient.invalidateQueries({ queryKey: documentVersionKeys.list(kanban_card_id) });
    },
  });
};

/**
 * Hook to create a named snapshot
 */
export const useCreateSnapshot = () => {
  const queryClient = useQueryClient();

  return useMutation<
    DocumentVersion,
    Error,
    { kanbanCardId: string; section: string; snapshotName: string }
  >({
    mutationFn: ({ kanbanCardId, section, snapshotName }) =>
      versionsApi.createSnapshot(kanbanCardId, section, snapshotName),
    onSuccess: (_, { kanbanCardId }) => {
      queryClient.invalidateQueries({ queryKey: documentVersionKeys.list(kanbanCardId) });
    },
  });
};

/**
 * Hook to compare two document versions
 */
export const useCompareVersions = () => {
  return useMutation<VersionDiffResult, Error, { versionAId: string; versionBId: string }>({
    mutationFn: ({ versionAId, versionBId }) =>
      versionsApi.compareVersions(versionAId, versionBId),
  });
};

/**
 * Hook to restore a document to a previous version
 */
export const useRestoreDocumentVersion = () => {
  const queryClient = useQueryClient();

  return useMutation<DocumentVersion, Error, { kanbanCardId: string; versionId: string }>({
    mutationFn: ({ kanbanCardId, versionId }) =>
      versionsApi.restoreVersion(kanbanCardId, versionId),
    onSuccess: (_, { kanbanCardId }) => {
      queryClient.invalidateQueries({ queryKey: documentVersionKeys.list(kanbanCardId) });
      queryClient.invalidateQueries({ queryKey: ['kanban-card', kanbanCardId] });
    },
  });
};

/**
 * Hook to delete a document version
 */
export const useDeleteVersion = () => {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { versionId: string; kanbanCardId: string }>({
    mutationFn: ({ versionId }) => versionsApi.deleteVersion(versionId),
    onSuccess: (_, { kanbanCardId }) => {
      queryClient.invalidateQueries({ queryKey: documentVersionKeys.list(kanbanCardId) });
    },
  });
};

/**
 * Hook to rename a snapshot
 */
export const useRenameSnapshot = () => {
  const queryClient = useQueryClient();

  return useMutation<
    DocumentVersion,
    Error,
    { versionId: string; snapshotName: string; kanbanCardId: string }
  >({
    mutationFn: ({ versionId, snapshotName }) =>
      versionsApi.renameSnapshot(versionId, snapshotName),
    onSuccess: (_, { kanbanCardId }) => {
      queryClient.invalidateQueries({ queryKey: documentVersionKeys.list(kanbanCardId) });
    },
  });
};
