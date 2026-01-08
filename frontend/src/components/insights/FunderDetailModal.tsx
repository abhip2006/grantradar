import { Fragment, useMemo } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  XMarkIcon,
  BuildingLibraryIcon,
  CurrencyDollarIcon,
  DocumentTextIcon,
  CalendarDaysIcon,
  ChartBarIcon,
  TrophyIcon,
  ArrowTopRightOnSquareIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { funderInsightsApi } from '../../services/api';
import type { FunderInsightsResponse, DeadlineMonth } from '../../types';

interface FunderDetailModalProps {
  funderName: string | null;
  isOpen: boolean;
  onClose: () => void;
}

function formatCurrency(amount: number): string {
  if (amount >= 1000000) {
    return `$${(amount / 1000000).toFixed(1)}M`;
  }
  if (amount >= 1000) {
    return `$${(amount / 1000).toFixed(0)}K`;
  }
  return `$${amount.toLocaleString()}`;
}

function SeasonalityChart({ months }: { months: DeadlineMonth[] }) {
  const maxCount = useMemo(
    () => Math.max(...months.map((m) => m.grant_count), 1),
    [months]
  );

  const allMonths = useMemo(() => {
    const monthMap = new Map(months.map((m) => [m.month, m]));
    return Array.from({ length: 12 }, (_, i) => {
      const month = i + 1;
      return (
        monthMap.get(month) || {
          month,
          month_name: [
            'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
          ][i],
          grant_count: 0,
        }
      );
    });
  }, [months]);

  return (
    <div className="flex items-end gap-1 h-24">
      {allMonths.map((month) => {
        const height = month.grant_count > 0
          ? Math.max((month.grant_count / maxCount) * 100, 10)
          : 4;
        const isActive = month.grant_count > 0;

        return (
          <div key={month.month} className="flex-1 flex flex-col items-center gap-1">
            <div
              className={`w-full rounded-t transition-all ${
                isActive
                  ? 'bg-[var(--gr-cyan-500)]'
                  : 'bg-[var(--gr-slate-700)]'
              }`}
              style={{ height: `${height}%` }}
              title={`${month.month_name}: ${month.grant_count} grants`}
            />
            <span className="text-[10px] text-[var(--gr-text-tertiary)]">
              {month.month_name.substring(0, 1)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  subValue,
  colorClass = 'text-[var(--gr-cyan-400)]',
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  subValue?: string;
  colorClass?: string;
}) {
  return (
    <div className="bg-[var(--gr-bg-secondary)] rounded-lg p-4 border border-[var(--gr-border-subtle)]">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`h-4 w-4 ${colorClass}`} />
        <span className="text-xs text-[var(--gr-text-tertiary)]">{label}</span>
      </div>
      <div className="text-xl font-display font-semibold text-[var(--gr-text-primary)]">
        {value}
      </div>
      {subValue && (
        <div className="text-xs text-[var(--gr-text-tertiary)] mt-1">{subValue}</div>
      )}
    </div>
  );
}

function UserHistorySection({ history }: { history: FunderInsightsResponse['user_history'] }) {
  if (!history || history.total_applications === 0) {
    return (
      <div className="text-center py-6 text-[var(--gr-text-tertiary)]">
        <p>No application history with this funder</p>
      </div>
    );
  }

  const successPercent = history.success_rate
    ? `${(history.success_rate * 100).toFixed(0)}%`
    : 'N/A';

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-[var(--gr-bg-secondary)] rounded-lg p-3 text-center">
          <div className="text-2xl font-display font-bold text-[var(--gr-text-primary)]">
            {history.total_applications}
          </div>
          <div className="text-xs text-[var(--gr-text-tertiary)]">Total</div>
        </div>
        <div className="bg-[var(--gr-emerald-500)]/10 rounded-lg p-3 text-center">
          <div className="flex items-center justify-center gap-1">
            <CheckCircleIcon className="h-5 w-5 text-[var(--gr-emerald-400)]" />
            <span className="text-2xl font-display font-bold text-[var(--gr-emerald-400)]">
              {history.awarded_count}
            </span>
          </div>
          <div className="text-xs text-[var(--gr-text-tertiary)]">Awarded</div>
        </div>
        <div className="bg-[var(--gr-red-500)]/10 rounded-lg p-3 text-center">
          <div className="flex items-center justify-center gap-1">
            <XCircleIcon className="h-5 w-5 text-[var(--gr-red-400)]" />
            <span className="text-2xl font-display font-bold text-[var(--gr-red-400)]">
              {history.rejected_count}
            </span>
          </div>
          <div className="text-xs text-[var(--gr-text-tertiary)]">Rejected</div>
        </div>
        <div className="bg-[var(--gr-amber-500)]/10 rounded-lg p-3 text-center">
          <div className="flex items-center justify-center gap-1">
            <ClockIcon className="h-5 w-5 text-[var(--gr-amber-400)]" />
            <span className="text-2xl font-display font-bold text-[var(--gr-amber-400)]">
              {history.pending_count}
            </span>
          </div>
          <div className="text-xs text-[var(--gr-text-tertiary)]">Pending</div>
        </div>
      </div>

      {/* Success rate */}
      {history.success_rate !== null && history.success_rate !== undefined && (
        <div className="flex items-center justify-center gap-3 py-3 bg-[var(--gr-bg-secondary)] rounded-lg">
          <TrophyIcon className="h-5 w-5 text-[var(--gr-amber-400)]" />
          <span className="text-sm text-[var(--gr-text-secondary)]">
            Your success rate: <span className="font-semibold text-[var(--gr-text-primary)]">{successPercent}</span>
          </span>
        </div>
      )}

      {/* Recent applications */}
      {history.applications.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-[var(--gr-text-secondary)]">
            Recent Applications
          </h4>
          <div className="space-y-2">
            {history.applications.map((app) => (
              <Link
                key={app.grant_id}
                to={`/grants/${app.grant_id}`}
                className="flex items-center justify-between p-3 bg-[var(--gr-bg-secondary)] rounded-lg hover:bg-[var(--gr-bg-hover)] transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-[var(--gr-text-primary)] truncate">
                    {app.grant_title}
                  </p>
                  {app.applied_at && (
                    <p className="text-xs text-[var(--gr-text-tertiary)]">
                      {new Date(app.applied_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
                <span
                  className={`ml-2 px-2 py-0.5 rounded text-xs font-medium ${
                    app.stage === 'awarded'
                      ? 'bg-[var(--gr-emerald-500)]/20 text-[var(--gr-emerald-400)]'
                      : app.stage === 'rejected'
                      ? 'bg-[var(--gr-red-500)]/20 text-[var(--gr-red-400)]'
                      : 'bg-[var(--gr-amber-500)]/20 text-[var(--gr-amber-400)]'
                  }`}
                >
                  {app.stage}
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function FunderDetailModal({
  funderName,
  isOpen,
  onClose,
}: FunderDetailModalProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['funder-insights', funderName],
    queryFn: () => funderInsightsApi.getFunderInsights(funderName!),
    enabled: isOpen && !!funderName,
    staleTime: 5 * 60 * 1000,
  });

  return (
    <Transition show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-2xl bg-[var(--gr-bg-elevated)] rounded-2xl border border-[var(--gr-border-default)] shadow-[var(--gr-shadow-xl)] overflow-hidden">
                {/* Header */}
                <div className="flex items-start justify-between p-6 border-b border-[var(--gr-border-subtle)]">
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 bg-[var(--gr-cyan-500)]/10 rounded-xl flex items-center justify-center">
                      <BuildingLibraryIcon className="h-7 w-7 text-[var(--gr-cyan-400)]" />
                    </div>
                    <div>
                      <Dialog.Title className="text-xl font-display font-semibold text-[var(--gr-text-primary)]">
                        {funderName}
                      </Dialog.Title>
                      {data && (
                        <p className="text-sm text-[var(--gr-text-tertiary)] mt-1">
                          {data.active_grants} active / {data.total_grants} total grants
                        </p>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={onClose}
                    className="p-2 rounded-lg text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-hover)] transition-colors"
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                </div>

                {/* Content */}
                <div className="p-6 max-h-[70vh] overflow-y-auto">
                  {isLoading ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        {[...Array(4)].map((_, i) => (
                          <div key={i} className="skeleton h-24 rounded-lg" />
                        ))}
                      </div>
                      <div className="skeleton h-32 rounded-lg" />
                    </div>
                  ) : error ? (
                    <div className="text-center py-8 text-[var(--gr-text-tertiary)]">
                      <p>Failed to load funder insights</p>
                    </div>
                  ) : data ? (
                    <div className="space-y-6">
                      {/* Key Stats */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        <StatCard
                          icon={DocumentTextIcon}
                          label="Total Grants"
                          value={data.total_grants}
                          subValue={`${data.active_grants} active`}
                        />
                        <StatCard
                          icon={CurrencyDollarIcon}
                          label="Avg. Award"
                          value={
                            data.avg_amount_max
                              ? formatCurrency(data.avg_amount_max)
                              : 'N/A'
                          }
                          subValue={
                            data.min_amount && data.max_amount
                              ? `${formatCurrency(data.min_amount)} - ${formatCurrency(data.max_amount)}`
                              : undefined
                          }
                          colorClass="text-[var(--gr-amber-400)]"
                        />
                        <StatCard
                          icon={ChartBarIcon}
                          label="Focus Areas"
                          value={data.focus_areas.length}
                          subValue="Categories"
                          colorClass="text-[var(--gr-emerald-400)]"
                        />
                        <StatCard
                          icon={CalendarDaysIcon}
                          label="Peak Months"
                          value={data.typical_deadline_months.slice(0, 2).join(', ') || 'N/A'}
                          subValue="Most deadlines"
                          colorClass="text-[var(--gr-blue-400)]"
                        />
                      </div>

                      {/* Seasonality Chart */}
                      {data.deadline_months.length > 0 && (
                        <div className="bg-[var(--gr-bg-secondary)] rounded-lg p-4 border border-[var(--gr-border-subtle)]">
                          <h3 className="text-sm font-medium text-[var(--gr-text-secondary)] mb-4 flex items-center gap-2">
                            <CalendarDaysIcon className="h-4 w-4" />
                            Deadline Seasonality
                          </h3>
                          <SeasonalityChart months={data.deadline_months} />
                          <p className="text-xs text-[var(--gr-text-tertiary)] mt-3 text-center">
                            Grant deadlines by month
                          </p>
                        </div>
                      )}

                      {/* Focus Areas */}
                      {data.focus_areas.length > 0 && (
                        <div>
                          <h3 className="text-sm font-medium text-[var(--gr-text-secondary)] mb-3">
                            Common Focus Areas
                          </h3>
                          <div className="flex flex-wrap gap-2">
                            {data.focus_areas.map((area, index) => {
                              const count = data.focus_area_counts[area] || 0;
                              return (
                                <span
                                  key={index}
                                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--gr-slate-700)]/50 text-sm text-[var(--gr-text-secondary)] border border-[var(--gr-border-subtle)]"
                                >
                                  {area}
                                  <span className="text-xs text-[var(--gr-text-tertiary)]">
                                    ({count})
                                  </span>
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* User History */}
                      {data.user_history && (
                        <div className="pt-4 border-t border-[var(--gr-border-subtle)]">
                          <h3 className="text-sm font-medium text-[var(--gr-text-secondary)] mb-4 flex items-center gap-2">
                            <TrophyIcon className="h-4 w-4 text-[var(--gr-amber-400)]" />
                            Your History with {funderName}
                          </h3>
                          <UserHistorySection history={data.user_history} />
                        </div>
                      )}
                    </div>
                  ) : null}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-3 p-4 border-t border-[var(--gr-border-subtle)] bg-[var(--gr-bg-secondary)]">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 text-sm font-medium text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] transition-colors"
                  >
                    Close
                  </button>
                  {funderName && (
                    <Link
                      to={`/funders?search=${encodeURIComponent(funderName)}`}
                      className="btn-primary inline-flex items-center gap-2"
                    >
                      View All Grants
                      <ArrowTopRightOnSquareIcon className="h-4 w-4" />
                    </Link>
                  )}
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}

export default FunderDetailModal;
