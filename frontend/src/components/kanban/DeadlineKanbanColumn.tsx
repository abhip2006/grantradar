import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { DeadlineKanbanCard } from './DeadlineKanbanCard';
import type { Deadline, DeadlineStatus } from '../../types';
import {
  ClockIcon,
  PencilSquareIcon,
  EyeIcon,
  PaperAirplaneIcon,
  MagnifyingGlassIcon,
  CheckBadgeIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import type { CSSProperties } from 'react';

interface StageConfig {
  label: string;
  color: string;
  bgColor: string;
  order: number;
}

interface ColumnConfig {
  label: string;
  color: string;
  bgGradient: string;
  iconBg: string;
  accentColor: string;
  countBg: string;
  Icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
}

const STAGE_CONFIG: Record<DeadlineStatus, ColumnConfig> = {
  not_started: {
    label: 'Not Started',
    color: 'text-gray-600',
    bgGradient: 'from-gray-50/80 to-gray-50/40',
    iconBg: 'bg-gradient-to-br from-gray-100 to-gray-50',
    accentColor: 'gray',
    countBg: 'bg-gray-100 text-gray-700 border-gray-200',
    Icon: ClockIcon,
  },
  drafting: {
    label: 'Drafting',
    color: 'text-blue-600',
    bgGradient: 'from-blue-50/80 to-blue-50/40',
    iconBg: 'bg-gradient-to-br from-blue-100 to-blue-50',
    accentColor: 'blue',
    countBg: 'bg-blue-100 text-blue-700 border-blue-200',
    Icon: PencilSquareIcon,
  },
  internal_review: {
    label: 'Internal Review',
    color: 'text-yellow-600',
    bgGradient: 'from-yellow-50/80 to-yellow-50/40',
    iconBg: 'bg-gradient-to-br from-yellow-100 to-yellow-50',
    accentColor: 'yellow',
    countBg: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    Icon: EyeIcon,
  },
  submitted: {
    label: 'Submitted',
    color: 'text-purple-600',
    bgGradient: 'from-purple-50/80 to-purple-50/40',
    iconBg: 'bg-gradient-to-br from-purple-100 to-purple-50',
    accentColor: 'purple',
    countBg: 'bg-purple-100 text-purple-700 border-purple-200',
    Icon: PaperAirplaneIcon,
  },
  under_review: {
    label: 'Under Review',
    color: 'text-orange-600',
    bgGradient: 'from-orange-50/80 to-orange-50/40',
    iconBg: 'bg-gradient-to-br from-orange-100 to-orange-50',
    accentColor: 'orange',
    countBg: 'bg-orange-100 text-orange-700 border-orange-200',
    Icon: MagnifyingGlassIcon,
  },
  awarded: {
    label: 'Awarded',
    color: 'text-emerald-600',
    bgGradient: 'from-emerald-50/80 to-emerald-50/40',
    iconBg: 'bg-gradient-to-br from-emerald-100 to-emerald-50',
    accentColor: 'emerald',
    countBg: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    Icon: CheckBadgeIcon,
  },
  rejected: {
    label: 'Rejected',
    color: 'text-slate-500',
    bgGradient: 'from-slate-50/80 to-slate-50/40',
    iconBg: 'bg-gradient-to-br from-slate-100 to-slate-50',
    accentColor: 'slate',
    countBg: 'bg-slate-100 text-slate-600 border-slate-200',
    Icon: XCircleIcon,
  },
};

interface DeadlineKanbanColumnProps {
  stage: DeadlineStatus;
  deadlines: Deadline[];
  count: number;
  config: StageConfig;
  style?: CSSProperties;
  onCardClick?: (deadlineId: string) => void;
}

export function DeadlineKanbanColumn({
  stage,
  deadlines,
  count,
  config,
  style,
  onCardClick,
}: DeadlineKanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: stage,
  });

  const columnConfig = STAGE_CONFIG[stage];
  const { Icon } = columnConfig;

  return (
    <div
      ref={setNodeRef}
      className={`
        kanban-column kanban-column-${stage}
        w-72 flex-shrink-0 flex flex-col
        bg-gradient-to-b ${columnConfig.bgGradient}
        rounded-2xl border border-gray-200/50 shadow-sm
        animate-fade-in-up
        ${isOver ? 'ring-2 ring-blue-400 ring-offset-2' : ''}
      `}
      style={style}
    >
      {/* Column Header */}
      <div className="px-4 py-3 border-b border-gray-200/50">
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-xl ${columnConfig.iconBg} flex items-center justify-center shadow-sm`}>
            <Icon className={`w-5 h-5 ${columnConfig.color}`} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className={`font-display font-semibold text-sm ${columnConfig.color} truncate`}>
              {columnConfig.label}
            </h3>
          </div>
          <span className={`px-2.5 py-1 text-xs font-semibold rounded-lg border ${columnConfig.countBg} shadow-sm`}>
            {count}
          </span>
        </div>
      </div>

      {/* Cards Container */}
      <div className="flex-1 p-3 space-y-3 overflow-y-auto kanban-scroll min-h-[200px] max-h-[calc(100vh-280px)]">
        <SortableContext items={deadlines.map(d => d.id)} strategy={verticalListSortingStrategy}>
          {deadlines.map((deadline, index) => (
            <div
              key={deadline.id}
              className="kanban-card-enter"
              style={{ animationDelay: `${index * 0.03}s` }}
            >
              <DeadlineKanbanCard
                deadline={deadline}
                onClick={() => onCardClick?.(deadline.id)}
              />
            </div>
          ))}
        </SortableContext>

        {deadlines.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className={`w-12 h-12 rounded-xl ${columnConfig.iconBg} flex items-center justify-center mb-3 opacity-60`}>
              <Icon className={`w-6 h-6 ${columnConfig.color} opacity-60`} />
            </div>
            <p className="text-sm text-gray-400 font-medium">
              No deadlines
            </p>
            <p className="text-xs text-gray-300 mt-1">
              Drag items here
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default DeadlineKanbanColumn;
