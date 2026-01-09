import { api } from './api';
import type {
  ChecklistTemplate,
  ChecklistTemplateListResponse,
  ApplicationChecklist,
  CreateChecklistRequest,
  UpdateChecklistItemRequest,
} from '../types/checklists';

// Checklists API - Dynamic checklist management for applications
export const checklistsApi = {
  // Template operations

  /**
   * Get all available checklist templates
   * @param params - Optional filter params (funder, mechanism)
   */
  getTemplates: async (params?: {
    funder?: string;
    mechanism?: string;
  }): Promise<ChecklistTemplateListResponse> => {
    const response = await api.get<ChecklistTemplateListResponse>('/checklists/templates', {
      params,
    });
    return response.data;
  },

  /**
   * Get templates for a specific funder
   * @param funder - Funder name (e.g., 'NIH', 'NSF', 'DOE')
   */
  getTemplatesByFunder: async (funder: string): Promise<ChecklistTemplate[]> => {
    const encodedFunder = encodeURIComponent(funder);
    const response = await api.get<{ templates: ChecklistTemplate[] }>(
      `/checklists/templates/${encodedFunder}`
    );
    return response.data.templates;
  },

  /**
   * Get a single template by ID
   * @param templateId - Template UUID
   */
  getTemplate: async (templateId: string): Promise<ChecklistTemplate> => {
    const response = await api.get<ChecklistTemplate>(`/checklists/templates/${templateId}`);
    return response.data;
  },

  // Application checklist operations

  /**
   * Get checklist for a specific kanban card (application)
   * @param cardId - Kanban card UUID
   */
  getApplicationChecklist: async (cardId: string): Promise<ApplicationChecklist | null> => {
    try {
      const response = await api.get<ApplicationChecklist>(`/kanban/${cardId}/checklist`);
      return response.data;
    } catch (error: any) {
      // Return null if no checklist exists yet
      if (error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  },

  /**
   * Create a new checklist for an application from a template
   * @param cardId - Kanban card UUID
   * @param data - Create request with template_id
   */
  createChecklist: async (
    cardId: string,
    data: CreateChecklistRequest
  ): Promise<ApplicationChecklist> => {
    const response = await api.post<ApplicationChecklist>(`/kanban/${cardId}/checklist`, data);
    return response.data;
  },

  /**
   * Update a checklist item's status (complete/incomplete, notes)
   * @param cardId - Kanban card UUID
   * @param itemId - Checklist item UUID
   * @param data - Update data (completed, notes)
   */
  updateChecklistItem: async (
    cardId: string,
    itemId: string,
    data: UpdateChecklistItemRequest
  ): Promise<ApplicationChecklist> => {
    const response = await api.patch<ApplicationChecklist>(
      `/kanban/${cardId}/checklist/items/${itemId}`,
      data
    );
    return response.data;
  },

  /**
   * Delete checklist from an application
   * @param cardId - Kanban card UUID
   */
  deleteChecklist: async (cardId: string): Promise<void> => {
    await api.delete(`/kanban/${cardId}/checklist`);
  },

  /**
   * Reset all items in a checklist to incomplete
   * @param cardId - Kanban card UUID
   */
  resetChecklist: async (cardId: string): Promise<ApplicationChecklist> => {
    const response = await api.post<ApplicationChecklist>(`/kanban/${cardId}/checklist/reset`);
    return response.data;
  },

  /**
   * Change the template for an existing checklist
   * @param cardId - Kanban card UUID
   * @param templateId - New template UUID
   */
  changeTemplate: async (
    cardId: string,
    templateId: string
  ): Promise<ApplicationChecklist> => {
    const response = await api.put<ApplicationChecklist>(`/kanban/${cardId}/checklist/template`, {
      template_id: templateId,
    });
    return response.data;
  },

  /**
   * Get checklist progress statistics for multiple cards
   * @param cardIds - Array of kanban card UUIDs
   */
  getBulkProgress: async (
    cardIds: string[]
  ): Promise<Record<string, { progress_percent: number; completed: number; total: number }>> => {
    const response = await api.post<{
      progress: Record<string, { progress_percent: number; completed: number; total: number }>;
    }>('/checklists/bulk-progress', { card_ids: cardIds });
    return response.data.progress;
  },
};

export default checklistsApi;
