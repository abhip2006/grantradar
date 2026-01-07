import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  PlusIcon,
  XMarkIcon,
  CalendarIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { pipelineApi } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { PipelineCard, STAGE_CONFIG } from '../components/PipelineCard';
import type { PipelineItem, ApplicationStage, PipelineItemUpdate } from '../types';

// Stage order for Kanban columns
const STAGE_ORDER: ApplicationStage[] = ['researching', 'writing', 'submitted', 'awarded', 'rejected'];

// Edit modal for pipeline items
function EditPipelineModal({
  item,
  onClose,
  onSave,
  isLoading,
}: {
  item: PipelineItem;
  onClose: () => void;
  onSave: (itemId: string, data: PipelineItemUpdate) => void;
  isLoading: boolean;
}) {
  const [notes, setNotes] = useState(item.notes || '');
  const [targetDate, setTargetDate] = useState(
    item.target_date ? new Date(item.target_date).toISOString().split('T')[0] : ''
  );
  const [stage, setStage] = useState<ApplicationStage>(item.stage);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(item.id, {
      notes: notes || undefined,
      target_date: targetDate ? new Date(targetDate).toISOString() : undefined,
      stage,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-[var(--gr-border-subtle)]">
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
            Edit Application
          </h3>
          <button
            onClick={onClose}
            className="p-1 text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)] rounded-lg hover:bg-[var(--gr-bg-hover)]"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {/* Grant title (read-only) */}
          <div>
            <label className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-1">
              Grant
            </label>
            <p className="text-sm text-[var(--gr-text-primary)] font-medium">
              {item.grant.title}
            </p>
          </div>

          {/* Stage selector */}
          <div>
            <label className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
              Stage
            </label>
            <div className="flex flex-wrap gap-2">
              {STAGE_ORDER.map((s) => {
                const config = STAGE_CONFIG[s];
                return (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setStage(s)}
                    className={`
                      px-3 py-1.5 rounded-lg text-sm font-medium transition-all border
                      ${
                        stage === s
                          ? `${config.bgColor} ${config.color} ${config.borderColor} ring-2 ring-offset-1 ring-${config.color.replace('text-', '')}`
                          : 'bg-[var(--gr-bg-secondary)] text-[var(--gr-text-secondary)] border-[var(--gr-border-default)] hover:bg-[var(--gr-bg-hover)]'
                      }
                    `}
                  >
                    {config.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Target date */}
          <div>
            <label className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-1">
              Target Submission Date
            </label>
            <div className="relative">
              <CalendarIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[var(--gr-text-tertiary)]" />
              <input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-[var(--gr-border-default)] rounded-lg text-sm text-[var(--gr-text-primary)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--gr-blue-500)] focus:border-transparent"
              />
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-1">
              Notes
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={4}
              placeholder="Add notes about your application progress, key contacts, deadlines..."
              className="w-full px-3 py-2 border border-[var(--gr-border-default)] rounded-lg text-sm text-[var(--gr-text-primary)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--gr-blue-500)] focus:border-transparent resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={isLoading} className="btn-primary">
              {isLoading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Main Pipeline page component
export function Pipeline() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [editingItem, setEditingItem] = useState<PipelineItem | null>(null);

  // Fetch pipeline data
  const {
    data: pipelineData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['pipeline'],
    queryFn: pipelineApi.getPipeline,
  });

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['pipeline-stats'],
    queryFn: pipelineApi.getStats,
  });

  // Move item mutation
  const moveMutation = useMutation({
    mutationFn: ({ itemId, stage }: { itemId: string; stage: ApplicationStage }) =>
      pipelineApi.moveItem(itemId, stage),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline'] });
      queryClient.invalidateQueries({ queryKey: ['pipeline-stats'] });
      showToast('Application moved', 'success');
    },
    onError: () => {
      showToast('Failed to move application', 'error');
    },
  });

  // Update item mutation
  const updateMutation = useMutation({
    mutationFn: ({ itemId, data }: { itemId: string; data: PipelineItemUpdate }) =>
      pipelineApi.updateItem(itemId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline'] });
      queryClient.invalidateQueries({ queryKey: ['pipeline-stats'] });
      setEditingItem(null);
      showToast('Application updated', 'success');
    },
    onError: () => {
      showToast('Failed to update application', 'error');
    },
  });

  // Delete item mutation
  const deleteMutation = useMutation({
    mutationFn: (itemId: string) => pipelineApi.removeFromPipeline(itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline'] });
      queryClient.invalidateQueries({ queryKey: ['pipeline-stats'] });
      showToast('Application removed from pipeline', 'success');
    },
    onError: () => {
      showToast('Failed to remove application', 'error');
    },
  });

  // Handlers
  const handleMoveStage = useCallback(
    (itemId: string, stage: ApplicationStage) => {
      moveMutation.mutate({ itemId, stage });
    },
    [moveMutation]
  );

  const handleEdit = useCallback((item: PipelineItem) => {
    setEditingItem(item);
  }, []);

  const handleDelete = useCallback(
    (itemId: string) => {
      if (window.confirm('Remove this grant from your pipeline?')) {
        deleteMutation.mutate(itemId);
      }
    },
    [deleteMutation]
  );

  const handleSaveEdit = useCallback(
    (itemId: string, data: PipelineItemUpdate) => {
      updateMutation.mutate({ itemId, data });
    },
    [updateMutation]
  );

  // Group items by stage
  const itemsByStage: Record<ApplicationStage, PipelineItem[]> = {
    researching: [],
    writing: [],
    submitted: [],
    awarded: [],
    rejected: [],
  };

  if (pipelineData?.stages) {
    for (const stageGroup of pipelineData.stages) {
      itemsByStage[stageGroup.stage] = stageGroup.items;
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[var(--gr-bg-primary)]">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="skeleton h-8 w-48 mb-6" />
          <div className="grid grid-cols-5 gap-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="space-y-3">
                <div className="skeleton h-6 w-24" />
                <div className="skeleton h-32 w-full rounded-lg" />
                <div className="skeleton h-32 w-full rounded-lg" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[var(--gr-bg-primary)] flex items-center justify-center">
        <div className="text-center">
          <ExclamationTriangleIcon className="h-12 w-12 text-[var(--gr-danger)] mx-auto mb-4" />
          <h2 className="text-xl font-display font-medium text-[var(--gr-text-primary)] mb-2">
            Failed to load pipeline
          </h2>
          <p className="text-[var(--gr-text-secondary)] mb-4">
            There was an error loading your application pipeline.
          </p>
          <button onClick={() => refetch()} className="btn-primary">
            <ArrowPathIcon className="h-4 w-4" />
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--gr-bg-secondary)]">
      <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-display font-semibold text-[var(--gr-text-primary)]">
              Application Pipeline
            </h1>
            <p className="text-sm text-[var(--gr-text-secondary)] mt-1">
              Track your grant applications through each stage
            </p>
          </div>

          {/* Stats summary */}
          {stats && (
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-lg border border-[var(--gr-border-default)]">
                <DocumentTextIcon className="h-4 w-4 text-[var(--gr-text-tertiary)]" />
                <span className="text-[var(--gr-text-secondary)]">
                  {stats.total} application{stats.total !== 1 ? 's' : ''}
                </span>
              </div>
              {stats.upcoming_deadlines > 0 && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 rounded-lg border border-amber-200 text-amber-700">
                  <ExclamationTriangleIcon className="h-4 w-4" />
                  <span>{stats.upcoming_deadlines} deadline{stats.upcoming_deadlines !== 1 ? 's' : ''} soon</span>
                </div>
              )}
              {stats.past_deadlines > 0 && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-red-50 rounded-lg border border-red-200 text-red-700">
                  <ExclamationTriangleIcon className="h-4 w-4" />
                  <span>{stats.past_deadlines} past deadline{stats.past_deadlines !== 1 ? 's' : ''}</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Kanban board */}
        {pipelineData?.total === 0 ? (
          <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-12 text-center">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-[var(--gr-bg-secondary)] flex items-center justify-center mb-6">
              <DocumentTextIcon className="w-8 h-8 text-[var(--gr-text-tertiary)]" />
            </div>
            <h3 className="text-xl font-display font-medium text-[var(--gr-text-primary)] mb-2">
              No applications tracked
            </h3>
            <p className="text-[var(--gr-text-secondary)] max-w-md mx-auto mb-6">
              Start tracking grants by clicking "Track Application" on any grant detail page.
              Organize your applications through each stage from research to submission.
            </p>
            <a href="/dashboard" className="btn-primary inline-flex">
              <PlusIcon className="h-4 w-4" />
              Browse Grants
            </a>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 overflow-x-auto pb-4">
            {STAGE_ORDER.map((stage) => {
              const config = STAGE_CONFIG[stage];
              const items = itemsByStage[stage];

              return (
                <div
                  key={stage}
                  className={`
                    min-w-[280px] bg-white rounded-xl border
                    ${config.borderColor}
                  `}
                >
                  {/* Column header */}
                  <div
                    className={`
                      px-4 py-3 border-b rounded-t-xl
                      ${config.bgColor} ${config.borderColor}
                    `}
                  >
                    <div className="flex items-center justify-between">
                      <h3 className={`font-medium text-sm ${config.color}`}>
                        {config.label}
                      </h3>
                      <span
                        className={`
                          px-2 py-0.5 rounded-full text-xs font-medium
                          ${config.bgColor} ${config.color}
                        `}
                      >
                        {items.length}
                      </span>
                    </div>
                  </div>

                  {/* Column items */}
                  <div className="p-3 space-y-3 min-h-[200px] max-h-[calc(100vh-280px)] overflow-y-auto">
                    {items.length === 0 ? (
                      <div className="text-center py-8 text-xs text-[var(--gr-text-tertiary)]">
                        No applications in this stage
                      </div>
                    ) : (
                      items.map((item) => (
                        <PipelineCard
                          key={item.id}
                          item={item}
                          onEdit={handleEdit}
                          onDelete={handleDelete}
                          onMoveStage={handleMoveStage}
                        />
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Edit modal */}
        {editingItem && (
          <EditPipelineModal
            item={editingItem}
            onClose={() => setEditingItem(null)}
            onSave={handleSaveEdit}
            isLoading={updateMutation.isPending}
          />
        )}
      </div>
    </div>
  );
}

export default Pipeline;
