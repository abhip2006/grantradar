import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { format } from 'date-fns';
import type { KanbanCard as KanbanCardType, Priority } from '../../types/kanban';
import {
  CalendarIcon,
  PaperClipIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';

const PRIORITY_CONFIG: Record<Priority, { className: string; label: string }> = {
  low: { className: 'kanban-card-priority-low', label: 'Low' },
  medium: { className: 'kanban-card-priority-medium', label: 'Medium' },
  high: { className: 'kanban-card-priority-high', label: 'High' },
  critical: { className: 'kanban-card-priority-critical', label: 'Critical' },
};

interface KanbanCardProps {
  card: KanbanCardType;
  isDragging?: boolean;
  onClick?: () => void;
}

export function KanbanCard({ card, isDragging, onClick }: KanbanCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging: isSortableDragging,
  } = useSortable({ id: card.id });

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

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={onClick}
      className={`
        kanban-card
        ${priorityConfig.className}
        ${isDragging || isSortableDragging ? 'kanban-card-dragging' : ''}
        ${isOverdue ? 'ring-2 ring-red-200 ring-offset-1' : ''}
        ${isSortableDragging ? 'opacity-50' : ''}
      `}
    >
      {/* Header with title */}
      <div className="mb-3">
        <h4 className="font-semibold text-gray-900 text-sm line-clamp-2 leading-snug">
          {grantTitle}
        </h4>
      </div>

      {/* Agency badge */}
      {grantAgency && (
        <div className="mb-3">
          <span className="inline-flex items-center px-2.5 py-1 text-xs font-medium rounded-lg bg-gray-50 text-gray-600 border border-gray-100">
            {grantAgency}
          </span>
        </div>
      )}

      {/* Progress bar for subtasks */}
      {card.subtask_progress && card.subtask_progress.total > 0 && (
        <div className="mb-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-gray-500 font-medium">Progress</span>
            <span className="text-xs font-semibold text-gray-700">
              {card.subtask_progress.completed}/{card.subtask_progress.total}
            </span>
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-full transition-all duration-500"
              style={{ width: `${subtaskProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Metadata row */}
      <div className="flex items-center flex-wrap gap-3 text-xs">
        {/* Subtask count icon */}
        {card.subtask_progress && card.subtask_progress.total > 0 && (
          <div className="flex items-center gap-1.5 text-gray-500">
            <CheckCircleIcon className="w-4 h-4" />
            <span className="font-medium">{card.subtask_progress.completed}/{card.subtask_progress.total}</span>
          </div>
        )}

        {/* Attachments */}
        {card.attachments_count > 0 && (
          <div className="flex items-center gap-1.5 text-gray-500">
            <PaperClipIcon className="w-4 h-4" />
            <span className="font-medium">{card.attachments_count}</span>
          </div>
        )}

        {/* Due date */}
        {card.target_date && (
          <div className={`flex items-center gap-1.5 ${isOverdue ? 'text-red-600' : 'text-gray-500'}`}>
            {isOverdue ? (
              <ExclamationCircleIcon className="w-4 h-4" />
            ) : (
              <CalendarIcon className="w-4 h-4" />
            )}
            <span className="font-medium">{format(new Date(card.target_date), 'MMM d')}</span>
          </div>
        )}
      </div>

      {/* Assignees */}
      {card.assignees && card.assignees.length > 0 && (
        <div className="flex items-center gap-1 mt-3 pt-3 border-t border-gray-50">
          <div className="flex -space-x-2">
            {card.assignees.slice(0, 3).map((assignee, idx) => (
              <div
                key={assignee.user_id}
                className="w-7 h-7 rounded-full bg-gradient-to-br from-gray-200 to-gray-300 border-2 border-white flex items-center justify-center shadow-sm"
                title={assignee.user?.name || assignee.user?.email || 'Unknown'}
                style={{ zIndex: 3 - idx }}
              >
                <span className="text-xs font-semibold text-gray-600">
                  {(assignee.user?.name || assignee.user?.email || '?')[0].toUpperCase()}
                </span>
              </div>
            ))}
          </div>
          {card.assignees.length > 3 && (
            <span className="text-xs text-gray-400 font-medium pl-1">
              +{card.assignees.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Priority indicator dot */}
      {card.priority === 'critical' && (
        <div className="absolute top-3 right-3">
          <span className="flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
          </span>
        </div>
      )}
    </div>
  );
}

export default KanbanCard;
