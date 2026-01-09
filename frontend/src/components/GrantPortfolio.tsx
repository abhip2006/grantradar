import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  BookmarkIcon,
  CalendarIcon,
  CurrencyDollarIcon,
  BuildingLibraryIcon,
  ChevronRightIcon,
  ClockIcon,
  CheckCircleIcon,
  PaperAirplaneIcon,
  EyeIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { BookmarkIcon as BookmarkSolidIcon } from '@heroicons/react/24/solid';
import { grantsApi } from '../services/api';
import { MatchScoreBadge } from './MatchScore';
import type { GrantMatch } from '../types';

/* ===================================================================
   GRANT PORTFOLIO VIEW
   Timeline visualization of saved/tracked grants with status grouping
   =================================================================== */

// Portfolio status types
type PortfolioStatus = 'watching' | 'in_progress' | 'submitted' | 'decided';

interface PortfolioStatusConfig {
  label: string;
  description: string;
  icon: React.ElementType;
  color: string;
  bgColor: string;
  borderColor: string;
}

const STATUS_CONFIG: Record<PortfolioStatus, PortfolioStatusConfig> = {
  watching: {
    label: 'Watching',
    description: 'Grants you\'re tracking',
    icon: EyeIcon,
    color: 'text-cyan-600',
    bgColor: 'bg-cyan-50',
    borderColor: 'border-cyan-200',
  },
  in_progress: {
    label: 'In Progress',
    description: 'Applications in development',
    icon: ClockIcon,
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
  },
  submitted: {
    label: 'Submitted',
    description: 'Awaiting decision',
    icon: PaperAirplaneIcon,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
  decided: {
    label: 'Decided',
    description: 'Awards & outcomes',
    icon: CheckCircleIcon,
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
  },
};

// Helper functions
function formatCurrency(amount: number): string {
  if (amount >= 1000000) {
    return `$${(amount / 1000000).toFixed(1)}M`;
  }
  if (amount >= 1000) {
    return `$${(amount / 1000).toFixed(0)}K`;
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

function getDaysUntilDeadline(deadline: string | undefined): number | null {
  if (!deadline) return null;
  const deadlineDate = new Date(deadline);
  const today = new Date();
  const diffTime = deadlineDate.getTime() - today.getTime();
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}

function getPortfolioStatus(match: GrantMatch): PortfolioStatus {
  // Determine status based on user_action
  const action = match.user_action || match.status;

  if (action === 'applied') {
    return 'submitted';
  }

  // For now, all saved grants are "watching"
  // In a full implementation, this would check pipeline stage
  return 'watching';
}

// Timeline Component
interface TimelineProps {
  grants: GrantMatch[];
}

function Timeline({ grants }: TimelineProps) {
  // Get the next 6 months for the timeline
  const months = useMemo(() => {
    const result = [];
    const today = new Date();
    for (let i = 0; i < 6; i++) {
      const date = new Date(today.getFullYear(), today.getMonth() + i, 1);
      result.push({
        month: date.toLocaleDateString('en-US', { month: 'short' }),
        year: date.getFullYear(),
        monthIndex: date.getMonth(),
      });
    }
    return result;
  }, []);

  // Group grants by month based on deadline
  const grantsByMonth = useMemo(() => {
    const map = new Map<string, GrantMatch[]>();

    for (const grant of grants) {
      if (!grant.grant.deadline) continue;
      const deadline = new Date(grant.grant.deadline);
      const key = `${deadline.getMonth()}-${deadline.getFullYear()}`;
      const existing = map.get(key) || [];
      map.set(key, [...existing, grant]);
    }

    return map;
  }, [grants]);

  return (
    <div className="card p-6 mb-8">
      <h3 className="text-sm font-medium text-[var(--gr-text-secondary)] mb-4">
        Deadline Timeline
      </h3>

      {/* Timeline visualization */}
      <div className="relative">
        {/* Timeline line */}
        <div className="absolute top-4 left-0 right-0 h-0.5 bg-[var(--gr-border-default)]" />

        {/* Month markers */}
        <div className="flex justify-between relative">
          {months.map((month, index) => {
            const key = `${month.monthIndex}-${month.year}`;
            const grantsInMonth = grantsByMonth.get(key) || [];
            const hasGrants = grantsInMonth.length > 0;

            return (
              <div key={index} className="flex flex-col items-center">
                {/* Dot */}
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center z-10 transition-all ${
                    hasGrants
                      ? 'bg-[var(--gr-blue-600)] text-white cursor-pointer hover:scale-110'
                      : 'bg-[var(--gr-bg-card)] border-2 border-[var(--gr-border-default)] text-[var(--gr-text-tertiary)]'
                  }`}
                  title={hasGrants ? `${grantsInMonth.length} deadline(s)` : 'No deadlines'}
                >
                  <span className="text-xs font-medium">
                    {hasGrants ? grantsInMonth.length : ''}
                  </span>
                </div>

                {/* Month label */}
                <span className="mt-2 text-xs text-[var(--gr-text-tertiary)]">
                  {month.month}
                </span>

                {/* Grant dots below */}
                {hasGrants && (
                  <div className="flex gap-1 mt-2">
                    {grantsInMonth.slice(0, 3).map((grant) => {
                      const days = getDaysUntilDeadline(grant.grant.deadline);
                      const isUrgent = days !== null && days <= 14 && days >= 0;
                      return (
                        <div
                          key={grant.id}
                          className={`w-2 h-2 rounded-full ${
                            isUrgent
                              ? 'bg-[var(--gr-danger)] animate-pulse'
                              : 'bg-[var(--gr-blue-400)]'
                          }`}
                          title={grant.grant.title}
                        />
                      );
                    })}
                    {grantsInMonth.length > 3 && (
                      <span className="text-xs text-[var(--gr-text-muted)]">
                        +{grantsInMonth.length - 3}
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// Portfolio Card Component (compact version for grid)
interface PortfolioCardProps {
  match: GrantMatch;
  delay?: number;
}

function PortfolioCard({ match, delay = 0 }: PortfolioCardProps) {
  const { grant, score } = match;
  const daysUntilDeadline = getDaysUntilDeadline(grant.deadline);
  const isUrgent = daysUntilDeadline !== null && daysUntilDeadline <= 7 && daysUntilDeadline > 0;
  const isPastDue = daysUntilDeadline !== null && daysUntilDeadline < 0;

  return (
    <Link
      to={`/grants/${match.id}`}
      className="block card p-4 hover:border-[var(--gr-blue-400)] transition-all animate-fade-in-up group"
      style={{ animationDelay: `${delay * 0.05}s` }}
    >
      {/* Title */}
      <h4 className="text-sm font-medium text-[var(--gr-text-primary)] line-clamp-2 mb-2 group-hover:text-[var(--gr-blue-600)] transition-colors">
        {grant.title}
      </h4>

      {/* Agency */}
      <div className="flex items-center gap-1.5 text-xs text-[var(--gr-text-secondary)] mb-3">
        <BuildingLibraryIcon className="h-3.5 w-3.5 text-[var(--gr-text-tertiary)]" />
        <span className="truncate">{grant.funder_name || grant.agency || 'Unknown'}</span>
      </div>

      {/* Deadline */}
      {grant.deadline && (
        <div
          className={`flex items-center gap-1.5 text-xs mb-3 ${
            isPastDue
              ? 'text-[var(--gr-text-muted)]'
              : isUrgent
                ? 'text-[var(--gr-danger)] font-medium'
                : 'text-[var(--gr-text-secondary)]'
          }`}
        >
          <CalendarIcon className={`h-3.5 w-3.5 ${
            isPastDue
              ? 'text-[var(--gr-text-muted)]'
              : isUrgent
                ? 'text-[var(--gr-danger)]'
                : 'text-[var(--gr-blue-500)]'
          }`} />
          {isPastDue ? (
            <span>Past deadline</span>
          ) : isUrgent && daysUntilDeadline !== null ? (
            <span className="flex items-center gap-1">
              <ExclamationTriangleIcon className="h-3 w-3" />
              {daysUntilDeadline} days left
            </span>
          ) : (
            <span>Due {formatDate(grant.deadline)}</span>
          )}
        </div>
      )}

      {/* Bottom row: Amount + Score */}
      <div className="flex items-center justify-between">
        {(grant.funding_amount_max || grant.amount_max) && (
          <div className="flex items-center gap-1 text-xs text-[var(--gr-text-secondary)]">
            <CurrencyDollarIcon className="h-3.5 w-3.5 text-[var(--gr-yellow-500)]" />
            <span>{formatCurrency(grant.funding_amount_max || grant.amount_max || 0)}</span>
          </div>
        )}
        <MatchScoreBadge score={score} />
      </div>
    </Link>
  );
}

// Status Group Component
interface StatusGroupProps {
  status: PortfolioStatus;
  grants: GrantMatch[];
  expanded?: boolean;
  onToggleExpand?: () => void;
}

function StatusGroup({ status, grants, expanded = true, onToggleExpand }: StatusGroupProps) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;
  const displayGrants = expanded ? grants : grants.slice(0, 4);

  if (grants.length === 0) return null;

  return (
    <div className="mb-8">
      {/* Section header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg ${config.bgColor} flex items-center justify-center`}>
            <Icon className={`w-4 h-4 ${config.color}`} />
          </div>
          <div>
            <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
              {config.label}
              <span className="ml-2 text-sm font-normal text-[var(--gr-text-tertiary)]">
                ({grants.length})
              </span>
            </h3>
            <p className="text-xs text-[var(--gr-text-tertiary)]">{config.description}</p>
          </div>
        </div>

        {grants.length > 4 && (
          <button
            onClick={onToggleExpand}
            className="flex items-center gap-1 text-sm text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-700)] transition-colors"
          >
            {expanded ? 'Show Less' : 'View All'}
            <ChevronRightIcon className={`w-4 h-4 transition-transform ${expanded ? 'rotate-90' : ''}`} />
          </button>
        )}
      </div>

      {/* Grant cards grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {displayGrants.map((match, index) => (
          <PortfolioCard key={match.id} match={match} delay={index} />
        ))}
      </div>
    </div>
  );
}

// Summary Stats Card Component
interface SummaryStatsProps {
  grants: GrantMatch[];
  isLoading: boolean;
}

function SummaryStats({ grants, isLoading }: SummaryStatsProps) {
  const stats = useMemo(() => {
    const totalPotentialFunding = grants.reduce((sum, match) => {
      const amount = match.grant.funding_amount_max || match.grant.amount_max || 0;
      return sum + amount;
    }, 0);

    const now = new Date();
    const endOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    const upcomingThisMonth = grants.filter((match) => {
      if (!match.grant.deadline) return false;
      const deadline = new Date(match.grant.deadline);
      return deadline >= now && deadline <= endOfMonth;
    }).length;

    const urgentCount = grants.filter((match) => {
      const days = getDaysUntilDeadline(match.grant.deadline);
      return days !== null && days <= 7 && days >= 0;
    }).length;

    // Count by source
    const bySource = grants.reduce((acc, match) => {
      const source = match.grant.source || 'other';
      acc[source] = (acc[source] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    // Average match score
    const avgScore = grants.length > 0
      ? Math.round(grants.reduce((sum, m) => sum + m.score, 0) / grants.length)
      : 0;

    return {
      totalGrants: grants.length,
      totalPotentialFunding,
      upcomingThisMonth,
      urgentCount,
      bySource,
      avgScore,
    };
  }, [grants]);

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="card p-5">
            <div className="skeleton w-10 h-10 rounded-xl mb-3" />
            <div className="skeleton h-8 w-16 mb-1" />
            <div className="skeleton h-4 w-24" />
          </div>
        ))}
      </div>
    );
  }

  const statCards = [
    {
      label: 'Active Grants',
      value: stats.totalGrants,
      icon: BookmarkSolidIcon,
      iconBg: 'bg-blue-50',
      iconColor: 'text-blue-600',
      subtext: stats.urgentCount > 0 ? `${stats.urgentCount} need attention` : 'All on track',
      subtextColor: stats.urgentCount > 0 ? 'text-amber-600' : 'text-emerald-600',
    },
    {
      label: 'Total Potential',
      value: formatCurrency(stats.totalPotentialFunding),
      icon: CurrencyDollarIcon,
      iconBg: 'bg-emerald-50',
      iconColor: 'text-emerald-600',
      subtext: `${stats.avgScore}% avg match`,
      subtextColor: 'text-[var(--gr-text-tertiary)]',
    },
    {
      label: 'Due This Month',
      value: stats.upcomingThisMonth,
      icon: CalendarIcon,
      iconBg: 'bg-cyan-50',
      iconColor: 'text-cyan-600',
      subtext: stats.upcomingThisMonth === 0 ? 'No deadlines' : `${stats.urgentCount} within 7 days`,
      subtextColor: stats.urgentCount > 0 ? 'text-red-500' : 'text-[var(--gr-text-tertiary)]',
    },
    {
      label: 'Sources',
      value: Object.keys(stats.bySource).length,
      icon: BuildingLibraryIcon,
      iconBg: 'bg-purple-50',
      iconColor: 'text-purple-600',
      subtext: Object.entries(stats.bySource).slice(0, 2).map(([k]) => k).join(', ') || 'None',
      subtextColor: 'text-[var(--gr-text-tertiary)]',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      {statCards.map((stat, i) => {
        const Icon = stat.icon;
        return (
          <div
            key={stat.label}
            className="card p-5 animate-fade-in-up hover:border-[var(--gr-blue-200)] transition-all"
            style={{ animationDelay: `${i * 0.05}s` }}
          >
            <div className={`w-10 h-10 rounded-xl ${stat.iconBg} flex items-center justify-center mb-3`}>
              <Icon className={`w-5 h-5 ${stat.iconColor}`} />
            </div>
            <div className="text-2xl font-display font-semibold text-[var(--gr-text-primary)] mb-0.5">
              {stat.value}
            </div>
            <div className="text-sm text-[var(--gr-text-secondary)] mb-1">{stat.label}</div>
            <div className={`text-xs ${stat.subtextColor}`}>{stat.subtext}</div>
          </div>
        );
      })}
    </div>
  );
}

// Main GrantPortfolio Component
export function GrantPortfolio() {
  const [expandedSections, setExpandedSections] = useState<Set<PortfolioStatus>>(
    new Set(['watching', 'in_progress'])
  );

  // Fetch saved and applied grants
  const { data: savedData, isLoading: savedLoading } = useQuery({
    queryKey: ['portfolio-saved'],
    queryFn: () =>
      grantsApi.getMatches({
        status: 'saved',
        per_page: 100,
      }),
  });

  const { data: appliedData, isLoading: appliedLoading } = useQuery({
    queryKey: ['portfolio-applied'],
    queryFn: () =>
      grantsApi.getMatches({
        status: 'applied',
        per_page: 100,
      }),
  });

  const isLoading = savedLoading || appliedLoading;

  // Combine and organize grants by status
  const { allGrants, grantsByStatus } = useMemo(() => {
    const saved = savedData?.items || [];
    const applied = appliedData?.items || [];
    const all = [...saved, ...applied];

    // Deduplicate by grant ID
    const uniqueGrants = Array.from(
      new Map(all.map((g) => [g.grant_id, g])).values()
    );

    // Group by portfolio status
    const byStatus: Record<PortfolioStatus, GrantMatch[]> = {
      watching: [],
      in_progress: [],
      submitted: [],
      decided: [],
    };

    for (const grant of uniqueGrants) {
      const status = getPortfolioStatus(grant);
      byStatus[status].push(grant);
    }

    // Sort each group by deadline (nearest first)
    for (const status of Object.keys(byStatus) as PortfolioStatus[]) {
      byStatus[status].sort((a, b) => {
        if (!a.grant.deadline && !b.grant.deadline) return 0;
        if (!a.grant.deadline) return 1;
        if (!b.grant.deadline) return -1;
        return new Date(a.grant.deadline).getTime() - new Date(b.grant.deadline).getTime();
      });
    }

    return { allGrants: uniqueGrants, grantsByStatus: byStatus };
  }, [savedData, appliedData]);

  const toggleSection = (status: PortfolioStatus) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(status)) {
        next.delete(status);
      } else {
        next.add(status);
      }
      return next;
    });
  };

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-6 animate-fade-in-up">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-[var(--gr-blue-600)]/10 flex items-center justify-center">
              <BookmarkIcon className="w-5 h-5 text-[var(--gr-blue-600)]" />
            </div>
            <h1 className="text-3xl font-display font-medium text-[var(--gr-text-primary)]">
              Your Grant Portfolio
            </h1>
          </div>

        </div>

        {/* Summary Stats Cards */}
        <SummaryStats grants={allGrants} isLoading={isLoading} />

        {/* Timeline */}
        {!isLoading && allGrants.length > 0 && (
          <Timeline grants={allGrants} />
        )}

        {/* Loading state */}
        {isLoading && (
          <div className="space-y-8">
            {/* Timeline skeleton */}
            <div className="card p-6 mb-8">
              <div className="skeleton h-4 w-32 mb-4" />
              <div className="flex justify-between">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="flex flex-col items-center">
                    <div className="skeleton w-8 h-8 rounded-full" />
                    <div className="skeleton h-3 w-8 mt-2" />
                  </div>
                ))}
              </div>
            </div>

            {/* Cards skeleton */}
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="skeleton w-8 h-8 rounded-lg" />
                <div className="skeleton h-6 w-32" />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="card p-4">
                    <div className="skeleton h-4 w-full mb-2" />
                    <div className="skeleton h-4 w-3/4 mb-3" />
                    <div className="skeleton h-3 w-1/2 mb-3" />
                    <div className="flex justify-between">
                      <div className="skeleton h-3 w-16" />
                      <div className="skeleton h-5 w-12 rounded-full" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && allGrants.length === 0 && (
          <div className="card text-center py-16">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-[var(--gr-blue-50)] flex items-center justify-center mb-6">
              <BookmarkIcon className="w-8 h-8 text-[var(--gr-blue-500)]" />
            </div>
            <h3 className="text-xl font-display font-medium text-[var(--gr-text-primary)] mb-2">
              No saved grants yet
            </h3>
            <p className="text-[var(--gr-text-secondary)] max-w-sm mx-auto mb-6">
              Start building your portfolio by saving grants from the dashboard.
              Track deadlines and manage your applications all in one place.
            </p>
            <Link
              to="/dashboard"
              className="btn-primary inline-flex items-center gap-2"
            >
              <BookmarkIcon className="w-4 h-4" />
              Browse Grants
            </Link>
          </div>
        )}

        {/* Status groups */}
        {!isLoading && allGrants.length > 0 && (
          <div className="space-y-2">
            <StatusGroup
              status="watching"
              grants={grantsByStatus.watching}
              expanded={expandedSections.has('watching')}
              onToggleExpand={() => toggleSection('watching')}
            />
            <StatusGroup
              status="in_progress"
              grants={grantsByStatus.in_progress}
              expanded={expandedSections.has('in_progress')}
              onToggleExpand={() => toggleSection('in_progress')}
            />
            <StatusGroup
              status="submitted"
              grants={grantsByStatus.submitted}
              expanded={expandedSections.has('submitted')}
              onToggleExpand={() => toggleSection('submitted')}
            />
            <StatusGroup
              status="decided"
              grants={grantsByStatus.decided}
              expanded={expandedSections.has('decided')}
              onToggleExpand={() => toggleSection('decided')}
            />
          </div>
        )}
      </main>
    </div>
  );
}

export default GrantPortfolio;
