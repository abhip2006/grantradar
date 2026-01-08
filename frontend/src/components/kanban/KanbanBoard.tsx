import { useState, useEffect } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import type { DragStartEvent, DragEndEvent } from '@dnd-kit/core';
import { useKanbanBoard, useReorderCard } from '../../hooks/useKanban';
import { KanbanColumn } from './KanbanColumn';
import { KanbanCard } from './KanbanCard';
import { BoardFilters } from './BoardFilters';
import { CardDetailModal } from './CardDetailModal';
import type { KanbanCard as KanbanCardType, ApplicationStage, KanbanFilters } from '../../types/kanban';

const STAGES: ApplicationStage[] = ['researching', 'writing', 'submitted', 'awarded', 'rejected'];

export function KanbanBoard() {
  const [filters, setFilters] = useState<KanbanFilters>({});
  const [activeCard, setActiveCard] = useState<KanbanCardType | null>(null);
  const [selectedCardId, setSelectedCardId] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const { data: board, isLoading, error } = useKanbanBoard(filters);
  const reorderMutation = useReorderCard();

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor)
  );

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    const card = findCard(active.id as string);
    setActiveCard(card || null);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCard(null);

    if (!over) return;

    const draggedCard = findCard(active.id as string);
    if (!draggedCard) return;

    const overId = over.id as string;
    let toStage: ApplicationStage;
    let newPosition: number;

    // Check if dropped on a column
    if (STAGES.includes(overId as ApplicationStage)) {
      toStage = overId as ApplicationStage;
      const columnCards = board?.columns[toStage] || [];
      newPosition = columnCards.length;
    } else {
      // Dropped on a card
      const overCard = findCard(overId);
      if (!overCard) return;
      toStage = overCard.stage;
      newPosition = overCard.position;
    }

    if (draggedCard.stage === toStage && draggedCard.position === newPosition) {
      return;
    }

    reorderMutation.mutate({
      card_id: draggedCard.id,
      from_stage: draggedCard.stage,
      to_stage: toStage,
      new_position: newPosition,
    });
  };

  const findCard = (id: string): KanbanCardType | undefined => {
    if (!board) return undefined;
    for (const stage of STAGES) {
      const card = board.columns[stage]?.find(c => c.id === id);
      if (card) return card;
    }
    return undefined;
  };

  if (isLoading) {
    return (
      <div className="h-full flex flex-col bg-mesh">
        <div className="p-4">
          <div className="skeleton h-12 rounded-xl mb-4" />
        </div>
        <div className="flex-1 flex gap-4 p-4 overflow-x-auto">
          {STAGES.map((stage, idx) => (
            <div
              key={stage}
              className="w-80 flex-shrink-0 skeleton rounded-2xl h-96"
              style={{ animationDelay: `${idx * 0.1}s` }}
            />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center bg-mesh">
        <div className="text-center animate-fade-in-up">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-red-50 flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 className="text-lg font-display font-semibold text-gray-900 mb-2">
            Error loading board
          </h3>
          <p className="text-gray-500 text-sm mb-4">
            {error.message}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-mesh">
      {/* Premium Filters Bar */}
      <div className={`${mounted ? 'animate-fade-in-up' : 'opacity-0'}`}>
        <BoardFilters filters={filters} onChange={setFilters} totals={board?.totals} />
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex-1 overflow-x-auto kanban-scroll">
          <div className="flex gap-5 p-5 min-w-max h-full">
            {STAGES.map((stage, idx) => (
              <div
                key={stage}
                className={`${mounted ? 'animate-fade-in-up' : 'opacity-0'}`}
                style={{ animationDelay: `${(idx + 1) * 0.05}s` }}
              >
                <KanbanColumn
                  stage={stage}
                  cards={board?.columns[stage] || []}
                  onCardClick={setSelectedCardId}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Drag Overlay with premium card preview */}
        <DragOverlay dropAnimation={{
          duration: 200,
          easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
        }}>
          {activeCard && (
            <div className="kanban-card-dragging">
              <KanbanCard card={activeCard} isDragging />
            </div>
          )}
        </DragOverlay>
      </DndContext>

      {/* Card Detail Modal */}
      {selectedCardId && (
        <CardDetailModal
          applicationId={selectedCardId}
          onClose={() => setSelectedCardId(null)}
        />
      )}
    </div>
  );
}

export default KanbanBoard;
