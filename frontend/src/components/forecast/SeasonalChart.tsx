import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { CalendarDaysIcon, FireIcon } from '@heroicons/react/24/outline';
import type { SeasonalTrend } from '../../types';

interface SeasonalChartProps {
  trends: SeasonalTrend[];
  peakMonths: number[];
  yearTotal: number;
}

interface ChartDataItem {
  name: string;
  month: number;
  count: number;
  avgAmount: number | null;
  isPeak: boolean;
  topCategories: string[];
  topFunders: string[];
}

export function SeasonalChart({ trends, peakMonths, yearTotal }: SeasonalChartProps) {
  const chartData: ChartDataItem[] = useMemo(() => {
    return trends.map((trend) => ({
      name: trend.month_name.substring(0, 3),
      month: trend.month,
      count: trend.grant_count,
      avgAmount: trend.avg_amount || null,
      isPeak: peakMonths.includes(trend.month),
      topCategories: trend.top_categories,
      topFunders: trend.top_funders,
    }));
  }, [trends, peakMonths]);

  const formatCurrency = (amount: number) => {
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(1)}M`;
    }
    if (amount >= 1000) {
      return `$${(amount / 1000).toFixed(0)}K`;
    }
    return `$${amount}`;
  };

  const currentMonth = new Date().getMonth() + 1;

  const CustomTooltip = ({
    active,
    payload,
  }: {
    active?: boolean;
    payload?: Array<{ payload: ChartDataItem }>;
  }) => {
    if (!active || !payload || !payload.length) return null;

    const data = payload[0].payload;

    return (
      <div className="bg-[var(--gr-bg-elevated)] border border-[var(--gr-border-default)] rounded-lg shadow-[var(--gr-shadow-lg)] p-4 max-w-xs">
        <div className="flex items-center gap-2 mb-2">
          <span className="font-display font-medium text-[var(--gr-text-primary)]">
            {trends.find((t) => t.month === data.month)?.month_name || data.name}
          </span>
          {data.isPeak && <FireIcon className="h-4 w-4 text-[var(--gr-yellow-500)]" />}
        </div>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between gap-4">
            <span className="text-[var(--gr-text-secondary)]">Grants:</span>
            <span className="font-medium text-[var(--gr-text-primary)]">{data.count}</span>
          </div>
          {data.avgAmount && (
            <div className="flex justify-between gap-4">
              <span className="text-[var(--gr-text-secondary)]">Avg Amount:</span>
              <span className="font-medium text-[var(--gr-text-primary)]">
                {formatCurrency(data.avgAmount)}
              </span>
            </div>
          )}
          {data.topCategories.length > 0 && (
            <div>
              <span className="text-[var(--gr-text-tertiary)] text-xs">Top categories:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {data.topCategories.slice(0, 3).map((cat, i) => (
                  <span
                    key={i}
                    className="px-1.5 py-0.5 text-xs bg-[var(--gr-blue-50)] text-[var(--gr-blue-700)] rounded"
                  >
                    {cat}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <CalendarDaysIcon className="h-5 w-5 text-[var(--gr-blue-600)]" />
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
            Seasonal Trends
          </h3>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-sm bg-[var(--gr-blue-500)]" />
            <span className="text-[var(--gr-text-secondary)]">Grants by month</span>
          </div>
          <div className="flex items-center gap-2">
            <FireIcon className="h-4 w-4 text-[var(--gr-yellow-500)]" />
            <span className="text-[var(--gr-text-secondary)]">Peak months</span>
          </div>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="text-center p-3 bg-[var(--gr-bg-secondary)] rounded-lg">
          <p className="text-2xl font-display font-semibold text-[var(--gr-text-primary)]">
            {yearTotal}
          </p>
          <p className="text-xs text-[var(--gr-text-tertiary)]">Total Grants/Year</p>
        </div>
        <div className="text-center p-3 bg-[var(--gr-bg-secondary)] rounded-lg">
          <p className="text-2xl font-display font-semibold text-[var(--gr-text-primary)]">
            {peakMonths.length > 0
              ? trends.find((t) => t.month === peakMonths[0])?.month_name?.substring(0, 3) || '-'
              : '-'}
          </p>
          <p className="text-xs text-[var(--gr-text-tertiary)]">Peak Month</p>
        </div>
        <div className="text-center p-3 bg-[var(--gr-bg-secondary)] rounded-lg">
          <p className="text-2xl font-display font-semibold text-[var(--gr-text-primary)]">
            {Math.round(yearTotal / 12)}
          </p>
          <p className="text-xs text-[var(--gr-text-tertiary)]">Avg/Month</p>
        </div>
      </div>

      {/* Chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--gr-border-subtle)"
              vertical={false}
            />
            <XAxis
              dataKey="name"
              tick={{ fill: 'var(--gr-text-tertiary)', fontSize: 12 }}
              axisLine={{ stroke: 'var(--gr-border-default)' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: 'var(--gr-text-tertiary)', fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'var(--gr-bg-hover)' }} />
            <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={40}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={
                    entry.month === currentMonth
                      ? 'var(--gr-green-500)'
                      : entry.isPeak
                        ? 'var(--gr-yellow-500)'
                        : 'var(--gr-blue-500)'
                  }
                  opacity={entry.month < currentMonth ? 0.6 : 1}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="mt-4 pt-4 border-t border-[var(--gr-border-subtle)]">
        <div className="flex items-center justify-center gap-6 text-xs text-[var(--gr-text-tertiary)]">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-sm bg-[var(--gr-green-500)]" />
            <span>Current month</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-sm bg-[var(--gr-yellow-500)]" />
            <span>Peak months</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-sm bg-[var(--gr-blue-500)] opacity-60" />
            <span>Past months</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SeasonalChart;
