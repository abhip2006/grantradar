import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { motion, AnimatePresence } from 'motion/react';
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
  PlusIcon,
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
  style,
  onCardClick,
}: DeadlineKanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: stage,
  });

  const columnConfig = STAGE_CONFIG[stage];
  const { Icon } = columnConfig;

  // Get stage index for animation delay
  const stageOrder = ['not_started', 'drafting', 'internal_review', 'submitted', 'under_review', 'awarded', 'rejected'];
  const stageIndex = stageOrder.indexOf(stage);

  return (
    <motion.div
      ref={setNodeRef}
      className={`
        kanban-column kanban-column-${stage}
        w-72 flex-shrink-0 flex flex-col relative
        bg-gradient-to-b ${columnConfig.bgGradient}
        rounded-2xl border border-gray-200/50 shadow-sm
        ${isOver ? 'kanban-column-drag-over-enhanced' : ''}
      `}
      initial={{ opacity: 0, y: 20 }}
      animate={{
        opacity: 1,
        y: 0,
        scale: isOver ? 1.01 : 1,
      }}
      transition={{
        opacity: { duration: 0.3, delay: stageIndex * 0.05 },
        y: { duration: 0.3, ease: [0.16, 1, 0.3, 1], delay: stageIndex * 0.05 },
        scale: { duration: 0.2 },
      }}
      style={style}
    >
      {/* Drag over overlay glow */}
      <AnimatePresence>
        {isOver && (
          <motion.div
            className="absolute inset-0 rounded-2xl pointer-events-none z-0"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{
              background: `linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, transparent 100%)`,
              boxShadow: '0 0 0 2px rgba(59, 130, 246, 0.4), 0 0 30px rgba(59, 130, 246, 0.15)',
            }}
          />
        )}
      </AnimatePresence>

      {/* Column Header */}
      <div className="px-4 py-3 border-b border-gray-200/50 relative z-10">
        <div className="flex items-center gap-3">
          <motion.div
            className={`w-9 h-9 rounded-xl ${columnConfig.iconBg} flex items-center justify-center shadow-sm`}
            whileHover={{ scale: 1.05 }}
            transition={{ type: 'spring', stiffness: 400, damping: 17 }}
          >
            <Icon className={`w-5 h-5 ${columnConfig.color}`} />
          </motion.div>
          <div className="flex-1 min-w-0">
            <h3 className={`font-display font-semibold text-sm ${columnConfig.color} truncate`}>
              {columnConfig.label}
            </h3>
          </div>
          <motion.span
            className={`px-2.5 py-1 text-xs font-semibold rounded-lg border ${columnConfig.countBg} shadow-sm`}
            key={count}
            initial={{ scale: 1.2 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 500, damping: 25 }}
          >
            {count}
          </motion.span>
        </div>
      </div>

      {/* Cards Container */}
      <div className="flex-1 p-3 space-y-3 overflow-y-auto kanban-scroll min-h-[200px] max-h-[calc(100vh-280px)] relative z-10">
        <SortableContext items={deadlines.map(d => d.id)} strategy={verticalListSortingStrategy}>
          <AnimatePresence mode="popLayout">
            {deadlines.map((deadline, index) => (
              <motion.div
                key={deadline.id}
                className="kanban-card-stagger"
                layout
                initial={{ opacity: 0, y: -10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9, x: -20 }}
                transition={{
                  layout: { type: 'spring', stiffness: 350, damping: 30 },
                  opacity: { duration: 0.2 },
                  scale: { duration: 0.2 },
                  delay: index * 0.02,
                }}
              >
                <DeadlineKanbanCard
                  deadline={deadline}
                  onClick={() => onCardClick?.(deadline.id)}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </SortableContext>

        {/* Enhanced empty state */}
        <AnimatePresence>
          {deadlines.length === 0 && (
            <motion.div
              className="flex flex-col items-center justify-center py-12 text-center kanban-empty-state"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.3 }}
            >
              <motion.div
                className={`w-14 h-14 rounded-xl ${columnConfig.iconBg} flex items-center justify-center mb-3 kanban-empty-icon`}
                animate={{
                  y: [0, -6, 0],
                }}
                transition={{
                  duration: 3,
                  repeat: Infinity,
                  ease: 'easeInOut',
                }}
              >
                <Icon className={`w-7 h-7 ${columnConfig.color} opacity-50`} />
              </motion.div>
              <p className="text-sm text-gray-400 font-medium mb-1">
                No deadlines
              </p>
              <p className="text-xs text-gray-300">
                Drag items here
              </p>

              {/* Dashed drop zone indicator when dragging */}
              <AnimatePresence>
                {isOver && (
                  <motion.div
                    className="mt-4 w-full h-20 border-2 border-dashed border-blue-300 rounded-xl flex items-center justify-center bg-blue-50/50"
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 80 }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <PlusIcon className="w-6 h-6 text-blue-400" />
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

export default DeadlineKanbanColumn;
