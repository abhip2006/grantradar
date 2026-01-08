import React from 'react';
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

const STAGE_CONFIG: Record<ApplicationStage, { label: string; color: string; bgColor: string; borderColor: string; Icon: React.ComponentType<React.SVGProps<SVGSVGElement>> }> = {
  researching: { label: 'Researching', color: 'text-cyan-600', bgColor: 'bg-cyan-50', borderColor: 'border-cyan-200', Icon: MagnifyingGlassIcon },
  writing: { label: 'Writing', color: 'text-amber-600', bgColor: 'bg-amber-50', borderColor: 'border-amber-200', Icon: PencilIcon },
  submitted: { label: 'Submitted', color: 'text-blue-600', bgColor: 'bg-blue-50', borderColor: 'border-blue-200', Icon: PaperAirplaneIcon },
  awarded: { label: 'Awarded', color: 'text-emerald-600', bgColor: 'bg-emerald-50', borderColor: 'border-emerald-200', Icon: CheckBadgeIcon },
  rejected: { label: 'Rejected', color: 'text-slate-500', bgColor: 'bg-slate-50', borderColor: 'border-slate-200', Icon: XCircleIcon },
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
      className={`w-80 flex-shrink-0 flex flex-col rounded-lg ${config.bgColor} ${config.borderColor} border ${
        isOver ? 'ring-2 ring-blue-400' : ''
      }`}
    >
      {/* Header */}
      <div className={`p-3 border-b ${config.borderColor}`}>
        <div className="flex items-center gap-2">
          <Icon className={`w-5 h-5 ${config.color}`} />
          <h3 className={`font-semibold ${config.color}`}>{config.label}</h3>
          <span className={`ml-auto px-2 py-0.5 text-xs rounded-full ${config.bgColor} ${config.color} border ${config.borderColor}`}>
            {cards.length}
          </span>
        </div>
      </div>

      {/* Cards */}
      <div className="flex-1 p-2 space-y-2 overflow-y-auto min-h-[200px]">
        <SortableContext items={cards.map(c => c.id)} strategy={verticalListSortingStrategy}>
          {cards.map(card => (
            <KanbanCard
              key={card.id}
              card={card}
              onClick={() => onCardClick(card.id)}
            />
          ))}
        </SortableContext>

        {cards.length === 0 && (
          <div className="text-center text-gray-400 py-8 text-sm">
            No applications
          </div>
        )}
      </div>
    </div>
  );
}

export default KanbanColumn;
