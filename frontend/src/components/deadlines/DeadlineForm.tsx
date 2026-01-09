import { useState, useEffect } from 'react';
import { useCreateDeadline, useUpdateDeadline } from '../../hooks/useDeadlines';
import type { Deadline, DeadlineCreate, DeadlinePriority, DeadlineStatus } from '../../types';
import { DEADLINE_STATUS_CONFIG, DEADLINE_PRIORITY_CONFIG } from '../../types';
import { ArrowPathIcon, BellIcon } from '@heroicons/react/24/outline';

interface DeadlineFormProps {
  deadline: Deadline | null;
  onSuccess: () => void;
}

const FUNDERS = ['NIH', 'NSF', 'DOE', 'DOD', 'NASA', 'Private Foundation', 'Other'];
const MECHANISMS = ['R01', 'R21', 'R03', 'K01', 'K08', 'K23', 'F31', 'F32', 'U01', 'P01', 'Other'];
const PRIORITIES: DeadlinePriority[] = ['low', 'medium', 'high', 'critical'];
const STATUSES: DeadlineStatus[] = ['not_started', 'drafting', 'internal_review', 'submitted', 'under_review', 'awarded', 'rejected'];
const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#6B7280'];

// Predefined reminder options (days before deadline)
const REMINDER_OPTIONS = [
  { value: 30, label: '30 days' },
  { value: 14, label: '14 days' },
  { value: 7, label: '7 days' },
  { value: 3, label: '3 days' },
  { value: 1, label: '1 day' },
];

// Predefined recurrence rules
const RECURRENCE_PRESETS = [
  { key: 'none', label: 'No recurrence', rule: '' },
  { key: 'nih_standard', label: 'NIH Standard (Feb 5, Jun 5, Oct 5)', rule: 'FREQ=YEARLY;BYMONTH=2,6,10;BYMONTHDAY=5' },
  { key: 'nih_aids', label: 'NIH AIDS (Jan 7, May 7, Sep 7)', rule: 'FREQ=YEARLY;BYMONTH=1,5,9;BYMONTHDAY=7' },
  { key: 'nsf_quarterly', label: 'NSF Quarterly', rule: 'FREQ=YEARLY;BYMONTH=1,4,7,10;BYMONTHDAY=15' },
  { key: 'annual', label: 'Annual (same date)', rule: 'FREQ=YEARLY' },
  { key: 'custom', label: 'Custom RRULE', rule: 'custom' },
];

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
    status: (deadline?.status as DeadlineStatus) || 'not_started',
    priority: (deadline?.priority as DeadlinePriority) || 'medium',
    url: deadline?.url || '',
    notes: deadline?.notes || '',
    color: deadline?.color || '#3B82F6',
    description: deadline?.description || '',
    is_recurring: deadline?.is_recurring || false,
    recurrence_rule: deadline?.recurrence_rule || '',
    reminder_config: deadline?.reminder_config || [30, 14, 7, 3, 1],
  });

  const [selectedRecurrencePreset, setSelectedRecurrencePreset] = useState('none');
  const [customRule, setCustomRule] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Initialize recurrence preset from existing data
  useEffect(() => {
    if (deadline?.recurrence_rule) {
      const preset = RECURRENCE_PRESETS.find(p => p.rule === deadline.recurrence_rule);
      if (preset) {
        setSelectedRecurrencePreset(preset.key);
      } else {
        setSelectedRecurrencePreset('custom');
        setCustomRule(deadline.recurrence_rule);
      }
    }
  }, [deadline]);

  const handleRecurrenceChange = (presetKey: string) => {
    setSelectedRecurrencePreset(presetKey);
    const preset = RECURRENCE_PRESETS.find(p => p.key === presetKey);
    if (preset && presetKey !== 'custom' && presetKey !== 'none') {
      setFormData({
        ...formData,
        is_recurring: true,
        recurrence_rule: preset.rule,
      });
    } else if (presetKey === 'none') {
      setFormData({
        ...formData,
        is_recurring: false,
        recurrence_rule: '',
      });
    } else if (presetKey === 'custom') {
      setFormData({
        ...formData,
        is_recurring: true,
        recurrence_rule: customRule,
      });
    }
  };

  const toggleReminder = (days: number) => {
    const current = formData.reminder_config || [];
    const newConfig = current.includes(days)
      ? current.filter(d => d !== days)
      : [...current, days].sort((a, b) => b - a);
    setFormData({ ...formData, reminder_config: newConfig });
  };

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
        recurrence_rule: selectedRecurrencePreset === 'custom' ? customRule : formData.recurrence_rule,
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
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Title */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Title *</label>
        <input
          type="text"
          required
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
          className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          placeholder="e.g., R01 Submission - ML for Climate"
        />
      </div>

      {/* Funder and Mechanism */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Funder</label>
          <select
            value={formData.funder}
            onChange={(e) => setFormData({ ...formData, funder: e.target.value })}
            className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          >
            <option value="">Select funder</option>
            {FUNDERS.map(f => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Mechanism</label>
          <select
            value={formData.mechanism}
            onChange={(e) => setFormData({ ...formData, mechanism: e.target.value })}
            className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          >
            <option value="">Select mechanism</option>
            {MECHANISMS.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
      </div>

      {/* Deadlines */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Sponsor Deadline *</label>
          <input
            type="date"
            required
            value={formData.sponsor_deadline}
            onChange={(e) => setFormData({ ...formData, sponsor_deadline: e.target.value })}
            className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Internal Deadline</label>
          <input
            type="date"
            value={formData.internal_deadline}
            onChange={(e) => setFormData({ ...formData, internal_deadline: e.target.value })}
            className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          />
        </div>
      </div>

      {/* Status and Priority */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
          <select
            value={formData.status}
            onChange={(e) => setFormData({ ...formData, status: e.target.value as DeadlineStatus })}
            className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          >
            {STATUSES.map(s => (
              <option key={s} value={s}>
                {DEADLINE_STATUS_CONFIG[s].label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
          <select
            value={formData.priority}
            onChange={(e) => setFormData({ ...formData, priority: e.target.value as DeadlinePriority })}
            className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          >
            {PRIORITIES.map(p => (
              <option key={p} value={p}>
                {DEADLINE_PRIORITY_CONFIG[p].label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Recurring Deadline Section */}
      <div className="border border-gray-200 rounded-lg p-4 bg-gray-50/50">
        <div className="flex items-center gap-2 mb-3">
          <ArrowPathIcon className="w-5 h-5 text-purple-500" />
          <span className="text-sm font-medium text-gray-700">Recurring Deadline</span>
        </div>
        <select
          value={selectedRecurrencePreset}
          onChange={(e) => handleRecurrenceChange(e.target.value)}
          className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
        >
          {RECURRENCE_PRESETS.map(preset => (
            <option key={preset.key} value={preset.key}>
              {preset.label}
            </option>
          ))}
        </select>
        {selectedRecurrencePreset === 'custom' && (
          <div className="mt-3">
            <label className="block text-xs text-gray-500 mb-1">Custom RRULE (RFC 5545)</label>
            <input
              type="text"
              value={customRule}
              onChange={(e) => {
                setCustomRule(e.target.value);
                setFormData({ ...formData, recurrence_rule: e.target.value });
              }}
              className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
              placeholder="FREQ=YEARLY;BYMONTH=2,6,10;BYMONTHDAY=5"
            />
          </div>
        )}
      </div>

      {/* Reminder Configuration */}
      <div className="border border-gray-200 rounded-lg p-4 bg-gray-50/50">
        <div className="flex items-center gap-2 mb-3">
          <BellIcon className="w-5 h-5 text-blue-500" />
          <span className="text-sm font-medium text-gray-700">Reminders</span>
          <span className="text-xs text-gray-400">(before deadline)</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {REMINDER_OPTIONS.map(option => {
            const isSelected = formData.reminder_config?.includes(option.value);
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => toggleReminder(option.value)}
                className={`
                  px-3 py-1.5 text-sm rounded-lg border transition-all
                  ${isSelected
                    ? 'bg-blue-50 border-blue-300 text-blue-700'
                    : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                  }
                `}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Color Picker */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Color</label>
        <div className="flex gap-2">
          {COLORS.map(c => (
            <button
              key={c}
              type="button"
              onClick={() => setFormData({ ...formData, color: c })}
              className={`w-8 h-8 rounded-full transition-all ${formData.color === c ? 'ring-2 ring-offset-2 ring-blue-500 scale-110' : 'hover:scale-105'}`}
              style={{ backgroundColor: c }}
            />
          ))}
        </div>
      </div>

      {/* URL */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">URL</label>
        <input
          type="url"
          value={formData.url}
          onChange={(e) => setFormData({ ...formData, url: e.target.value })}
          className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          placeholder="https://grants.nih.gov/..."
        />
      </div>

      {/* Notes */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
        <textarea
          rows={3}
          value={formData.notes}
          onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
          className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          placeholder="Additional notes..."
        />
      </div>

      {/* Submit Buttons */}
      <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
        <button
          type="button"
          onClick={onSuccess}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-5 py-2 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-500 rounded-lg hover:from-blue-700 hover:to-blue-600 disabled:opacity-50 transition-all shadow-sm"
        >
          {isSubmitting ? 'Saving...' : isEditing ? 'Update Deadline' : 'Create Deadline'}
        </button>
      </div>
    </form>
  );
}
