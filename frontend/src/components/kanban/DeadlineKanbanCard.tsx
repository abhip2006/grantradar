import { useState } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { motion, AnimatePresence } from 'motion/react';
import { format, formatDistanceToNow } from 'date-fns';
import type { Deadline, DeadlinePriority } from '../../types';
import {
  CalendarIcon,
  ExclamationCircleIcon,
  ArrowPathIcon,
  BellIcon,
  EyeIcon,
  PencilSquareIcon,
  EllipsisHorizontalIcon,
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
  const [isHovered, setIsHovered] = useState(false);

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

  const handleActionClick = (e: React.MouseEvent, action: string) => {
    e.stopPropagation();
    console.log(`Action: ${action} on deadline ${deadline.id}`);
  };

  return (
    <motion.div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`
        kanban-card kanban-card-enhanced kanban-card-status-transition
        bg-white rounded-xl p-4 shadow-sm
        border-l-4 ${priorityConfig.className}
        border border-gray-100
        cursor-pointer relative
        ${isDragging || isSortableDragging ? 'kanban-card-is-dragging opacity-40' : ''}
        ${getUrgencyStyles()}
        ${isSortableDragging ? 'z-50' : ''}
      `}
      initial={false}
      animate={{
        scale: isDragging || isSortableDragging ? 1.02 : 1,
        rotate: isDragging ? 2 : 0,
        boxShadow: isDragging || isSortableDragging
          ? '0 20px 40px rgba(0, 0, 0, 0.18), 0 10px 20px rgba(0, 0, 0, 0.12)'
          : isHovered
            ? '0 8px 16px rgba(0, 0, 0, 0.08), 0 16px 32px rgba(0, 0, 0, 0.06)'
            : '0 1px 2px rgba(0, 0, 0, 0.04), 0 2px 4px rgba(0, 0, 0, 0.02)',
      }}
      transition={{
        type: 'spring',
        stiffness: 400,
        damping: 25,
      }}
    >
      {/* Hover action buttons */}
      <AnimatePresence>
        {isHovered && !isDragging && !isSortableDragging && (
          <motion.div
            className="kanban-card-actions"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
          >
            <button
              className="kanban-card-action-btn"
              onClick={(e) => handleActionClick(e, 'view')}
              title="View details"
            >
              <EyeIcon className="w-4 h-4" />
            </button>
            <button
              className="kanban-card-action-btn"
              onClick={(e) => handleActionClick(e, 'edit')}
              title="Edit"
            >
              <PencilSquareIcon className="w-4 h-4" />
            </button>
            <button
              className="kanban-card-action-btn"
              onClick={(e) => handleActionClick(e, 'more')}
              title="More options"
            >
              <EllipsisHorizontalIcon className="w-4 h-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Title */}
      <div className="mb-3 pr-20">
        <h4 className="font-semibold text-gray-900 text-sm line-clamp-2 leading-snug">
          {deadline.title}
        </h4>
      </div>

      {/* Funder badge */}
      {deadline.funder && (
        <motion.div
          className="mb-3"
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.05 }}
        >
          <span className="inline-flex items-center px-2.5 py-1 text-xs font-medium rounded-lg bg-gray-50 text-gray-600 border border-gray-100 transition-colors hover:bg-gray-100 hover:border-gray-200">
            {deadline.funder}
          </span>
        </motion.div>
      )}

      {/* Mechanism badge */}
      {deadline.mechanism && (
        <motion.div
          className="mb-3"
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.08 }}
        >
          <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-blue-50 text-blue-600 transition-colors hover:bg-blue-100">
            {deadline.mechanism}
          </span>
        </motion.div>
      )}

      {/* Metadata row */}
      <div className="flex items-center flex-wrap gap-3 text-xs">
        {/* Recurring indicator */}
        {deadline.is_recurring && (
          <motion.div
            className="flex items-center gap-1.5 text-purple-500 transition-colors hover:text-purple-700"
            title="Recurring deadline"
            animate={{ rotate: [0, 360] }}
            transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
          >
            <ArrowPathIcon className="w-4 h-4" />
          </motion.div>
        )}

        {/* Reminder indicator */}
        {hasReminders && (
          <motion.div
            className="flex items-center gap-1.5 text-blue-500 transition-colors hover:text-blue-700"
            title={`${deadline.reminder_config.length} reminders set`}
            animate={{ scale: [1, 1.1, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <BellIcon className="w-4 h-4" />
          </motion.div>
        )}

        {/* Due date with countdown animation */}
        <motion.div
          className={`flex items-center gap-1.5 transition-colors ${isOverdue ? 'text-red-600 font-medium' : 'text-gray-500'}`}
          animate={
            !isOverdue && deadline.days_until_deadline <= 3
              ? { scale: [1, 1.05, 1] }
              : {}
          }
          transition={{
            repeat: !isOverdue && deadline.days_until_deadline <= 3 ? Infinity : 0,
            duration: 2,
          }}
        >
          {isOverdue ? (
            <ExclamationCircleIcon className="w-4 h-4" />
          ) : (
            <CalendarIcon className="w-4 h-4" />
          )}
          <span className={`font-medium ${
            !isOverdue && deadline.days_until_deadline <= 3 ? 'kanban-deadline-urgent' : ''
          }`}>
            {isOverdue
              ? `Overdue ${formatDistanceToNow(deadlineDate)}`
              : format(deadlineDate, 'MMM d, yyyy')
            }
          </span>
        </motion.div>
      </div>

      {/* Days remaining / Overdue indicator */}
      <AnimatePresence>
        {!isOverdue && deadline.days_until_deadline <= 14 && (
          <motion.div
            className={`mt-3 pt-3 border-t border-gray-50 text-xs ${
              deadline.days_until_deadline <= 3 ? 'text-red-600' :
              deadline.days_until_deadline <= 7 ? 'text-orange-600' :
              'text-yellow-600'
            }`}
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
          >
            <motion.span
              className="font-medium"
              animate={
                deadline.days_until_deadline <= 3
                  ? { scale: [1, 1.02, 1] }
                  : {}
              }
              transition={{
                repeat: deadline.days_until_deadline <= 3 ? Infinity : 0,
                duration: 1.5,
              }}
            >
              {deadline.days_until_deadline === 0
                ? 'Due today!'
                : deadline.days_until_deadline === 1
                  ? 'Due tomorrow'
                  : `${deadline.days_until_deadline} days remaining`
              }
            </motion.span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Priority indicator for critical */}
      {deadline.priority === 'critical' && !deadline.escalation_sent && (
        <div className="absolute top-3 right-3 kanban-status-urgent">
          <span className="flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
          </span>
        </div>
      )}

      {/* Escalation indicator */}
      {deadline.escalation_sent && (
        <motion.div
          className="absolute top-3 right-3"
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 500, damping: 25 }}
        >
          <span className="px-1.5 py-0.5 text-[10px] font-medium bg-amber-100 text-amber-700 rounded animate-pulse">
            Escalated
          </span>
        </motion.div>
      )}
    </motion.div>
  );
}

export default DeadlineKanbanCard;
