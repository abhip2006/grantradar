import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  BookmarkIcon,
  TrashIcon,
  PlayIcon,
  PencilIcon,
  BellIcon,
  BellSlashIcon,
  XMarkIcon,
  FolderOpenIcon,
} from '@heroicons/react/24/outline';
import { BookmarkIcon as BookmarkSolidIcon } from '@heroicons/react/24/solid';
import { savedSearchesApi } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import type { SavedSearch, SavedSearchFilters, SavedSearchCreate } from '../types';

/* ═══════════════════════════════════════════════════════════════════════════
   SAVED SEARCHES COMPONENT
   Manages saved search filters for quick access and email alerts
   ═══════════════════════════════════════════════════════════════════════════ */

interface SavedSearchesProps {
  currentFilters: SavedSearchFilters;
  onApplySearch: (filters: SavedSearchFilters) => void;
  className?: string;
}

// Modal for creating/editing saved searches
function SaveSearchModal({
  isOpen,
  onClose,
  onSave,
  currentFilters,
  editingSearch,
  isLoading,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSave: (name: string, alertEnabled: boolean) => void;
  currentFilters: SavedSearchFilters;
  editingSearch?: SavedSearch | null;
  isLoading: boolean;
}) {
  const [name, setName] = useState(editingSearch?.name || '');
  const [alertEnabled, setAlertEnabled] = useState(editingSearch?.alert_enabled || false);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      onSave(name.trim(), alertEnabled);
    }
  };

  const getActiveFiltersDescription = () => {
    const parts: string[] = [];
    if (currentFilters.source) parts.push(`Source: ${currentFilters.source}`);
    if (currentFilters.min_score) parts.push(`Min score: ${currentFilters.min_score}%`);
    if (currentFilters.min_amount) parts.push(`Min: $${currentFilters.min_amount.toLocaleString()}`);
    if (currentFilters.max_amount) parts.push(`Max: $${currentFilters.max_amount.toLocaleString()}`);
    if (currentFilters.show_saved_only) parts.push('Saved only');
    if (currentFilters.categories?.length) parts.push(`${currentFilters.categories.length} categories`);
    return parts.length > 0 ? parts.join(' | ') : 'No filters active';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-md bg-[var(--gr-bg-card)] rounded-2xl border border-[var(--gr-border-default)] shadow-xl animate-fade-in-up">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
              {editingSearch ? 'Edit Saved Search' : 'Save Current Search'}
            </h3>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)] hover:bg-[var(--gr-slate-700)]"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            {/* Current Filters Preview */}
            {!editingSearch && (
              <div className="mb-6 p-3 rounded-xl bg-[var(--gr-slate-700)]/50 border border-[var(--gr-border-subtle)]">
                <div className="text-xs font-medium text-[var(--gr-text-tertiary)] uppercase tracking-wider mb-1">
                  Current Filters
                </div>
                <div className="text-sm text-[var(--gr-text-secondary)]">
                  {getActiveFiltersDescription()}
                </div>
              </div>
            )}

            {/* Name Input */}
            <div className="mb-4">
              <label
                htmlFor="search-name"
                className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-2"
              >
                Search Name
              </label>
              <input
                id="search-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., NIH Research Grants"
                className="input"
                autoFocus
                required
              />
            </div>

            {/* Alert Toggle */}
            <div className="mb-6">
              <button
                type="button"
                onClick={() => setAlertEnabled(!alertEnabled)}
                className={`w-full flex items-center justify-between p-4 rounded-xl border transition-all ${
                  alertEnabled
                    ? 'bg-[var(--gr-blue-600)]/10 border-[var(--gr-blue-600)]/30 text-[var(--gr-blue-400)]'
                    : 'bg-[var(--gr-slate-700)]/30 border-[var(--gr-border-subtle)] text-[var(--gr-text-secondary)]'
                }`}
              >
                <div className="flex items-center gap-3">
                  {alertEnabled ? (
                    <BellIcon className="w-5 h-5" />
                  ) : (
                    <BellSlashIcon className="w-5 h-5" />
                  )}
                  <div className="text-left">
                    <div className="font-medium">Email Alerts</div>
                    <div className="text-xs opacity-70">
                      Get notified when new grants match this search
                    </div>
                  </div>
                </div>
                <div
                  className={`w-10 h-6 rounded-full transition-colors ${
                    alertEnabled ? 'bg-[var(--gr-blue-600)]' : 'bg-[var(--gr-slate-600)]'
                  }`}
                >
                  <div
                    className={`w-4 h-4 m-1 rounded-full bg-white transition-transform ${
                      alertEnabled ? 'translate-x-4' : 'translate-x-0'
                    }`}
                  />
                </div>
              </button>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 btn bg-[var(--gr-slate-700)] text-[var(--gr-text-secondary)] hover:bg-[var(--gr-slate-600)]"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!name.trim() || isLoading}
                className="flex-1 btn btn-primary"
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Saving...
                  </span>
                ) : editingSearch ? (
                  'Update Search'
                ) : (
                  'Save Search'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// Individual saved search item
function SavedSearchItem({
  search,
  onApply,
  onEdit,
  onDelete,
  onToggleAlert,
  isDeleting,
}: {
  search: SavedSearch;
  onApply: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onToggleAlert: () => void;
  isDeleting: boolean;
}) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const getFiltersSummary = (filters: SavedSearchFilters) => {
    const parts: string[] = [];
    if (filters.source) parts.push(filters.source);
    if (filters.min_score) parts.push(`${filters.min_score}%+`);
    if (filters.show_saved_only) parts.push('Saved');
    return parts.length > 0 ? parts.join(', ') : 'All grants';
  };

  return (
    <div className="group p-3 rounded-xl border border-[var(--gr-border-subtle)] bg-[var(--gr-slate-700)]/30 hover:border-[var(--gr-border-default)] transition-all">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="text-sm font-medium text-[var(--gr-text-primary)] truncate">
              {search.name}
            </h4>
            {search.alert_enabled && (
              <BellIcon className="w-3.5 h-3.5 text-[var(--gr-blue-500)] flex-shrink-0" />
            )}
          </div>
          <div className="text-xs text-[var(--gr-text-tertiary)]">
            {getFiltersSummary(search.filters)} | {formatDate(search.created_at)}
          </div>
        </div>
      </div>

      {/* Actions - show on hover */}
      <div className="flex items-center gap-1 mt-3 pt-3 border-t border-[var(--gr-border-subtle)] opacity-60 group-hover:opacity-100 transition-opacity">
        <button
          onClick={onApply}
          className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-medium text-[var(--gr-blue-400)] hover:bg-[var(--gr-blue-600)]/10 transition-colors"
        >
          <PlayIcon className="w-3.5 h-3.5" />
          Apply
        </button>
        <button
          onClick={onToggleAlert}
          className={`p-1.5 rounded-lg transition-colors ${
            search.alert_enabled
              ? 'text-[var(--gr-blue-400)] hover:bg-[var(--gr-blue-600)]/10'
              : 'text-[var(--gr-text-tertiary)] hover:bg-[var(--gr-slate-600)]'
          }`}
          title={search.alert_enabled ? 'Disable alerts' : 'Enable alerts'}
        >
          {search.alert_enabled ? (
            <BellIcon className="w-4 h-4" />
          ) : (
            <BellSlashIcon className="w-4 h-4" />
          )}
        </button>
        <button
          onClick={onEdit}
          className="p-1.5 rounded-lg text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)] hover:bg-[var(--gr-slate-600)] transition-colors"
          title="Edit"
        >
          <PencilIcon className="w-4 h-4" />
        </button>
        <button
          onClick={onDelete}
          disabled={isDeleting}
          className="p-1.5 rounded-lg text-[var(--gr-text-tertiary)] hover:text-[var(--gr-danger)] hover:bg-[var(--gr-danger)]/10 transition-colors disabled:opacity-50"
          title="Delete"
        >
          <TrashIcon className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

export function SavedSearches({
  currentFilters,
  onApplySearch,
  className = '',
}: SavedSearchesProps) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [showModal, setShowModal] = useState(false);
  const [editingSearch, setEditingSearch] = useState<SavedSearch | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Fetch saved searches
  const { data: savedSearchesData, isLoading } = useQuery({
    queryKey: ['saved-searches'],
    queryFn: savedSearchesApi.list,
  });

  const savedSearches = savedSearchesData?.saved_searches || [];

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: SavedSearchCreate) => savedSearchesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-searches'] });
      setShowModal(false);
      showToast('Search saved successfully!', 'success');
    },
    onError: () => {
      showToast('Failed to save search', 'error');
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { name?: string; alert_enabled?: boolean } }) =>
      savedSearchesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-searches'] });
      setShowModal(false);
      setEditingSearch(null);
      showToast('Search updated!', 'success');
    },
    onError: () => {
      showToast('Failed to update search', 'error');
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => savedSearchesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-searches'] });
      setDeletingId(null);
      showToast('Search deleted', 'info');
    },
    onError: () => {
      showToast('Failed to delete search', 'error');
      setDeletingId(null);
    },
  });

  const handleSave = useCallback(
    (name: string, alertEnabled: boolean) => {
      if (editingSearch) {
        updateMutation.mutate({
          id: editingSearch.id,
          data: { name, alert_enabled: alertEnabled },
        });
      } else {
        createMutation.mutate({
          name,
          filters: currentFilters,
          alert_enabled: alertEnabled,
        });
      }
    },
    [editingSearch, currentFilters, createMutation, updateMutation]
  );

  const handleEdit = useCallback((search: SavedSearch) => {
    setEditingSearch(search);
    setShowModal(true);
  }, []);

  const handleDelete = useCallback(
    (id: string) => {
      setDeletingId(id);
      deleteMutation.mutate(id);
    },
    [deleteMutation]
  );

  const handleToggleAlert = useCallback(
    (search: SavedSearch) => {
      updateMutation.mutate({
        id: search.id,
        data: { alert_enabled: !search.alert_enabled },
      });
    },
    [updateMutation]
  );

  const handleApply = useCallback(
    (search: SavedSearch) => {
      onApplySearch(search.filters);
      showToast(`Applied: ${search.name}`, 'info');
    },
    [onApplySearch, showToast]
  );

  // Check if current filters have any active values
  const hasActiveFilters =
    currentFilters.source ||
    currentFilters.min_score ||
    currentFilters.min_amount ||
    currentFilters.max_amount ||
    currentFilters.show_saved_only ||
    (currentFilters.categories && currentFilters.categories.length > 0);

  return (
    <div className={className}>
      {/* Header with Save Button */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-sm font-medium text-[var(--gr-text-secondary)]">
          <BookmarkSolidIcon className="w-4 h-4 text-[var(--gr-blue-500)]" />
          Saved Searches
        </div>
        <button
          onClick={() => {
            setEditingSearch(null);
            setShowModal(true);
          }}
          disabled={!hasActiveFilters}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            hasActiveFilters
              ? 'bg-[var(--gr-blue-600)]/10 text-[var(--gr-blue-400)] hover:bg-[var(--gr-blue-600)]/20'
              : 'bg-[var(--gr-slate-700)]/50 text-[var(--gr-text-tertiary)] cursor-not-allowed'
          }`}
          title={hasActiveFilters ? 'Save current filters' : 'Apply filters to save a search'}
        >
          <BookmarkIcon className="w-3.5 h-3.5" />
          Save Search
        </button>
      </div>

      {/* Saved Searches List */}
      {isLoading ? (
        <div className="space-y-2">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="p-3 rounded-xl border border-[var(--gr-border-subtle)]">
              <div className="skeleton h-4 w-32 mb-2" />
              <div className="skeleton h-3 w-24" />
            </div>
          ))}
        </div>
      ) : savedSearches.length === 0 ? (
        <div className="p-4 rounded-xl border border-dashed border-[var(--gr-border-subtle)] text-center">
          <FolderOpenIcon className="w-8 h-8 text-[var(--gr-text-tertiary)] mx-auto mb-2" />
          <p className="text-sm text-[var(--gr-text-tertiary)]">
            No saved searches yet
          </p>
          <p className="text-xs text-[var(--gr-text-tertiary)] mt-1">
            Apply filters and click "Save Search"
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {savedSearches.map((search) => (
            <SavedSearchItem
              key={search.id}
              search={search}
              onApply={() => handleApply(search)}
              onEdit={() => handleEdit(search)}
              onDelete={() => handleDelete(search.id)}
              onToggleAlert={() => handleToggleAlert(search)}
              isDeleting={deletingId === search.id}
            />
          ))}
        </div>
      )}

      {/* Save Modal */}
      <SaveSearchModal
        isOpen={showModal}
        onClose={() => {
          setShowModal(false);
          setEditingSearch(null);
        }}
        onSave={handleSave}
        currentFilters={currentFilters}
        editingSearch={editingSearch}
        isLoading={createMutation.isPending || updateMutation.isPending}
      />
    </div>
  );
}

export default SavedSearches;
