import { Link } from 'react-router-dom';
import {
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  BuildingOfficeIcon,
  CurrencyDollarIcon,
} from '@heroicons/react/24/outline';
import type { CalendarUpcomingDeadline, UrgencyLevel, CalendarEventType } from '../../types';

interface DeadlineListProps {
  deadlines: CalendarUpcomingDeadline[];
  isLoading?: boolean;
  emptyMessage?: string;
}

function getUrgencyIcon(urgency: UrgencyLevel) {
  switch (urgency) {
    case 'critical':
      return <ExclamationTriangleIcon className="w-5 h-5 text-red-500" />;
    case 'warning':
      return <ClockIcon className="w-5 h-5 text-amber-500" />;
    case 'normal':
    default:
      return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
  }
}

function getUrgencyBadge(urgency: UrgencyLevel, daysUntil: number) {
  const baseClasses = 'px-2 py-0.5 text-xs font-medium rounded-full';

  switch (urgency) {
    case 'critical':
      return (
        <span className={`${baseClasses} bg-red-100 text-red-700`}>
          {daysUntil === 0 ? 'Due Today' : daysUntil === 1 ? '1 day' : `${daysUntil} days`}
        </span>
      );
    case 'warning':
      return (
        <span className={`${baseClasses} bg-amber-100 text-amber-700`}>
          {daysUntil} days
        </span>
      );
    case 'normal':
    default:
      return (
        <span className={`${baseClasses} bg-green-100 text-green-700`}>
          {daysUntil} days
        </span>
      );
  }
}

function getTypeBadge(eventType: CalendarEventType) {
  if (eventType === 'saved') {
    return (
      <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-[var(--gr-blue-50)] text-[var(--gr-blue-700)]">
        Saved
      </span>
    );
  }
  return (
    <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-purple-50 text-purple-700">
      Pipeline
    </span>
  );
}

function formatAmount(amount: number | undefined): string {
  if (!amount) return '';
  if (amount >= 1000000) {
    return `$${(amount / 1000000).toFixed(1)}M`;
  }
  if (amount >= 1000) {
    return `$${(amount / 1000).toFixed(0)}K`;
  }
  return `$${amount.toLocaleString()}`;
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function DeadlineItemSkeleton() {
  return (
    <div className="p-4 border-b border-[var(--gr-border-subtle)] last:border-b-0">
      <div className="flex items-start gap-4">
        <div className="skeleton w-10 h-10 rounded-full flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="skeleton h-5 w-3/4" />
          <div className="skeleton h-4 w-1/2" />
          <div className="flex gap-2">
            <div className="skeleton h-5 w-16 rounded-full" />
            <div className="skeleton h-5 w-20 rounded-full" />
          </div>
        </div>
      </div>
    </div>
  );
}

export function DeadlineList({ deadlines, isLoading, emptyMessage = 'No upcoming deadlines' }: DeadlineListProps) {
  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] overflow-hidden">
        {[...Array(5)].map((_, i) => (
          <DeadlineItemSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (deadlines.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-8 text-center">
        <ClockIcon className="w-12 h-12 text-[var(--gr-text-tertiary)] mx-auto mb-3" />
        <p className="text-[var(--gr-text-secondary)]">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-[var(--gr-border-default)] overflow-hidden divide-y divide-[var(--gr-border-subtle)]">
      {deadlines.map((deadline) => (
        <Link
          key={deadline.grant_id}
          to={`/grants/${deadline.grant_id}`}
          className="block p-4 hover:bg-[var(--gr-bg-hover)] transition-colors"
        >
          <div className="flex items-start gap-4">
            {/* Urgency icon */}
            <div className="flex-shrink-0 mt-1">
              {getUrgencyIcon(deadline.urgency)}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              {/* Title */}
              <h3 className="font-medium text-[var(--gr-text-primary)] line-clamp-2 mb-1">
                {deadline.title}
              </h3>

              {/* Agency and amount */}
              <div className="flex items-center gap-4 text-sm text-[var(--gr-text-secondary)] mb-2">
                {deadline.agency && (
                  <span className="flex items-center gap-1 truncate">
                    <BuildingOfficeIcon className="w-4 h-4 flex-shrink-0" />
                    <span className="truncate">{deadline.agency}</span>
                  </span>
                )}
                {deadline.amount_max && (
                  <span className="flex items-center gap-1 flex-shrink-0">
                    <CurrencyDollarIcon className="w-4 h-4" />
                    {formatAmount(deadline.amount_max)}
                  </span>
                )}
              </div>

              {/* Badges */}
              <div className="flex items-center flex-wrap gap-2">
                {getUrgencyBadge(deadline.urgency, deadline.days_until_deadline)}
                {getTypeBadge(deadline.event_type)}
                {deadline.stage && (
                  <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-[var(--gr-gray-100)] text-[var(--gr-gray-600)] capitalize">
                    {deadline.stage}
                  </span>
                )}
              </div>
            </div>

            {/* Date */}
            <div className="flex-shrink-0 text-right">
              <div className="text-sm font-medium text-[var(--gr-text-primary)]">
                {formatDate(deadline.deadline)}
              </div>
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}

export default DeadlineList;
