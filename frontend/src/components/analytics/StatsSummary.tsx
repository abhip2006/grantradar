import { useMemo } from 'react';
import {
  TrophyIcon,
  DocumentCheckIcon,
  CurrencyDollarIcon,
  ArrowTrendingUpIcon,
  ChartBarIcon,
  StarIcon,
} from '@heroicons/react/24/outline';
import type { AnalyticsSummaryResponse } from '../../types';

interface StatsSummaryProps {
  data: AnalyticsSummaryResponse;
}

function formatCurrency(value: number): string {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
}

interface StatCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  icon: React.ReactNode;
  accentColor: 'blue' | 'green' | 'amber' | 'violet' | 'cyan' | 'rose';
}

function StatCard({ label, value, subValue, icon, accentColor }: StatCardProps) {
  const colorClasses = {
    blue: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      icon: 'text-blue-600',
      value: 'text-blue-700',
    },
    green: {
      bg: 'bg-emerald-50',
      border: 'border-emerald-200',
      icon: 'text-emerald-600',
      value: 'text-emerald-700',
    },
    amber: {
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      icon: 'text-amber-600',
      value: 'text-amber-700',
    },
    violet: {
      bg: 'bg-violet-50',
      border: 'border-violet-200',
      icon: 'text-violet-600',
      value: 'text-violet-700',
    },
    cyan: {
      bg: 'bg-cyan-50',
      border: 'border-cyan-200',
      icon: 'text-cyan-600',
      value: 'text-cyan-700',
    },
    rose: {
      bg: 'bg-rose-50',
      border: 'border-rose-200',
      icon: 'text-rose-600',
      value: 'text-rose-700',
    },
  };

  const colors = colorClasses[accentColor];

  return (
    <div
      className={`
        rounded-xl p-5 border transition-all duration-200
        ${colors.bg} ${colors.border}
        hover:shadow-md
      `}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium text-[var(--gr-text-tertiary)] uppercase tracking-wider mb-1">
            {label}
          </p>
          <p className={`text-2xl font-display font-bold ${colors.value}`}>
            {value}
          </p>
          {subValue && (
            <p className="text-xs text-[var(--gr-text-secondary)] mt-1">
              {subValue}
            </p>
          )}
        </div>
        <div className={`p-2 rounded-lg ${colors.bg}`}>
          <div className={`h-5 w-5 ${colors.icon}`}>{icon}</div>
        </div>
      </div>
    </div>
  );
}

export function StatsSummary({ data }: StatsSummaryProps) {
  const stats = useMemo(() => {
    return [
      {
        label: 'Total Applications',
        value: data.total_applications,
        subValue: `${data.total_in_pipeline} in pipeline`,
        icon: <ChartBarIcon className="h-5 w-5" />,
        accentColor: 'blue' as const,
      },
      {
        label: 'Win Rate',
        value: `${data.overall_success_rate.toFixed(1)}%`,
        subValue: `${data.total_awarded} awarded / ${data.total_submitted} submitted`,
        icon: <TrophyIcon className="h-5 w-5" />,
        accentColor: 'green' as const,
      },
      {
        label: 'Funding Awarded',
        value: formatCurrency(data.total_funding_awarded),
        subValue: data.avg_funding_per_award
          ? `Avg: ${formatCurrency(data.avg_funding_per_award)}`
          : undefined,
        icon: <CurrencyDollarIcon className="h-5 w-5" />,
        accentColor: 'amber' as const,
      },
      {
        label: 'Pipeline Conversion',
        value: `${data.pipeline_conversion_rate.toFixed(1)}%`,
        subValue: 'From research to award',
        icon: <ArrowTrendingUpIcon className="h-5 w-5" />,
        accentColor: 'violet' as const,
      },
      {
        label: 'Top Funder',
        value: data.top_funder || 'N/A',
        subValue: data.top_funder ? 'Highest success rate' : 'No data yet',
        icon: <StarIcon className="h-5 w-5" />,
        accentColor: 'cyan' as const,
      },
      {
        label: 'Top Category',
        value: data.top_category || 'N/A',
        subValue: data.top_category ? 'Best performing area' : 'No data yet',
        icon: <DocumentCheckIcon className="h-5 w-5" />,
        accentColor: 'rose' as const,
      },
    ];
  }, [data]);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
        Performance Summary
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {stats.map((stat, index) => (
          <StatCard
            key={index}
            label={stat.label}
            value={stat.value}
            subValue={stat.subValue}
            icon={stat.icon}
            accentColor={stat.accentColor}
          />
        ))}
      </div>
    </div>
  );
}

export default StatsSummary;
