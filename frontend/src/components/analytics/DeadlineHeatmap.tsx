import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../../services/api';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameDay, parseISO, addMonths } from 'date-fns';
import { CalendarDaysIcon } from '@heroicons/react/24/outline';

interface DeadlineDay {
  date: string;
  count: number;
  intensity: 'none' | 'low' | 'medium' | 'high' | 'critical';
  applications: number;
}

interface DeadlineHeatmapResponse {
  days: DeadlineDay[];
  total_deadlines: number;
  upcoming_count: number;
  period_start: string;
  period_end: string;
}

const INTENSITY_COLORS: Record<string, string> = {
  none: 'bg-[var(--gr-gray-100)]',
  low: 'bg-emerald-200',
  medium: 'bg-amber-300',
  high: 'bg-orange-400',
  critical: 'bg-red-500',
};

const INTENSITY_TEXT: Record<string, string> = {
  none: 'text-[var(--gr-text-tertiary)]',
  low: 'text-emerald-800',
  medium: 'text-amber-900',
  high: 'text-white',
  critical: 'text-white',
};

const WEEKDAY_LABELS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

export function DeadlineHeatmap() {
  const { data, isLoading, error } = useQuery<DeadlineHeatmapResponse>({
    queryKey: ['analytics', 'deadline-heatmap'],
    queryFn: () => analyticsApi.getDeadlineHeatmap(),
  });

  const calendarData = useMemo(() => {
    const now = new Date();
    const months = [];

    for (let i = 0; i < 3; i++) {
      const monthStart = startOfMonth(addMonths(now, i));
      const monthEnd = endOfMonth(monthStart);
      const days = eachDayOfInterval({ start: monthStart, end: monthEnd });

      months.push({
        name: format(monthStart, 'MMMM yyyy'),
        days: days.map((day) => {
          const dayData = data?.days?.find((d) =>
            isSameDay(parseISO(d.date), day)
          );
          return {
            date: day,
            count: dayData?.count || 0,
            intensity: dayData?.intensity || 'none',
            applications: dayData?.applications || 0,
          };
        }),
      });
    }

    return months;
  }, [data]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <div className="animate-pulse">
          <div className="h-6 w-48 bg-[var(--gr-bg-secondary)] rounded mb-4" />
          <div className="h-[200px] bg-[var(--gr-bg-secondary)] rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <div className="flex items-center gap-2 mb-4">
          <CalendarDaysIcon className="h-5 w-5 text-[var(--gr-blue-600)]" />
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
            Deadline Heatmap
          </h3>
        </div>
        <div className="flex items-center justify-center h-48 text-[var(--gr-text-tertiary)]">
          Unable to load deadline heatmap data
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <CalendarDaysIcon className="h-5 w-5 text-[var(--gr-blue-600)]" />
          <div>
            <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
              Deadline Heatmap
            </h3>
            <p className="text-sm text-[var(--gr-text-tertiary)]">
              {data?.total_deadlines || 0} upcoming deadlines
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        {calendarData.map((month) => (
          <div key={month.name}>
            <h4 className="text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
              {month.name}
            </h4>
            <div className="grid grid-cols-7 gap-1">
              {/* Weekday headers */}
              {WEEKDAY_LABELS.map((day, i) => (
                <div
                  key={`header-${i}`}
                  className="text-center text-xs text-[var(--gr-text-tertiary)] py-1 font-medium"
                >
                  {day}
                </div>
              ))}

              {/* Padding for first day of month */}
              {Array.from({ length: month.days[0]?.date.getDay() || 0 }).map((_, i) => (
                <div key={`pad-${i}`} className="aspect-square" />
              ))}

              {/* Days */}
              {month.days.map((day, i) => {
                const intensityClass = INTENSITY_COLORS[day.intensity] || INTENSITY_COLORS.none;
                const textClass = INTENSITY_TEXT[day.intensity] || INTENSITY_TEXT.none;

                return (
                  <div
                    key={i}
                    className={`
                      aspect-square rounded-sm flex items-center justify-center text-xs
                      cursor-default transition-all hover:ring-2 hover:ring-[var(--gr-blue-400)] hover:ring-offset-1
                      ${intensityClass}
                      ${day.count > 0 ? 'font-medium' : ''}
                    `}
                    title={`${format(day.date, 'MMM d, yyyy')}: ${day.count} deadline${day.count !== 1 ? 's' : ''}`}
                  >
                    <span className={textClass}>
                      {format(day.date, 'd')}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-6 pt-4 border-t border-[var(--gr-border-subtle)]">
        <span className="text-xs text-[var(--gr-text-tertiary)]">Fewer</span>
        <div className="flex gap-1">
          {Object.entries(INTENSITY_COLORS).map(([key, colorClass]) => (
            <div
              key={key}
              className={`w-4 h-4 rounded-sm ${colorClass}`}
              title={key.charAt(0).toUpperCase() + key.slice(1)}
            />
          ))}
        </div>
        <span className="text-xs text-[var(--gr-text-tertiary)]">More</span>
      </div>
    </div>
  );
}

export default DeadlineHeatmap;
