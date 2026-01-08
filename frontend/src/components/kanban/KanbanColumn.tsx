import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { KanbanCard } from './KanbanCard';
import type { KanbanCard as KanbanCardType, ApplicationStage } from '../../types/kanban';
import {
  MagnifyingGlassIcon,
  PencilIcon,
  PaperAirplaneIcon,
  CheckBadgeIcon,
  XCircleIcon,
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
    <div
      ref={setNodeRef}
      className={`
        kanban-column kanban-column-${stage}
        w-80 flex-shrink-0 flex flex-col
        bg-gradient-to-b ${config.bgGradient}
        ${isOver ? 'kanban-column-drag-over' : ''}
      `}
      style={{
        animationDelay: `${['researching', 'writing', 'submitted', 'awarded', 'rejected'].indexOf(stage) * 0.05}s`,
      }}
    >
      {/* Premium Header */}
      <div className="kanban-column-header">
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-xl ${config.iconBg} flex items-center justify-center shadow-sm`}>
            <Icon className={`w-5 h-5 ${config.color}`} />
          </div>
          <div className="flex-1">
            <h3 className={`font-display font-semibold ${config.color}`}>
              {config.label}
            </h3>
          </div>
          <span className={`px-2.5 py-1 text-xs font-semibold rounded-lg border ${config.countBg} shadow-sm`}>
            {cards.length}
          </span>
        </div>
      </div>

      {/* Cards Container with smooth scroll */}
      <div className="flex-1 p-3 space-y-3 overflow-y-auto kanban-scroll min-h-[200px]">
        <SortableContext items={cards.map(c => c.id)} strategy={verticalListSortingStrategy}>
          {cards.map((card, index) => (
            <div
              key={card.id}
              className="kanban-card-enter"
              style={{ animationDelay: `${index * 0.03}s` }}
            >
              <KanbanCard
                card={card}
                onClick={() => onCardClick(card.id)}
              />
            </div>
          ))}
        </SortableContext>

        {cards.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className={`w-12 h-12 rounded-xl ${config.iconBg} flex items-center justify-center mb-3 opacity-60`}>
              <Icon className={`w-6 h-6 ${config.color} opacity-60`} />
            </div>
            <p className="text-sm text-gray-400 font-medium">
              No applications
            </p>
            <p className="text-xs text-gray-300 mt-1">
              Drag cards here
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default KanbanColumn;
