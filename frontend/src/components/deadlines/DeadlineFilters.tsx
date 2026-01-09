import type { DeadlineFilters as FiltersType, DeadlineStatus } from '../../types';

interface DeadlineFiltersProps {
  filters: FiltersType;
  onChange: (filters: FiltersType) => void;
}

const STATUSES: DeadlineStatus[] = ['not_started', 'drafting', 'internal_review', 'submitted', 'under_review', 'awarded', 'rejected'];
const FUNDERS = ['NIH', 'NSF', 'DOE', 'DOD', 'NASA', 'Private Foundation'];

export function DeadlineFilters({ filters, onChange }: DeadlineFiltersProps) {
  return (
    <div className="mt-4 p-4 bg-gray-50 rounded-lg space-y-4">
      <div className="grid grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Status</label>
          <select
            value={filters.status || ''}
            onChange={(e) => onChange({ ...filters, status: e.target.value as DeadlineStatus || undefined })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          >
            <option value="">All</option>
            {STATUSES.map(s => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Funder</label>
          <select
            value={filters.funder || ''}
            onChange={(e) => onChange({ ...filters, funder: e.target.value || undefined })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          >
            <option value="">All</option>
            {FUNDERS.map(f => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">From Date</label>
          <input
            type="date"
            value={filters.from_date || ''}
            onChange={(e) => onChange({ ...filters, from_date: e.target.value || undefined })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">To Date</label>
          <input
            type="date"
            value={filters.to_date || ''}
            onChange={(e) => onChange({ ...filters, to_date: e.target.value || undefined })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700">Search</label>
          <input
            type="text"
            value={filters.search || ''}
            onChange={(e) => onChange({ ...filters, search: e.target.value || undefined })}
            placeholder="Search by title..."
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          />
        </div>
        <div className="pt-6">
          <button
            onClick={() => onChange({})}
            className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900"
          >
            Clear filters
          </button>
        </div>
      </div>
    </div>
  );
}
