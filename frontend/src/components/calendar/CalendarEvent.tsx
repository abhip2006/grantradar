import { Link } from 'react-router-dom';
import type { CalendarEvent as CalendarEventType, UrgencyLevel, CalendarEventType as EventSourceType } from '../../types';

interface CalendarEventProps {
  event: CalendarEventType;
  compact?: boolean;
}

function getUrgencyClasses(urgency: UrgencyLevel): { bg: string; text: string; border: string } {
  switch (urgency) {
    case 'critical':
      return {
        bg: 'bg-red-50',
        text: 'text-red-700',
        border: 'border-red-200',
      };
    case 'warning':
      return {
        bg: 'bg-amber-50',
        text: 'text-amber-700',
        border: 'border-amber-200',
      };
    case 'normal':
    default:
      return {
        bg: 'bg-green-50',
        text: 'text-green-700',
        border: 'border-green-200',
      };
  }
}

function getTypeClasses(eventType: EventSourceType): { bg: string; text: string } {
  switch (eventType) {
    case 'saved':
      return {
        bg: 'bg-[var(--gr-blue-50)]',
        text: 'text-[var(--gr-blue-700)]',
      };
    case 'pipeline':
      return {
        bg: 'bg-purple-50',
        text: 'text-purple-700',
      };
    default:
      return {
        bg: 'bg-[var(--gr-gray-100)]',
        text: 'text-[var(--gr-gray-600)]',
      };
  }
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

export function CalendarEventChip({ event, compact = false }: CalendarEventProps) {
  const urgencyClasses = getUrgencyClasses(event.urgency);
  const typeClasses = getTypeClasses(event.event_type);

  if (compact) {
    return (
      <Link
        to={`/grants/${event.grant_id}`}
        className={`block px-2 py-1 text-xs rounded truncate transition-all hover:opacity-80 ${urgencyClasses.bg} ${urgencyClasses.text} border ${urgencyClasses.border}`}
        title={event.title}
      >
        {event.title}
      </Link>
    );
  }

  return (
    <Link
      to={`/grants/${event.grant_id}`}
      className={`block p-3 rounded-lg transition-all hover:shadow-md ${urgencyClasses.bg} border ${urgencyClasses.border}`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <h4 className={`font-medium text-sm line-clamp-2 ${urgencyClasses.text}`}>
          {event.title}
        </h4>
        <span
          className={`flex-shrink-0 px-2 py-0.5 text-xs font-medium rounded-full ${typeClasses.bg} ${typeClasses.text}`}
        >
          {event.event_type === 'saved' ? 'Saved' : 'Pipeline'}
        </span>
      </div>

      <div className="space-y-1">
        {event.agency && (
          <p className="text-xs text-[var(--gr-text-tertiary)] truncate">
            {event.agency}
          </p>
        )}

        <div className="flex items-center justify-between text-xs">
          <span className={`font-medium ${urgencyClasses.text}`}>
            {event.days_until_deadline === 0
              ? 'Due today'
              : event.days_until_deadline === 1
                ? '1 day left'
                : event.days_until_deadline < 0
                  ? `${Math.abs(event.days_until_deadline)} days ago`
                  : `${event.days_until_deadline} days left`}
          </span>
          {event.amount_max && (
            <span className="text-[var(--gr-text-secondary)]">
              {formatAmount(event.amount_max)}
            </span>
          )}
        </div>

        {event.stage && (
          <div className="mt-1">
            <span className="inline-flex items-center px-2 py-0.5 text-xs rounded-full bg-[var(--gr-gray-100)] text-[var(--gr-gray-600)] capitalize">
              {event.stage}
            </span>
          </div>
        )}
      </div>
    </Link>
  );
}

export default CalendarEventChip;
