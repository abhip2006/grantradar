import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { motion, AnimatePresence } from 'motion/react';
import { KanbanCard } from './KanbanCard';
import type { KanbanCard as KanbanCardType, ApplicationStage } from '../../types/kanban';
import {
  MagnifyingGlassIcon,
  PencilIcon,
  PaperAirplaneIcon,
  CheckBadgeIcon,
  XCircleIcon,
  PlusIcon,
} from '@heroicons/react/24/outline';

interface StageConfig {
  label: string;
  color: string;
  bgGradient: string;
  iconBg: string;
  accentColor: string;
  countBg: string;
  Icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
}

const STAGE_CONFIG: Record<ApplicationStage, StageConfig> = {
  researching: {
    label: 'Researching',
    color: 'text-cyan-600',
    bgGradient: 'from-cyan-50/80 to-cyan-50/40',
    iconBg: 'bg-gradient-to-br from-cyan-100 to-cyan-50',
    accentColor: 'cyan',
    countBg: 'bg-cyan-100 text-cyan-700 border-cyan-200',
    Icon: MagnifyingGlassIcon,
  },
  writing: {
    label: 'Writing',
    color: 'text-amber-600',
    bgGradient: 'from-amber-50/80 to-amber-50/40',
    iconBg: 'bg-gradient-to-br from-amber-100 to-amber-50',
    accentColor: 'amber',
    countBg: 'bg-amber-100 text-amber-700 border-amber-200',
    Icon: PencilIcon,
  },
  submitted: {
    label: 'Submitted',
    color: 'text-blue-600',
    bgGradient: 'from-blue-50/80 to-blue-50/40',
    iconBg: 'bg-gradient-to-br from-blue-100 to-blue-50',
    accentColor: 'blue',
    countBg: 'bg-blue-100 text-blue-700 border-blue-200',
    Icon: PaperAirplaneIcon,
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

interface KanbanColumnProps {
  stage: ApplicationStage;
  cards: KanbanCardType[];
  onCardClick: (cardId: string) => void;
}

export function KanbanColumn({ stage, cards, onCardClick }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: stage,
  });

  const config = STAGE_CONFIG[stage];
  const { Icon } = config;

  return (
    <motion.div
      ref={setNodeRef}
      className={`
        kanban-column kanban-column-${stage}
        w-80 flex-shrink-0 flex flex-col relative
        bg-gradient-to-b ${config.bgGradient}
        ${isOver ? 'kanban-column-drag-over-enhanced' : ''}
      `}
      initial={{ opacity: 0, y: 20 }}
      animate={{
        opacity: 1,
        y: 0,
        scale: isOver ? 1.01 : 1,
      }}
      transition={{
        opacity: { duration: 0.3 },
        y: { duration: 0.3, ease: [0.16, 1, 0.3, 1] },
        scale: { duration: 0.2 },
      }}
      style={{
        animationDelay: `${['researching', 'writing', 'submitted', 'awarded', 'rejected'].indexOf(stage) * 0.05}s`,
      }}
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

      {/* Premium Header */}
      <div className="kanban-column-header relative z-10">
        <div className="flex items-center gap-3">
          <motion.div
            className={`w-9 h-9 rounded-xl ${config.iconBg} flex items-center justify-center shadow-sm`}
            whileHover={{ scale: 1.05 }}
            transition={{ type: 'spring', stiffness: 400, damping: 17 }}
          >
            <Icon className={`w-5 h-5 ${config.color}`} />
          </motion.div>
          <div className="flex-1">
            <h3 className={`font-display font-semibold ${config.color}`}>
              {config.label}
            </h3>
          </div>
          <motion.span
            className={`px-2.5 py-1 text-xs font-semibold rounded-lg border ${config.countBg} shadow-sm`}
            key={cards.length}
            initial={{ scale: 1.2 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 500, damping: 25 }}
          >
            {cards.length}
          </motion.span>
        </div>
      </div>

      {/* Cards Container with smooth scroll */}
      <div className="flex-1 p-3 space-y-3 overflow-y-auto kanban-scroll min-h-[200px] relative z-10">
        <SortableContext items={cards.map(c => c.id)} strategy={verticalListSortingStrategy}>
          <AnimatePresence mode="popLayout">
            {cards.map((card, index) => (
              <motion.div
                key={card.id}
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
                <KanbanCard
                  card={card}
                  onClick={() => onCardClick(card.id)}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </SortableContext>

        {/* Enhanced empty state */}
        <AnimatePresence>
          {cards.length === 0 && (
            <motion.div
              className="flex flex-col items-center justify-center py-12 text-center kanban-empty-state"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.3 }}
            >
              <motion.div
                className={`w-14 h-14 rounded-xl ${config.iconBg} flex items-center justify-center mb-3 kanban-empty-icon`}
                animate={{
                  y: [0, -6, 0],
                }}
                transition={{
                  duration: 3,
                  repeat: Infinity,
                  ease: 'easeInOut',
                }}
              >
                <Icon className={`w-7 h-7 ${config.color} opacity-50`} />
              </motion.div>
              <p className="text-sm text-gray-400 font-medium mb-1">
                No applications
              </p>
              <p className="text-xs text-gray-300">
                Drag cards here
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

export default KanbanColumn;
