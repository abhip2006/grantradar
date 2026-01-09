import {
  CalendarIcon,
  PencilIcon,
  TrashIcon,
  ClockIcon,
  ArrowPathIcon,
  BellAlertIcon,
  ExclamationTriangleIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import type { Deadline, DeadlineStatus } from '../../types';
import { DEADLINE_STATUS_CONFIG, DEADLINE_PRIORITY_CONFIG } from '../../types';
import { format } from 'date-fns';

interface DeadlinesListProps {
  deadlines: Deadline[];
  onEdit: (deadline: Deadline) => void;
  onDelete: (id: string) => void;
  onStatusChange: (id: string, status: DeadlineStatus) => void;
  onViewHistory?: (deadline: Deadline) => void;
}

// Status workflow - valid next statuses from each status
const STATUS_TRANSITIONS: Record<DeadlineStatus, DeadlineStatus[]> = {
  not_started: ['drafting'],
  drafting: ['internal_review', 'not_started'],
  internal_review: ['submitted', 'drafting'],
  submitted: ['under_review', 'internal_review'],
  under_review: ['awarded', 'rejected'],
  awarded: [],
  rejected: [],
};

export function DeadlinesList({ deadlines, onEdit, onDelete, onStatusChange, onViewHistory }: DeadlinesListProps) {
  if (deadlines.length === 0) {
    return (
      <div className="text-center py-12">
        <CalendarIcon className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">No deadlines</h3>
        <p className="mt-1 text-sm text-gray-500">
          Get started by creating a new deadline.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white shadow-sm rounded-xl overflow-hidden border border-gray-100">
      <ul className="divide-y divide-gray-100">
        {deadlines.map((deadline) => {
          const statusConfig = DEADLINE_STATUS_CONFIG[deadline.status];
          const priorityConfig = DEADLINE_PRIORITY_CONFIG[deadline.priority];
          const nextStatuses = STATUS_TRANSITIONS[deadline.status];

          return (
            <li
              key={deadline.id}
              className={`p-4 hover:bg-gray-50/50 transition-colors ${deadline.is_overdue ? 'bg-red-50/30' : ''}`}
            >
              <div className="flex items-center justify-between gap-4">
                <div className="flex-1 min-w-0">
                  {/* Title row */}
                  <div className="flex items-center gap-3">
                    <div
                      className="w-3 h-3 rounded-full flex-shrink-0 shadow-sm"
                      style={{ backgroundColor: deadline.color }}
                    />
                    <h3 className="text-sm font-semibold text-gray-900 truncate">
                      {deadline.title}
                    </h3>

                    {/* Recurring indicator */}
                    {deadline.is_recurring && (
                      <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-50 text-purple-600 text-xs">
                        <ArrowPathIcon className="w-3 h-3" />
                        Recurring
                      </span>
                    )}

                    {/* Escalation indicator */}
                    {deadline.escalation_sent && (
                      <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-50 text-amber-600 text-xs">
                        <ExclamationTriangleIcon className="w-3 h-3" />
                        Escalated
                      </span>
                    )}
                  </div>

                  {/* Badges row */}
                  <div className="mt-2 flex items-center gap-2 flex-wrap">
                    {/* Status badge */}
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium ${statusConfig.bgColor} ${statusConfig.color}`}>
                      {statusConfig.label}
                    </span>

                    {/* Priority badge */}
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium ${priorityConfig.bgColor} ${priorityConfig.color}`}>
                      {priorityConfig.label}
                      {deadline.priority === 'critical' && (
                        <span className="ml-1 flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-red-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                        </span>
                      )}
                    </span>

                    {/* Funder */}
                    {deadline.funder && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded bg-gray-100 text-gray-600 text-xs">
                        {deadline.funder}
                      </span>
                    )}

                    {/* Mechanism */}
                    {deadline.mechanism && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded bg-blue-50 text-blue-600 text-xs">
                        {deadline.mechanism}
                      </span>
                    )}
                  </div>

                  {/* Meta row */}
                  <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
                    {/* Deadline date */}
                    <span className="flex items-center gap-1">
                      <CalendarIcon className="h-3.5 w-3.5" />
                      {format(new Date(deadline.sponsor_deadline), 'MMM d, yyyy')}
                    </span>

                    {/* Days remaining */}
                    <span className={`flex items-center gap-1 ${
                      deadline.is_overdue
                        ? 'text-red-600 font-medium'
                        : deadline.days_until_deadline <= 7
                          ? 'text-orange-600 font-medium'
                          : ''
                    }`}>
                      <ClockIcon className="h-3.5 w-3.5" />
                      {deadline.is_overdue
                        ? `${Math.abs(deadline.days_until_deadline)} days overdue`
                        : deadline.days_until_deadline === 0
                          ? 'Due today'
                          : deadline.days_until_deadline === 1
                            ? '1 day left'
                            : `${deadline.days_until_deadline} days left`
                      }
                    </span>

                    {/* Reminders count */}
                    {deadline.reminder_config?.length > 0 && (
                      <span className="flex items-center gap-1 text-blue-500">
                        <BellAlertIcon className="h-3.5 w-3.5" />
                        {deadline.reminder_config.length} reminders
                      </span>
                    )}

                    {/* View history link */}
                    {onViewHistory && (
                      <button
                        onClick={() => onViewHistory(deadline)}
                        className="flex items-center gap-1 text-gray-400 hover:text-blue-600 transition-colors"
                      >
                        View history
                        <ChevronRightIcon className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Actions column */}
                <div className="flex items-center gap-1">
                  {/* Quick status change buttons */}
                  {nextStatuses.length > 0 && (
                    <div className="flex items-center gap-1 mr-2">
                      {nextStatuses.slice(0, 2).map(nextStatus => {
                        const nextConfig = DEADLINE_STATUS_CONFIG[nextStatus];
                        return (
                          <button
                            key={nextStatus}
                            onClick={() => onStatusChange(deadline.id, nextStatus)}
                            className={`px-2 py-1 text-xs rounded-lg border transition-colors hover:shadow-sm ${nextConfig.bgColor} ${nextConfig.color} border-current/20`}
                            title={`Move to ${nextConfig.label}`}
                          >
                            {nextConfig.label}
                          </button>
                        );
                      })}
                    </div>
                  )}

                  <button
                    onClick={() => onEdit(deadline)}
                    className="p-2 text-gray-400 hover:text-blue-600 rounded-lg hover:bg-blue-50 transition-colors"
                    title="Edit"
                  >
                    <PencilIcon className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => onDelete(deadline.id)}
                    className="p-2 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors"
                    title="Delete"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
