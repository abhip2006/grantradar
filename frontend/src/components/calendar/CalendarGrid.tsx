import { useMemo } from 'react';
import type { CalendarDay, CalendarEvent } from '../../types';
import { CalendarEventChip } from './CalendarEvent';

interface CalendarGridProps {
  year: number;
  month: number;
  days: CalendarDay[];
  onDateClick?: (date: Date) => void;
}

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate();
}

function getFirstDayOfMonth(year: number, month: number): number {
  return new Date(year, month - 1, 1).getDay();
}

function isToday(year: number, month: number, day: number): boolean {
  const today = new Date();
  return (
    today.getFullYear() === year &&
    today.getMonth() + 1 === month &&
    today.getDate() === day
  );
}

export function CalendarGrid({ year, month, days, onDateClick }: CalendarGridProps) {
  // Build a map of day number to events for quick lookup
  const eventsByDay = useMemo(() => {
    const map = new Map<number, CalendarEvent[]>();
    for (const day of days) {
      const dateObj = new Date(day.date);
      map.set(dateObj.getDate(), day.events);
    }
    return map;
  }, [days]);

  // Calculate grid
  const daysInMonth = getDaysInMonth(year, month);
  const firstDayOfWeek = getFirstDayOfMonth(year, month);

  // Build the grid cells
  const gridCells = useMemo(() => {
    const cells: Array<{ day: number | null; events: CalendarEvent[] }> = [];

    // Add empty cells for days before the first of the month
    for (let i = 0; i < firstDayOfWeek; i++) {
      cells.push({ day: null, events: [] });
    }

    // Add cells for each day of the month
    for (let day = 1; day <= daysInMonth; day++) {
      cells.push({
        day,
        events: eventsByDay.get(day) || [],
      });
    }

    // Fill remaining cells to complete the last row
    const remainingCells = 7 - (cells.length % 7);
    if (remainingCells < 7) {
      for (let i = 0; i < remainingCells; i++) {
        cells.push({ day: null, events: [] });
      }
    }

    return cells;
  }, [daysInMonth, firstDayOfWeek, eventsByDay]);

  const handleDateClick = (day: number) => {
    if (onDateClick) {
      onDateClick(new Date(year, month - 1, day));
    }
  };

  return (
    <div className="bg-white rounded-xl border border-[var(--gr-border-default)] overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-[var(--gr-border-subtle)] bg-[var(--gr-bg-secondary)]">
        <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
          {MONTH_NAMES[month - 1]} {year}
        </h3>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 border-b border-[var(--gr-border-subtle)]">
        {WEEKDAYS.map((day) => (
          <div
            key={day}
            className="p-2 text-center text-xs font-medium text-[var(--gr-text-tertiary)] uppercase tracking-wider"
          >
            {day}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7">
        {gridCells.map((cell, index) => {
          const isTodayCell = cell.day !== null && isToday(year, month, cell.day);
          const hasEvents = cell.events.length > 0;

          return (
            <div
              key={index}
              className={`min-h-[100px] p-2 border-b border-r border-[var(--gr-border-subtle)] last:border-r-0 ${
                cell.day === null
                  ? 'bg-[var(--gr-gray-50)]'
                  : hasEvents
                    ? 'bg-white hover:bg-[var(--gr-bg-hover)] cursor-pointer'
                    : 'bg-white'
              }`}
              onClick={() => cell.day !== null && handleDateClick(cell.day)}
            >
              {cell.day !== null && (
                <>
                  {/* Day number */}
                  <div className="flex items-center justify-between mb-1">
                    <span
                      className={`inline-flex items-center justify-center w-7 h-7 text-sm rounded-full ${
                        isTodayCell
                          ? 'bg-[var(--gr-blue-600)] text-white font-semibold'
                          : 'text-[var(--gr-text-primary)]'
                      }`}
                    >
                      {cell.day}
                    </span>
                    {hasEvents && (
                      <span className="text-xs font-medium text-[var(--gr-text-tertiary)]">
                        {cell.events.length}
                      </span>
                    )}
                  </div>

                  {/* Events */}
                  <div className="space-y-1">
                    {cell.events.slice(0, 2).map((event) => (
                      <CalendarEventChip
                        key={event.grant_id}
                        event={event}
                        compact
                      />
                    ))}
                    {cell.events.length > 2 && (
                      <div className="text-xs text-[var(--gr-text-tertiary)] text-center py-0.5">
                        +{cell.events.length - 2} more
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default CalendarGrid;
