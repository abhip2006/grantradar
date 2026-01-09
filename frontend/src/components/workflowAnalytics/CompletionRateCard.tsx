import { useMemo } from 'react';
import {
  CheckCircleIcon,
  ArrowTrendingUpIcon,
} from '@heroicons/react/24/outline';
import type { CompletionRatesResponse, CompletionRateData } from '../../types/workflowAnalytics';

interface CompletionRateCardProps {
  data: CompletionRatesResponse;
  isLoading?: boolean;
}

// Stage colors configuration
const STAGE_COLORS: Record<string, { color: string; bgColor: string; barColor: string }> = {
  researching: { color: 'text-cyan-600', bgColor: 'bg-cyan-50', barColor: 'bg-cyan-500' },
  writing: { color: 'text-amber-600', bgColor: 'bg-amber-50', barColor: 'bg-amber-500' },
  internal_review: { color: 'text-violet-600', bgColor: 'bg-violet-50', barColor: 'bg-violet-500' },
  submitted: { color: 'text-blue-600', bgColor: 'bg-blue-50', barColor: 'bg-blue-500' },
  under_review: { color: 'text-orange-600', bgColor: 'bg-orange-50', barColor: 'bg-orange-500' },
  awarded: { color: 'text-emerald-600', bgColor: 'bg-emerald-50', barColor: 'bg-emerald-500' },
};

const DEFAULT_COLORS = {
  color: 'text-gray-600',
  bgColor: 'bg-gray-50',
  barColor: 'bg-gray-500',
};

function getStageColors(stage: string) {
  return STAGE_COLORS[stage.toLowerCase()] || DEFAULT_COLORS;
}

function formatDays(days: number): string {
  if (days < 1) {
    return `${Math.round(days * 24)}h`;
  }
  return `${days.toFixed(1)}d`;
}

function ProgressRing({ percentage, size = 100, strokeWidth = 8 }: { percentage: number; size?: number; strokeWidth?: number }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;

  // Determine color based on percentage
  const getColor = () => {
    if (percentage >= 80) return '#22c55e'; // green-500
    if (percentage >= 60) return '#3b82f6'; // blue-500
    if (percentage >= 40) return '#f59e0b'; // amber-500
    return '#ef4444'; // red-500
  };

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--gr-border-subtle)"
          strokeWidth={strokeWidth}
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={getColor()}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-500 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-2xl font-display font-bold text-[var(--gr-text-primary)]">
          {percentage.toFixed(0)}%
        </span>
      </div>
    </div>
  );
}

function StageCompletionBar({ stage }: { stage: CompletionRateData }) {
  const colors = getStageColors(stage.stage);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-medium ${colors.color}`}>
            {stage.stage_label}
          </span>
          <span className="text-xs text-[var(--gr-text-tertiary)]">
            {stage.completed}/{stage.started}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[var(--gr-text-primary)]">
            {stage.completion_rate.toFixed(0)}%
          </span>
          {stage.avg_days_to_complete > 0 && (
            <span className="text-xs text-[var(--gr-text-tertiary)]">
              ({formatDays(stage.avg_days_to_complete)} avg)
            </span>
          )}
        </div>
      </div>
      <div className="h-2 bg-[var(--gr-bg-secondary)] rounded-full overflow-hidden">
        <div
          className={`h-full ${colors.barColor} rounded-full transition-all duration-500`}
          style={{ width: `${stage.completion_rate}%` }}
        />
      </div>
    </div>
  );
}

export function CompletionRateCard({ data, isLoading }: CompletionRateCardProps) {
  // Sort stages by typical workflow order
  const sortedStages = useMemo(() => {
    const order = ['researching', 'writing', 'internal_review', 'submitted', 'under_review', 'awarded'];
    return [...data.rates].sort((a, b) => {
      const aIndex = order.indexOf(a.stage.toLowerCase());
      const bIndex = order.indexOf(b.stage.toLowerCase());
      return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
    });
  }, [data.rates]);

  // Calculate overall metrics
  const overallMetrics = useMemo(() => {
    const highestRate = Math.max(...data.rates.map((r) => r.completion_rate), 0);
    const lowestRate = Math.min(...data.rates.map((r) => r.completion_rate), 100);
    const avgRate = data.rates.reduce((sum, r) => sum + r.completion_rate, 0) / data.rates.length || 0;

    return { highestRate, lowestRate, avgRate };
  }, [data.rates]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <div className="animate-pulse">
          <div className="h-6 w-48 bg-gray-200 rounded mb-6"></div>
          <div className="flex justify-center mb-6">
            <div className="w-24 h-24 rounded-full bg-gray-100"></div>
          </div>
          <div className="space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="space-y-2">
                <div className="h-4 bg-gray-200 rounded w-full"></div>
                <div className="h-2 bg-gray-100 rounded"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (data.rates.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <div className="flex items-center gap-2 mb-4">
          <CheckCircleIcon className="h-5 w-5 text-[var(--gr-text-tertiary)]" />
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
            Completion Rates
          </h3>
        </div>
        <div className="flex items-center justify-center h-48 text-[var(--gr-text-tertiary)]">
          No completion data available yet.
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <ArrowTrendingUpIcon className="h-5 w-5 text-[var(--gr-text-tertiary)]" />
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
            Completion Rates
          </h3>
        </div>
        <span className="text-xs text-[var(--gr-text-tertiary)]">
          {data.total_started} started / {data.total_completed} completed
        </span>
      </div>

      {/* Overall completion rate ring */}
      <div className="flex justify-center mb-6">
        <div className="text-center">
          <ProgressRing percentage={data.overall_completion_rate} size={120} />
          <p className="text-sm text-[var(--gr-text-secondary)] mt-2">Overall Completion</p>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="bg-emerald-50 rounded-lg p-3 text-center">
          <p className="text-lg font-display font-bold text-emerald-600">
            {overallMetrics.highestRate.toFixed(0)}%
          </p>
          <p className="text-xs text-[var(--gr-text-tertiary)]">Highest</p>
        </div>
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <p className="text-lg font-display font-bold text-blue-600">
            {overallMetrics.avgRate.toFixed(0)}%
          </p>
          <p className="text-xs text-[var(--gr-text-tertiary)]">Average</p>
        </div>
        <div className="bg-amber-50 rounded-lg p-3 text-center">
          <p className="text-lg font-display font-bold text-amber-600">
            {overallMetrics.lowestRate.toFixed(0)}%
          </p>
          <p className="text-xs text-[var(--gr-text-tertiary)]">Lowest</p>
        </div>
      </div>

      {/* Stage-by-stage breakdown */}
      <div className="space-y-4">
        <h4 className="text-sm font-medium text-[var(--gr-text-secondary)]">By Stage</h4>
        {sortedStages.map((stage) => (
          <StageCompletionBar key={stage.stage} stage={stage} />
        ))}
      </div>
    </div>
  );
}

export default CompletionRateCard;
