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
import { motion, AnimatePresence } from 'motion/react';
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

  // Helper to find card by id
  const findCard = (id: string): KanbanCardType | undefined => {
    if (!board) return undefined;
    for (const stage of STAGES) {
      const card = board.columns[stage]?.find(c => c.id === id);
      if (card) return card;
    }
    return undefined;
  };

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

  if (isLoading) {
    return (
      <div className="h-full flex flex-col bg-mesh">
        <div className="p-4">
          <div className="skeleton h-12 rounded-xl mb-4" />
        </div>
        <div className="flex-1 flex gap-5 p-5 overflow-x-auto">
          {STAGES.map((stage, idx) => (
            <motion.div
              key={stage}
              className="w-80 flex-shrink-0 rounded-2xl overflow-hidden"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.08, duration: 0.4 }}
            >
              {/* Skeleton column */}
              <div className="bg-white/80 rounded-2xl border border-gray-100 p-4 h-96">
                {/* Header skeleton */}
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-9 h-9 rounded-xl skeleton" />
                  <div className="flex-1">
                    <div className="h-4 w-20 skeleton rounded" />
                  </div>
                  <div className="w-8 h-6 skeleton rounded-lg" />
                </div>
                {/* Card skeletons */}
                {[0, 1, 2].map((cardIdx) => (
                  <motion.div
                    key={cardIdx}
                    className="kanban-card-skeleton p-4 mb-3"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: idx * 0.08 + cardIdx * 0.05 + 0.2 }}
                  >
                    <div className="kanban-card-skeleton-title" />
                    <div className="kanban-card-skeleton-badge" />
                    <div className="kanban-card-skeleton-meta" />
                  </motion.div>
                ))}
              </div>
            </motion.div>
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
              <motion.div
                key={stage}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  delay: (idx + 1) * 0.05,
                  duration: 0.4,
                  ease: [0.16, 1, 0.3, 1],
                }}
              >
                <KanbanColumn
                  stage={stage}
                  cards={board?.columns[stage] || []}
                  onCardClick={setSelectedCardId}
                />
              </motion.div>
            ))}
          </div>
        </div>

        {/* Drag Overlay with enhanced animation */}
        <DragOverlay dropAnimation={{
          duration: 300,
          easing: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
          keyframes: ({ transform }) => [
            { transform: `${transform.initial} rotate(3deg) scale(1.05)`, opacity: 0.95 },
            { transform: `${transform.final} rotate(0deg) scale(0.98)`, opacity: 1 },
            { transform: `${transform.final} rotate(0deg) scale(1.02)`, opacity: 1 },
            { transform: `${transform.final} rotate(0deg) scale(1)`, opacity: 1 },
          ],
        }}>
          <AnimatePresence>
            {activeCard && (
              <motion.div
                className="kanban-drag-overlay"
                initial={{ scale: 1, rotate: 0, opacity: 1 }}
                animate={{
                  scale: 1.05,
                  rotate: 3,
                  opacity: 0.95,
                  boxShadow: '0 24px 48px rgba(0, 0, 0, 0.2), 0 12px 24px rgba(0, 0, 0, 0.15)',
                }}
                exit={{
                  scale: 1,
                  rotate: 0,
                  opacity: 1,
                }}
                transition={{
                  type: 'spring',
                  stiffness: 300,
                  damping: 20,
                }}
              >
                <KanbanCard card={activeCard} isDragging />
              </motion.div>
            )}
          </AnimatePresence>
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
