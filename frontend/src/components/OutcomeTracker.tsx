import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ChartBarIcon,
  CalendarIcon,
  CurrencyDollarIcon,
  DocumentTextIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import { grantsApi } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import type { ApplicationStatus, OutcomeUpdate } from '../types';
import { APPLICATION_STATUS_CONFIG } from '../types';

interface OutcomeTrackerProps {
  matchId: string;
  initialStatus?: ApplicationStatus;
  initialSubmittedAt?: string;
  initialOutcomeReceivedAt?: string;
  initialAwardAmount?: number;
  initialNotes?: string;
}

export function OutcomeTracker({
  matchId,
  initialStatus = 'not_applied',
  initialSubmittedAt,
  initialOutcomeReceivedAt,
  initialAwardAmount,
  initialNotes,
}: OutcomeTrackerProps) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  // Form state
  const [status, setStatus] = useState<ApplicationStatus>(initialStatus);
  const [submittedAt, setSubmittedAt] = useState(initialSubmittedAt || '');
  const [outcomeReceivedAt, setOutcomeReceivedAt] = useState(initialOutcomeReceivedAt || '');
  const [awardAmount, setAwardAmount] = useState<string>(
    initialAwardAmount ? String(initialAwardAmount) : ''
  );
  const [notes, setNotes] = useState(initialNotes || '');

  // Track if form has been modified
  const [isDirty, setIsDirty] = useState(false);

  // Validation errors
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Update form when initial values change
  useEffect(() => {
    setStatus(initialStatus);
    setSubmittedAt(initialSubmittedAt || '');
    setOutcomeReceivedAt(initialOutcomeReceivedAt || '');
    setAwardAmount(initialAwardAmount ? String(initialAwardAmount) : '');
    setNotes(initialNotes || '');
    setIsDirty(false);
  }, [initialStatus, initialSubmittedAt, initialOutcomeReceivedAt, initialAwardAmount, initialNotes]);

  // Update outcome mutation
  const updateOutcomeMutation = useMutation({
    mutationFn: (outcome: OutcomeUpdate) => grantsApi.updateOutcome(matchId, outcome),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['grant-match', matchId] });
      queryClient.invalidateQueries({ queryKey: ['matches'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      showToast('Application status updated', 'success');
      setIsDirty(false);
    },
    onError: () => {
      showToast('Failed to update application status', 'error');
    },
  });

  // Validate form
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    const today = new Date();
    today.setHours(23, 59, 59, 999);

    // Validate submitted date
    if (submittedAt) {
      const submittedDate = new Date(submittedAt);
      if (submittedDate > today) {
        newErrors.submittedAt = 'Date cannot be in the future';
      }
    }

    // Validate outcome received date
    if (outcomeReceivedAt) {
      const outcomeDate = new Date(outcomeReceivedAt);
      if (outcomeDate > today) {
        newErrors.outcomeReceivedAt = 'Date cannot be in the future';
      }
      // Outcome date should be after submitted date
      if (submittedAt && outcomeDate < new Date(submittedAt)) {
        newErrors.outcomeReceivedAt = 'Outcome date must be after submission date';
      }
    }

    // Validate award amount
    if (awardAmount) {
      const amount = parseFloat(awardAmount);
      if (isNaN(amount) || amount < 0) {
        newErrors.awardAmount = 'Award amount must be a positive number';
      }
    }

    // Require submitted date for certain statuses
    if (['submitted', 'awarded', 'rejected'].includes(status) && !submittedAt) {
      newErrors.submittedAt = 'Submission date is required';
    }

    // Require outcome date for awarded/rejected
    if (['awarded', 'rejected'].includes(status) && !outcomeReceivedAt) {
      newErrors.outcomeReceivedAt = 'Outcome date is required';
    }

    // Require award amount for awarded status
    if (status === 'awarded' && !awardAmount) {
      newErrors.awardAmount = 'Award amount is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form submission
  const handleSubmit = () => {
    if (!validateForm()) {
      return;
    }

    const outcome: OutcomeUpdate = {
      application_status: status,
      application_submitted_at: submittedAt || undefined,
      outcome_received_at: outcomeReceivedAt || undefined,
      award_amount: awardAmount ? parseFloat(awardAmount) : undefined,
      outcome_notes: notes || undefined,
    };

    updateOutcomeMutation.mutate(outcome);
  };

  // Handle field changes
  const handleStatusChange = (newStatus: ApplicationStatus) => {
    setStatus(newStatus);
    setIsDirty(true);
    setErrors({});

    // Clear fields that don't apply to the new status
    if (['not_applied', 'in_progress'].includes(newStatus)) {
      setOutcomeReceivedAt('');
      setAwardAmount('');
    }
    if (newStatus === 'not_applied') {
      setSubmittedAt('');
    }
  };

  // Status configuration for display
  const statusConfig = APPLICATION_STATUS_CONFIG[status];

  // Determine which fields to show
  const showSubmittedDate = ['in_progress', 'submitted', 'awarded', 'rejected', 'withdrawn'].includes(status);
  const showOutcomeDate = ['awarded', 'rejected'].includes(status);
  const showAwardAmount = status === 'awarded';

  return (
    <section className="bg-white rounded-2xl border border-[var(--gr-border-default)] shadow-sm overflow-hidden">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-indigo-50">
            <ChartBarIcon className="h-5 w-5 text-indigo-600" />
          </div>
          <div>
            <h2 className="text-xl font-display font-medium text-[var(--gr-text-primary)]">
              Application Status
            </h2>
            <p className="text-sm text-[var(--gr-text-tertiary)]">
              Track your application progress and outcomes
            </p>
          </div>
        </div>

        {/* Status Selector */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
            Current Status
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {(Object.keys(APPLICATION_STATUS_CONFIG) as ApplicationStatus[]).map((statusKey) => {
              const config = APPLICATION_STATUS_CONFIG[statusKey];
              const isSelected = status === statusKey;
              return (
                <button
                  key={statusKey}
                  onClick={() => handleStatusChange(statusKey)}
                  className={`px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 border-2 ${
                    isSelected
                      ? `${config.bgColor} ${config.color} border-current`
                      : 'bg-[var(--gr-gray-50)] text-[var(--gr-text-secondary)] border-transparent hover:bg-[var(--gr-gray-100)]'
                  }`}
                >
                  {config.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Submitted Date */}
        {showSubmittedDate && (
          <div className="mb-4">
            <label className="flex items-center gap-2 text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
              <CalendarIcon className="h-4 w-4" />
              Application Submitted On
            </label>
            <input
              type="date"
              value={submittedAt}
              onChange={(e) => {
                setSubmittedAt(e.target.value);
                setIsDirty(true);
                setErrors((prev) => ({ ...prev, submittedAt: '' }));
              }}
              max={new Date().toISOString().split('T')[0]}
              className={`w-full px-4 py-3 rounded-xl border bg-[var(--gr-bg-card)] text-[var(--gr-text-primary)] transition-colors ${
                errors.submittedAt
                  ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                  : 'border-[var(--gr-border-default)] focus:border-[var(--gr-blue-500)] focus:ring-[var(--gr-blue-500)]'
              } focus:outline-none focus:ring-2 focus:ring-opacity-20`}
            />
            {errors.submittedAt && (
              <p className="mt-1.5 text-sm text-red-600 flex items-center gap-1">
                <ExclamationCircleIcon className="h-4 w-4" />
                {errors.submittedAt}
              </p>
            )}
          </div>
        )}

        {/* Outcome Date */}
        {showOutcomeDate && (
          <div className="mb-4">
            <label className="flex items-center gap-2 text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
              <CalendarIcon className="h-4 w-4" />
              Outcome Received On
            </label>
            <input
              type="date"
              value={outcomeReceivedAt}
              onChange={(e) => {
                setOutcomeReceivedAt(e.target.value);
                setIsDirty(true);
                setErrors((prev) => ({ ...prev, outcomeReceivedAt: '' }));
              }}
              max={new Date().toISOString().split('T')[0]}
              min={submittedAt || undefined}
              className={`w-full px-4 py-3 rounded-xl border bg-[var(--gr-bg-card)] text-[var(--gr-text-primary)] transition-colors ${
                errors.outcomeReceivedAt
                  ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                  : 'border-[var(--gr-border-default)] focus:border-[var(--gr-blue-500)] focus:ring-[var(--gr-blue-500)]'
              } focus:outline-none focus:ring-2 focus:ring-opacity-20`}
            />
            {errors.outcomeReceivedAt && (
              <p className="mt-1.5 text-sm text-red-600 flex items-center gap-1">
                <ExclamationCircleIcon className="h-4 w-4" />
                {errors.outcomeReceivedAt}
              </p>
            )}
          </div>
        )}

        {/* Award Amount */}
        {showAwardAmount && (
          <div className="mb-4">
            <label className="flex items-center gap-2 text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
              <CurrencyDollarIcon className="h-4 w-4" />
              Award Amount
            </label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--gr-text-tertiary)]">
                $
              </span>
              <input
                type="number"
                value={awardAmount}
                onChange={(e) => {
                  setAwardAmount(e.target.value);
                  setIsDirty(true);
                  setErrors((prev) => ({ ...prev, awardAmount: '' }));
                }}
                min="0"
                step="1"
                placeholder="0"
                className={`w-full pl-8 pr-4 py-3 rounded-xl border bg-[var(--gr-bg-card)] text-[var(--gr-text-primary)] transition-colors ${
                  errors.awardAmount
                    ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                    : 'border-[var(--gr-border-default)] focus:border-[var(--gr-blue-500)] focus:ring-[var(--gr-blue-500)]'
                } focus:outline-none focus:ring-2 focus:ring-opacity-20`}
              />
            </div>
            {errors.awardAmount && (
              <p className="mt-1.5 text-sm text-red-600 flex items-center gap-1">
                <ExclamationCircleIcon className="h-4 w-4" />
                {errors.awardAmount}
              </p>
            )}
          </div>
        )}

        {/* Notes */}
        <div className="mb-6">
          <label className="flex items-center gap-2 text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
            <DocumentTextIcon className="h-4 w-4" />
            Notes
          </label>
          <textarea
            value={notes}
            onChange={(e) => {
              setNotes(e.target.value);
              setIsDirty(true);
            }}
            rows={3}
            placeholder="Add any notes about this application..."
            className="w-full px-4 py-3 rounded-xl border border-[var(--gr-border-default)] bg-[var(--gr-bg-card)] text-[var(--gr-text-primary)] placeholder:text-[var(--gr-text-muted)] transition-colors focus:border-[var(--gr-blue-500)] focus:ring-[var(--gr-blue-500)] focus:outline-none focus:ring-2 focus:ring-opacity-20 resize-none"
          />
        </div>

        {/* Save Button */}
        <button
          onClick={handleSubmit}
          disabled={!isDirty || updateOutcomeMutation.isPending}
          className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-all duration-200 ${
            isDirty && !updateOutcomeMutation.isPending
              ? 'bg-indigo-600 text-white hover:bg-indigo-700'
              : 'bg-[var(--gr-gray-100)] text-[var(--gr-text-muted)] cursor-not-allowed'
          }`}
        >
          {updateOutcomeMutation.isPending ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
              Saving...
            </>
          ) : (
            <>
              <CheckCircleIcon className="h-5 w-5" />
              Save Changes
            </>
          )}
        </button>

        {/* Current Status Display */}
        {status !== 'not_applied' && (
          <div className={`mt-4 p-4 rounded-xl ${statusConfig.bgColor} border border-current/20`}>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${statusConfig.color.replace('text-', 'bg-')}`} />
              <span className={`text-sm font-medium ${statusConfig.color}`}>
                {statusConfig.label}
              </span>
            </div>
            {submittedAt && (
              <p className="text-sm text-[var(--gr-text-secondary)] mt-2">
                Submitted: {new Date(submittedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
              </p>
            )}
            {outcomeReceivedAt && (
              <p className="text-sm text-[var(--gr-text-secondary)] mt-1">
                Outcome received: {new Date(outcomeReceivedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
              </p>
            )}
            {awardAmount && status === 'awarded' && (
              <p className="text-sm text-emerald-700 font-medium mt-1">
                Award: ${parseFloat(awardAmount).toLocaleString()}
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

export default OutcomeTracker;
