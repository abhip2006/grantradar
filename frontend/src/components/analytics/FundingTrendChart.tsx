import { useMemo, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Area,
  ComposedChart,
  Bar,
} from 'recharts';
import type { FundingTrendsResponse } from '../../types';

interface FundingTrendChartProps {
  data: FundingTrendsResponse;
  onPeriodChange?: (period: 'monthly' | 'quarterly' | 'yearly') => void;
}

type ChartView = 'amount' | 'count' | 'both';

const CHART_COLORS = {
  applied: '#2d5a47', // forest
  awarded: '#22c55e', // green
  appliedLight: 'rgba(45, 90, 71, 0.1)',
  awardedLight: 'rgba(34, 197, 94, 0.1)',
};

function formatCurrency(value: number): string {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
}

function formatPeriod(period: string, periodType: string): string {
  if (periodType === 'yearly') {
    return period;
  }
  if (periodType === 'quarterly') {
    return period;
  }
  // Monthly: 2024-01 -> Jan '24
  const [year, month] = period.split('-');
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const monthIndex = parseInt(month, 10) - 1;
  return `${monthNames[monthIndex]} '${year.slice(2)}`;
}

interface CustomTooltipPayload {
  dataKey?: string | number;
  value?: number | string;
  color?: string;
  name?: string;
}

function CustomTooltip({
  active,
  payload,
  label,
  periodType
}: {
  active?: boolean;
  payload?: CustomTooltipPayload[];
  label?: string;
  periodType: string;
}) {
  if (!active || !payload || !payload.length) return null;

  return (
    <div className="bg-white border border-[var(--gr-border-default)] rounded-lg shadow-lg p-3">
      <p className="text-sm font-medium text-[var(--gr-text-primary)] mb-2">
        {formatPeriod(label || '', periodType)}
      </p>
      {payload.map((entry, index) => (
        <div key={index} className="flex items-center gap-2 text-sm">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-[var(--gr-text-secondary)]">{entry.name}:</span>
          <span className="font-medium text-[var(--gr-text-primary)]">
            {String(entry.dataKey || '').includes('amount')
              ? formatCurrency(Number(entry.value) || 0)
              : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

function SummaryStats({ data }: { data: FundingTrendsResponse }) {
  const stats = [
    {
      label: 'Total Applied',
      value: formatCurrency(data.total_applied_amount),
      subValue: `${data.total_applied_count} applications`,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      label: 'Total Awarded',
      value: formatCurrency(data.total_awarded_amount),
      subValue: `${data.total_awarded_count} grants`,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-50',
    },
    {
      label: 'Success Rate',
      value: data.total_applied_count > 0
        ? `${((data.total_awarded_count / data.total_applied_count) * 100).toFixed(0)}%`
        : '0%',
      subValue: 'of submitted',
      color: 'text-amber-600',
      bgColor: 'bg-amber-50',
    },
    {
      label: 'Award Rate',
      value: data.total_applied_amount > 0
        ? `${((data.total_awarded_amount / data.total_applied_amount) * 100).toFixed(0)}%`
        : '0%',
      subValue: 'of funding',
      color: 'text-violet-600',
      bgColor: 'bg-violet-50',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {stats.map((stat, index) => (
        <div
          key={index}
          className={`rounded-xl p-4 ${stat.bgColor} border border-transparent`}
        >
          <p className="text-xs font-medium text-[var(--gr-text-tertiary)] mb-1">
            {stat.label}
          </p>
          <p className={`text-2xl font-display font-bold ${stat.color}`}>
            {stat.value}
          </p>
          <p className="text-xs text-[var(--gr-text-tertiary)]">
            {stat.subValue}
          </p>
        </div>
      ))}
    </div>
  );
}

export function FundingTrendChart({ data, onPeriodChange }: FundingTrendChartProps) {
  const [chartView, setChartView] = useState<ChartView>('amount');
  const [selectedPeriod, setSelectedPeriod] = useState<'monthly' | 'quarterly' | 'yearly'>(
    data.period_type as 'monthly' | 'quarterly' | 'yearly'
  );

  const chartData = useMemo(() => {
    return data.data_points.map(point => ({
      ...point,
      periodLabel: formatPeriod(point.period, data.period_type),
    }));
  }, [data.data_points, data.period_type]);

  const handlePeriodChange = (period: 'monthly' | 'quarterly' | 'yearly') => {
    setSelectedPeriod(period);
    onPeriodChange?.(period);
  };

  if (chartData.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-4">
          Funding Trends
        </h3>
        <div className="flex items-center justify-center h-64 text-[var(--gr-text-tertiary)]">
          No funding data available yet. Start tracking applications to see trends.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <SummaryStats data={data} />

      {/* Main Chart */}
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        {/* Header with controls */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
            Funding Over Time
          </h3>

          <div className="flex items-center gap-4">
            {/* Chart view toggle */}
            <div className="flex rounded-lg bg-[var(--gr-bg-secondary)] p-1">
              {[
                { key: 'amount', label: 'Amount' },
                { key: 'count', label: 'Count' },
                { key: 'both', label: 'Both' },
              ].map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => setChartView(key as ChartView)}
                  className={`
                    px-3 py-1.5 text-xs font-medium rounded-md transition-all
                    ${chartView === key
                      ? 'bg-white text-[var(--gr-text-primary)] shadow-sm'
                      : 'text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)]'
                    }
                  `}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Period selector */}
            {onPeriodChange && (
              <div className="flex rounded-lg bg-[var(--gr-bg-secondary)] p-1">
                {[
                  { key: 'monthly', label: 'Monthly' },
                  { key: 'quarterly', label: 'Quarterly' },
                  { key: 'yearly', label: 'Yearly' },
                ].map(({ key, label }) => (
                  <button
                    key={key}
                    onClick={() => handlePeriodChange(key as 'monthly' | 'quarterly' | 'yearly')}
                    className={`
                      px-3 py-1.5 text-xs font-medium rounded-md transition-all
                      ${selectedPeriod === key
                        ? 'bg-white text-[var(--gr-text-primary)] shadow-sm'
                        : 'text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)]'
                      }
                    `}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Chart */}
        <ResponsiveContainer width="100%" height={350}>
          {chartView === 'both' ? (
            <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--gr-border-subtle)" />
              <XAxis
                dataKey="periodLabel"
                tick={{ fontSize: 12, fill: 'var(--gr-text-tertiary)' }}
                tickLine={false}
                axisLine={{ stroke: 'var(--gr-border-default)' }}
              />
              <YAxis
                yAxisId="left"
                tick={{ fontSize: 12, fill: 'var(--gr-text-tertiary)' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={formatCurrency}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 12, fill: 'var(--gr-text-tertiary)' }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip content={(props: any) => <CustomTooltip {...props} periodType={data.period_type} />} />
              <Legend />
              <Area
                yAxisId="left"
                type="monotone"
                dataKey="applied_amount"
                name="Applied Amount"
                fill={CHART_COLORS.appliedLight}
                stroke={CHART_COLORS.applied}
                strokeWidth={2}
              />
              <Area
                yAxisId="left"
                type="monotone"
                dataKey="awarded_amount"
                name="Awarded Amount"
                fill={CHART_COLORS.awardedLight}
                stroke={CHART_COLORS.awarded}
                strokeWidth={2}
              />
              <Bar yAxisId="right" dataKey="applied_count" name="Applied Count" fill={CHART_COLORS.applied} opacity={0.3} />
              <Bar yAxisId="right" dataKey="awarded_count" name="Awarded Count" fill={CHART_COLORS.awarded} opacity={0.3} />
            </ComposedChart>
          ) : (
            <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--gr-border-subtle)" />
              <XAxis
                dataKey="periodLabel"
                tick={{ fontSize: 12, fill: 'var(--gr-text-tertiary)' }}
                tickLine={false}
                axisLine={{ stroke: 'var(--gr-border-default)' }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: 'var(--gr-text-tertiary)' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={chartView === 'amount' ? formatCurrency : undefined}
              />
              <Tooltip content={(props: any) => <CustomTooltip {...props} periodType={data.period_type} />} />
              <Legend />
              {chartView === 'amount' ? (
                <>
                  <Line
                    type="monotone"
                    dataKey="applied_amount"
                    name="Applied Amount"
                    stroke={CHART_COLORS.applied}
                    strokeWidth={2}
                    dot={{ fill: CHART_COLORS.applied, strokeWidth: 2 }}
                    activeDot={{ r: 6 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="awarded_amount"
                    name="Awarded Amount"
                    stroke={CHART_COLORS.awarded}
                    strokeWidth={2}
                    dot={{ fill: CHART_COLORS.awarded, strokeWidth: 2 }}
                    activeDot={{ r: 6 }}
                  />
                </>
              ) : (
                <>
                  <Line
                    type="monotone"
                    dataKey="applied_count"
                    name="Applications Submitted"
                    stroke={CHART_COLORS.applied}
                    strokeWidth={2}
                    dot={{ fill: CHART_COLORS.applied, strokeWidth: 2 }}
                    activeDot={{ r: 6 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="awarded_count"
                    name="Grants Awarded"
                    stroke={CHART_COLORS.awarded}
                    strokeWidth={2}
                    dot={{ fill: CHART_COLORS.awarded, strokeWidth: 2 }}
                    activeDot={{ r: 6 }}
                  />
                </>
              )}
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default FundingTrendChart;
