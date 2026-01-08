import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  SparklesIcon,
  ChartBarIcon,
  CalendarDaysIcon,
  ArrowPathIcon,
  ExclamationCircleIcon,
  LightBulbIcon,
} from '@heroicons/react/24/outline';
import { forecastApi } from '../services/api';
import { ForecastCard } from '../components/forecast/ForecastCard';
import { SeasonalChart } from '../components/forecast/SeasonalChart';
import { ForecastTimeline } from '../components/forecast/ForecastTimeline';

type ViewMode = 'cards' | 'timeline';

export function Forecast() {
  const [viewMode, setViewMode] = useState<ViewMode>('cards');
  const [lookaheadMonths, setLookaheadMonths] = useState(6);

  // Fetch upcoming forecasts
  const {
    data: upcomingData,
    isLoading: isLoadingUpcoming,
    error: upcomingError,
    refetch: refetchUpcoming,
  } = useQuery({
    queryKey: ['forecast-upcoming', lookaheadMonths],
    queryFn: () => forecastApi.getUpcoming({ lookahead_months: lookaheadMonths, limit: 20 }),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  // Fetch seasonal trends
  const {
    data: seasonalData,
    isLoading: isLoadingSeasonal,
    error: seasonalError,
  } = useQuery({
    queryKey: ['forecast-seasonal'],
    queryFn: () => forecastApi.getSeasonal(),
    staleTime: 30 * 60 * 1000, // 30 minutes
  });

  // Fetch recommendations (requires auth)
  const {
    data: recommendationsData,
    isLoading: isLoadingRecommendations,
    error: recommendationsError,
  } = useQuery({
    queryKey: ['forecast-recommendations'],
    queryFn: () => forecastApi.getRecommendations({ limit: 6 }),
    staleTime: 10 * 60 * 1000, // 10 minutes
    retry: false, // Don't retry on auth errors
  });

  const isLoading = isLoadingUpcoming || isLoadingSeasonal;
  const hasError = upcomingError || seasonalError;

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-[var(--gr-blue-500)]/10 rounded-lg">
              <LightBulbIcon className="h-6 w-6 text-[var(--gr-blue-600)]" />
            </div>
            <h1 className="text-2xl font-display font-semibold text-[var(--gr-text-primary)]">
              Funding Forecast
            </h1>
          </div>
          <p className="text-[var(--gr-text-secondary)]">
            Predict upcoming grant opportunities based on historical patterns and your research
            profile.
          </p>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            {/* View mode toggle */}
            <div className="flex bg-[var(--gr-bg-secondary)] rounded-lg p-1">
              <button
                onClick={() => setViewMode('cards')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                  viewMode === 'cards'
                    ? 'bg-[var(--gr-bg-elevated)] text-[var(--gr-text-primary)] shadow-sm'
                    : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)]'
                }`}
              >
                <ChartBarIcon className="h-4 w-4" />
                Cards
              </button>
              <button
                onClick={() => setViewMode('timeline')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                  viewMode === 'timeline'
                    ? 'bg-[var(--gr-bg-elevated)] text-[var(--gr-text-primary)] shadow-sm'
                    : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)]'
                }`}
              >
                <CalendarDaysIcon className="h-4 w-4" />
                Timeline
              </button>
            </div>

            {/* Lookahead selector */}
            <select
              value={lookaheadMonths}
              onChange={(e) => setLookaheadMonths(Number(e.target.value))}
              className="input py-1.5 px-3 text-sm w-auto"
            >
              <option value={3}>Next 3 months</option>
              <option value={6}>Next 6 months</option>
              <option value={9}>Next 9 months</option>
              <option value={12}>Next 12 months</option>
            </select>
          </div>

          <button
            onClick={() => refetchUpcoming()}
            className="btn-secondary py-1.5 px-3 text-sm"
            disabled={isLoading}
          >
            <ArrowPathIcon className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Error state */}
        {hasError && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
            <ExclamationCircleIcon className="h-5 w-5 text-red-500 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-red-800">Unable to load forecast data</p>
              <p className="text-xs text-red-600">Please try again later.</p>
            </div>
          </div>
        )}

        {/* Main content grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column - Forecasts */}
          <div className="lg:col-span-2 space-y-6">
            {/* Personalized Recommendations */}
            {recommendationsData && recommendationsData.recommendations.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <SparklesIcon className="h-5 w-5 text-[var(--gr-yellow-500)]" />
                  <h2 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
                    Recommended for You
                  </h2>
                  {!recommendationsData.profile_complete && (
                    <span className="text-xs text-[var(--gr-text-tertiary)] bg-[var(--gr-yellow-100)] px-2 py-0.5 rounded">
                      Complete profile for better matches
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {recommendationsData.recommendations.slice(0, 4).map((rec, index) => (
                    <ForecastCard
                      key={`rec-${rec.grant.funder_name}-${index}`}
                      forecast={rec.grant}
                      recommendation={rec}
                      index={index}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Loading state for recommendations */}
            {isLoadingRecommendations && !recommendationsError && (
              <div className="space-y-4">
                <div className="flex items-center gap-2 mb-4">
                  <div className="skeleton h-5 w-5 rounded" />
                  <div className="skeleton h-6 w-48" />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {[...Array(4)].map((_, i) => (
                    <div key={i} className="card p-5">
                      <div className="skeleton h-4 w-24 mb-3" />
                      <div className="skeleton h-5 w-full mb-2" />
                      <div className="skeleton h-4 w-32 mb-3" />
                      <div className="skeleton h-4 w-24" />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* All Forecasts */}
            <div>
              <h2 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-4">
                All Upcoming Opportunities
              </h2>

              {isLoadingUpcoming ? (
                viewMode === 'cards' ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[...Array(6)].map((_, i) => (
                      <div key={i} className="card p-5">
                        <div className="skeleton h-4 w-24 mb-3" />
                        <div className="skeleton h-5 w-full mb-2" />
                        <div className="skeleton h-4 w-32 mb-3" />
                        <div className="skeleton h-4 w-24" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="card p-6">
                    <div className="space-y-4">
                      {[...Array(4)].map((_, i) => (
                        <div key={i} className="flex items-start gap-4">
                          <div className="skeleton h-8 w-8 rounded-full" />
                          <div className="flex-1 space-y-2">
                            <div className="skeleton h-4 w-32" />
                            <div className="skeleton h-16 w-full rounded-lg" />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              ) : upcomingData && upcomingData.forecasts.length > 0 ? (
                viewMode === 'cards' ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {upcomingData.forecasts.map((forecast, index) => (
                      <ForecastCard
                        key={`${forecast.funder_name}-${index}`}
                        forecast={forecast}
                        index={index}
                      />
                    ))}
                  </div>
                ) : (
                  <ForecastTimeline forecasts={upcomingData.forecasts} />
                )
              ) : (
                <div className="card p-8 text-center">
                  <CalendarDaysIcon className="h-12 w-12 text-[var(--gr-text-muted)] mx-auto mb-4" />
                  <h3 className="text-lg font-display font-medium text-[var(--gr-text-secondary)] mb-2">
                    No Forecasts Available
                  </h3>
                  <p className="text-sm text-[var(--gr-text-tertiary)]">
                    We need more historical data to generate accurate forecasts. Check back soon!
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Right column - Seasonal Trends */}
          <div className="space-y-6">
            {isLoadingSeasonal ? (
              <div className="card p-6">
                <div className="skeleton h-5 w-32 mb-6" />
                <div className="skeleton h-64 w-full rounded-lg" />
              </div>
            ) : seasonalData ? (
              <SeasonalChart
                trends={seasonalData.trends}
                peakMonths={seasonalData.peak_months}
                yearTotal={seasonalData.year_total}
              />
            ) : null}

            {/* Info card */}
            <div className="card p-5 bg-[var(--gr-blue-50)] border-[var(--gr-blue-100)]">
              <div className="flex items-start gap-3">
                <LightBulbIcon className="h-5 w-5 text-[var(--gr-blue-600)] flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-medium text-[var(--gr-blue-800)] mb-1">
                    How Forecasts Work
                  </h3>
                  <p className="text-sm text-[var(--gr-blue-700)]">
                    We analyze historical grant patterns to predict when funders typically release
                    opportunities. Confidence scores indicate how reliable each prediction is based
                    on past data consistency.
                  </p>
                </div>
              </div>
            </div>

            {/* Stats summary */}
            {upcomingData && (
              <div className="card p-5">
                <h3 className="font-display font-medium text-[var(--gr-text-primary)] mb-4">
                  Forecast Summary
                </h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-[var(--gr-text-secondary)]">
                      Total Predictions
                    </span>
                    <span className="font-medium text-[var(--gr-text-primary)]">
                      {upcomingData.total}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-[var(--gr-text-secondary)]">Lookahead Period</span>
                    <span className="font-medium text-[var(--gr-text-primary)]">
                      {upcomingData.lookahead_months} months
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-[var(--gr-text-secondary)]">High Confidence</span>
                    <span className="font-medium text-[var(--gr-green-600)]">
                      {upcomingData.forecasts.filter((f) => f.confidence >= 0.7).length}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-[var(--gr-text-secondary)]">Next 30 Days</span>
                    <span className="font-medium text-[var(--gr-blue-600)]">
                      {
                        upcomingData.forecasts.filter((f) => {
                          const date = new Date(f.predicted_open_date);
                          const now = new Date();
                          const diffDays = Math.ceil(
                            (date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
                          );
                          return diffDays <= 30 && diffDays >= 0;
                        }).length
                      }
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Forecast;
