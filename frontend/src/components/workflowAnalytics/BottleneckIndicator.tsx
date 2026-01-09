import { useMemo } from 'react';
import {
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
  InformationCircleIcon,
  CheckCircleIcon,
  LightBulbIcon,
} from '@heroicons/react/24/outline';
import type { Bottleneck, BottlenecksResponse } from '../../types/workflowAnalytics';

interface BottleneckIndicatorProps {
  data: BottlenecksResponse;
  isLoading?: boolean;
  compact?: boolean;
}

// Severity configuration
const SEVERITY_CONFIG: Record<
  Bottleneck['severity'],
  {
    label: string;
    color: string;
    bgColor: string;
    borderColor: string;
    icon: React.ReactNode;
    pulseClass: string;
  }
> = {
  critical: {
    label: 'Critical',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    icon: <ExclamationCircleIcon className="h-5 w-5 text-red-500" />,
    pulseClass: 'animate-pulse',
  },
  high: {
    label: 'High',
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    icon: <ExclamationTriangleIcon className="h-5 w-5 text-orange-500" />,
    pulseClass: '',
  },
  medium: {
    label: 'Medium',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    icon: <InformationCircleIcon className="h-5 w-5 text-amber-500" />,
    pulseClass: '',
  },
  low: {
    label: 'Low',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    icon: <InformationCircleIcon className="h-5 w-5 text-blue-500" />,
    pulseClass: '',
  },
};

function BottleneckCard({ bottleneck }: { bottleneck: Bottleneck }) {
  const config = SEVERITY_CONFIG[bottleneck.severity];

  return (
    <div
      className={`
        rounded-xl border-2 p-4 transition-all hover:shadow-md
        ${config.bgColor} ${config.borderColor} ${config.pulseClass}
      `}
    >
      <div className="flex items-start gap-3">
        <div className={`flex-shrink-0 mt-0.5`}>{config.icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1">
            <h4 className={`text-sm font-semibold ${config.color}`}>
              {bottleneck.stage_label}
            </h4>
            <span
              className={`
                inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
                ${config.bgColor} ${config.color} border ${config.borderColor}
              `}
            >
              {config.label}
            </span>
          </div>
          <p className="text-sm text-[var(--gr-text-secondary)] mb-2">
            {bottleneck.description}
          </p>
          <div className="flex items-center gap-4 text-xs text-[var(--gr-text-tertiary)] mb-3">
            <span>
              <strong className={config.color}>{bottleneck.avg_delay_days.toFixed(1)}</strong> days avg delay
            </span>
            <span>
              <strong className={config.color}>{bottleneck.affected_applications}</strong> applications affected
            </span>
          </div>
          <div className="flex items-start gap-2 pt-2 border-t border-[var(--gr-border-subtle)]">
            <LightBulbIcon className="h-4 w-4 text-[var(--gr-text-tertiary)] flex-shrink-0 mt-0.5" />
            <p className="text-xs text-[var(--gr-text-secondary)]">
              {bottleneck.recommendation}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function CompactBottleneckItem({ bottleneck }: { bottleneck: Bottleneck }) {
  const config = SEVERITY_CONFIG[bottleneck.severity];

  return (
    <div
      className={`
        flex items-center gap-3 rounded-lg p-3 transition-all
        ${config.bgColor} border ${config.borderColor}
      `}
    >
      <div className="flex-shrink-0">{config.icon}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <span className={`text-sm font-medium ${config.color}`}>
            {bottleneck.stage_label}
          </span>
          <span className="text-xs text-[var(--gr-text-tertiary)]">
            {bottleneck.avg_delay_days.toFixed(1)}d delay
          </span>
        </div>
        <p className="text-xs text-[var(--gr-text-secondary)] truncate">
          {bottleneck.affected_applications} applications affected
        </p>
      </div>
    </div>
  );
}

function BottleneckSummary({ data }: { data: BottlenecksResponse }) {
  const severityCounts = useMemo(() => {
    return data.bottlenecks.reduce(
      (acc, b) => {
        acc[b.severity] = (acc[b.severity] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );
  }, [data.bottlenecks]);

  return (
    <div className="grid grid-cols-4 gap-3 mb-4">
      {(['critical', 'high', 'medium', 'low'] as const).map((severity) => {
        const config = SEVERITY_CONFIG[severity];
        const count = severityCounts[severity] || 0;
        return (
          <div
            key={severity}
            className={`
              rounded-lg p-3 text-center border
              ${config.bgColor} ${config.borderColor}
            `}
          >
            <p className={`text-2xl font-display font-bold ${config.color}`}>
              {count}
            </p>
            <p className="text-xs text-[var(--gr-text-tertiary)]">{config.label}</p>
          </div>
        );
      })}
    </div>
  );
}

export function BottleneckIndicator({ data, isLoading, compact = false }: BottleneckIndicatorProps) {
  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <div className="animate-pulse">
          <div className="h-6 w-48 bg-gray-200 rounded mb-4"></div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 bg-gray-100 rounded-xl"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (data.bottlenecks.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <div className="flex items-center gap-2 mb-4">
          <CheckCircleIcon className="h-5 w-5 text-emerald-500" />
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
            Workflow Bottlenecks
          </h3>
        </div>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="w-16 h-16 rounded-full bg-emerald-50 flex items-center justify-center mb-4">
            <CheckCircleIcon className="h-8 w-8 text-emerald-500" />
          </div>
          <p className="text-[var(--gr-text-primary)] font-medium mb-1">
            No bottlenecks detected
          </p>
          <p className="text-sm text-[var(--gr-text-tertiary)]">
            Your workflow is running smoothly
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ExclamationTriangleIcon className="h-5 w-5 text-amber-500" />
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
            Workflow Bottlenecks
          </h3>
        </div>
        {data.critical_count > 0 && (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 animate-pulse">
            {data.critical_count} critical
          </span>
        )}
      </div>

      {!compact && <BottleneckSummary data={data} />}

      <div className={compact ? 'space-y-2' : 'space-y-4'}>
        {data.bottlenecks.map((bottleneck) =>
          compact ? (
            <CompactBottleneckItem key={bottleneck.id} bottleneck={bottleneck} />
          ) : (
            <BottleneckCard key={bottleneck.id} bottleneck={bottleneck} />
          )
        )}
      </div>
    </div>
  );
}

export default BottleneckIndicator;
