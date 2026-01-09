import { useMemo } from 'react';
import {
  ArrowRightIcon,
  ArrowLeftIcon,
  FlagIcon,
  BoltIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import type { ApplicationEventsResponse, WorkflowEvent } from '../../types/workflowAnalytics';

interface ApplicationEventsTimelineProps {
  data: ApplicationEventsResponse;
  isLoading?: boolean;
  maxEvents?: number;
}

// Event type configuration
const EVENT_TYPE_CONFIG: Record<
  WorkflowEvent['event_type'],
  {
    label: string;
    icon: React.ReactNode;
    color: string;
    bgColor: string;
    borderColor: string;
  }
> = {
  stage_enter: {
    label: 'Entered Stage',
    icon: <ArrowRightIcon className="h-4 w-4" />,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
  stage_exit: {
    label: 'Exited Stage',
    icon: <ArrowLeftIcon className="h-4 w-4" />,
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
  },
  action: {
    label: 'Action Taken',
    icon: <BoltIcon className="h-4 w-4" />,
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
  },
  milestone: {
    label: 'Milestone',
    icon: <FlagIcon className="h-4 w-4" />,
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
  },
};

// Stage labels
const STAGE_LABELS: Record<string, string> = {
  researching: 'Researching',
  writing: 'Writing',
  internal_review: 'Internal Review',
  submitted: 'Submitted',
  under_review: 'Under Review',
  awarded: 'Awarded',
  rejected: 'Rejected',
};

function getStageLabel(stage: string): string {
  return STAGE_LABELS[stage.toLowerCase()] || stage;
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatTime(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours === 0) {
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      return diffMinutes <= 1 ? 'Just now' : `${diffMinutes}m ago`;
    }
    return `${diffHours}h ago`;
  }
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return `${Math.floor(diffDays / 30)} months ago`;
}

function TimelineEvent({ event, isFirst: _isFirst, isLast }: { event: WorkflowEvent; isFirst: boolean; isLast: boolean }) {
  const config = EVENT_TYPE_CONFIG[event.event_type];

  return (
    <div className="relative flex gap-4">
      {/* Timeline line */}
      <div className="flex flex-col items-center">
        <div
          className={`
            w-8 h-8 rounded-full flex items-center justify-center z-10
            ${config.bgColor} border-2 ${config.borderColor}
          `}
        >
          <span className={config.color}>{config.icon}</span>
        </div>
        {!isLast && (
          <div className="w-0.5 flex-1 bg-[var(--gr-border-subtle)] -my-1"></div>
        )}
      </div>

      {/* Event content */}
      <div className={`flex-1 pb-6 ${isLast ? 'pb-0' : ''}`}>
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-sm font-medium text-[var(--gr-text-primary)]">
              {config.label}: {getStageLabel(event.stage)}
            </p>
            {event.metadata && Object.keys(event.metadata).length > 0 && (
              <div className="mt-1 text-xs text-[var(--gr-text-tertiary)]">
                {Object.entries(event.metadata).map(([key, value]) => (
                  <span key={key} className="mr-3">
                    {key}: {String(value)}
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="text-right flex-shrink-0">
            <p className="text-xs font-medium text-[var(--gr-text-secondary)]">
              {formatRelativeTime(event.occurred_at)}
            </p>
            <p className="text-xs text-[var(--gr-text-tertiary)]">
              {formatDate(event.occurred_at)} at {formatTime(event.occurred_at)}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="w-16 h-16 rounded-full bg-gray-50 flex items-center justify-center mb-4">
        <ClockIcon className="h-8 w-8 text-gray-400" />
      </div>
      <p className="text-[var(--gr-text-primary)] font-medium mb-1">
        No events recorded
      </p>
      <p className="text-sm text-[var(--gr-text-tertiary)]">
        Events will appear here as the application progresses
      </p>
    </div>
  );
}

function TimelineSummary({ events }: { events: WorkflowEvent[] }) {
  const summary = useMemo(() => {
    const stageEnters = events.filter((e) => e.event_type === 'stage_enter').length;
    const actions = events.filter((e) => e.event_type === 'action').length;
    const milestones = events.filter((e) => e.event_type === 'milestone').length;

    // Calculate time from first to last event
    if (events.length >= 2) {
      const firstDate = new Date(events[events.length - 1].occurred_at);
      const lastDate = new Date(events[0].occurred_at);
      const diffDays = Math.ceil((lastDate.getTime() - firstDate.getTime()) / (1000 * 60 * 60 * 24));
      return { stageEnters, actions, milestones, totalDays: diffDays };
    }

    return { stageEnters, actions, milestones, totalDays: 0 };
  }, [events]);

  return (
    <div className="grid grid-cols-4 gap-2 mb-4">
      <div className="bg-blue-50 rounded-lg p-2 text-center">
        <p className="text-lg font-display font-bold text-blue-600">{summary.stageEnters}</p>
        <p className="text-xs text-[var(--gr-text-tertiary)]">Stages</p>
      </div>
      <div className="bg-amber-50 rounded-lg p-2 text-center">
        <p className="text-lg font-display font-bold text-amber-600">{summary.actions}</p>
        <p className="text-xs text-[var(--gr-text-tertiary)]">Actions</p>
      </div>
      <div className="bg-emerald-50 rounded-lg p-2 text-center">
        <p className="text-lg font-display font-bold text-emerald-600">{summary.milestones}</p>
        <p className="text-xs text-[var(--gr-text-tertiary)]">Milestones</p>
      </div>
      <div className="bg-gray-50 rounded-lg p-2 text-center">
        <p className="text-lg font-display font-bold text-gray-600">{summary.totalDays}</p>
        <p className="text-xs text-[var(--gr-text-tertiary)]">Days</p>
      </div>
    </div>
  );
}

export function ApplicationEventsTimeline({
  data,
  isLoading,
  maxEvents = 10,
}: ApplicationEventsTimelineProps) {
  // Sort events by date (most recent first)
  const sortedEvents = useMemo(() => {
    return [...data.events]
      .sort((a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime())
      .slice(0, maxEvents);
  }, [data.events, maxEvents]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <div className="animate-pulse">
          <div className="h-6 w-48 bg-gray-200 rounded mb-6"></div>
          <div className="space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex gap-4">
                <div className="w-8 h-8 rounded-full bg-gray-100"></div>
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-3 bg-gray-100 rounded w-1/2"></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ClockIcon className="h-5 w-5 text-[var(--gr-text-tertiary)]" />
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
            Application Timeline
          </h3>
        </div>
        {data.total > 0 && (
          <span className="text-xs text-[var(--gr-text-tertiary)]">
            {data.total} events
          </span>
        )}
      </div>

      {sortedEvents.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          <TimelineSummary events={sortedEvents} />

          <div className="space-y-0">
            {sortedEvents.map((event, index) => (
              <TimelineEvent
                key={event.id}
                event={event}
                isFirst={index === 0}
                isLast={index === sortedEvents.length - 1}
              />
            ))}
          </div>

          {data.total > maxEvents && (
            <div className="mt-4 pt-4 border-t border-[var(--gr-border-subtle)] text-center">
              <p className="text-sm text-[var(--gr-text-tertiary)]">
                Showing {maxEvents} of {data.total} events
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default ApplicationEventsTimeline;
