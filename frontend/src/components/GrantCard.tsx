import { Link, useNavigate } from 'react-router-dom';
import {
  CalendarIcon,
  CurrencyDollarIcon,
  BuildingLibraryIcon,
  BookmarkIcon,
  XMarkIcon,
  SparklesIcon,
  ScaleIcon,
} from '@heroicons/react/24/outline';
import { BookmarkIcon as BookmarkSolidIcon, CheckIcon } from '@heroicons/react/24/solid';
import { MatchScoreBadge } from './MatchScore';
import { CompetitionBadge } from './CompetitionBadge';
import type { GrantMatch, CompetitionLevel } from '../types';

interface GrantCardProps {
  match: GrantMatch;
  onSave?: (matchId: string) => void;
  onDismiss?: (matchId: string) => void;
  onFindSimilar?: (grantId: string) => void;
  onToggleCompare?: (grantId: string) => void;
  showFindSimilar?: boolean;
  isSelectedForCompare?: boolean;
  compareDisabled?: boolean;
  delay?: number;
  // Competition data - optional, show when available
  competitionLevel?: CompetitionLevel | null;
  competitionScore?: number;
}

export function GrantCard({
  match,
  onSave,
  onDismiss,
  onFindSimilar,
  onToggleCompare,
  showFindSimilar = false,
  isSelectedForCompare = false,
  compareDisabled = false,
  delay = 0,
  competitionLevel,
  competitionScore,
}: GrantCardProps) {
  const { grant, score, status } = match;
  const isSaved = status === 'saved';
  const navigate = useNavigate();

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
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getSourceBadgeColor = (source: string) => {
    switch (source) {
      case 'federal':
        return 'badge-blue';
      case 'foundation':
        return 'badge-emerald';
      case 'state':
        return 'badge-yellow';
      case 'corporate':
        return 'badge-slate';
      default:
        return 'badge-slate';
    }
  };

  const getDaysUntilDeadline = () => {
    if (!grant.deadline) return null;
    const deadline = new Date(grant.deadline);
    const today = new Date();
    const diffTime = deadline.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const daysUntilDeadline = getDaysUntilDeadline();
  const isUrgent = daysUntilDeadline !== null && daysUntilDeadline <= 7 && daysUntilDeadline > 0;

  return (
    <div
      className={`grant-card ${isSaved ? 'grant-card-saved' : ''} ${isSelectedForCompare ? 'grant-card-compare' : ''} animate-fade-in-up`}
      style={{ animationDelay: `${delay * 0.05}s` }}
    >
      {/* Compare checkbox */}
      {onToggleCompare && (
        <div className="absolute top-3 right-3 z-10">
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              if (!compareDisabled || isSelectedForCompare) {
                onToggleCompare(grant.id);
              }
            }}
            disabled={compareDisabled && !isSelectedForCompare}
            className={`w-6 h-6 rounded-md flex items-center justify-center transition-all ${
              isSelectedForCompare
                ? 'bg-[var(--gr-blue-600)] text-white'
                : compareDisabled
                ? 'bg-[var(--gr-gray-100)] text-[var(--gr-text-muted)] cursor-not-allowed'
                : 'bg-[var(--gr-bg-card)] border border-[var(--gr-border-default)] text-[var(--gr-text-tertiary)] hover:border-[var(--gr-blue-400)] hover:text-[var(--gr-blue-600)]'
            }`}
            title={
              isSelectedForCompare
                ? 'Remove from comparison'
                : compareDisabled
                ? 'Maximum 4 grants can be compared'
                : 'Add to comparison'
            }
          >
            {isSelectedForCompare ? (
              <CheckIcon className="w-4 h-4" />
            ) : (
              <ScaleIcon className="w-4 h-4" />
            )}
          </button>
        </div>
      )}

      <Link to={`/grants/${match.id}`} className="block">
        {/* Header with score */}
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center flex-wrap gap-2 mb-3">
              <span className={`badge ${getSourceBadgeColor(grant.source)}`}>
                {grant.source}
              </span>
              <MatchScoreBadge score={score} />
              {competitionLevel && (
                <CompetitionBadge
                  level={competitionLevel}
                  score={competitionScore}
                  size="sm"
                  showLabel={true}
                />
              )}
            </div>
            <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)] group-hover:text-[var(--gr-blue-600)] transition-colors line-clamp-2 pr-8">
              {grant.title}
            </h3>
          </div>
        </div>

        {/* Funder */}
        <div className="flex items-center gap-2 text-sm text-[var(--gr-text-secondary)] mb-3">
          <BuildingLibraryIcon className="h-4 w-4 flex-shrink-0 text-[var(--gr-text-tertiary)]" />
          <span className="truncate">{grant.funder_name}</span>
        </div>

        {/* Description */}
        <p className="text-sm text-[var(--gr-text-tertiary)] line-clamp-2 mb-4">
          {grant.description}
        </p>

        {/* Meta info */}
        <div className="flex flex-wrap items-center gap-4 text-sm mb-4">
          {(grant.funding_amount_min || grant.funding_amount_max) && (
            <div className="flex items-center gap-1.5 text-[var(--gr-text-secondary)]">
              <CurrencyDollarIcon className="h-4 w-4 text-[var(--gr-yellow-500)]" />
              <span>
                {grant.funding_amount_min && grant.funding_amount_max
                  ? `${formatCurrency(grant.funding_amount_min)} - ${formatCurrency(grant.funding_amount_max)}`
                  : grant.funding_amount_max
                  ? `Up to ${formatCurrency(grant.funding_amount_max)}`
                  : formatCurrency(grant.funding_amount_min!)}
              </span>
            </div>
          )}
          {grant.deadline && (
            <div
              className={`flex items-center gap-1.5 ${
                isUrgent ? 'text-[var(--gr-danger)]' : 'text-[var(--gr-text-secondary)]'
              }`}
            >
              <CalendarIcon className={`h-4 w-4 ${isUrgent ? 'text-[var(--gr-danger)]' : 'text-[var(--gr-blue-500)]'}`} />
              <span className={isUrgent ? 'font-medium' : ''}>
                {isUrgent && daysUntilDeadline !== null
                  ? `${daysUntilDeadline} days left`
                  : formatDate(grant.deadline)}
              </span>
            </div>
          )}
        </div>

        {/* Focus areas */}
        {grant.focus_areas && grant.focus_areas.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {grant.focus_areas.slice(0, 3).map((area) => (
              <span
                key={area}
                className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-[var(--gr-slate-700)] text-[var(--gr-text-secondary)] border border-[var(--gr-border-subtle)]"
              >
                {area}
              </span>
            ))}
            {grant.focus_areas.length > 3 && (
              <span className="text-xs text-[var(--gr-text-tertiary)]">
                +{grant.focus_areas.length - 3} more
              </span>
            )}
          </div>
        )}
      </Link>

      {/* Actions */}
      {(onSave || onDismiss || showFindSimilar) && (
        <div className="flex items-center justify-end gap-2 mt-4 pt-4 border-t border-[var(--gr-border-subtle)]">
          {showFindSimilar && (
            <button
              onClick={(e) => {
                e.preventDefault();
                if (onFindSimilar) {
                  onFindSimilar(grant.id);
                } else {
                  // Navigate to grant detail page which shows similar grants
                  navigate(`/grants/${match.id}#similar`);
                }
              }}
              className="btn-ghost text-[var(--gr-text-tertiary)] hover:text-[var(--gr-amber-400)]"
            >
              <SparklesIcon className="h-4 w-4" />
              <span>Find Similar</span>
            </button>
          )}
          {onDismiss && status !== 'dismissed' && (
            <button
              onClick={(e) => {
                e.preventDefault();
                onDismiss(match.id);
              }}
              className="btn-ghost text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)]"
            >
              <XMarkIcon className="h-4 w-4" />
              <span>Dismiss</span>
            </button>
          )}
          {onSave && (
            <button
              onClick={(e) => {
                e.preventDefault();
                onSave(match.id);
              }}
              className={`btn-ghost ${
                isSaved
                  ? 'text-[var(--gr-emerald-400)]'
                  : 'text-[var(--gr-text-tertiary)] hover:text-[var(--gr-blue-600)]'
              }`}
            >
              {isSaved ? (
                <>
                  <BookmarkSolidIcon className="h-4 w-4" />
                  <span>Saved</span>
                </>
              ) : (
                <>
                  <BookmarkIcon className="h-4 w-4" />
                  <span>Save</span>
                </>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default GrantCard;
