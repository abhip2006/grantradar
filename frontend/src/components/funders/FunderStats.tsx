import {
  DocumentTextIcon,
  CurrencyDollarIcon,
  CalendarDaysIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import type { FunderInsightsResponse } from '../../types';

interface FunderStatsProps {
  data: FunderInsightsResponse;
}

function formatCurrency(amount: number): string {
  if (amount >= 1000000) {
    return `$${(amount / 1000000).toFixed(1)}M`;
  }
  if (amount >= 1000) {
    return `$${(amount / 1000).toFixed(0)}K`;
  }
  return `$${amount.toLocaleString()}`;
}

interface StatCardProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  subValue?: string;
  colorClass?: string;
  bgClass?: string;
}

function StatCard({
  icon: Icon,
  label,
  value,
  subValue,
  colorClass = 'text-[var(--gr-blue-600)]',
  bgClass = 'bg-[var(--gr-blue-50)]',
}: StatCardProps) {
  return (
    <div className="bg-[var(--gr-bg-card)] rounded-xl p-5 border border-[var(--gr-border-default)] hover:border-[var(--gr-border-strong)] hover:shadow-[var(--gr-shadow-md)] transition-all">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-10 h-10 ${bgClass} rounded-lg flex items-center justify-center`}>
          <Icon className={`h-5 w-5 ${colorClass}`} />
        </div>
        <span className="text-sm font-medium text-[var(--gr-text-secondary)]">{label}</span>
      </div>
      <div className="text-2xl font-display font-semibold text-[var(--gr-text-primary)]">
        {value}
      </div>
      {subValue && (
        <div className="text-sm text-[var(--gr-text-tertiary)] mt-1">{subValue}</div>
      )}
    </div>
  );
}

export function FunderStats({ data }: FunderStatsProps) {
  const successRate = data.user_history?.success_rate;
  const successRateDisplay = successRate !== null && successRate !== undefined
    ? `${(successRate * 100).toFixed(0)}%`
    : 'N/A';

  return (
    <div className="space-y-6">
      {/* Primary Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={DocumentTextIcon}
          label="Total Grants"
          value={data.total_grants}
          subValue={`${data.active_grants} currently active`}
          colorClass="text-[var(--gr-blue-600)]"
          bgClass="bg-[var(--gr-blue-50)]"
        />
        <StatCard
          icon={CurrencyDollarIcon}
          label="Avg. Award"
          value={data.avg_amount_max ? formatCurrency(data.avg_amount_max) : 'N/A'}
          subValue={
            data.min_amount && data.max_amount
              ? `Range: ${formatCurrency(data.min_amount)} - ${formatCurrency(data.max_amount)}`
              : undefined
          }
          colorClass="text-[var(--gr-yellow-600)]"
          bgClass="bg-[var(--gr-yellow-50)]"
        />
        <StatCard
          icon={ChartBarIcon}
          label="Focus Areas"
          value={data.focus_areas.length}
          subValue="Research categories"
          colorClass="text-[var(--gr-green-600)]"
          bgClass="bg-[rgba(34,197,94,0.1)]"
        />
        <StatCard
          icon={CalendarDaysIcon}
          label="Peak Months"
          value={data.typical_deadline_months.slice(0, 2).join(', ') || 'N/A'}
          subValue="Most common deadlines"
          colorClass="text-[var(--gr-blue-500)]"
          bgClass="bg-[var(--gr-blue-50)]"
        />
      </div>

      {/* User History Stats (if available) */}
      {data.user_history && data.user_history.total_applications > 0 && (
        <div className="bg-[var(--gr-bg-secondary)] rounded-xl p-5 border border-[var(--gr-border-default)]">
          <h3 className="text-sm font-medium text-[var(--gr-text-secondary)] mb-4 flex items-center gap-2">
            <ArrowTrendingUpIcon className="h-4 w-4" />
            Your History with this Funder
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
            <div className="text-center">
              <div className="text-2xl font-display font-bold text-[var(--gr-text-primary)]">
                {data.user_history.total_applications}
              </div>
              <div className="text-xs text-[var(--gr-text-tertiary)]">Total Applied</div>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-1">
                <CheckCircleIcon className="h-5 w-5 text-[var(--gr-green-500)]" />
                <span className="text-2xl font-display font-bold text-[var(--gr-green-600)]">
                  {data.user_history.awarded_count}
                </span>
              </div>
              <div className="text-xs text-[var(--gr-text-tertiary)]">Awarded</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-display font-bold text-[var(--gr-danger)]">
                {data.user_history.rejected_count}
              </div>
              <div className="text-xs text-[var(--gr-text-tertiary)]">Rejected</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-display font-bold text-[var(--gr-yellow-600)]">
                {data.user_history.pending_count}
              </div>
              <div className="text-xs text-[var(--gr-text-tertiary)]">Pending</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-display font-bold text-[var(--gr-blue-600)]">
                {successRateDisplay}
              </div>
              <div className="text-xs text-[var(--gr-text-tertiary)]">Success Rate</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default FunderStats;
