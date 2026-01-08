import { useState } from 'react';
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
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-600 p-4">
        Error loading board: {error.message}
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <BoardFilters filters={filters} onChange={setFilters} totals={board?.totals} />

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex-1 overflow-x-auto">
          <div className="flex gap-4 p-4 min-w-max h-full">
            {STAGES.map(stage => (
              <KanbanColumn
                key={stage}
                stage={stage}
                cards={board?.columns[stage] || []}
                onCardClick={setSelectedCardId}
              />
            ))}
          </div>
        </div>

        <DragOverlay>
          {activeCard && (
            <KanbanCard card={activeCard} isDragging />
          )}
        </DragOverlay>
      </DndContext>

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
