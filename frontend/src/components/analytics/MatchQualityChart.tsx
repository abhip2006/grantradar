import { useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../../services/api';
import { SparklesIcon } from '@heroicons/react/24/outline';

interface MatchQualityResponse {
  total_matches: number;
  score_distribution: Array<{
    range_start: number;
    range_end: number;
    count: number;
    percentage: number;
  }>;
  action_breakdown: Record<string, number>;
  avg_score: number;
  high_quality_count: number;
  high_quality_percentage: number;
}

type ViewType = 'distribution' | 'actions';

const ACTION_COLORS: Record<string, string> = {
  saved: '#22c55e',     // green
  applied: '#3b82f6',   // blue
  dismissed: '#64748b', // slate
  viewed: '#f59e0b',    // amber
  new: '#8b5cf6',       // violet
};

const PIE_COLORS = ['#22c55e', '#f59e0b', '#3b82f6', '#64748b', '#8b5cf6'];

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    payload: {
      range_start?: number;
      range_end?: number;
      count?: number;
      percentage?: number;
      name?: string;
    };
  }>;
}

function DistributionTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;
  const startPercent = ((data.range_start || 0) * 100).toFixed(0);
  const endPercent = ((data.range_end || 0) * 100).toFixed(0);

  return (
    <div className="bg-white border border-[var(--gr-border-default)] rounded-lg shadow-lg px-3 py-2">
      <p className="text-sm font-medium text-[var(--gr-text-primary)]">
        Score: {startPercent}% - {endPercent}%
      </p>
      <p className="text-sm text-[var(--gr-text-secondary)]">
        {data.count} match{data.count !== 1 ? 'es' : ''}
      </p>
      {data.percentage !== undefined && (
        <p className="text-xs text-[var(--gr-text-tertiary)]">
          {data.percentage.toFixed(1)}% of total
        </p>
      )}
    </div>
  );
}

export function MatchQualityChart() {
  const [view, setView] = useState<ViewType>('distribution');

  const { data, isLoading, error } = useQuery<MatchQualityResponse>({
    queryKey: ['analytics', 'match-quality'],
    queryFn: () => analyticsApi.getMatchQuality(),
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
          <SparklesIcon className="h-5 w-5 text-[var(--gr-blue-600)]" />
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
            Match Quality
          </h3>
        </div>
        <div className="flex items-center justify-center h-64 text-[var(--gr-text-tertiary)]">
          Unable to load match quality data
        </div>
      </div>
    );
  }

  const actionData = Object.entries(data?.action_breakdown || {})
    .filter(([, value]) => value > 0)
    .map(([name, value]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      value,
      color: ACTION_COLORS[name] || '#64748b',
    }));

  const distributionData = data?.score_distribution || [];
  const hasData = (data?.total_matches || 0) > 0;

  return (
    <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div className="flex items-center gap-2">
          <SparklesIcon className="h-5 w-5 text-[var(--gr-blue-600)]" />
          <div>
            <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
              Match Quality
            </h3>
            <p className="text-sm text-[var(--gr-text-tertiary)]">
              {data?.total_matches?.toLocaleString() || 0} matches analyzed
              {data?.avg_score !== undefined && (
                <span className="ml-2">
                  (avg: {(data.avg_score * 100).toFixed(0)}%)
                </span>
              )}
            </p>
          </div>
        </div>

        <div className="flex rounded-lg bg-[var(--gr-bg-secondary)] p-1">
          <button
            onClick={() => setView('distribution')}
            className={`
              px-3 py-1.5 text-xs font-medium rounded-md transition-all
              ${view === 'distribution'
                ? 'bg-white text-[var(--gr-text-primary)] shadow-sm'
                : 'text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)]'
              }
            `}
          >
            Score Distribution
          </button>
          <button
            onClick={() => setView('actions')}
            className={`
              px-3 py-1.5 text-xs font-medium rounded-md transition-all
              ${view === 'actions'
                ? 'bg-white text-[var(--gr-text-primary)] shadow-sm'
                : 'text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)]'
              }
            `}
          >
            User Actions
          </button>
        </div>
      </div>

      {!hasData ? (
        <div className="flex items-center justify-center h-[300px] text-[var(--gr-text-tertiary)]">
          No match data available yet
        </div>
      ) : view === 'distribution' ? (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={distributionData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--gr-border-subtle)" />
            <XAxis
              dataKey="range_start"
              tick={{ fontSize: 12, fill: 'var(--gr-text-tertiary)' }}
              tickLine={false}
              axisLine={{ stroke: 'var(--gr-border-default)' }}
              tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            />
            <YAxis
              tick={{ fontSize: 12, fill: 'var(--gr-text-tertiary)' }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<DistributionTooltip />} />
            <Bar
              dataKey="count"
              fill="#3B82F6"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <div className="flex items-center justify-center">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={actionData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={2}
                dataKey="value"
                nameKey="name"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {actionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color || PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number) => [value, 'Count']}
              />
              <Legend
                layout="horizontal"
                align="center"
                verticalAlign="bottom"
                formatter={(value) => (
                  <span className="text-sm text-[var(--gr-text-secondary)]">{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* High quality summary */}
      {hasData && data?.high_quality_count !== undefined && (
        <div className="mt-4 pt-4 border-t border-[var(--gr-border-subtle)]">
          <div className="flex items-center justify-between text-sm">
            <span className="text-[var(--gr-text-secondary)]">High quality matches (70%+)</span>
            <span className="font-medium text-emerald-600">
              {data.high_quality_count} ({data.high_quality_percentage?.toFixed(1) || 0}%)
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default MatchQualityChart;
