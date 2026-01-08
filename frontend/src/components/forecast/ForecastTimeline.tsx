import { useMemo } from 'react';
import {
  CalendarIcon,
  CurrencyDollarIcon,
  BuildingLibraryIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import type { ForecastGrant } from '../../types';

interface ForecastTimelineProps {
  forecasts: ForecastGrant[];
}

interface MonthGroup {
  month: string;
  year: number;
  monthNum: number;
  forecasts: ForecastGrant[];
  isCurrentMonth: boolean;
}

export function ForecastTimeline({ forecasts }: ForecastTimelineProps) {
  const groupedByMonth = useMemo(() => {
    const groups: Record<string, MonthGroup> = {};
    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();

    forecasts.forEach((forecast) => {
      const date = new Date(forecast.predicted_open_date);
      const monthKey = `${date.getFullYear()}-${date.getMonth()}`;
      const monthName = date.toLocaleDateString('en-US', { month: 'long' });

      if (!groups[monthKey]) {
        groups[monthKey] = {
          month: monthName,
          year: date.getFullYear(),
          monthNum: date.getMonth(),
          forecasts: [],
          isCurrentMonth: date.getMonth() === currentMonth && date.getFullYear() === currentYear,
        };
      }
      groups[monthKey].forecasts.push(forecast);
    });

    // Sort by date and return as array
    return Object.values(groups).sort((a, b) => {
      if (a.year !== b.year) return a.year - b.year;
      return a.monthNum - b.monthNum;
    });
  }, [forecasts]);

  const formatCurrency = (amount: number) => {
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(1)}M`;
    }
    if (amount >= 1000) {
      return `$${(amount / 1000).toFixed(0)}K`;
    }
    return `$${amount}`;
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.7) return 'bg-[var(--gr-green-500)]';
    if (confidence >= 0.5) return 'bg-[var(--gr-blue-500)]';
    return 'bg-[var(--gr-gray-400)]';
  };

  if (forecasts.length === 0) {
    return (
      <div className="card p-8 text-center">
        <CalendarIcon className="h-12 w-12 text-[var(--gr-text-muted)] mx-auto mb-4" />
        <h3 className="text-lg font-display font-medium text-[var(--gr-text-secondary)] mb-2">
          No Upcoming Forecasts
        </h3>
        <p className="text-sm text-[var(--gr-text-tertiary)]">
          Check back later for predicted grant opportunities.
        </p>
      </div>
    );
  }

  return (
    <div className="card p-6">
      <div className="flex items-center gap-2 mb-6">
        <CalendarIcon className="h-5 w-5 text-[var(--gr-blue-600)]" />
        <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
          Forecast Timeline
        </h3>
        <span className="text-sm text-[var(--gr-text-tertiary)]">({forecasts.length} predicted)</span>
      </div>

      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-[var(--gr-border-default)]" />

        <div className="space-y-6">
          {groupedByMonth.map((group, groupIndex) => (
            <div key={`${group.year}-${group.monthNum}`} className="relative">
              {/* Month header */}
              <div className="flex items-center gap-3 mb-4">
                <div
                  className={`relative z-10 w-8 h-8 rounded-full flex items-center justify-center ${
                    group.isCurrentMonth
                      ? 'bg-[var(--gr-green-500)] text-white'
                      : 'bg-[var(--gr-bg-elevated)] border-2 border-[var(--gr-blue-500)] text-[var(--gr-blue-600)]'
                  }`}
                >
                  <span className="text-xs font-semibold">{group.month.substring(0, 3)}</span>
                </div>
                <div>
                  <h4 className="font-display font-medium text-[var(--gr-text-primary)]">
                    {group.month} {group.year}
                  </h4>
                  <p className="text-xs text-[var(--gr-text-tertiary)]">
                    {group.forecasts.length} grant{group.forecasts.length !== 1 ? 's' : ''} predicted
                  </p>
                </div>
              </div>

              {/* Forecasts in this month */}
              <div className="ml-11 space-y-3">
                {group.forecasts.map((forecast, index) => (
                  <div
                    key={`${forecast.funder_name}-${index}`}
                    className="group relative bg-[var(--gr-bg-secondary)] rounded-lg p-4 hover:bg-[var(--gr-bg-hover)] transition-colors cursor-pointer"
                    style={{
                      animationDelay: `${(groupIndex * group.forecasts.length + index) * 0.03}s`,
                    }}
                  >
                    {/* Confidence indicator */}
                    <div
                      className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-lg ${getConfidenceColor(forecast.confidence)}`}
                    />

                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        {/* Title */}
                        <h5 className="text-sm font-medium text-[var(--gr-text-primary)] line-clamp-1 mb-1 group-hover:text-[var(--gr-blue-600)] transition-colors">
                          {forecast.title || `${forecast.funder_name} Opportunity`}
                        </h5>

                        {/* Funder */}
                        <div className="flex items-center gap-1.5 text-xs text-[var(--gr-text-secondary)] mb-2">
                          <BuildingLibraryIcon className="h-3.5 w-3.5 text-[var(--gr-text-tertiary)]" />
                          <span className="truncate">{forecast.funder_name}</span>
                        </div>

                        {/* Meta row */}
                        <div className="flex items-center gap-4 text-xs">
                          {(forecast.historical_amount_min || forecast.historical_amount_max) && (
                            <div className="flex items-center gap-1 text-[var(--gr-text-tertiary)]">
                              <CurrencyDollarIcon className="h-3.5 w-3.5" />
                              <span>
                                {forecast.historical_amount_max
                                  ? `Up to ${formatCurrency(forecast.historical_amount_max)}`
                                  : formatCurrency(forecast.historical_amount_min!)}
                              </span>
                            </div>
                          )}
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                              forecast.confidence >= 0.7
                                ? 'bg-[var(--gr-green-500)]/10 text-[var(--gr-green-600)]'
                                : forecast.confidence >= 0.5
                                  ? 'bg-[var(--gr-blue-500)]/10 text-[var(--gr-blue-600)]'
                                  : 'bg-[var(--gr-gray-200)] text-[var(--gr-gray-600)]'
                            }`}
                          >
                            {Math.round(forecast.confidence * 100)}% confident
                          </span>
                        </div>

                        {/* Focus areas */}
                        {forecast.focus_areas && forecast.focus_areas.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {forecast.focus_areas.slice(0, 2).map((area, i) => (
                              <span
                                key={i}
                                className="px-1.5 py-0.5 text-[10px] bg-[var(--gr-blue-50)] text-[var(--gr-blue-700)] rounded"
                              >
                                {area}
                              </span>
                            ))}
                            {forecast.focus_areas.length > 2 && (
                              <span className="text-[10px] text-[var(--gr-text-tertiary)]">
                                +{forecast.focus_areas.length - 2}
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Arrow */}
                      <ChevronRightIcon className="h-5 w-5 text-[var(--gr-text-muted)] group-hover:text-[var(--gr-blue-500)] transition-colors flex-shrink-0" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default ForecastTimeline;
