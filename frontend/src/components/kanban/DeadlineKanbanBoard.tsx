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
import { useDeadlines, useChangeDeadlineStatus } from '../../hooks/useDeadlines';
import { DeadlineKanbanColumn } from './DeadlineKanbanColumn';
import { DeadlineKanbanCard } from './DeadlineKanbanCard';
import type { Deadline, DeadlineStatus } from '../../types';
import { DEADLINE_STATUS_CONFIG } from '../../types';

// Deadline workflow stages for Kanban
const DEADLINE_STAGES: DeadlineStatus[] = [
  'not_started',
  'drafting',
  'internal_review',
  'submitted',
  'under_review',
  'awarded',
  'rejected',
];

interface DeadlineKanbanFilters {
  priorities?: string[];
  search?: string;
}

export function DeadlineKanbanBoard() {
  const [filters, setFilters] = useState<DeadlineKanbanFilters>({});
  const [activeDeadline, setActiveDeadline] = useState<Deadline | null>(null);
  const [selectedDeadlineId, setSelectedDeadlineId] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const { data, isLoading, error, refetch } = useDeadlines({});
  const changeStatus = useChangeDeadlineStatus();

  // Group deadlines by status
  const columns: Record<DeadlineStatus, Deadline[]> = {
    not_started: [],
    drafting: [],
    internal_review: [],
    submitted: [],
    under_review: [],
    awarded: [],
    rejected: [],
  };

  if (data?.items) {
    for (const deadline of data.items) {
      if (columns[deadline.status]) {
        // Apply filters
        if (filters.priorities?.length && !filters.priorities.includes(deadline.priority)) {
          continue;
        }
        if (filters.search && !deadline.title.toLowerCase().includes(filters.search.toLowerCase())) {
          continue;
        }
        columns[deadline.status].push(deadline);
      }
    }
  }

  // Calculate totals
  const totals = {
    total: data?.total || 0,
    by_status: Object.fromEntries(
      DEADLINE_STAGES.map(stage => [stage, columns[stage].length])
    ) as Record<DeadlineStatus, number>,
    overdue: data?.items?.filter(d => d.is_overdue).length || 0,
  };

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
    const deadline = findDeadline(active.id as string);
    setActiveDeadline(deadline || null);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveDeadline(null);

    if (!over) return;

    const draggedDeadline = findDeadline(active.id as string);
    if (!draggedDeadline) return;

    const overId = over.id as string;
    let toStatus: DeadlineStatus;

    // Check if dropped on a column
    if (DEADLINE_STAGES.includes(overId as DeadlineStatus)) {
      toStatus = overId as DeadlineStatus;
    } else {
      // Dropped on a card - find its status
      const overDeadline = findDeadline(overId);
      if (!overDeadline) return;
      toStatus = overDeadline.status;
    }

    if (draggedDeadline.status === toStatus) {
      return;
    }

    // Update deadline status via mutation hook
    changeStatus.mutate(
      { id: draggedDeadline.id, status: toStatus },
      {
        onError: (error) => {
          console.error('Failed to update deadline status:', error);
        },
      }
    );
  };

  const findDeadline = (id: string): Deadline | undefined => {
    for (const stage of DEADLINE_STAGES) {
      const deadline = columns[stage]?.find(d => d.id === id);
      if (deadline) return deadline;
    }
    return undefined;
  };

  if (isLoading) {
    return (
      <div className="h-full flex flex-col bg-mesh">
        <div className="flex-1 flex gap-4 p-4 overflow-x-auto">
          {DEADLINE_STAGES.slice(0, 5).map((stage, idx) => (
            <div
              key={stage}
              className="w-72 flex-shrink-0 skeleton rounded-2xl h-96"
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
            Error loading deadlines
          </h3>
          <p className="text-gray-500 text-sm mb-4">
            {(error as Error).message}
          </p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-mesh">
      {/* Stats Bar */}
      <div className={`px-4 py-3 border-b border-gray-200/50 ${mounted ? 'animate-fade-in-up' : 'opacity-0'}`}>
        <div className="flex items-center gap-4 overflow-x-auto">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/50 backdrop-blur-sm">
            <span className="text-sm text-gray-500">Total:</span>
            <span className="text-sm font-semibold text-gray-900">{totals.total}</span>
          </div>
          {totals.overdue > 0 && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-50 border border-red-100">
              <span className="text-sm text-red-600">Overdue:</span>
              <span className="text-sm font-semibold text-red-700">{totals.overdue}</span>
            </div>
          )}
          <div className="flex-1" />
          {/* Search filter */}
          <input
            type="text"
            placeholder="Search deadlines..."
            value={filters.search || ''}
            onChange={(e) => setFilters({ ...filters, search: e.target.value || undefined })}
            className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 bg-white/70 focus:outline-none focus:ring-2 focus:ring-blue-500/20 w-48"
          />
        </div>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex-1 flex gap-3 p-4 overflow-x-auto">
          {DEADLINE_STAGES.map((stage, idx) => {
            const stageConfig = DEADLINE_STATUS_CONFIG[stage];
            return (
              <DeadlineKanbanColumn
                key={stage}
                stage={stage}
                deadlines={columns[stage]}
                count={columns[stage].length}
                config={stageConfig}
                style={{ animationDelay: `${idx * 0.05}s` }}
                onCardClick={setSelectedDeadlineId}
              />
            );
          })}
        </div>

        <DragOverlay>
          {activeDeadline ? (
            <DeadlineKanbanCard
              deadline={activeDeadline}
              isDragging
            />
          ) : null}
        </DragOverlay>
      </DndContext>
    </div>
  );
}
