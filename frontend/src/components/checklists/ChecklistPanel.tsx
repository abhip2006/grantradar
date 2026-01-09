import React, { useState, useMemo } from 'react';
import {
  DocumentCheckIcon,
  ArrowPathIcon,
  TrashIcon,
  FunnelIcon,
  Squares2X2Icon,
  ListBulletIcon,
  ChevronDownIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import {
  useApplicationChecklist,
  useCreateChecklist,
  useUpdateChecklistItem,
  useDeleteChecklist,
  useResetChecklist,
  useChangeChecklistTemplate,
} from '../../hooks/useChecklists';
import {
  mergeChecklistItems,
  groupItemsByCategory,
  type ChecklistItem as ChecklistItemType,
  type ChecklistCategory,
  CHECKLIST_CATEGORY_CONFIGS,
} from '../../types/checklists';
import { ChecklistProgress } from './ChecklistProgress';
import { ChecklistItem } from './ChecklistItem';
import { ChecklistTemplateSelector } from './ChecklistTemplateSelector';

interface ChecklistPanelProps {
  /** Kanban card ID */
  cardId: string;
  /** Optional funder hint for template selection */
  funderHint?: string;
  /** Whether the panel is in a modal or inline */
  mode?: 'panel' | 'modal' | 'inline';
  /** Callback when checklist is created */
  onChecklistCreated?: () => void;
  /** Additional class name */
  className?: string;
}

type ViewMode = 'list' | 'grouped';
type FilterMode = 'all' | 'incomplete' | 'required';

export const ChecklistPanel = React.memo(function ChecklistPanel({
  cardId,
  funderHint,
  mode = 'panel',
  onChecklistCreated,
  className = '',
}: ChecklistPanelProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('grouped');
  const [filterMode, setFilterMode] = useState<FilterMode>('all');
  const [showChangeTemplate, setShowChangeTemplate] = useState(false);

  // Queries and mutations
  const { data: checklist, isLoading, error } = useApplicationChecklist(cardId);
  const createMutation = useCreateChecklist();
  const updateItemMutation = useUpdateChecklistItem();
  const deleteMutation = useDeleteChecklist();
  const resetMutation = useResetChecklist();
  const changeTemplateMutation = useChangeChecklistTemplate();

  // Merge template items with status
  const items = useMemo(() => {
    if (!checklist?.template?.items) return [];
    return mergeChecklistItems(checklist.template.items, checklist.items);
  }, [checklist]);

  // Filter items
  const filteredItems = useMemo(() => {
    switch (filterMode) {
      case 'incomplete':
        return items.filter((item) => !item.completed);
      case 'required':
        return items.filter((item) => item.required);
      default:
        return items;
    }
  }, [items, filterMode]);

  // Group items by category
  const groupedItems = useMemo(() => {
    return groupItemsByCategory(filteredItems);
  }, [filteredItems]);

  // Handlers
  const handleToggleItem = (itemId: string, completed: boolean) => {
    updateItemMutation.mutate({ cardId, itemId, data: { completed } });
  };

  const handleUpdateNotes = (itemId: string, notes: string) => {
    updateItemMutation.mutate({ cardId, itemId, data: { notes } });
  };

  const handleCreateChecklist = (templateId: string) => {
    createMutation.mutate(
      { cardId, data: { template_id: templateId } },
      {
        onSuccess: () => {
          onChecklistCreated?.();
        },
      }
    );
  };

  const handleDeleteChecklist = () => {
    if (window.confirm('Are you sure you want to delete this checklist? This cannot be undone.')) {
      deleteMutation.mutate(cardId);
    }
  };

  const handleResetChecklist = () => {
    if (window.confirm('Are you sure you want to mark all items as incomplete?')) {
      resetMutation.mutate(cardId);
    }
  };

  const handleChangeTemplate = (templateId: string) => {
    if (
      window.confirm(
        'Changing the template will reset your progress. Are you sure you want to continue?'
      )
    ) {
      changeTemplateMutation.mutate(
        { cardId, templateId },
        {
          onSuccess: () => setShowChangeTemplate(false),
        }
      );
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className={`flex items-center justify-center py-12 ${className}`}>
        <div className="flex items-center gap-2 text-gray-500">
          <ArrowPathIcon className="w-5 h-5 animate-spin" />
          <span className="text-sm">Loading checklist...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={`flex items-center justify-center py-12 ${className}`}>
        <div className="text-center">
          <ExclamationTriangleIcon className="w-10 h-10 text-amber-500 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Failed to load checklist</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-2 text-sm text-blue-600 hover:text-blue-700"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  // No checklist - show template selector
  if (!checklist) {
    return (
      <div className={`${className}`}>
        <div className="text-center py-8">
          <DocumentCheckIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <h3 className="text-sm font-medium text-gray-900 mb-1">No Checklist</h3>
          <p className="text-sm text-gray-500 mb-4">
            Add a checklist to track your progress on this application
          </p>
        </div>

        <div className="space-y-3">
          <label className="block text-sm font-medium text-gray-700">
            Choose a checklist template
          </label>
          <ChecklistTemplateSelector
            funder={funderHint}
            onSelect={(template) => handleCreateChecklist(template.id)}
            placeholder="Select a template to get started..."
          />
          {createMutation.isPending && (
            <p className="text-sm text-gray-500 text-center">Creating checklist...</p>
          )}
        </div>
      </div>
    );
  }

  // Stats
  const completedCount = items.filter((i) => i.completed).length;
  const requiredItems = items.filter((i) => i.required);
  const requiredCompletedCount = requiredItems.filter((i) => i.completed).length;
  const allRequiredComplete = requiredItems.length === requiredCompletedCount;

  return (
    <div className={className}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <DocumentCheckIcon className="w-5 h-5 text-gray-500" />
          <h3 className="text-sm font-semibold text-gray-900">
            {checklist.template?.name || 'Checklist'}
          </h3>
        </div>

        {/* Actions menu */}
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setShowChangeTemplate(!showChangeTemplate)}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
            title="Change template"
          >
            <ArrowPathIcon className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={handleResetChecklist}
            disabled={resetMutation.isPending}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
            title="Reset all items"
          >
            <ArrowPathIcon className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={handleDeleteChecklist}
            disabled={deleteMutation.isPending}
            className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
            title="Delete checklist"
          >
            <TrashIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Change template dropdown */}
      {showChangeTemplate && (
        <div className="mb-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
          <label className="block text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">
            Change Template
          </label>
          <ChecklistTemplateSelector
            selectedTemplateId={checklist.template_id}
            funder={funderHint}
            onSelect={(template) => handleChangeTemplate(template.id)}
            disabled={changeTemplateMutation.isPending}
          />
        </div>
      )}

      {/* Progress */}
      <div className="mb-4 p-3 bg-gray-50 rounded-lg">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Overall Progress</span>
          <span className="text-sm text-gray-500">
            {completedCount} of {items.length} complete
          </span>
        </div>
        <ChecklistProgress
          total={items.length}
          completed={completedCount}
          size="md"
        />

        {/* Required items warning */}
        {requiredItems.length > 0 && !allRequiredComplete && (
          <div className="mt-2 flex items-center gap-2 text-xs text-amber-600">
            <ExclamationTriangleIcon className="w-4 h-4" />
            <span>
              {requiredItems.length - requiredCompletedCount} required items remaining
            </span>
          </div>
        )}
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between mb-3">
        {/* View mode toggle */}
        <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-0.5">
          <button
            type="button"
            onClick={() => setViewMode('grouped')}
            className={`p-1.5 rounded ${
              viewMode === 'grouped'
                ? 'bg-white shadow-sm text-gray-900'
                : 'text-gray-500 hover:text-gray-700'
            }`}
            title="Group by category"
          >
            <Squares2X2Icon className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => setViewMode('list')}
            className={`p-1.5 rounded ${
              viewMode === 'list'
                ? 'bg-white shadow-sm text-gray-900'
                : 'text-gray-500 hover:text-gray-700'
            }`}
            title="List view"
          >
            <ListBulletIcon className="w-4 h-4" />
          </button>
        </div>

        {/* Filter dropdown */}
        <div className="relative">
          <button
            type="button"
            className="flex items-center gap-1.5 px-2 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded"
          >
            <FunnelIcon className="w-4 h-4" />
            <span className="capitalize">{filterMode}</span>
            <ChevronDownIcon className="w-3 h-3" />
          </button>
          {/* Filter menu would go here */}
        </div>

        {/* Quick filter buttons */}
        <div className="flex items-center gap-1">
          {(['all', 'incomplete', 'required'] as FilterMode[]).map((filter) => (
            <button
              key={filter}
              type="button"
              onClick={() => setFilterMode(filter)}
              className={`px-2 py-1 text-xs font-medium rounded ${
                filterMode === filter
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
              }`}
            >
              {filter.charAt(0).toUpperCase() + filter.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Items */}
      <div className="space-y-4">
        {viewMode === 'grouped' ? (
          // Grouped view
          Object.entries(groupedItems).map(([category, categoryItems]) => {
            if (categoryItems.length === 0) return null;
            const config = CHECKLIST_CATEGORY_CONFIGS[category as ChecklistCategory];

            return (
              <div key={category}>
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded ${config.bgColor} ${config.color}`}
                  >
                    {config.label}
                  </span>
                  <span className="text-xs text-gray-400">
                    {categoryItems.filter((i) => i.completed).length}/{categoryItems.length}
                  </span>
                </div>
                <div className="space-y-2">
                  {categoryItems.map((item) => (
                    <ChecklistItem
                      key={item.id}
                      item={item}
                      onToggle={handleToggleItem}
                      onUpdateNotes={handleUpdateNotes}
                      disabled={updateItemMutation.isPending}
                    />
                  ))}
                </div>
              </div>
            );
          })
        ) : (
          // List view
          <div className="space-y-2">
            {filteredItems.map((item) => (
              <ChecklistItem
                key={item.id}
                item={item}
                onToggle={handleToggleItem}
                onUpdateNotes={handleUpdateNotes}
                disabled={updateItemMutation.isPending}
                showCategory
              />
            ))}
          </div>
        )}

        {/* Empty state */}
        {filteredItems.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <p className="text-sm">
              {filterMode === 'incomplete'
                ? 'All items are complete!'
                : filterMode === 'required'
                ? 'No required items'
                : 'No items in this checklist'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
});

/**
 * Compact checklist panel for card preview
 */
export const ChecklistPanelCompact = React.memo(function ChecklistPanelCompact({
  cardId,
  className = '',
}: {
  cardId: string;
  className?: string;
}) {
  const { data: checklist, isLoading } = useApplicationChecklist(cardId);
  const updateItemMutation = useUpdateChecklistItem();

  const items = useMemo(() => {
    if (!checklist?.template?.items) return [];
    return mergeChecklistItems(checklist.template.items, checklist.items);
  }, [checklist]);

  const handleToggle = (itemId: string, completed: boolean) => {
    updateItemMutation.mutate({ cardId, itemId, data: { completed } });
  };

  if (isLoading) {
    return <div className="animate-pulse h-20 bg-gray-100 rounded" />;
  }

  if (!checklist) {
    return null;
  }

  const completedCount = items.filter((i) => i.completed).length;
  const incompleteItems = items.filter((i) => !i.completed).slice(0, 3);

  return (
    <div className={className}>
      <ChecklistProgress total={items.length} completed={completedCount} size="sm" />

      {incompleteItems.length > 0 && (
        <div className="mt-2 space-y-1">
          {incompleteItems.map((item) => (
            <div
              key={item.id}
              className="flex items-center gap-2 text-xs text-gray-600"
              onClick={() => handleToggle(item.id, true)}
            >
              <input
                type="checkbox"
                checked={item.completed}
                onChange={() => handleToggle(item.id, !item.completed)}
                className="w-3 h-3 rounded border-gray-300"
              />
              <span className="truncate">{item.title}</span>
            </div>
          ))}
          {items.filter((i) => !i.completed).length > 3 && (
            <p className="text-xs text-gray-400">
              +{items.filter((i) => !i.completed).length - 3} more
            </p>
          )}
        </div>
      )}
    </div>
  );
});

export default ChecklistPanel;
