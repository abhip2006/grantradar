import {
  UserGroupIcon,
  EnvelopeIcon,
  DocumentTextIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
} from '@heroicons/react/24/outline';
import type { TeamStats as TeamStatsType } from '../../types/team';

interface TeamStatsProps {
  stats: TeamStatsType | undefined;
  isLoading?: boolean;
}

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

// Stat card component
interface StatCardProps {
  label: string;
  value: number | string;
  icon: React.ElementType;
  iconBgColor: string;
  iconColor: string;
  trend?: { value: number; isPositive: boolean };
  isLoading?: boolean;
}

function StatCard({ label, value, icon: Icon, iconBgColor, iconColor, trend, isLoading }: StatCardProps) {
  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
        <div className="flex items-start justify-between">
          <div className="w-10 h-10 rounded-xl bg-gray-200" />
          <div className="h-8 bg-gray-200 rounded w-12" />
        </div>
        <div className="mt-3 h-4 bg-gray-200 rounded w-24" />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className={classNames('w-10 h-10 rounded-xl flex items-center justify-center', iconBgColor)}>
          <Icon className={classNames('w-5 h-5', iconColor)} />
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          {trend && (
            <div className={classNames(
              'flex items-center gap-1 text-xs font-medium',
              trend.isPositive ? 'text-green-600' : 'text-red-600'
            )}>
              {trend.isPositive ? (
                <ArrowTrendingUpIcon className="w-3 h-3" />
              ) : (
                <ArrowTrendingDownIcon className="w-3 h-3" />
              )}
              {trend.value}%
            </div>
          )}
        </div>
      </div>
      <p className="mt-3 text-sm font-medium text-gray-500">{label}</p>
    </div>
  );
}

export function TeamStats({ stats, isLoading = false }: TeamStatsProps) {
  const statCards = [
    {
      label: 'Total Members',
      value: stats?.total_members ?? 0,
      icon: UserGroupIcon,
      iconBgColor: 'bg-blue-50',
      iconColor: 'text-blue-600',
    },
    {
      label: 'Pending Invitations',
      value: stats?.pending_invitations ?? 0,
      icon: EnvelopeIcon,
      iconBgColor: 'bg-yellow-50',
      iconColor: 'text-yellow-600',
    },
    {
      label: 'Applications In Progress',
      value: stats?.applications_in_progress ?? 0,
      icon: DocumentTextIcon,
      iconBgColor: 'bg-purple-50',
      iconColor: 'text-purple-600',
    },
    {
      label: 'Activity This Week',
      value: stats?.activity_count_7d ?? 0,
      icon: ChartBarIcon,
      iconBgColor: 'bg-green-50',
      iconColor: 'text-green-600',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {statCards.map((card) => (
        <StatCard
          key={card.label}
          {...card}
          isLoading={isLoading}
        />
      ))}
    </div>
  );
}

export default TeamStats;
