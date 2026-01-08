import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { format } from 'date-fns';
import type { KanbanCard as KanbanCardType, Priority } from '../../types/kanban';
import {
  CalendarIcon,
  PaperClipIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';

const PRIORITY_STYLES: Record<Priority, string> = {
  low: 'border-l-slate-400',
  medium: 'border-l-blue-500',
  high: 'border-l-amber-500',
  critical: 'border-l-red-500',
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
    opacity: isSortableDragging ? 0.5 : 1,
  };

  const isOverdue = card.target_date && new Date(card.target_date) < new Date() &&
    card.stage !== 'awarded' && card.stage !== 'rejected';

  // Get grant title from grant object or card itself
  const grantTitle = card.grant?.title || 'Untitled Application';
  const grantAgency = card.grant?.agency || card.grant?.funder_name;

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={onClick}
      className={`
        bg-white rounded-lg shadow-sm border border-gray-200 p-3 cursor-pointer
        hover:shadow-md transition-shadow
        border-l-4 ${PRIORITY_STYLES[card.priority]}
        ${isDragging ? 'shadow-lg rotate-2' : ''}
        ${isOverdue ? 'ring-2 ring-red-200' : ''}
      `}
    >
      {/* Title */}
      <h4 className="font-medium text-gray-900 text-sm line-clamp-2 mb-2">
        {grantTitle}
      </h4>

      {/* Agency badge */}
      {grantAgency && (
        <span className="inline-block px-2 py-0.5 text-xs rounded bg-gray-100 text-gray-600 mb-2">
          {grantAgency}
        </span>
      )}

      {/* Metadata row */}
      <div className="flex items-center gap-3 text-xs text-gray-500 mt-2">
        {/* Subtask progress */}
        {card.subtask_progress && card.subtask_progress.total > 0 && (
          <div className="flex items-center gap-1">
            <CheckCircleIcon className="w-4 h-4" />
            <span>
              {card.subtask_progress.completed}/{card.subtask_progress.total}
            </span>
          </div>
        )}

        {/* Attachments */}
        {card.attachments_count > 0 && (
          <div className="flex items-center gap-1">
            <PaperClipIcon className="w-4 h-4" />
            <span>{card.attachments_count}</span>
          </div>
        )}

        {/* Due date */}
        {card.target_date && (
          <div className={`flex items-center gap-1 ${isOverdue ? 'text-red-600' : ''}`}>
            <CalendarIcon className="w-4 h-4" />
            <span>{format(new Date(card.target_date), 'MMM d')}</span>
          </div>
        )}
      </div>

      {/* Assignees */}
      {card.assignees && card.assignees.length > 0 && (
        <div className="flex items-center gap-1 mt-2 -space-x-1">
          {card.assignees.slice(0, 3).map(assignee => (
            <div
              key={assignee.user_id}
              className="w-6 h-6 rounded-full bg-gray-300 border-2 border-white flex items-center justify-center"
              title={assignee.user?.name || assignee.user?.email || 'Unknown'}
            >
              <span className="text-xs text-gray-600">
                {(assignee.user?.name || assignee.user?.email || '?')[0].toUpperCase()}
              </span>
            </div>
          ))}
          {card.assignees.length > 3 && (
            <span className="text-xs text-gray-500 pl-2">
              +{card.assignees.length - 3}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export default KanbanCard;
