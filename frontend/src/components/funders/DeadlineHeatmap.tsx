import { useMemo } from 'react';
import { CalendarDaysIcon } from '@heroicons/react/24/outline';
import type { DeadlineMonth } from '../../types';

interface DeadlineHeatmapProps {
  deadlineMonths: DeadlineMonth[];
  typicalDeadlineMonths: string[];
}

const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

const FULL_MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

export function DeadlineHeatmap({ deadlineMonths, typicalDeadlineMonths }: DeadlineHeatmapProps) {
  // Create a complete 12-month array with counts
  const monthData = useMemo(() => {
    const monthMap = new Map(deadlineMonths.map((m) => [m.month, m.grant_count]));
    return MONTH_NAMES.map((name, index) => ({
      name,
      fullName: FULL_MONTH_NAMES[index],
      month: index + 1,
      count: monthMap.get(index + 1) || 0,
    }));
  }, [deadlineMonths]);

  const maxCount = useMemo(
    () => Math.max(...monthData.map((m) => m.count), 1),
    [monthData]
  );

  const totalDeadlines = useMemo(
    () => monthData.reduce((sum, m) => sum + m.count, 0),
    [monthData]
  );

  // Get intensity class based on count
  const getIntensityClass = (count: number): string => {
    if (count === 0) return 'bg-[var(--gr-gray-100)]';
    const ratio = count / maxCount;
    if (ratio >= 0.8) return 'bg-[var(--gr-blue-600)]';
    if (ratio >= 0.6) return 'bg-[var(--gr-blue-500)]';
    if (ratio >= 0.4) return 'bg-[var(--gr-blue-400)]';
    if (ratio >= 0.2) return 'bg-[var(--gr-blue-300)]';
    return 'bg-[var(--gr-blue-200)]';
  };

  // Get text color based on intensity
  const getTextClass = (count: number): string => {
    if (count === 0) return 'text-[var(--gr-text-tertiary)]';
    const ratio = count / maxCount;
    if (ratio >= 0.5) return 'text-white';
    return 'text-[var(--gr-blue-800)]';
  };

  // Check if this is a peak month
  const isPeakMonth = (monthName: string): boolean => {
    return typicalDeadlineMonths.some(
      (m) => m.toLowerCase().startsWith(monthName.toLowerCase().substring(0, 3))
    );
  };

  if (totalDeadlines === 0) {
    return (
      <div className="bg-[var(--gr-bg-card)] rounded-xl p-6 border border-[var(--gr-border-default)]">
        <div className="flex items-center gap-2 mb-4">
          <CalendarDaysIcon className="h-5 w-5 text-[var(--gr-blue-600)]" />
          <h3 className="text-base font-display font-medium text-[var(--gr-text-primary)]">
            Deadline Seasonality
          </h3>
        </div>
        <div className="text-center py-8 text-[var(--gr-text-tertiary)]">
          <p>No deadline data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[var(--gr-bg-card)] rounded-xl p-6 border border-[var(--gr-border-default)]">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <CalendarDaysIcon className="h-5 w-5 text-[var(--gr-blue-600)]" />
          <h3 className="text-base font-display font-medium text-[var(--gr-text-primary)]">
            Deadline Seasonality
          </h3>
        </div>
        <div className="text-sm text-[var(--gr-text-tertiary)]">
          {totalDeadlines} deadlines tracked
        </div>
      </div>

      {/* Heatmap Grid */}
      <div className="grid grid-cols-6 sm:grid-cols-12 gap-2 mb-6">
        {monthData.map((month) => (
          <div
            key={month.month}
            className={`relative aspect-square rounded-lg ${getIntensityClass(month.count)}
              flex flex-col items-center justify-center transition-all hover:scale-105 cursor-default
              ${isPeakMonth(month.fullName) ? 'ring-2 ring-[var(--gr-yellow-400)] ring-offset-2 ring-offset-[var(--gr-bg-card)]' : ''}`}
            title={`${month.fullName}: ${month.count} deadlines`}
          >
            <span className={`text-xs font-medium ${getTextClass(month.count)}`}>
              {month.name}
            </span>
            <span className={`text-lg font-display font-bold ${getTextClass(month.count)}`}>
              {month.count}
            </span>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--gr-text-tertiary)]">Fewer</span>
          <div className="flex gap-1">
            <div className="w-4 h-4 rounded bg-[var(--gr-gray-100)]" />
            <div className="w-4 h-4 rounded bg-[var(--gr-blue-200)]" />
            <div className="w-4 h-4 rounded bg-[var(--gr-blue-300)]" />
            <div className="w-4 h-4 rounded bg-[var(--gr-blue-400)]" />
            <div className="w-4 h-4 rounded bg-[var(--gr-blue-500)]" />
            <div className="w-4 h-4 rounded bg-[var(--gr-blue-600)]" />
          </div>
          <span className="text-xs text-[var(--gr-text-tertiary)]">More</span>
        </div>

        {typicalDeadlineMonths.length > 0 && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded border-2 border-[var(--gr-yellow-400)]" />
            <span className="text-xs text-[var(--gr-text-tertiary)]">Peak months</span>
          </div>
        )}
      </div>

      {/* Peak Months Summary */}
      {typicalDeadlineMonths.length > 0 && (
        <div className="mt-4 pt-4 border-t border-[var(--gr-border-subtle)]">
          <p className="text-sm text-[var(--gr-text-secondary)]">
            <span className="font-medium">Peak deadline periods:</span>{' '}
            <span className="text-[var(--gr-blue-600)]">
              {typicalDeadlineMonths.join(', ')}
            </span>
          </p>
        </div>
      )}
    </div>
  );
}

export default DeadlineHeatmap;
