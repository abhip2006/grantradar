import type { KanbanFilters, Priority, ApplicationStage } from '../../types/kanban';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

interface BoardFiltersProps {
  filters: KanbanFilters;
  onChange: (filters: KanbanFilters) => void;
  totals?: {
    total: number;
    by_stage: Record<ApplicationStage, number>;
    overdue: number;
  };
}

export function BoardFilters({ filters, onChange, totals }: BoardFiltersProps) {
  return (
    <div className="bg-white border-b px-4 py-3 flex items-center gap-4">
      {/* Search */}
      <div className="relative flex-1 max-w-xs">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search applications..."
          value={filters.search || ''}
          onChange={e => onChange({ ...filters, search: e.target.value || undefined })}
          className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* Priority filter */}
      <select
        value={filters.priorities?.join(',') || ''}
        onChange={e => onChange({
          ...filters,
          priorities: e.target.value ? e.target.value.split(',') as Priority[] : undefined,
        })}
        className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
      >
        <option value="">All Priorities</option>
        <option value="critical">Critical</option>
        <option value="high">High</option>
        <option value="medium">Medium</option>
        <option value="low">Low</option>
      </select>

      {/* Show archived toggle */}
      <label className="flex items-center gap-2 text-sm text-gray-600">
        <input
          type="checkbox"
          checked={filters.show_archived || false}
          onChange={e => onChange({ ...filters, show_archived: e.target.checked })}
          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
        Show archived
      </label>

      {/* Stats */}
      {totals && (
        <div className="ml-auto flex items-center gap-4 text-sm text-gray-500">
          <span>{totals.total} total</span>
          {totals.overdue > 0 && (
            <span className="text-red-600">{totals.overdue} overdue</span>
          )}
        </div>
      )}
    </div>
  );
}

export default BoardFilters;
