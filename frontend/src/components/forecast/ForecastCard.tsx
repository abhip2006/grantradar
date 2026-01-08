import {
  CalendarIcon,
  CurrencyDollarIcon,
  BuildingLibraryIcon,
  SparklesIcon,
  ArrowTrendingUpIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import type { ForecastGrant, RecommendationGrant } from '../../types';

interface ForecastCardProps {
  forecast: ForecastGrant;
  recommendation?: RecommendationGrant;
  index?: number;
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const getConfidenceStyle = () => {
    if (confidence >= 0.7)
      return 'bg-[var(--gr-green-500)]/10 text-[var(--gr-green-600)] border-[var(--gr-green-500)]/20';
    if (confidence >= 0.5)
      return 'bg-[var(--gr-blue-500)]/10 text-[var(--gr-blue-600)] border-[var(--gr-blue-500)]/20';
    return 'bg-[var(--gr-gray-200)] text-[var(--gr-gray-600)] border-[var(--gr-gray-300)]';
  };

  const getConfidenceLabel = () => {
    if (confidence >= 0.7) return 'High Confidence';
    if (confidence >= 0.5) return 'Medium Confidence';
    return 'Low Confidence';
  };

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${getConfidenceStyle()}`}
    >
      <ArrowTrendingUpIcon className="h-3 w-3" />
      {getConfidenceLabel()} ({Math.round(confidence * 100)}%)
    </span>
  );
}

function MatchScoreBadge({ score }: { score: number }) {
  const getScoreStyle = () => {
    if (score >= 0.7)
      return 'bg-[var(--gr-yellow-100)] text-[var(--gr-yellow-700)] border-[var(--gr-yellow-200)]';
    if (score >= 0.5)
      return 'bg-[var(--gr-blue-50)] text-[var(--gr-blue-700)] border-[var(--gr-blue-100)]';
    return 'bg-[var(--gr-gray-100)] text-[var(--gr-gray-600)] border-[var(--gr-gray-200)]';
  };

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${getScoreStyle()}`}
    >
      <SparklesIcon className="h-3 w-3" />
      {Math.round(score * 100)}% Match
    </span>
  );
}

function RecurrenceBadge({ pattern }: { pattern: string }) {
  const getPatternLabel = () => {
    switch (pattern) {
      case 'annual':
        return 'Annual';
      case 'biannual':
        return 'Twice Yearly';
      case 'quarterly':
        return 'Quarterly';
      case 'monthly':
        return 'Monthly';
      default:
        return 'Variable';
    }
  };

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs bg-[var(--gr-gray-100)] text-[var(--gr-gray-600)] border border-[var(--gr-gray-200)]">
      <ClockIcon className="h-3 w-3" />
      {getPatternLabel()}
    </span>
  );
}

export function ForecastCard({ forecast, recommendation, index = 0 }: ForecastCardProps) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      year: 'numeric',
    });
  };

  const getMonthName = (month: number) => {
    const months = [
      'January',
      'February',
      'March',
      'April',
      'May',
      'June',
      'July',
      'August',
      'September',
      'October',
      'November',
      'December',
    ];
    return months[month - 1] || 'Unknown';
  };

  const daysUntil = () => {
    const predicted = new Date(forecast.predicted_open_date);
    const today = new Date();
    const diffTime = predicted.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const days = daysUntil();

  return (
    <div
      className="card p-5 hover:shadow-[var(--gr-shadow-lg)] transition-all animate-fade-in-up"
      style={{ animationDelay: `${index * 0.05}s` }}
    >
      {/* Header with badges */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <ConfidenceBadge confidence={forecast.confidence} />
          {recommendation && <MatchScoreBadge score={recommendation.match_score} />}
        </div>
        <RecurrenceBadge pattern={forecast.recurrence_pattern} />
      </div>

      {/* Title */}
      <h3 className="text-base font-display font-medium text-[var(--gr-text-primary)] line-clamp-2 mb-2">
        {forecast.title || `${forecast.funder_name} Grant Opportunity`}
      </h3>

      {/* Funder */}
      <div className="flex items-center gap-2 text-sm text-[var(--gr-text-secondary)] mb-3">
        <BuildingLibraryIcon className="h-4 w-4 flex-shrink-0 text-[var(--gr-text-tertiary)]" />
        <span className="truncate">{forecast.funder_name}</span>
        {forecast.source && (
          <span className="badge badge-blue text-[10px] py-0">{forecast.source.toUpperCase()}</span>
        )}
      </div>

      {/* Meta info */}
      <div className="flex flex-wrap items-center gap-3 text-sm mb-3">
        {(forecast.historical_amount_min || forecast.historical_amount_max) && (
          <div className="flex items-center gap-1.5 text-[var(--gr-text-secondary)]">
            <CurrencyDollarIcon className="h-4 w-4 text-[var(--gr-yellow-500)]" />
            <span>
              {forecast.historical_amount_min && forecast.historical_amount_max
                ? `${formatCurrency(forecast.historical_amount_min)} - ${formatCurrency(forecast.historical_amount_max)}`
                : forecast.historical_amount_max
                  ? `Up to ${formatCurrency(forecast.historical_amount_max)}`
                  : formatCurrency(forecast.historical_amount_min!)}
            </span>
          </div>
        )}
        <div className="flex items-center gap-1.5 text-[var(--gr-text-secondary)]">
          <CalendarIcon className="h-4 w-4 text-[var(--gr-blue-500)]" />
          <span>Opens {formatDate(forecast.predicted_open_date)}</span>
        </div>
      </div>

      {/* Days until opening */}
      <div
        className={`text-xs font-medium mb-3 ${
          days <= 30
            ? 'text-[var(--gr-green-600)]'
            : days <= 90
              ? 'text-[var(--gr-blue-600)]'
              : 'text-[var(--gr-gray-500)]'
        }`}
      >
        {days <= 0 ? 'Opening soon' : days === 1 ? 'Opens tomorrow' : `Opens in ${days} days`}
      </div>

      {/* Historical deadline info */}
      {forecast.historical_deadline_month && (
        <p className="text-xs text-[var(--gr-text-tertiary)] mb-3">
          Based on {forecast.funder_name} releasing similar grants in{' '}
          {getMonthName(forecast.historical_deadline_month)} historically
        </p>
      )}

      {/* Focus areas */}
      {forecast.focus_areas && forecast.focus_areas.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {forecast.focus_areas.slice(0, 4).map((area, i) => (
            <span
              key={i}
              className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-[var(--gr-blue-50)] text-[var(--gr-blue-700)] border border-[var(--gr-blue-100)]"
            >
              {area}
            </span>
          ))}
          {forecast.focus_areas.length > 4 && (
            <span className="text-xs text-[var(--gr-text-tertiary)]">
              +{forecast.focus_areas.length - 4} more
            </span>
          )}
        </div>
      )}

      {/* Recommendation reasons */}
      {recommendation && recommendation.match_reasons.length > 0 && (
        <div className="pt-3 border-t border-[var(--gr-border-subtle)]">
          <p className="text-xs text-[var(--gr-text-tertiary)] mb-2">Why we recommend this:</p>
          <ul className="space-y-1">
            {recommendation.match_reasons.slice(0, 3).map((reason, i) => (
              <li key={i} className="text-xs text-[var(--gr-text-secondary)] flex items-start gap-2">
                <SparklesIcon className="h-3 w-3 text-[var(--gr-yellow-500)] flex-shrink-0 mt-0.5" />
                {reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default ForecastCard;
