import React, { useState } from 'react';
import { format } from 'date-fns';
import {
  ShieldCheckIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ClockIcon,
  FunnelIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { useComplianceScan } from '../../hooks/useCompliance';
import type { ComplianceScan, ComplianceSeverity, ScanResultItem } from '../../types/compliance';
import ComplianceSummary from './ComplianceSummary';
import ComplianceResultItem from './ComplianceResultItem';
import ComplianceScanButton from './ComplianceScanButton';

interface CompliancePanelProps {
  cardId: string;
  funder?: string;
  mechanism?: string;
  initialExpanded?: boolean;
}

type FilterType = 'all' | 'failed' | 'passed' | ComplianceSeverity;

export const CompliancePanel = React.memo(function CompliancePanel({
  cardId,
  funder,
  mechanism,
  initialExpanded = true,
}: CompliancePanelProps) {
  const [isExpanded, setIsExpanded] = useState(initialExpanded);
  const [filter, setFilter] = useState<FilterType>('all');
  const [showDetails, setShowDetails] = useState(true);

  const { data: scan, isLoading, error, refetch } = useComplianceScan(cardId);

  // Calculate summary from scan results
  const getSummary = (scanData: ComplianceScan) => {
    const passed = scanData.passed_count;
    const failed = scanData.results.filter((r) => !r.passed && r.severity === 'error').length;
    const warnings = scanData.results.filter((r) => !r.passed && r.severity === 'warning').length;
    const info = scanData.results.filter((r) => !r.passed && r.severity === 'info').length;
    const total = scanData.results.length;

    return {
      passed,
      failed,
      warnings,
      info,
      total,
      overall_status: scanData.overall_status,
    };
  };

  // Filter results based on selected filter
  const getFilteredResults = (results: ScanResultItem[]): ScanResultItem[] => {
    switch (filter) {
      case 'all':
        return results;
      case 'failed':
        return results.filter((r) => !r.passed);
      case 'passed':
        return results.filter((r) => r.passed);
      case 'error':
      case 'warning':
      case 'info':
        return results.filter((r) => !r.passed && r.severity === filter);
      default:
        return results;
    }
  };

  const handleRefresh = () => {
    refetch();
  };

  const handleScanComplete = () => {
    refetch();
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <ShieldCheckIcon className="w-5 h-5 text-gray-600" />
          <h3 className="font-semibold text-gray-900">Compliance Scanner</h3>
          {scan && (
            <ComplianceSummary summary={getSummary(scan)} compact />
          )}
        </div>
        <button
          type="button"
          className="p-1 hover:bg-gray-200 rounded-lg transition-colors"
          onClick={(e) => {
            e.stopPropagation();
            setIsExpanded(!isExpanded);
          }}
        >
          {isExpanded ? (
            <ChevronUpIcon className="w-5 h-5 text-gray-500" />
          ) : (
            <ChevronDownIcon className="w-5 h-5 text-gray-500" />
          )}
        </button>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* Loading state */}
          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <ArrowPathIcon className="w-6 h-6 text-gray-400 animate-spin" />
              <span className="ml-2 text-gray-500">Loading scan results...</span>
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="text-center py-8">
              <p className="text-red-500 mb-2">Failed to load scan results</p>
              <button
                onClick={handleRefresh}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                Try again
              </button>
            </div>
          )}

          {/* No scan yet */}
          {!isLoading && !error && !scan && (
            <div className="text-center py-8">
              <ShieldCheckIcon className="w-12 h-12 mx-auto text-gray-300 mb-3" />
              <p className="text-gray-500 mb-4">No compliance scan has been run yet</p>
              <ComplianceScanButton
                cardId={cardId}
                funder={funder}
                mechanism={mechanism}
                onScanComplete={handleScanComplete}
              />
            </div>
          )}

          {/* Scan results */}
          {scan && (
            <>
              {/* Summary */}
              <ComplianceSummary summary={getSummary(scan)} />

              {/* Scan metadata */}
              <div className="flex items-center justify-between text-sm text-gray-500">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <ClockIcon className="w-4 h-4" />
                    Last scanned: {format(new Date(scan.scanned_at), 'MMM d, yyyy h:mm a')}
                  </span>
                  {scan.file_name && (
                    <span className="text-gray-400">|</span>
                  )}
                  {scan.file_name && (
                    <span>{scan.file_name}</span>
                  )}
                </div>
                <ComplianceScanButton
                  cardId={cardId}
                  funder={funder}
                  mechanism={mechanism}
                  variant="secondary"
                  size="sm"
                  onScanComplete={handleScanComplete}
                />
              </div>

              {/* Filter bar */}
              <div className="flex items-center justify-between border-t border-gray-100 pt-4">
                <div className="flex items-center gap-2">
                  <FunnelIcon className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-500">Filter:</span>
                  <div className="flex gap-1">
                    {(['all', 'failed', 'passed', 'error', 'warning', 'info'] as FilterType[]).map(
                      (filterType) => (
                        <button
                          key={filterType}
                          onClick={() => setFilter(filterType)}
                          className={`
                            px-2.5 py-1 text-xs font-medium rounded-full transition-colors
                            ${filter === filterType
                              ? 'bg-blue-100 text-blue-700'
                              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                            }
                          `}
                        >
                          {filterType === 'all' && 'All'}
                          {filterType === 'failed' && 'Failed'}
                          {filterType === 'passed' && 'Passed'}
                          {filterType === 'error' && 'Errors'}
                          {filterType === 'warning' && 'Warnings'}
                          {filterType === 'info' && 'Info'}
                        </button>
                      )
                    )}
                  </div>
                </div>
                <label className="flex items-center gap-2 text-sm text-gray-500 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showDetails}
                    onChange={(e) => setShowDetails(e.target.checked)}
                    className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  Show details
                </label>
              </div>

              {/* Results list */}
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {getFilteredResults(scan.results).length === 0 ? (
                  <p className="text-center py-4 text-gray-500 text-sm">
                    No results match the selected filter
                  </p>
                ) : (
                  getFilteredResults(scan.results).map((result, idx) => (
                    <ComplianceResultItem
                      key={`${result.rule_id}-${idx}`}
                      result={result}
                      showDetails={showDetails}
                    />
                  ))
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
});

export default CompliancePanel;
