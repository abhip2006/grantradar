import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { format, formatDistanceToNow } from 'date-fns';
import type { Deadline, DeadlinePriority } from '../../types';
import {
  CalendarIcon,
  ExclamationCircleIcon,
  ArrowPathIcon,
  BellIcon,
} from '@heroicons/react/24/outline';

const PRIORITY_CONFIG: Record<DeadlinePriority, { className: string; label: string; dotColor: string }> = {
  low: { className: 'border-l-gray-300', label: 'Low', dotColor: 'bg-gray-400' },
  medium: { className: 'border-l-blue-400', label: 'Medium', dotColor: 'bg-blue-500' },
  high: { className: 'border-l-orange-400', label: 'High', dotColor: 'bg-orange-500' },
  critical: { className: 'border-l-red-500', label: 'Critical', dotColor: 'bg-red-500' },
};

interface DeadlineKanbanCardProps {
  deadline: Deadline;
  isDragging?: boolean;
  onClick?: () => void;
}

export function DeadlineKanbanCard({ deadline, isDragging, onClick }: DeadlineKanbanCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging: isSortableDragging,
  } = useSortable({ id: deadline.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const priorityConfig = PRIORITY_CONFIG[deadline.priority];
  const deadlineDate = new Date(deadline.sponsor_deadline);
  const isOverdue = deadline.is_overdue;
  const hasReminders = deadline.reminder_config && deadline.reminder_config.length > 0;

  // Urgency styling
  const getUrgencyStyles = () => {
    if (isOverdue) return 'ring-2 ring-red-300 ring-offset-1 bg-red-50/50';
    if (deadline.urgency_level === 'critical') return 'ring-2 ring-orange-200 ring-offset-1';
    if (deadline.urgency_level === 'high') return 'ring-1 ring-yellow-200';
    return '';
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={onClick}
      className={`
        kanban-card bg-white rounded-xl p-4 shadow-sm
        border-l-4 ${priorityConfig.className}
        border border-gray-100
        hover:shadow-md hover:border-gray-200
        transition-all duration-200 cursor-pointer
        ${isDragging || isSortableDragging ? 'opacity-50 shadow-lg scale-105' : ''}
        ${getUrgencyStyles()}
        ${isSortableDragging ? 'z-50' : ''}
      `}
    >
      {/* Title */}
      <div className="mb-3">
        <h4 className="font-semibold text-gray-900 text-sm line-clamp-2 leading-snug">
          {deadline.title}
        </h4>
      </div>

      {/* Funder badge */}
      {deadline.funder && (
        <div className="mb-3">
          <span className="inline-flex items-center px-2.5 py-1 text-xs font-medium rounded-lg bg-gray-50 text-gray-600 border border-gray-100">
            {deadline.funder}
          </span>
        </div>
      )}

      {/* Mechanism badge */}
      {deadline.mechanism && (
        <div className="mb-3">
          <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-blue-50 text-blue-600">
            {deadline.mechanism}
          </span>
        </div>
      )}

      {/* Metadata row */}
      <div className="flex items-center flex-wrap gap-3 text-xs">
        {/* Recurring indicator */}
        {deadline.is_recurring && (
          <div className="flex items-center gap-1.5 text-purple-500" title="Recurring deadline">
            <ArrowPathIcon className="w-4 h-4" />
          </div>
        )}

        {/* Reminder indicator */}
        {hasReminders && (
          <div className="flex items-center gap-1.5 text-blue-500" title={`${deadline.reminder_config.length} reminders set`}>
            <BellIcon className="w-4 h-4" />
          </div>
        )}

        {/* Due date */}
        <div className={`flex items-center gap-1.5 ${isOverdue ? 'text-red-600 font-medium' : 'text-gray-500'}`}>
          {isOverdue ? (
            <ExclamationCircleIcon className="w-4 h-4" />
          ) : (
            <CalendarIcon className="w-4 h-4" />
          )}
          <span className="font-medium">
            {isOverdue
              ? `Overdue ${formatDistanceToNow(deadlineDate)}`
              : format(deadlineDate, 'MMM d, yyyy')
            }
          </span>
        </div>
      </div>

      {/* Days remaining / Overdue indicator */}
      {!isOverdue && deadline.days_until_deadline <= 14 && (
        <div className={`mt-3 pt-3 border-t border-gray-50 text-xs ${
          deadline.days_until_deadline <= 3 ? 'text-red-600' :
          deadline.days_until_deadline <= 7 ? 'text-orange-600' :
          'text-yellow-600'
        }`}>
          <span className="font-medium">
            {deadline.days_until_deadline === 0
              ? 'Due today!'
              : deadline.days_until_deadline === 1
                ? 'Due tomorrow'
                : `${deadline.days_until_deadline} days remaining`
            }
          </span>
        </div>
      )}

      {/* Priority indicator for critical */}
      {deadline.priority === 'critical' && (
        <div className="absolute top-3 right-3">
          <span className="flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
          </span>
        </div>
      )}

      {/* Escalation indicator */}
      {deadline.escalation_sent && (
        <div className="absolute top-3 right-3">
          <span className="px-1.5 py-0.5 text-[10px] font-medium bg-amber-100 text-amber-700 rounded">
            Escalated
          </span>
        </div>
      )}
    </div>
  );
}

export default DeadlineKanbanCard;
