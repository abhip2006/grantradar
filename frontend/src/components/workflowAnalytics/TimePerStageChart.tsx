import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend,
} from 'recharts';
import { ClockIcon } from '@heroicons/react/24/outline';
import type { TimePerStageResponse, TimePerStage } from '../../types/workflowAnalytics';

interface TimePerStageChartProps {
  data: TimePerStageResponse;
  isLoading?: boolean;
}

// Stage colors configuration
const STAGE_COLORS: Record<string, string> = {
  researching: '#06b6d4', // cyan-500
  writing: '#f59e0b', // amber-500
  internal_review: '#8b5cf6', // violet-500
  submitted: '#3b82f6', // blue-500
  under_review: '#f97316', // orange-500
  awarded: '#22c55e', // green-500
  rejected: '#64748b', // slate-500
};

const DEFAULT_COLOR = '#9ca3af'; // gray-400

function getStageColor(stage: string): string {
  return STAGE_COLORS[stage.toLowerCase()] || DEFAULT_COLOR;
}

function formatDays(days: number): string {
  if (days < 1) {
    return `${Math.round(days * 24)}h`;
  }
  return `${days.toFixed(1)}d`;
}

interface TooltipPayload {
  payload?: TimePerStage;
  active?: boolean;
}

function CustomTooltip({ active, payload }: TooltipPayload & { payload?: Array<{ payload: TimePerStage }> }) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;
  return (
    <div className="bg-white border border-[var(--gr-border-default)] rounded-lg shadow-lg p-3 min-w-[180px]">
      <p className="text-sm font-medium text-[var(--gr-text-primary)] mb-2">
        {data.stage_label}
      </p>
      <div className="space-y-1.5 text-sm">
        <div className="flex justify-between">
          <span className="text-[var(--gr-text-secondary)]">Average:</span>
          <span className="font-medium text-[var(--gr-text-primary)]">{formatDays(data.avg_days)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-[var(--gr-text-secondary)]">Median:</span>
          <span className="font-medium text-[var(--gr-text-primary)]">{formatDays(data.median_days)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-[var(--gr-text-secondary)]">Min:</span>
          <span className="font-medium text-[var(--gr-text-primary)]">{formatDays(data.min_days)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-[var(--gr-text-secondary)]">Max:</span>
          <span className="font-medium text-[var(--gr-text-primary)]">{formatDays(data.max_days)}</span>
        </div>
        <div className="flex justify-between pt-1 border-t border-[var(--gr-border-subtle)]">
          <span className="text-[var(--gr-text-secondary)]">Applications:</span>
          <span className="font-medium text-[var(--gr-text-primary)]">{data.count}</span>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, subValue }: { label: string; value: string; subValue?: string }) {
  return (
    <div className="bg-[var(--gr-bg-secondary)] rounded-lg p-4">
      <p className="text-xs font-medium text-[var(--gr-text-tertiary)] mb-1">{label}</p>
      <p className="text-2xl font-display font-bold text-[var(--gr-text-primary)]">{value}</p>
      {subValue && (
        <p className="text-xs text-[var(--gr-text-secondary)] mt-0.5">{subValue}</p>
      )}
    </div>
  );
}

export const TimePerStageChart = React.memo(function TimePerStageChart({ data, isLoading }: TimePerStageChartProps) {
  const chartData = useMemo(() => {
    return data.stages.map((stage) => ({
      ...stage,
      color: getStageColor(stage.stage),
    }));
  }, [data.stages]);

  // Calculate summary stats
  const totalAvgTime = useMemo(() => {
    return data.stages.reduce((sum, stage) => sum + stage.avg_days, 0);
  }, [data.stages]);

  const slowestStage = useMemo(() => {
    return data.stages.reduce((prev, current) =>
      current.avg_days > prev.avg_days ? current : prev
    );
  }, [data.stages]);

  const fastestStage = useMemo(() => {
    return data.stages.reduce((prev, current) =>
      current.avg_days < prev.avg_days ? current : prev
    );
  }, [data.stages]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <div className="animate-pulse">
          <div className="h-6 w-48 bg-gray-200 rounded mb-6"></div>
          <div className="h-64 bg-gray-100 rounded"></div>
        </div>
      </div>
    );
  }

  if (data.stages.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <div className="flex items-center gap-2 mb-4">
          <ClockIcon className="h-5 w-5 text-[var(--gr-text-tertiary)]" />
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
            Time Per Stage
          </h3>
        </div>
        <div className="flex items-center justify-center h-64 text-[var(--gr-text-tertiary)]">
          No stage timing data available yet. Complete some applications to see insights.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          label="Total Avg Cycle Time"
          value={formatDays(totalAvgTime)}
          subValue={`${data.total_applications} applications`}
        />
        <StatCard
          label="Slowest Stage"
          value={slowestStage.stage_label}
          subValue={`Avg ${formatDays(slowestStage.avg_days)}`}
        />
        <StatCard
          label="Fastest Stage"
          value={fastestStage.stage_label}
          subValue={`Avg ${formatDays(fastestStage.avg_days)}`}
        />
      </div>

      {/* Chart */}
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <ClockIcon className="h-5 w-5 text-[var(--gr-text-tertiary)]" />
            <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
              Average Time Per Stage
            </h3>
          </div>
          <span className="text-xs text-[var(--gr-text-tertiary)]">
            Based on {data.total_applications} applications
          </span>
        </div>

        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--gr-border-subtle)" />
            <XAxis
              type="number"
              tick={{ fontSize: 12, fill: 'var(--gr-text-tertiary)' }}
              tickLine={false}
              axisLine={{ stroke: 'var(--gr-border-default)' }}
              tickFormatter={(value) => formatDays(value)}
            />
            <YAxis
              type="category"
              dataKey="stage_label"
              tick={{ fontSize: 12, fill: 'var(--gr-text-secondary)' }}
              tickLine={false}
              axisLine={false}
              width={90}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ paddingTop: '20px' }}
              formatter={() => <span className="text-sm text-[var(--gr-text-secondary)]">Average days</span>}
            />
            <Bar dataKey="avg_days" name="Average Days" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});

export default TimePerStageChart;
