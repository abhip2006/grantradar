import { useMemo } from 'react';
import {
  ExclamationCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  CheckCircleIcon,
  CalendarDaysIcon,
  ChevronRightIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';
import type { DeadlineRiskForecastResponse, DeadlineRisk } from '../../types/workflowAnalytics';

interface DeadlineRiskForecastProps {
  data: DeadlineRiskForecastResponse;
  isLoading?: boolean;
  onApplicationClick?: (cardId: string) => void;
}

// Risk level configuration
const RISK_CONFIG: Record<
  DeadlineRisk['risk_level'],
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
    label: 'High Risk',
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    icon: <ExclamationTriangleIcon className="h-5 w-5 text-orange-500" />,
    pulseClass: '',
  },
  medium: {
    label: 'Medium Risk',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    icon: <ClockIcon className="h-5 w-5 text-amber-500" />,
    pulseClass: '',
  },
  low: {
    label: 'Low Risk',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    icon: <CheckCircleIcon className="h-5 w-5 text-green-500" />,
    pulseClass: '',
  },
};

// Stage labels
const STAGE_LABELS: Record<string, string> = {
  researching: 'Researching',
  writing: 'Writing',
  internal_review: 'Internal Review',
  submitted: 'Submitted',
  under_review: 'Under Review',
  awarded: 'Awarded',
};

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatDaysRemaining(days: number): string {
  if (days < 0) return `${Math.abs(days)} days overdue`;
  if (days === 0) return 'Due today';
  if (days === 1) return '1 day left';
  return `${days} days left`;
}

function RiskScoreGauge({ score }: { score: number }) {
  // Score 0-100, higher = more risky
  const getColor = () => {
    if (score >= 75) return '#ef4444'; // red-500
    if (score >= 50) return '#f97316'; // orange-500
    if (score >= 25) return '#f59e0b'; // amber-500
    return '#22c55e'; // green-500
  };

  const rotation = (score / 100) * 180 - 90;

  return (
    <div className="relative w-16 h-8 overflow-hidden">
      {/* Background arc */}
      <div className="absolute bottom-0 left-0 w-16 h-16 rounded-full border-4 border-gray-200" />
      {/* Colored arc */}
      <div
        className="absolute bottom-0 left-0 w-16 h-16 rounded-full border-4 border-transparent"
        style={{
          borderTopColor: getColor(),
          borderRightColor: getColor(),
          transform: 'rotate(-45deg)',
          clipPath: 'polygon(0 50%, 100% 50%, 100% 0, 0 0)',
        }}
      />
      {/* Needle */}
      <div
        className="absolute bottom-0 left-1/2 w-0.5 h-6 origin-bottom bg-gray-800"
        style={{
          transform: `translateX(-50%) rotate(${rotation}deg)`,
          transition: 'transform 0.5s ease-out',
        }}
      />
      {/* Center dot */}
      <div className="absolute bottom-0 left-1/2 w-2 h-2 -translate-x-1/2 translate-y-1/2 rounded-full bg-gray-800" />
    </div>
  );
}

function RiskCard({
  risk,
  onApplicationClick,
}: {
  risk: DeadlineRisk;
  onApplicationClick?: (cardId: string) => void;
}) {
  const config = RISK_CONFIG[risk.risk_level];

  return (
    <div
      className={`
        rounded-xl border-2 p-4 transition-all
        ${config.bgColor} ${config.borderColor} ${config.pulseClass}
        ${onApplicationClick ? 'cursor-pointer hover:shadow-md' : ''}
      `}
      onClick={() => onApplicationClick?.(risk.card_id)}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">{config.icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="min-w-0">
              <h4 className="text-sm font-semibold text-[var(--gr-text-primary)] truncate">
                {risk.grant_title}
              </h4>
              <div className="flex items-center gap-2 mt-0.5">
                <span
                  className={`
                    inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
                    ${config.bgColor} ${config.color} border ${config.borderColor}
                  `}
                >
                  {config.label}
                </span>
                <span className="text-xs text-[var(--gr-text-tertiary)]">
                  {STAGE_LABELS[risk.current_stage] || risk.current_stage}
                </span>
              </div>
            </div>
            {onApplicationClick && (
              <ChevronRightIcon className="h-5 w-5 text-[var(--gr-text-tertiary)] flex-shrink-0" />
            )}
          </div>

          <div className="flex items-center gap-4 text-xs text-[var(--gr-text-secondary)] mb-3">
            <div className="flex items-center gap-1">
              <CalendarDaysIcon className="h-4 w-4" />
              <span>{formatDate(risk.deadline)}</span>
            </div>
            <span className={risk.days_remaining <= 0 ? 'text-red-600 font-medium' : ''}>
              {formatDaysRemaining(risk.days_remaining)}
            </span>
          </div>

          {/* Risk factors */}
          {risk.risk_factors.length > 0 && (
            <div className="mb-3">
              <p className="text-xs font-medium text-[var(--gr-text-tertiary)] mb-1">
                Risk factors:
              </p>
              <div className="flex flex-wrap gap-1">
                {risk.risk_factors.slice(0, 3).map((factor, index) => (
                  <span
                    key={index}
                    className="inline-flex px-2 py-0.5 rounded text-xs bg-white/60 text-[var(--gr-text-secondary)]"
                  >
                    {factor}
                  </span>
                ))}
                {risk.risk_factors.length > 3 && (
                  <span className="text-xs text-[var(--gr-text-tertiary)]">
                    +{risk.risk_factors.length - 3} more
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Recommendation */}
          <div className="pt-2 border-t border-[var(--gr-border-subtle)]">
            <p className="text-xs text-[var(--gr-text-secondary)]">
              <span className="font-medium">Recommendation:</span> {risk.recommendation}
            </p>
          </div>

          {/* Predicted completion */}
          {risk.predicted_completion_date && (
            <div className="mt-2 text-xs text-[var(--gr-text-tertiary)]">
              Predicted completion: {formatDate(risk.predicted_completion_date)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function RiskSummaryBar({ data }: { data: DeadlineRiskForecastResponse }) {
  return (
    <div className="grid grid-cols-4 gap-3 mb-4">
      <div className="bg-red-50 rounded-lg p-3 text-center border border-red-200">
        <p className="text-2xl font-display font-bold text-red-600">{data.critical_count}</p>
        <p className="text-xs text-[var(--gr-text-tertiary)]">Critical</p>
      </div>
      <div className="bg-orange-50 rounded-lg p-3 text-center border border-orange-200">
        <p className="text-2xl font-display font-bold text-orange-600">{data.high_risk_count}</p>
        <p className="text-xs text-[var(--gr-text-tertiary)]">High</p>
      </div>
      <div className="bg-amber-50 rounded-lg p-3 text-center border border-amber-200">
        <p className="text-2xl font-display font-bold text-amber-600">{data.medium_risk_count}</p>
        <p className="text-xs text-[var(--gr-text-tertiary)]">Medium</p>
      </div>
      <div className="bg-green-50 rounded-lg p-3 text-center border border-green-200">
        <p className="text-2xl font-display font-bold text-green-600">{data.safe.length}</p>
        <p className="text-xs text-[var(--gr-text-tertiary)]">Safe</p>
      </div>
    </div>
  );
}

export function DeadlineRiskForecast({
  data,
  isLoading,
  onApplicationClick,
}: DeadlineRiskForecastProps) {
  // Sort at-risk applications by risk score (highest first)
  const sortedAtRisk = useMemo(() => {
    return [...data.at_risk].sort((a, b) => b.risk_score - a.risk_score);
  }, [data.at_risk]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <div className="animate-pulse">
          <div className="h-6 w-48 bg-gray-200 rounded mb-4"></div>
          <div className="grid grid-cols-4 gap-3 mb-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-16 bg-gray-100 rounded-lg"></div>
            ))}
          </div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 bg-gray-100 rounded-xl"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const hasAtRiskApplications = data.at_risk.length > 0;

  return (
    <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {hasAtRiskApplications ? (
            <ExclamationTriangleIcon className="h-5 w-5 text-amber-500" />
          ) : (
            <ShieldCheckIcon className="h-5 w-5 text-emerald-500" />
          )}
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
            Deadline Risk Forecast
          </h3>
        </div>
        <span className="text-xs text-[var(--gr-text-tertiary)]">
          {data.total_applications} applications tracked
        </span>
      </div>

      <RiskSummaryBar data={data} />

      {!hasAtRiskApplications ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="w-16 h-16 rounded-full bg-emerald-50 flex items-center justify-center mb-4">
            <ShieldCheckIcon className="h-8 w-8 text-emerald-500" />
          </div>
          <p className="text-[var(--gr-text-primary)] font-medium mb-1">
            All deadlines on track
          </p>
          <p className="text-sm text-[var(--gr-text-tertiary)]">
            No applications are at risk of missing their deadlines
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-[var(--gr-text-secondary)]">
            At-Risk Applications
          </h4>
          {sortedAtRisk.map((risk) => (
            <RiskCard
              key={risk.card_id}
              risk={risk}
              onApplicationClick={onApplicationClick}
            />
          ))}
        </div>
      )}

      {/* Show safe applications count if there are at-risk ones */}
      {hasAtRiskApplications && data.safe.length > 0 && (
        <div className="mt-4 pt-4 border-t border-[var(--gr-border-subtle)]">
          <p className="text-sm text-[var(--gr-text-secondary)]">
            <CheckCircleIcon className="h-4 w-4 text-emerald-500 inline mr-1" />
            {data.safe.length} application{data.safe.length !== 1 ? 's' : ''} on track
          </p>
        </div>
      )}
    </div>
  );
}

export default DeadlineRiskForecast;
