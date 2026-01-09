import { api } from './api';
import type {
  DocumentComponent,
  DocumentComponentCreate,
  DocumentComponentUpdate,
  DocumentComponentListResponse,
  DocumentComponentFilters,
  ComponentUsageResponse,
  DocumentVersion,
  DocumentVersionCreate,
  DocumentVersionListResponse,
  VersionDiffResult,
  InsertComponentRequest,
  InsertComponentResponse,
} from '../types/components';

/**
 * Document Components API
 * Manages reusable document components for grant applications
 */
export const componentsApi = {
  /**
   * Get all document components with optional filters
   */
  getComponents: async (params?: DocumentComponentFilters): Promise<DocumentComponentListResponse> => {
    const response = await api.get<DocumentComponentListResponse>('/components', { params });
    return response.data;
  },

  /**
   * Get a single document component by ID
   */
  getComponent: async (id: string): Promise<DocumentComponent> => {
    const response = await api.get<DocumentComponent>(`/components/${id}`);
    return response.data;
  },

  /**
   * Create a new document component
   */
  createComponent: async (data: DocumentComponentCreate): Promise<DocumentComponent> => {
    const response = await api.post<DocumentComponent>('/components', data);
    return response.data;
  },

  /**
   * Update an existing document component
   * This creates a new version while preserving version history
   */
  updateComponent: async (id: string, data: DocumentComponentUpdate): Promise<DocumentComponent> => {
    const response = await api.patch<DocumentComponent>(`/components/${id}`, data);
    return response.data;
  },

  /**
   * Delete a document component
   */
  deleteComponent: async (id: string): Promise<void> => {
    await api.delete(`/components/${id}`);
  },

  /**
   * Get version history for a component
   */
  getComponentVersions: async (id: string): Promise<DocumentComponent[]> => {
    const response = await api.get<DocumentComponent[]>(`/components/${id}/versions`);
    return response.data;
  },

  /**
   * Restore a previous version of a component
   */
  restoreVersion: async (id: string, versionNumber: number): Promise<DocumentComponent> => {
    const response = await api.post<DocumentComponent>(`/components/${id}/restore`, {
      version_number: versionNumber,
    });
    return response.data;
  },

  /**
   * Get usage history for a component
   */
  getComponentUsage: async (id: string): Promise<ComponentUsageResponse> => {
    const response = await api.get<ComponentUsageResponse>(`/components/${id}/usage`);
    return response.data;
  },

  /**
   * Duplicate a component
   */
  duplicateComponent: async (id: string, newName?: string): Promise<DocumentComponent> => {
    const response = await api.post<DocumentComponent>(`/components/${id}/duplicate`, {
      name: newName,
    });
    return response.data;
  },

  /**
   * Insert a component into a document/application
   */
  insertComponent: async (data: InsertComponentRequest): Promise<InsertComponentResponse> => {
    const response = await api.post<InsertComponentResponse>('/components/insert', data);
    return response.data;
  },
};

/**
 * Document Versions API
 * Manages version history for application documents
 */
export const versionsApi = {
  /**
   * Get all versions for a kanban card (application)
   */
  getVersions: async (
    kanbanCardId: string,
    section?: string
  ): Promise<DocumentVersionListResponse> => {
    const response = await api.get<DocumentVersionListResponse>(`/kanban/${kanbanCardId}/versions`, {
      params: { section },
    });
    return response.data;
  },

  /**
   * Get a single version by ID
   */
  getVersion: async (versionId: string): Promise<DocumentVersion> => {
    const response = await api.get<DocumentVersion>(`/versions/${versionId}`);
    return response.data;
  },

  /**
   * Create a new version (snapshot) of a document
   */
  createVersion: async (data: DocumentVersionCreate): Promise<DocumentVersion> => {
    const response = await api.post<DocumentVersion>('/versions', data);
    return response.data;
  },

  /**
   * Create a named snapshot of current document state
   */
  createSnapshot: async (
    kanbanCardId: string,
    section: string,
    snapshotName: string
  ): Promise<DocumentVersion> => {
    const response = await api.post<DocumentVersion>(`/kanban/${kanbanCardId}/versions/snapshot`, {
      section,
      snapshot_name: snapshotName,
    });
    return response.data;
  },

  /**
   * Compare two versions and get diff
   */
  compareVersions: async (
    versionAId: string,
    versionBId: string
  ): Promise<VersionDiffResult> => {
    const response = await api.post<VersionDiffResult>('/versions/compare', {
      version_a_id: versionAId,
      version_b_id: versionBId,
    });
    return response.data;
  },

  /**
   * Restore a document to a previous version
   */
  restoreVersion: async (
    kanbanCardId: string,
    versionId: string
  ): Promise<DocumentVersion> => {
    const response = await api.post<DocumentVersion>(
      `/kanban/${kanbanCardId}/versions/${versionId}/restore`
    );
    return response.data;
  },

  /**
   * Delete a version (only non-current versions can be deleted)
   */
  deleteVersion: async (versionId: string): Promise<void> => {
    await api.delete(`/versions/${versionId}`);
  },

  /**
   * Rename a snapshot
   */
  renameSnapshot: async (versionId: string, snapshotName: string): Promise<DocumentVersion> => {
    const response = await api.patch<DocumentVersion>(`/versions/${versionId}`, {
      snapshot_name: snapshotName,
    });
    return response.data;
  },
};

export default { componentsApi, versionsApi };
