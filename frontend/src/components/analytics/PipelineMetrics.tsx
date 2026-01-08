import { useMemo } from 'react';
import {
  ArrowDownIcon,
  ArrowRightIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import type { PipelineMetricsResponse, PipelineStageMetric } from '../../types';

interface PipelineMetricsProps {
  data: PipelineMetricsResponse;
}

// Stage configuration matching pipeline design
const STAGE_CONFIG: Record<string, { label: string; color: string; bgColor: string; borderColor: string; icon?: React.ReactNode }> = {
  researching: {
    label: 'Researching',
    color: 'text-cyan-600',
    bgColor: 'bg-cyan-50',
    borderColor: 'border-cyan-200',
  },
  writing: {
    label: 'Writing',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
  },
  submitted: {
    label: 'Submitted',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
  awarded: {
    label: 'Awarded',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    icon: <CheckCircleIcon className="h-5 w-5 text-emerald-500" />,
  },
  rejected: {
    label: 'Rejected',
    color: 'text-slate-500',
    bgColor: 'bg-slate-50',
    borderColor: 'border-slate-200',
    icon: <XCircleIcon className="h-5 w-5 text-slate-400" />,
  },
};

// Vertical funnel stage component (kept for potential use)
function _FunnelStage({
  stage,
  maxCount,
  isLast,
}: {
  stage: PipelineStageMetric;
  maxCount: number;
  isLast: boolean;
}) {
  const config = STAGE_CONFIG[stage.stage] || {
    label: stage.stage,
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
  };

  // Calculate width percentage for funnel visualization
  const widthPercent = maxCount > 0 ? Math.max((stage.count / maxCount) * 100, 20) : 20;

  return (
    <div className="flex flex-col items-center">
      {/* Stage box */}
      <div
        className={`
          relative rounded-xl border-2 p-4 transition-all
          ${config.bgColor} ${config.borderColor}
        `}
        style={{ width: `${widthPercent}%`, minWidth: '140px' }}
      >
        <div className="text-center">
          <div className="flex items-center justify-center gap-2 mb-1">
            {config.icon}
            <span className={`text-sm font-medium ${config.color}`}>
              {config.label}
            </span>
          </div>
          <div className={`text-3xl font-display font-bold ${config.color}`}>
            {stage.count}
          </div>
          {stage.avg_days_in_stage && (
            <div className="text-xs text-[var(--gr-text-tertiary)] mt-1">
              ~{stage.avg_days_in_stage.toFixed(0)} days avg
            </div>
          )}
        </div>
      </div>

      {/* Arrow and conversion rate to next stage */}
      {!isLast && stage.stage !== 'rejected' && (
        <div className="flex flex-col items-center my-2">
          <ArrowDownIcon className="h-5 w-5 text-[var(--gr-text-tertiary)]" />
          {stage.conversion_rate !== null && stage.conversion_rate !== undefined && (
            <div className="text-xs font-medium text-[var(--gr-text-secondary)] bg-[var(--gr-bg-secondary)] px-2 py-0.5 rounded-full mt-1">
              {stage.conversion_rate.toFixed(0)}%
            </div>
          )}
        </div>
      )}
    </div>
  );
}
// Export to prevent unused warning (can be used for vertical funnel layout)
export { _FunnelStage };

function HorizontalFunnel({ stages }: { stages: PipelineStageMetric[]; maxCount: number }) {
  // Filter to show main funnel stages (exclude rejected)
  const funnelStages = stages.filter(s => s.stage !== 'rejected');
  const rejectedStage = stages.find(s => s.stage === 'rejected');

  return (
    <div className="space-y-6">
      {/* Main horizontal funnel */}
      <div className="flex items-center justify-center gap-2 flex-wrap">
        {funnelStages.map((stage, index) => {
          const config = STAGE_CONFIG[stage.stage] || {
            label: stage.stage,
            color: 'text-gray-600',
            bgColor: 'bg-gray-50',
            borderColor: 'border-gray-200',
          };

          const isLast = index === funnelStages.length - 1;

          return (
            <div key={stage.stage} className="flex items-center">
              <div
                className={`
                  rounded-xl border-2 p-4 transition-all
                  ${config.bgColor} ${config.borderColor}
                `}
                style={{ minWidth: '120px' }}
              >
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    {config.icon}
                    <span className={`text-xs font-medium ${config.color}`}>
                      {config.label}
                    </span>
                  </div>
                  <div className={`text-2xl font-display font-bold ${config.color}`}>
                    {stage.count}
                  </div>
                </div>
              </div>

              {!isLast && (
                <div className="flex flex-col items-center mx-2">
                  <ArrowRightIcon className="h-5 w-5 text-[var(--gr-text-tertiary)]" />
                  {stage.conversion_rate !== null && stage.conversion_rate !== undefined && (
                    <div className="text-xs font-medium text-[var(--gr-blue-600)] mt-0.5">
                      {stage.conversion_rate.toFixed(0)}%
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Rejected section */}
      {rejectedStage && rejectedStage.count > 0 && (
        <div className="flex justify-center">
          <div className="bg-slate-50 border-2 border-slate-200 rounded-xl p-4 text-center min-w-[120px]">
            <div className="flex items-center justify-center gap-1 mb-1">
              <XCircleIcon className="h-4 w-4 text-slate-400" />
              <span className="text-xs font-medium text-slate-500">Rejected</span>
            </div>
            <div className="text-2xl font-display font-bold text-slate-500">
              {rejectedStage.count}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ConversionRateBar({ label, rate, color }: { label: string; rate: number; color: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="w-32 text-sm text-[var(--gr-text-secondary)]">{label}</div>
      <div className="flex-1 h-6 bg-[var(--gr-bg-secondary)] rounded-full overflow-hidden">
        <div
          className={`h-full ${color} transition-all duration-500`}
          style={{ width: `${rate}%` }}
        />
      </div>
      <div className="w-16 text-sm font-medium text-[var(--gr-text-primary)] text-right">
        {rate.toFixed(1)}%
      </div>
    </div>
  );
}

export function PipelineMetrics({ data }: PipelineMetricsProps) {
  const maxCount = useMemo(() => {
    return Math.max(...data.stages.map(s => s.count), 1);
  }, [data.stages]);

  // Calculate stage-to-stage conversion rates
  const conversionRates = useMemo(() => {
    const rates: { label: string; rate: number }[] = [];
    const orderedStages = ['researching', 'writing', 'submitted', 'awarded'];

    for (let i = 0; i < orderedStages.length - 1; i++) {
      const currentStage = data.stages.find(s => s.stage === orderedStages[i]);
      const nextStage = data.stages.find(s => s.stage === orderedStages[i + 1]);

      if (currentStage && nextStage && currentStage.count > 0) {
        const rate = (nextStage.count / currentStage.count) * 100;
        rates.push({
          label: `${STAGE_CONFIG[orderedStages[i]]?.label || orderedStages[i]} -> ${STAGE_CONFIG[orderedStages[i + 1]]?.label || orderedStages[i + 1]}`,
          rate: Math.min(rate, 100),
        });
      }
    }

    return rates;
  }, [data.stages]);

  if (data.total_in_pipeline === 0) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-4">
          Pipeline Funnel
        </h3>
        <div className="flex items-center justify-center h-64 text-[var(--gr-text-tertiary)]">
          No applications in pipeline yet. Add grants to track your progress.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-4">
          <p className="text-xs font-medium text-[var(--gr-text-tertiary)] mb-1">
            Total in Pipeline
          </p>
          <p className="text-3xl font-display font-bold text-[var(--gr-text-primary)]">
            {data.total_in_pipeline}
          </p>
        </div>

        <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-4">
          <p className="text-xs font-medium text-[var(--gr-text-tertiary)] mb-1">
            Overall Conversion
          </p>
          <p className="text-3xl font-display font-bold text-emerald-600">
            {data.overall_conversion_rate.toFixed(1)}%
          </p>
          <p className="text-xs text-[var(--gr-text-tertiary)]">
            Researching to Awarded
          </p>
        </div>

        {data.avg_time_to_award && (
          <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-4">
            <p className="text-xs font-medium text-[var(--gr-text-tertiary)] mb-1">
              Avg. Time to Award
            </p>
            <p className="text-3xl font-display font-bold text-blue-600">
              {data.avg_time_to_award.toFixed(0)}
            </p>
            <p className="text-xs text-[var(--gr-text-tertiary)]">days</p>
          </div>
        )}
      </div>

      {/* Funnel visualization */}
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-6">
          Pipeline Funnel
        </h3>
        <HorizontalFunnel stages={data.stages} maxCount={maxCount} />
      </div>

      {/* Conversion rate bars */}
      {conversionRates.length > 0 && (
        <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-4">
            Stage Conversion Rates
          </h3>
          <div className="space-y-3">
            {conversionRates.map((item, index) => (
              <ConversionRateBar
                key={index}
                label={item.label}
                rate={item.rate}
                color={index === conversionRates.length - 1 ? 'bg-emerald-500' : 'bg-blue-500'}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default PipelineMetrics;
