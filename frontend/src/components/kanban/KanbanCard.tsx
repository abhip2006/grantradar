import { useState, useEffect } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { motion, AnimatePresence } from 'motion/react';
import { format } from 'date-fns';
import type { KanbanCard as KanbanCardType, Priority } from '../../types/kanban';
import {
  CalendarIcon,
  PaperClipIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  EyeIcon,
  PencilSquareIcon,
  EllipsisHorizontalIcon,
} from '@heroicons/react/24/outline';

const PRIORITY_CONFIG: Record<Priority, { className: string; label: string; accentColor: string }> = {
  low: { className: 'kanban-card-priority-low', label: 'Low', accentColor: 'slate' },
  medium: { className: 'kanban-card-priority-medium', label: 'Medium', accentColor: 'blue' },
  high: { className: 'kanban-card-priority-high', label: 'High', accentColor: 'amber' },
  critical: { className: 'kanban-card-priority-critical', label: 'Critical', accentColor: 'red' },
};

interface KanbanCardProps {
  card: KanbanCardType;
  isDragging?: boolean;
  onClick?: () => void;
}

export function KanbanCard({ card, isDragging, onClick }: KanbanCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [hasAnimated, setHasAnimated] = useState(false);

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging: isSortableDragging,
  } = useSortable({ id: card.id });

  // Track when progress bar should animate
  useEffect(() => {
    const timer = setTimeout(() => setHasAnimated(true), 100);
    return () => clearTimeout(timer);
  }, []);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const isOverdue = card.target_date && new Date(card.target_date) < new Date() &&
    card.stage !== 'awarded' && card.stage !== 'rejected';

  // Get grant title from card - API returns flat fields
  const grantTitle = card.grant_title || card.grant?.title || 'Untitled Application';
  const grantAgency = card.grant_agency || card.grant?.agency;

  const priorityConfig = PRIORITY_CONFIG[card.priority];
  const subtaskProgress = card.subtask_progress?.total > 0
    ? Math.round((card.subtask_progress.completed / card.subtask_progress.total) * 100)
    : 0;

  // Calculate days until deadline
  const daysUntilDeadline = card.target_date
    ? Math.ceil((new Date(card.target_date).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24))
    : null;

  const handleActionClick = (e: React.MouseEvent, action: string) => {
    e.stopPropagation();
    // Action handlers would go here
    console.log(`Action: ${action} on card ${card.id}`);
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
        ${priorityConfig.className}
        ${isDragging || isSortableDragging ? 'kanban-card-is-dragging' : ''}
        ${isOverdue ? 'ring-2 ring-red-200 ring-offset-1' : ''}
        ${isSortableDragging ? 'opacity-40' : ''}
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

      {/* Header with title */}
      <div className="mb-3 pr-20">
        <h4 className="font-semibold text-gray-900 text-sm line-clamp-2 leading-snug">
          {grantTitle}
        </h4>
      </div>

      {/* Agency badge with smooth color transition */}
      {grantAgency && (
        <motion.div
          className="mb-3"
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.05 }}
        >
          <span className="inline-flex items-center px-2.5 py-1 text-xs font-medium rounded-lg bg-gray-50 text-gray-600 border border-gray-100 transition-colors hover:bg-gray-100 hover:border-gray-200">
            {grantAgency}
          </span>
        </motion.div>
      )}

      {/* Progress bar for subtasks - animated */}
      {card.subtask_progress && card.subtask_progress.total > 0 && (
        <div className="mb-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-gray-500 font-medium">Progress</span>
            <motion.span
              className="text-xs font-semibold text-gray-700"
              key={`progress-${card.subtask_progress.completed}`}
              initial={{ scale: 1.2, color: '#2d5a47' }}
              animate={{ scale: 1, color: '#374151' }}
              transition={{ duration: 0.3 }}
            >
              {card.subtask_progress.completed}/{card.subtask_progress.total}
            </motion.span>
          </div>
          <div className="kanban-progress-bar">
            <motion.div
              className="kanban-progress-fill"
              initial={{ width: 0 }}
              animate={{ width: hasAnimated ? `${subtaskProgress}%` : 0 }}
              transition={{
                duration: 0.8,
                ease: [0.16, 1, 0.3, 1],
                delay: 0.1
              }}
            />
          </div>
        </div>
      )}

      {/* Metadata row */}
      <div className="flex items-center flex-wrap gap-3 text-xs">
        {/* Subtask count icon */}
        {card.subtask_progress && card.subtask_progress.total > 0 && (
          <div className="flex items-center gap-1.5 text-gray-500 transition-colors hover:text-gray-700">
            <CheckCircleIcon className="w-4 h-4" />
            <span className="font-medium">{card.subtask_progress.completed}/{card.subtask_progress.total}</span>
          </div>
        )}

        {/* Attachments */}
        {card.attachments_count > 0 && (
          <div className="flex items-center gap-1.5 text-gray-500 transition-colors hover:text-gray-700">
            <PaperClipIcon className="w-4 h-4" />
            <span className="font-medium">{card.attachments_count}</span>
          </div>
        )}

        {/* Due date with countdown animation for urgent */}
        {card.target_date && (
          <motion.div
            className={`flex items-center gap-1.5 transition-colors ${
              isOverdue
                ? 'text-red-600'
                : daysUntilDeadline !== null && daysUntilDeadline <= 3
                  ? 'text-orange-600'
                  : 'text-gray-500'
            }`}
            animate={
              daysUntilDeadline !== null && daysUntilDeadline <= 3 && !isOverdue
                ? { scale: [1, 1.05, 1] }
                : {}
            }
            transition={{
              repeat: daysUntilDeadline !== null && daysUntilDeadline <= 3 ? Infinity : 0,
              duration: 2,
            }}
          >
            {isOverdue ? (
              <ExclamationCircleIcon className="w-4 h-4" />
            ) : (
              <CalendarIcon className="w-4 h-4" />
            )}
            <span className={`font-medium ${
              daysUntilDeadline !== null && daysUntilDeadline <= 3 && !isOverdue
                ? 'kanban-deadline-urgent'
                : ''
            }`}>
              {format(new Date(card.target_date), 'MMM d')}
            </span>
          </motion.div>
        )}
      </div>

      {/* Assignees with stagger animation */}
      {card.assignees && card.assignees.length > 0 && (
        <motion.div
          className="flex items-center gap-1 mt-3 pt-3 border-t border-gray-50"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
        >
          <div className="flex -space-x-2">
            {card.assignees.slice(0, 3).map((assignee, idx) => (
              <motion.div
                key={assignee.user_id}
                className="w-7 h-7 rounded-full bg-gradient-to-br from-gray-200 to-gray-300 border-2 border-white flex items-center justify-center shadow-sm transition-transform hover:scale-110 hover:z-10"
                title={assignee.user?.name || assignee.user?.email || 'Unknown'}
                style={{ zIndex: 3 - idx }}
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: idx * 0.05 + 0.1 }}
                whileHover={{ scale: 1.15, zIndex: 10 }}
              >
                <span className="text-xs font-semibold text-gray-600">
                  {(assignee.user?.name || assignee.user?.email || '?')[0].toUpperCase()}
                </span>
              </motion.div>
            ))}
          </div>
          {card.assignees.length > 3 && (
            <span className="text-xs text-gray-400 font-medium pl-1">
              +{card.assignees.length - 3}
            </span>
          )}
        </motion.div>
      )}

      {/* Priority indicator dot - with enhanced pulse */}
      {card.priority === 'critical' && (
        <div className="absolute top-3 right-3 kanban-status-urgent">
          <span className="flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
          </span>
        </div>
      )}
    </motion.div>
  );
}

export default KanbanCard;
