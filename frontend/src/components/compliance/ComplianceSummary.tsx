import {
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/solid';
import type { ComplianceSummary as ComplianceSummaryType } from '../../types/compliance';
import { STATUS_CONFIG } from '../../types/compliance';

interface ComplianceSummaryProps {
  summary: ComplianceSummaryType;
  compact?: boolean;
}

export function ComplianceSummary({ summary, compact = false }: ComplianceSummaryProps) {
  const statusConfig = STATUS_CONFIG[summary.overall_status];

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        {summary.overall_status === 'passed' && (
          <CheckCircleIcon className="w-5 h-5 text-green-500" />
        )}
        {summary.overall_status === 'failed' && (
          <XCircleIcon className="w-5 h-5 text-red-500" />
        )}
        {summary.overall_status === 'warnings' && (
          <ExclamationTriangleIcon className="w-5 h-5 text-amber-500" />
        )}
        <span className={`text-sm font-medium ${statusConfig.color}`}>
          {statusConfig.label}
        </span>
        <span className="text-xs text-gray-500">
          ({summary.passed}/{summary.total} passed)
        </span>
      </div>
    );
  }

  return (
    <div className={`rounded-lg p-4 ${statusConfig.bgColor}`}>
      {/* Overall status */}
      <div className="flex items-center gap-2 mb-4">
        {summary.overall_status === 'passed' && (
          <CheckCircleIcon className={`w-6 h-6 ${statusConfig.iconColor}`} />
        )}
        {summary.overall_status === 'failed' && (
          <XCircleIcon className={`w-6 h-6 ${statusConfig.iconColor}`} />
        )}
        {summary.overall_status === 'warnings' && (
          <ExclamationTriangleIcon className={`w-6 h-6 ${statusConfig.iconColor}`} />
        )}
        <span className={`text-lg font-semibold ${statusConfig.color}`}>
          {statusConfig.label}
        </span>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-4 gap-4">
        {/* Passed */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-1.5">
            <CheckCircleIcon className="w-4 h-4 text-green-500" />
            <span className="text-2xl font-bold text-green-600">{summary.passed}</span>
          </div>
          <p className="text-xs text-gray-600 mt-1">Passed</p>
        </div>

        {/* Failed */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-1.5">
            <XCircleIcon className="w-4 h-4 text-red-500" />
            <span className="text-2xl font-bold text-red-600">{summary.failed}</span>
          </div>
          <p className="text-xs text-gray-600 mt-1">Errors</p>
        </div>

        {/* Warnings */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-1.5">
            <ExclamationTriangleIcon className="w-4 h-4 text-amber-500" />
            <span className="text-2xl font-bold text-amber-600">{summary.warnings}</span>
          </div>
          <p className="text-xs text-gray-600 mt-1">Warnings</p>
        </div>

        {/* Info */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-1.5">
            <InformationCircleIcon className="w-4 h-4 text-blue-500" />
            <span className="text-2xl font-bold text-blue-600">{summary.info}</span>
          </div>
          <p className="text-xs text-gray-600 mt-1">Info</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mt-4">
        <div className="h-2 bg-white rounded-full overflow-hidden flex">
          {summary.passed > 0 && (
            <div
              className="h-full bg-green-500"
              style={{ width: `${(summary.passed / summary.total) * 100}%` }}
            />
          )}
          {summary.failed > 0 && (
            <div
              className="h-full bg-red-500"
              style={{ width: `${(summary.failed / summary.total) * 100}%` }}
            />
          )}
          {summary.warnings > 0 && (
            <div
              className="h-full bg-amber-500"
              style={{ width: `${(summary.warnings / summary.total) * 100}%` }}
            />
          )}
          {summary.info > 0 && (
            <div
              className="h-full bg-blue-500"
              style={{ width: `${(summary.info / summary.total) * 100}%` }}
            />
          )}
        </div>
        <p className="text-xs text-gray-500 mt-1 text-center">
          {summary.passed} of {summary.total} checks passed
        </p>
      </div>
    </div>
  );
}

export default ComplianceSummary;
