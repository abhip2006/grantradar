import { useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import type { SuccessRatesResponse, SuccessRateByFunder, SuccessRateByCategory } from '../../types';

interface SuccessRateChartProps {
  data: SuccessRatesResponse;
  view?: 'stage' | 'funder' | 'category';
}

// Stage colors matching the pipeline design
const STAGE_COLORS: Record<string, string> = {
  researching: '#06b6d4', // cyan-500
  writing: '#f59e0b', // amber-500
  submitted: '#2d5a47', // forest-500
  awarded: '#22c55e', // green-500
  rejected: '#64748b', // slate-500
};

// Success rate donut colors
const SUCCESS_COLORS = {
  awarded: '#22c55e', // green-500
  rejected: '#ef4444', // red-500
  pending: '#2d5a47', // forest-500
};

// Color palette for dynamic data - exported for potential reuse
export const CHART_COLOR_PALETTE = [
  '#2d5a47', // forest
  '#22c55e', // green
  '#f59e0b', // amber
  '#8b5cf6', // violet
  '#06b6d4', // cyan
  '#ec4899', // pink
  '#f97316', // orange
  '#14b8a6', // teal
];

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ name: string; value: number; payload: { percentage?: number } }> }) {
  if (!active || !payload || !payload.length) return null;

  const item = payload[0];
  return (
    <div className="bg-white border border-[var(--gr-border-default)] rounded-lg shadow-lg px-3 py-2">
      <p className="text-sm font-medium text-[var(--gr-text-primary)]">{item.name}</p>
      <p className="text-sm text-[var(--gr-text-secondary)]">
        Count: {item.value}
        {item.payload.percentage !== undefined && (
          <span className="ml-2">({item.payload.percentage.toFixed(1)}%)</span>
        )}
      </p>
    </div>
  );
}

function StageDistributionChart({ data }: { data: SuccessRatesResponse }) {
  const chartData = useMemo(() => {
    const total = data.by_stage.reduce((sum, s) => sum + s.count, 0);
    return data.by_stage
      .filter(s => s.count > 0)
      .map(s => ({
        name: s.stage.charAt(0).toUpperCase() + s.stage.slice(1),
        value: s.count,
        percentage: total > 0 ? (s.count / total) * 100 : 0,
        fill: STAGE_COLORS[s.stage] || '#64748b',
      }));
  }, [data.by_stage]);

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-[var(--gr-text-tertiary)]">
        No applications to display
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={100}
          paddingAngle={2}
          dataKey="value"
          nameKey="name"
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.fill} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
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
  );
}

function SuccessRateDonut({ data }: { data: SuccessRatesResponse }) {
  const chartData = useMemo(() => {
    const submitted = data.by_stage.find(s => s.stage === 'submitted')?.count || 0;
    const awarded = data.by_stage.find(s => s.stage === 'awarded')?.count || 0;
    const rejected = data.by_stage.find(s => s.stage === 'rejected')?.count || 0;
    const totalOutcomes = submitted + awarded + rejected;

    if (totalOutcomes === 0) return [];

    return [
      { name: 'Awarded', value: awarded, fill: SUCCESS_COLORS.awarded },
      { name: 'Rejected', value: rejected, fill: SUCCESS_COLORS.rejected },
      { name: 'Pending', value: submitted, fill: SUCCESS_COLORS.pending },
    ].filter(d => d.value > 0);
  }, [data.by_stage]);

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-[var(--gr-text-tertiary)]">
        No outcomes to display
      </div>
    );
  }

  return (
    <div className="relative">
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={70}
            outerRadius={100}
            paddingAngle={2}
            dataKey="value"
            nameKey="name"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.fill} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
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
      {/* Center text showing overall rate */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none" style={{ marginBottom: '40px' }}>
        <div className="text-center">
          <div className="text-3xl font-display font-bold text-[var(--gr-text-primary)]">
            {data.overall_success_rate.toFixed(0)}%
          </div>
          <div className="text-xs text-[var(--gr-text-tertiary)]">Win Rate</div>
        </div>
      </div>
    </div>
  );
}

function TopPerformersTable({
  items,
  type
}: {
  items: SuccessRateByFunder[] | SuccessRateByCategory[];
  type: 'funder' | 'category'
}) {
  const topItems = items.slice(0, 5);

  if (topItems.length === 0) {
    return (
      <div className="text-center py-8 text-[var(--gr-text-tertiary)]">
        No data available
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {topItems.map((item, index) => {
        const name = type === 'funder' ? (item as SuccessRateByFunder).funder : (item as SuccessRateByCategory).category;
        const successRate = item.success_rate;
        const total = item.total;

        return (
          <div
            key={index}
            className="flex items-center justify-between p-3 rounded-lg bg-[var(--gr-bg-secondary)] border border-[var(--gr-border-subtle)]"
          >
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-[var(--gr-text-primary)] truncate">
                {name}
              </p>
              <p className="text-xs text-[var(--gr-text-tertiary)]">
                {item.awarded} awarded / {item.submitted || (item.awarded + item.rejected)} submitted
              </p>
            </div>
            <div className="ml-4 text-right">
              <div className="text-lg font-semibold text-[var(--gr-text-primary)]">
                {successRate.toFixed(0)}%
              </div>
              <div className="text-xs text-[var(--gr-text-tertiary)]">
                {total} total
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function SuccessRateChart({ data }: SuccessRateChartProps) {
  return (
    <div className="space-y-6">
      {/* Main donut chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Stage Distribution */}
        <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-4">
            Applications by Stage
          </h3>
          <StageDistributionChart data={data} />
        </div>

        {/* Win Rate Donut */}
        <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-4">
            Overall Win Rate
          </h3>
          <SuccessRateDonut data={data} />
        </div>
      </div>

      {/* Top performers tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* By Funder */}
        <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-4">
            Success by Funder
          </h3>
          <TopPerformersTable items={data.by_funder} type="funder" />
        </div>

        {/* By Category */}
        <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-4">
            Success by Category
          </h3>
          <TopPerformersTable items={data.by_category} type="category" />
        </div>
      </div>
    </div>
  );
}

export default SuccessRateChart;
