import { api } from './api';
import type {
  ComplianceRuleSet,
  ComplianceScan,
  ComplianceScanRequest,
  ComplianceScanListResponse,
} from '../types/compliance';

// Compliance API - Automated validation of application documents
export const complianceApi = {
  // Get compliance rules for a specific funder
  getRules: async (funder: string, mechanism?: string): Promise<ComplianceRuleSet> => {
    const encodedFunder = encodeURIComponent(funder);
    const response = await api.get<ComplianceRuleSet>(`/compliance/rules/${encodedFunder}`, {
      params: mechanism ? { mechanism } : undefined,
    });
    return response.data;
  },

  // Run compliance scan on a kanban card's documents
  runScan: async (
    cardId: string,
    request?: ComplianceScanRequest
  ): Promise<ComplianceScan> => {
    const response = await api.post<ComplianceScan>(
      `/kanban/${cardId}/compliance/scan`,
      request || {}
    );
    return response.data;
  },

  // Get compliance scan results for a kanban card
  getScanResults: async (cardId: string): Promise<ComplianceScan | null> => {
    try {
      const response = await api.get<ComplianceScan>(
        `/kanban/${cardId}/compliance/results`
      );
      return response.data;
    } catch (error: unknown) {
      // Return null if no scan exists yet (404)
      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as { response?: { status?: number } };
        if (axiosError.response?.status === 404) {
          return null;
        }
      }
      throw error;
    }
  },

  // Get scan history for a kanban card
  getScanHistory: async (
    cardId: string,
    params?: { limit?: number; offset?: number }
  ): Promise<ComplianceScanListResponse> => {
    const response = await api.get<ComplianceScanListResponse>(
      `/kanban/${cardId}/compliance/history`,
      { params }
    );
    return response.data;
  },

  // Get all available funders with compliance rules
  getAvailableFunders: async (): Promise<string[]> => {
    const response = await api.get<{ funders: string[] }>('/compliance/funders');
    return response.data.funders;
  },
};

export default complianceApi;
