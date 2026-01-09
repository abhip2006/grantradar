import React from 'react';
import {
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';
import type { ScanResultItem, ComplianceSeverity } from '../../types/compliance';
import { SEVERITY_CONFIG } from '../../types/compliance';

interface ComplianceResultItemProps {
  result: ScanResultItem;
  showDetails?: boolean;
}

// Icon mapping for severity levels
const SEVERITY_ICONS: Record<ComplianceSeverity, React.ComponentType<React.SVGProps<SVGSVGElement>>> = {
  error: XCircleIcon,
  warning: ExclamationTriangleIcon,
  info: InformationCircleIcon,
};

export const ComplianceResultItem = React.memo(function ComplianceResultItem({ result, showDetails = true }: ComplianceResultItemProps) {
  const config = SEVERITY_CONFIG[result.severity];
  const Icon = result.passed ? CheckCircleIcon : SEVERITY_ICONS[result.severity];

  return (
    <div
      className={`
        flex items-start gap-3 p-3 rounded-lg border
        ${result.passed ? 'bg-green-50 border-green-200' : `${config.bgColor} ${config.borderColor}`}
      `}
    >
      {/* Status icon */}
      <div className="flex-shrink-0 mt-0.5">
        <Icon
          className={`w-5 h-5 ${result.passed ? 'text-green-500' : config.iconColor}`}
        />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Rule name */}
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`font-medium text-sm ${result.passed ? 'text-green-700' : config.color}`}
          >
            {result.rule_name}
          </span>
          {!result.passed && (
            <span
              className={`
                inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full
                ${result.severity === 'error' ? 'bg-red-100 text-red-700' : ''}
                ${result.severity === 'warning' ? 'bg-amber-100 text-amber-700' : ''}
                ${result.severity === 'info' ? 'bg-blue-100 text-blue-700' : ''}
              `}
            >
              {config.label}
            </span>
          )}
        </div>

        {/* Message */}
        <p className={`mt-1 text-sm ${result.passed ? 'text-green-600' : 'text-gray-600'}`}>
          {result.message}
        </p>

        {/* Location if available */}
        {result.location && showDetails && (
          <p className="mt-1 text-xs text-gray-500">
            Location: {result.location}
          </p>
        )}

        {/* Additional details */}
        {showDetails && result.details && Object.keys(result.details).length > 0 && (
          <div className="mt-2 text-xs text-gray-500 space-y-0.5">
            {Object.entries(result.details).map(([key, value]) => (
              <div key={key}>
                <span className="font-medium capitalize">{key.replace(/_/g, ' ')}:</span>{' '}
                {String(value)}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
});

export default ComplianceResultItem;
