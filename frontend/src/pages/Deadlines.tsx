import { useState, useMemo } from 'react';
import {
  PlusIcon,
  CalendarIcon,
  ListBulletIcon,
  FunnelIcon,
  ArrowDownTrayIcon,
} from '@heroicons/react/24/outline';
import { useDeadlines, useDeleteDeadline, useUpdateDeadline } from '../hooks/useDeadlines';
import { DeadlinesList } from '../components/deadlines/DeadlinesList';
import { DeadlinesCalendar } from '../components/deadlines/DeadlinesCalendar';
import { DeadlineModal } from '../components/deadlines/DeadlineModal';
import { DeadlineFilters } from '../components/deadlines/DeadlineFilters';
import type { Deadline, DeadlineFilters as FiltersType, DeadlineStatus } from '../types';
import { deadlinesApi } from '../services/api';

type ViewMode = 'list' | 'calendar';

export function Deadlines() {
  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    return (localStorage.getItem('deadlines-view') as ViewMode) || 'list';
  });
  const [filters, setFilters] = useState<FiltersType>({});
  const [showFilters, setShowFilters] = useState(false);
  const [selectedDeadline, setSelectedDeadline] = useState<Deadline | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { data, isLoading, error } = useDeadlines(filters);
  const deleteDeadline = useDeleteDeadline();
  const updateDeadline = useUpdateDeadline();

  const handleViewChange = (view: ViewMode) => {
    setViewMode(view);
    localStorage.setItem('deadlines-view', view);
  };

  const handleCreateNew = () => {
    setSelectedDeadline(null);
    setIsModalOpen(true);
  };

  const handleEdit = (deadline: Deadline) => {
    setSelectedDeadline(deadline);
    setIsModalOpen(true);
  };

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this deadline?')) {
      await deleteDeadline.mutateAsync(id);
    }
  };

  const handleStatusChange = async (id: string, status: DeadlineStatus) => {
    await updateDeadline.mutateAsync({ id, data: { status } });
  };

  const handleExportIcs = async () => {
    try {
      const blob = await deadlinesApi.exportIcs();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'grantradar-deadlines.ics';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (error) {
      console.error('Failed to export:', error);
    }
  };

  const stats = useMemo(() => {
    if (!data?.items) return { active: 0, overdue: 0, upcoming: 0 };
    const items = data.items;
    return {
      active: items.filter((d) => d.status === 'active').length,
      overdue: items.filter((d) => d.is_overdue).length,
      upcoming: items.filter((d) => d.days_until_deadline <= 7 && d.days_until_deadline >= 0).length,
    };
  }, [data]);

  if (error) {
    return (
      <div className="p-8 text-center text-red-600">
        Error loading deadlines. Please try again.
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      {/* Header */}
      <div className="bg-[var(--gr-bg-secondary)] border-b border-[var(--gr-border-subtle)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-display font-semibold text-[var(--gr-text-primary)]">
                Deadlines
              </h1>
              <p className="mt-1 text-sm text-[var(--gr-text-secondary)]">
                Track and manage your grant submission deadlines
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handleExportIcs}
                className="btn-secondary flex items-center gap-2"
              >
                <ArrowDownTrayIcon className="h-4 w-4" />
                Export .ics
              </button>
              <button
                onClick={handleCreateNew}
                className="btn-primary flex items-center gap-2"
              >
                <PlusIcon className="h-4 w-4" />
                Add Deadline
              </button>
            </div>
          </div>

          {/* Stats */}
          <div className="mt-4 grid grid-cols-3 gap-4">
            <div className="bg-[var(--gr-blue-50)] rounded-xl p-3 border border-[var(--gr-blue-200)]">
              <div className="text-2xl font-display font-bold text-[var(--gr-blue-700)]">
                {stats.active}
              </div>
              <div className="text-sm text-[var(--gr-blue-600)]">Active</div>
            </div>
            <div className="bg-red-50 rounded-xl p-3 border border-red-200">
              <div className="text-2xl font-display font-bold text-red-700">{stats.overdue}</div>
              <div className="text-sm text-red-600">Overdue</div>
            </div>
            <div className="bg-amber-50 rounded-xl p-3 border border-amber-200">
              <div className="text-2xl font-display font-bold text-amber-700">{stats.upcoming}</div>
              <div className="text-sm text-amber-600">Due in 7 days</div>
            </div>
          </div>

          {/* View Toggle & Filters */}
          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex p-1 bg-[var(--gr-bg-primary)] rounded-lg">
                <button
                  onClick={() => handleViewChange('list')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    viewMode === 'list'
                      ? 'bg-white text-[var(--gr-blue-600)] shadow-sm'
                      : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)]'
                  }`}
                >
                  <ListBulletIcon className="h-4 w-4" />
                  List
                </button>
                <button
                  onClick={() => handleViewChange('calendar')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    viewMode === 'calendar'
                      ? 'bg-white text-[var(--gr-blue-600)] shadow-sm'
                      : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)]'
                  }`}
                >
                  <CalendarIcon className="h-4 w-4" />
                  Calendar
                </button>
              </div>
            </div>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                showFilters
                  ? 'bg-[var(--gr-blue-50)] text-[var(--gr-blue-700)] border border-[var(--gr-blue-200)]'
                  : 'bg-[var(--gr-bg-primary)] text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)]'
              }`}
            >
              <FunnelIcon className="h-4 w-4" />
              Filters
            </button>
          </div>

          {/* Filters Panel */}
          {showFilters && <DeadlineFilters filters={filters} onChange={setFilters} />}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--gr-blue-600)]" />
          </div>
        ) : viewMode === 'list' ? (
          <DeadlinesList
            deadlines={data?.items || []}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onStatusChange={handleStatusChange}
          />
        ) : (
          <DeadlinesCalendar deadlines={data?.items || []} onEdit={handleEdit} />
        )}
      </div>

      {/* Modal */}
      <DeadlineModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        deadline={selectedDeadline}
      />
    </div>
  );
}

export default Deadlines;
