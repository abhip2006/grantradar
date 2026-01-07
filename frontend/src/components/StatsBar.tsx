import {
  SparklesIcon,
  FireIcon,
  ClockIcon,
  BookmarkIcon,
} from '@heroicons/react/24/outline';
import type { DashboardStats } from '../types';

interface StatItemProps {
  label: string;
  value: number;
  icon: typeof SparklesIcon;
  color: 'amber' | 'emerald' | 'cyan' | 'slate';
}

function StatItem({ label, value, icon: Icon, color }: StatItemProps) {
  const colorClasses = {
    amber: {
      bg: 'bg-[var(--gr-amber-500)]/10',
      icon: 'text-[var(--gr-amber-400)]',
      glow: 'stat-card-amber',
    },
    emerald: {
      bg: 'bg-[var(--gr-emerald-500)]/10',
      icon: 'text-[var(--gr-emerald-400)]',
      glow: 'stat-card-emerald',
    },
    cyan: {
      bg: 'bg-[var(--gr-cyan-500)]/10',
      icon: 'text-[var(--gr-cyan-400)]',
      glow: 'stat-card-cyan',
    },
    slate: {
      bg: 'bg-[var(--gr-slate-700)]',
      icon: 'text-[var(--gr-text-secondary)]',
      glow: '',
    },
  };

  const classes = colorClasses[color];

  return (
    <div className={`stat-card ${classes.glow}`}>
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-xl ${classes.bg}`}>
          <Icon className={`h-6 w-6 ${classes.icon}`} />
        </div>
        <div>
          <p className="text-2xl font-display font-semibold text-[var(--gr-text-primary)]">{value}</p>
          <p className="text-sm text-[var(--gr-text-tertiary)]">{label}</p>
        </div>
      </div>
    </div>
  );
}

interface StatsBarProps {
  stats: DashboardStats | undefined;
  isLoading?: boolean;
}

export function StatsBar({ stats, isLoading }: StatsBarProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="stat-card">
            <div className="flex items-center gap-4">
              <div className="skeleton h-12 w-12 rounded-xl" />
              <div className="flex-1">
                <div className="skeleton h-7 w-12 mb-1" />
                <div className="skeleton h-4 w-20" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  const statItems: StatItemProps[] = [
    {
      label: 'New Grants',
      value: stats?.new_grants ?? 0,
      icon: SparklesIcon,
      color: 'amber',
    },
    {
      label: 'High Matches',
      value: stats?.high_matches ?? 0,
      icon: FireIcon,
      color: 'emerald',
    },
    {
      label: 'Due This Week',
      value: stats?.upcoming_deadline_count ?? stats?.upcoming_deadlines?.length ?? 0,
      icon: ClockIcon,
      color: 'cyan',
    },
    {
      label: 'Saved',
      value: stats?.saved_grants ?? 0,
      icon: BookmarkIcon,
      color: 'slate',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {statItems.map((stat, index) => (
        <div key={stat.label} className={`animate-fade-in-up stagger-${index + 1}`}>
          <StatItem {...stat} />
        </div>
      ))}
    </div>
  );
}

export default StatsBar;
