import { useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../../services/api';
import { ClockIcon } from '@heroicons/react/24/outline';

interface TimeToAwardData {
  overall_avg_days: number;
  overall_median_days: number;
  by_stage: Array<{
    stage: string;
    avg_days: number;
    median_days: number;
    count: number;
  }>;
  by_category: Record<string, number>;
  by_funder: Record<string, number>;
}

type ViewType = 'stage' | 'category' | 'funder';

// Stage label mapping
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
    value: number;
    dataKey: string;
    payload: {
      name?: string;
      stage?: string;
      avg_days?: number;
      median_days?: number;
      count?: number;
    };
  }>;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;
  const name = data.name || STAGE_LABELS[data.stage || ''] || data.stage;

  return (
    <div className="bg-white border border-[var(--gr-border-default)] rounded-lg shadow-lg px-3 py-2">
      <p className="text-sm font-medium text-[var(--gr-text-primary)]">{name}</p>
      <p className="text-sm text-[var(--gr-text-secondary)]">
        Avg: {payload[0].value?.toFixed(0) || 0} days
      </p>
      {data.median_days !== undefined && (
        <p className="text-sm text-[var(--gr-text-tertiary)]">
          Median: {data.median_days.toFixed(0)} days
        </p>
      )}
      {data.count !== undefined && (
        <p className="text-xs text-[var(--gr-text-tertiary)]">
          {data.count} application{data.count !== 1 ? 's' : ''}
        </p>
      )}
    </div>
  );
}

export function TimeToAwardChart() {
  const [view, setView] = useState<ViewType>('stage');

  const { data, isLoading, error } = useQuery<TimeToAwardData>({
    queryKey: ['analytics', 'time-to-award'],
    queryFn: () => analyticsApi.getTimeToAward(),
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <div className="animate-pulse">
          <div className="h-6 w-48 bg-[var(--gr-bg-secondary)] rounded mb-4" />
          <div className="h-[300px] bg-[var(--gr-bg-secondary)] rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <div className="flex items-center gap-2 mb-4">
          <ClockIcon className="h-5 w-5 text-[var(--gr-blue-600)]" />
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
            Time to Award
          </h3>
        </div>
        <div className="flex items-center justify-center h-64 text-[var(--gr-text-tertiary)]">
          Unable to load time to award data
        </div>
      </div>
    );
  }

  // Transform data based on view
  const chartData = view === 'stage'
    ? (data?.by_stage || []).map(item => ({
        ...item,
        name: STAGE_LABELS[item.stage] || item.stage,
      }))
    : Object.entries(data?.[`by_${view}` as keyof TimeToAwardData] as Record<string, number> || {})
        .map(([name, days]) => ({
          name,
          avg_days: days,
        }))
        .sort((a, b) => b.avg_days - a.avg_days)
        .slice(0, 10);

  const hasData = chartData.length > 0;

  return (
    <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div className="flex items-center gap-2">
          <ClockIcon className="h-5 w-5 text-[var(--gr-blue-600)]" />
          <div>
            <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
              Time to Award
            </h3>
            {data?.overall_avg_days !== undefined && (
              <p className="text-sm text-[var(--gr-text-tertiary)]">
                Overall average: {data.overall_avg_days.toFixed(0)} days
                {data.overall_median_days !== undefined && (
                  <span className="ml-2">
                    (median: {data.overall_median_days.toFixed(0)} days)
                  </span>
                )}
              </p>
            )}
          </div>
        </div>

        <div className="flex rounded-lg bg-[var(--gr-bg-secondary)] p-1">
          {(['stage', 'category', 'funder'] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`
                px-3 py-1.5 text-xs font-medium rounded-md transition-all
                ${view === v
                  ? 'bg-white text-[var(--gr-text-primary)] shadow-sm'
                  : 'text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)]'
                }
              `}
            >
              {v.charAt(0).toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {!hasData ? (
        <div className="flex items-center justify-center h-[300px] text-[var(--gr-text-tertiary)]">
          No time tracking data available yet
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--gr-border-subtle)" />
            <XAxis
              type="number"
              tick={{ fontSize: 12, fill: 'var(--gr-text-tertiary)' }}
              tickLine={false}
              axisLine={{ stroke: 'var(--gr-border-default)' }}
              tickFormatter={(value) => `${value}d`}
            />
            <YAxis
              dataKey="name"
              type="category"
              width={100}
              tick={{ fontSize: 12, fill: 'var(--gr-text-secondary)' }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Bar
              dataKey="avg_days"
              name="Avg. Days"
              fill="#3B82F6"
              radius={[0, 4, 4, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export default TimeToAwardChart;
