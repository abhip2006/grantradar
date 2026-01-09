import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { complianceApi } from '../services/complianceApi';
import type { ComplianceScanRequest } from '../types/compliance';

// Stale time constants for consistency
const STALE_TIMES = {
  LIST: 5 * 60 * 1000,     // 5 minutes for list queries
  DETAIL: 2 * 60 * 1000,   // 2 minutes for detail queries
  REALTIME: 30 * 1000,     // 30 seconds for real-time data
} as const;

// Query keys for cache management
export const complianceKeys = {
  all: ['compliance'] as const,
  rules: (funder: string, mechanism?: string) =>
    [...complianceKeys.all, 'rules', funder, mechanism] as const,
  scan: (cardId: string) => [...complianceKeys.all, 'scan', cardId] as const,
  history: (cardId: string) => [...complianceKeys.all, 'history', cardId] as const,
  funders: () => [...complianceKeys.all, 'funders'] as const,
};

// Hook to get compliance rules for a funder
export function useComplianceRules(funder: string, mechanism?: string) {
  return useQuery({
    queryKey: complianceKeys.rules(funder, mechanism),
    queryFn: () => complianceApi.getRules(funder, mechanism),
    enabled: !!funder,
    staleTime: STALE_TIMES.LIST,
  });
}

// Hook to get current compliance scan results for a card
export function useComplianceScan(cardId: string) {
  return useQuery({
    queryKey: complianceKeys.scan(cardId),
    queryFn: () => complianceApi.getScanResults(cardId),
    enabled: !!cardId,
    staleTime: STALE_TIMES.REALTIME,
  });
}

// Hook to get scan history for a card
export function useComplianceScanHistory(
  cardId: string,
  options?: { limit?: number; offset?: number }
) {
  return useQuery({
    queryKey: complianceKeys.history(cardId),
    queryFn: () => complianceApi.getScanHistory(cardId, options),
    enabled: !!cardId,
    staleTime: STALE_TIMES.DETAIL,
  });
}

// Hook to run a compliance scan
export function useRunComplianceScan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      cardId,
      request,
    }: {
      cardId: string;
      request?: ComplianceScanRequest;
    }) => complianceApi.runScan(cardId, request),
    onSuccess: (_, { cardId }) => {
      // Invalidate the scan results to refetch
      queryClient.invalidateQueries({ queryKey: complianceKeys.scan(cardId) });
      queryClient.invalidateQueries({ queryKey: complianceKeys.history(cardId) });
    },
  });
}

// Hook to get available funders with compliance rules
export function useAvailableFunders() {
  return useQuery({
    queryKey: complianceKeys.funders(),
    queryFn: () => complianceApi.getAvailableFunders(),
    staleTime: STALE_TIMES.LIST,
  });
}

export default {
  useComplianceRules,
  useComplianceScan,
  useComplianceScanHistory,
  useRunComplianceScan,
  useAvailableFunders,
};
