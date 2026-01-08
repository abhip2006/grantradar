import { useState } from 'react';
import { useCreateDeadline, useUpdateDeadline } from '../../hooks/useDeadlines';
import type { Deadline, DeadlineCreate, DeadlinePriority } from '../../types';

interface DeadlineFormProps {
  deadline: Deadline | null;
  onSuccess: () => void;
}

const FUNDERS = ['NIH', 'NSF', 'DOE', 'DOD', 'NASA', 'Private Foundation', 'Other'];
const MECHANISMS = ['R01', 'R21', 'R03', 'K01', 'K08', 'K23', 'F31', 'F32', 'U01', 'P01', 'Other'];
const PRIORITIES: DeadlinePriority[] = ['low', 'medium', 'high', 'critical'];
const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#6B7280'];

export function DeadlineForm({ deadline, onSuccess }: DeadlineFormProps) {
  const createDeadline = useCreateDeadline();
  const updateDeadline = useUpdateDeadline();
  const isEditing = !!deadline;

  const [formData, setFormData] = useState<DeadlineCreate>({
    title: deadline?.title || '',
    sponsor_deadline: deadline?.sponsor_deadline?.split('T')[0] || '',
    funder: deadline?.funder || '',
    mechanism: deadline?.mechanism || '',
    internal_deadline: deadline?.internal_deadline?.split('T')[0] || '',
    priority: (deadline?.priority as DeadlinePriority) || 'medium',
    url: deadline?.url || '',
    notes: deadline?.notes || '',
    color: deadline?.color || '#3B82F6',
    description: deadline?.description || '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const data = {
        ...formData,
        sponsor_deadline: new Date(formData.sponsor_deadline).toISOString(),
        internal_deadline: formData.internal_deadline
          ? new Date(formData.internal_deadline).toISOString()
          : undefined,
      };

      if (isEditing && deadline) {
        await updateDeadline.mutateAsync({ id: deadline.id, data });
      } else {
        await createDeadline.mutateAsync(data);
      }
      onSuccess();
    } catch (error) {
      console.error('Failed to save deadline:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700">Title *</label>
        <input
          type="text"
          required
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          placeholder="e.g., R01 Submission - ML for Climate"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Funder</label>
          <select
            value={formData.funder}
            onChange={(e) => setFormData({ ...formData, funder: e.target.value })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          >
            <option value="">Select funder</option>
            {FUNDERS.map(f => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Mechanism</label>
          <select
            value={formData.mechanism}
            onChange={(e) => setFormData({ ...formData, mechanism: e.target.value })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          >
            <option value="">Select mechanism</option>
            {MECHANISMS.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Sponsor Deadline *</label>
          <input
            type="date"
            required
            value={formData.sponsor_deadline}
            onChange={(e) => setFormData({ ...formData, sponsor_deadline: e.target.value })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Internal Deadline</label>
          <input
            type="date"
            value={formData.internal_deadline}
            onChange={(e) => setFormData({ ...formData, internal_deadline: e.target.value })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Priority</label>
          <select
            value={formData.priority}
            onChange={(e) => setFormData({ ...formData, priority: e.target.value as DeadlinePriority })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          >
            {PRIORITIES.map(p => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Color</label>
          <div className="mt-1 flex gap-2">
            {COLORS.map(c => (
              <button
                key={c}
                type="button"
                onClick={() => setFormData({ ...formData, color: c })}
                className={`w-6 h-6 rounded-full ${formData.color === c ? 'ring-2 ring-offset-2 ring-blue-500' : ''}`}
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">URL</label>
        <input
          type="url"
          value={formData.url}
          onChange={(e) => setFormData({ ...formData, url: e.target.value })}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          placeholder="https://grants.nih.gov/..."
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Notes</label>
        <textarea
          rows={3}
          value={formData.notes}
          onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          placeholder="Additional notes..."
        />
      </div>

      <div className="flex justify-end gap-3 pt-4">
        <button
          type="button"
          onClick={onSuccess}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {isSubmitting ? 'Saving...' : isEditing ? 'Update' : 'Create'}
        </button>
      </div>
    </form>
  );
}
