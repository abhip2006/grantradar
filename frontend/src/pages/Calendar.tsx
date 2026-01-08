import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  CalendarDaysIcon,
  ListBulletIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  CheckCircleIcon,
  ArrowDownTrayIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';
import { calendarApi } from '../services/api';
import { Navbar } from '../components/Navbar';
import { CalendarGrid, DeadlineList } from '../components/calendar';

type ViewMode = 'calendar' | 'list';

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

export function Calendar() {
  const [viewMode, setViewMode] = useState<ViewMode>('calendar');
  const [currentDate, setCurrentDate] = useState(() => new Date());
  const [includeSaved, setIncludeSaved] = useState(true);
  const [includePipeline, setIncludePipeline] = useState(true);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth() + 1; // JavaScript months are 0-indexed

  // Fetch month deadlines for calendar view
  const { data: monthData, isLoading: monthLoading } = useQuery({
    queryKey: ['calendar-month', year, month, includeSaved, includePipeline],
    queryFn: () => calendarApi.getMonthDeadlines(year, month, {
      include_saved: includeSaved,
      include_pipeline: includePipeline,
    }),
    enabled: viewMode === 'calendar',
  });

  // Fetch upcoming deadlines for list view
  const { data: upcomingData, isLoading: upcomingLoading } = useQuery({
    queryKey: ['calendar-upcoming', includeSaved, includePipeline],
    queryFn: () => calendarApi.getUpcomingDeadlines({
      days: 60,
      include_saved: includeSaved,
      include_pipeline: includePipeline,
    }),
    enabled: viewMode === 'list',
  });

  // Navigation handlers
  const goToPreviousMonth = () => {
    setCurrentDate(new Date(year, month - 2, 1));
  };

  const goToNextMonth = () => {
    setCurrentDate(new Date(year, month, 1));
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  // Export handler
  const handleExport = async () => {
    try {
      const blob = await calendarApi.exportCalendar(true, 365);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'grantradar-deadlines.ics';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to export calendar:', error);
    }
  };

  // Compute summary stats
  const summaryStats = useMemo(() => {
    if (viewMode === 'list' && upcomingData) {
      return {
        total: upcomingData.total,
        critical: upcomingData.critical_count,
        warning: upcomingData.warning_count,
        normal: upcomingData.total - upcomingData.critical_count - upcomingData.warning_count,
      };
    }
    if (viewMode === 'calendar' && monthData) {
      const events = monthData.days.flatMap(d => d.events);
      return {
        total: events.length,
        critical: events.filter(e => e.urgency === 'critical').length,
        warning: events.filter(e => e.urgency === 'warning').length,
        normal: events.filter(e => e.urgency === 'normal').length,
      };
    }
    return { total: 0, critical: 0, warning: 0, normal: 0 };
  }, [viewMode, monthData, upcomingData]);

  const isLoading = viewMode === 'calendar' ? monthLoading : upcomingLoading;

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      <Navbar />

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8 animate-fade-in-up">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-display font-medium text-[var(--gr-text-primary)]">
                Deadline Calendar
              </h1>
              <p className="mt-2 text-[var(--gr-text-secondary)]">
                Track all your grant deadlines in one place
              </p>
            </div>

            {/* Export button */}
            <button
              onClick={handleExport}
              className="btn-secondary flex items-center gap-2"
            >
              <ArrowDownTrayIcon className="w-5 h-5" />
              Export to Calendar
            </button>
          </div>
        </div>

        {/* Stats Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8 animate-fade-in-up stagger-1">
          <div className="stat-card">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[var(--gr-blue-50)] flex items-center justify-center">
                <CalendarDaysIcon className="w-5 h-5 text-[var(--gr-blue-600)]" />
              </div>
              <div>
                <div className="text-2xl font-display font-semibold text-[var(--gr-text-primary)]">
                  {summaryStats.total}
                </div>
                <div className="text-sm text-[var(--gr-text-tertiary)]">Total Deadlines</div>
              </div>
            </div>
          </div>

          <div className="stat-card">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center">
                <ExclamationTriangleIcon className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <div className="text-2xl font-display font-semibold text-red-600">
                  {summaryStats.critical}
                </div>
                <div className="text-sm text-[var(--gr-text-tertiary)]">Critical (&lt;7 days)</div>
              </div>
            </div>
          </div>

          <div className="stat-card">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-50 flex items-center justify-center">
                <ClockIcon className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <div className="text-2xl font-display font-semibold text-amber-600">
                  {summaryStats.warning}
                </div>
                <div className="text-sm text-[var(--gr-text-tertiary)]">Warning (&lt;14 days)</div>
              </div>
            </div>
          </div>

          <div className="stat-card">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-green-50 flex items-center justify-center">
                <CheckCircleIcon className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <div className="text-2xl font-display font-semibold text-green-600">
                  {summaryStats.normal}
                </div>
                <div className="text-sm text-[var(--gr-text-tertiary)]">On Track</div>
              </div>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="card p-4 mb-8 animate-fade-in-up stagger-2">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            {/* View Toggle */}
            <div className="flex items-center gap-2">
              <div className="flex p-1 bg-[var(--gr-bg-secondary)] rounded-lg">
                <button
                  onClick={() => setViewMode('calendar')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    viewMode === 'calendar'
                      ? 'bg-white text-[var(--gr-blue-600)] shadow-sm'
                      : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)]'
                  }`}
                >
                  <CalendarDaysIcon className="w-4 h-4" />
                  Calendar
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    viewMode === 'list'
                      ? 'bg-white text-[var(--gr-blue-600)] shadow-sm'
                      : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)]'
                  }`}
                >
                  <ListBulletIcon className="w-4 h-4" />
                  List
                </button>
              </div>
            </div>

            {/* Month Navigation (only for calendar view) */}
            {viewMode === 'calendar' && (
              <div className="flex items-center gap-4">
                <button
                  onClick={goToPreviousMonth}
                  className="p-2 rounded-lg hover:bg-[var(--gr-bg-hover)] transition-colors"
                  aria-label="Previous month"
                >
                  <ChevronLeftIcon className="w-5 h-5 text-[var(--gr-text-secondary)]" />
                </button>

                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-medium text-[var(--gr-text-primary)] min-w-[180px] text-center">
                    {MONTH_NAMES[month - 1]} {year}
                  </h2>
                  <button
                    onClick={goToToday}
                    className="text-sm text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-700)] font-medium"
                  >
                    Today
                  </button>
                </div>

                <button
                  onClick={goToNextMonth}
                  className="p-2 rounded-lg hover:bg-[var(--gr-bg-hover)] transition-colors"
                  aria-label="Next month"
                >
                  <ChevronRightIcon className="w-5 h-5 text-[var(--gr-text-secondary)]" />
                </button>
              </div>
            )}

            {/* Filters */}
            <div className="flex items-center gap-2">
              <FunnelIcon className="w-4 h-4 text-[var(--gr-text-tertiary)]" />
              <span className="text-sm text-[var(--gr-text-tertiary)] mr-2">Show:</span>
              <button
                onClick={() => setIncludeSaved(!includeSaved)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  includeSaved
                    ? 'bg-[var(--gr-blue-50)] text-[var(--gr-blue-700)] border border-[var(--gr-blue-200)]'
                    : 'bg-[var(--gr-bg-secondary)] text-[var(--gr-text-tertiary)] border border-transparent'
                }`}
              >
                Saved
              </button>
              <button
                onClick={() => setIncludePipeline(!includePipeline)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  includePipeline
                    ? 'bg-purple-50 text-purple-700 border border-purple-200'
                    : 'bg-[var(--gr-bg-secondary)] text-[var(--gr-text-tertiary)] border border-transparent'
                }`}
              >
                Pipeline
              </button>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="animate-fade-in-up stagger-3">
          {viewMode === 'calendar' ? (
            <CalendarGrid
              year={year}
              month={month}
              days={monthData?.days || []}
            />
          ) : (
            <DeadlineList
              deadlines={upcomingData?.deadlines || []}
              isLoading={isLoading}
              emptyMessage="No upcoming deadlines. Save some grants or add them to your pipeline to see them here."
            />
          )}
        </div>

        {/* Legend */}
        <div className="mt-8 p-4 bg-[var(--gr-bg-secondary)] rounded-xl border border-[var(--gr-border-subtle)]">
          <h3 className="text-sm font-medium text-[var(--gr-text-secondary)] mb-3">Legend</h3>
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <span className="text-[var(--gr-text-secondary)]">Critical (&lt;7 days)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-amber-500" />
              <span className="text-[var(--gr-text-secondary)]">Warning (&lt;14 days)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span className="text-[var(--gr-text-secondary)]">On Track (14+ days)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[var(--gr-blue-500)]" />
              <span className="text-[var(--gr-text-secondary)]">Saved Match</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-purple-500" />
              <span className="text-[var(--gr-text-secondary)]">In Pipeline</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default Calendar;
