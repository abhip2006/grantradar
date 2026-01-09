import { useMemo } from 'react';
import {
  FunnelChart,
  Funnel,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import type { PipelineMetricsResponse } from '../../types';

interface StageConversionFunnelProps {
  data: PipelineMetricsResponse;
}

// Stage colors matching the design system
const STAGE_COLORS: Record<string, string> = {
  researching: '#06b6d4', // cyan-500
  writing: '#f59e0b', // amber-500
  submitted: '#2d5a47', // forest-500
  awarded: '#22c55e', // green-500
  rejected: '#64748b', // slate-500
};

const STAGE_LABELS: Record<string, string> = {
  researching: 'Researching',
  writing: 'Writing',
  submitted: 'Submitted',
  awarded: 'Awarded',
  rejected: 'Rejected',
};

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: {
      name: string;
      value: number;
      conversionRate?: number;
    };
  }>;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;
  return (
    <div className="bg-white border border-[var(--gr-border-default)] rounded-lg shadow-lg p-3">
      <p className="text-sm font-medium text-[var(--gr-text-primary)]">{data.name}</p>
      <p className="text-sm text-[var(--gr-text-secondary)]">
        Count: {data.value}
      </p>
      {data.conversionRate !== undefined && (
        <p className="text-sm text-[var(--gr-text-secondary)]">
          Conversion: {data.conversionRate.toFixed(1)}%
        </p>
      )}
    </div>
  );
}

export function StageConversionFunnel({ data }: StageConversionFunnelProps) {
  // Filter out rejected for the funnel view (show separately)
  const funnelData = useMemo(() => {
    const funnelStages = data.stages
      .filter((s) => s.stage !== 'rejected')
      .map((stage) => ({
        name: STAGE_LABELS[stage.stage] || stage.stage,
        value: stage.count,
        fill: STAGE_COLORS[stage.stage] || '#64748b',
        conversionRate: stage.conversion_rate,
        stage: stage.stage,
      }));

    return funnelStages;
  }, [data.stages]);

  const rejectedStage = useMemo(() => {
    return data.stages.find((s) => s.stage === 'rejected');
  }, [data.stages]);

  if (data.total_in_pipeline === 0) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-4">
          Conversion Funnel
        </h3>
        <div className="flex items-center justify-center h-64 text-[var(--gr-text-tertiary)]">
          No applications in pipeline yet. Add grants to see your conversion funnel.
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
          Conversion Funnel
        </h3>
        <div className="flex items-center gap-4">
          <div className="text-sm text-[var(--gr-text-secondary)]">
            Total: <span className="font-medium text-[var(--gr-text-primary)]">{data.total_in_pipeline}</span>
          </div>
          <div className="text-sm text-[var(--gr-text-secondary)]">
            Conversion:{' '}
            <span className="font-medium text-emerald-600">{data.overall_conversion_rate.toFixed(1)}%</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Funnel Chart */}
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <FunnelChart>
              <Tooltip content={<CustomTooltip />} />
              <Funnel
                dataKey="value"
                data={funnelData}
                isAnimationActive
              >
                <LabelList
                  position="right"
                  fill="#374151"
                  stroke="none"
                  dataKey="name"
                  fontSize={13}
                  fontWeight={500}
                />
                <LabelList
                  position="center"
                  fill="#fff"
                  stroke="none"
                  dataKey="value"
                  fontSize={16}
                  fontWeight={600}
                />
                {funnelData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Funnel>
            </FunnelChart>
          </ResponsiveContainer>
        </div>

        {/* Stage Details */}
        <div className="space-y-3">
          {funnelData.map((stage, index) => {
            const prevCount = index > 0 ? funnelData[index - 1].value : null;
            const dropoff = prevCount && prevCount > 0 ? prevCount - stage.value : null;
            const dropoffPercent = prevCount && prevCount > 0 ? ((dropoff || 0) / prevCount) * 100 : null;

            return (
              <div
                key={stage.stage}
                className="flex items-center justify-between p-3 rounded-lg bg-[var(--gr-bg-secondary)] border border-[var(--gr-border-subtle)]"
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: stage.fill }}
                  />
                  <div>
                    <p className="text-sm font-medium text-[var(--gr-text-primary)]">
                      {stage.name}
                    </p>
                    {dropoff !== null && dropoff > 0 && (
                      <p className="text-xs text-[var(--gr-text-tertiary)]">
                        -{dropoff} ({dropoffPercent?.toFixed(0)}% drop)
                      </p>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-semibold text-[var(--gr-text-primary)]">
                    {stage.value}
                  </p>
                  {stage.conversionRate !== undefined && (
                    <p className="text-xs text-[var(--gr-text-tertiary)]">
                      {stage.conversionRate.toFixed(0)}% conversion
                    </p>
                  )}
                </div>
              </div>
            );
          })}

          {/* Rejected section */}
          {rejectedStage && rejectedStage.count > 0 && (
            <div className="mt-4 pt-4 border-t border-[var(--gr-border-subtle)]">
              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200">
                <div className="flex items-center gap-3">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: STAGE_COLORS.rejected }}
                  />
                  <div>
                    <p className="text-sm font-medium text-slate-600">
                      Rejected
                    </p>
                    <p className="text-xs text-slate-500">
                      Did not receive funding
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-semibold text-slate-600">
                    {rejectedStage.count}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default StageConversionFunnel;
