import { Link } from 'react-router-dom';
import {
  BuildingLibraryIcon,
  CurrencyDollarIcon,
  DocumentTextIcon,
  TagIcon,
} from '@heroicons/react/24/outline';
import type { FunderSummary } from '../../types';

interface FunderCardProps {
  funder: FunderSummary;
  onClick?: () => void;
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

export function FunderCard({ funder, onClick }: FunderCardProps) {
  const hasAmounts = funder.avg_amount_min || funder.avg_amount_max;

  const cardContent = (
    <>
      {/* Header with icon and name */}
      <div className="flex items-start gap-4 mb-4">
        <div className="flex-shrink-0 w-12 h-12 bg-[var(--gr-blue-50)] rounded-xl flex items-center justify-center">
          <BuildingLibraryIcon className="h-6 w-6 text-[var(--gr-blue-600)]" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-display font-medium text-[var(--gr-text-primary)] group-hover:text-[var(--gr-blue-600)] transition-colors line-clamp-2">
            {funder.funder_name}
          </h3>
          <p className="text-sm text-[var(--gr-text-tertiary)] mt-0.5">
            {funder.active_grants} active / {funder.total_grants} total grants
          </p>
        </div>
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-4 text-sm mb-4">
        <div className="flex items-center gap-1.5 text-[var(--gr-text-secondary)]">
          <DocumentTextIcon className="h-4 w-4 text-[var(--gr-text-tertiary)]" />
          <span>{funder.total_grants} grants</span>
        </div>
        {hasAmounts && (
          <div className="flex items-center gap-1.5 text-[var(--gr-text-secondary)]">
            <CurrencyDollarIcon className="h-4 w-4 text-[var(--gr-yellow-600)]" />
            <span>
              {funder.avg_amount_min && funder.avg_amount_max
                ? `${formatCurrency(funder.avg_amount_min)} - ${formatCurrency(funder.avg_amount_max)}`
                : funder.avg_amount_max
                ? `Up to ${formatCurrency(funder.avg_amount_max)}`
                : `From ${formatCurrency(funder.avg_amount_min!)}`}
            </span>
          </div>
        )}
      </div>

      {/* Focus areas */}
      {funder.focus_areas.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <TagIcon className="h-4 w-4 text-[var(--gr-text-tertiary)] flex-shrink-0 mt-0.5" />
          {funder.focus_areas.slice(0, 4).map((area, index) => (
            <span
              key={index}
              className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-[var(--gr-gray-100)] text-[var(--gr-text-secondary)] border border-[var(--gr-border-subtle)]"
            >
              {area}
            </span>
          ))}
          {funder.focus_areas.length > 4 && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs text-[var(--gr-text-tertiary)]">
              +{funder.focus_areas.length - 4} more
            </span>
          )}
        </div>
      )}

      {/* Active indicator */}
      {funder.active_grants > 0 && (
        <div className="mt-4 pt-3 border-t border-[var(--gr-border-subtle)]">
          <span className="inline-flex items-center gap-1.5 text-xs text-[var(--gr-green-600)]">
            <span className="w-2 h-2 rounded-full bg-[var(--gr-green-500)] animate-pulse" />
            {funder.active_grants} active {funder.active_grants === 1 ? 'grant' : 'grants'}
          </span>
        </div>
      )}
    </>
  );

  // If onClick is provided, render as button; otherwise render as Link
  if (onClick) {
    return (
      <button
        onClick={onClick}
        className="w-full text-left bg-[var(--gr-bg-card)] border border-[var(--gr-border-default)] rounded-xl p-5 hover:border-[var(--gr-blue-300)] hover:shadow-[var(--gr-shadow-md)] transition-all group"
      >
        {cardContent}
      </button>
    );
  }

  return (
    <Link
      to={`/funders/${encodeURIComponent(funder.funder_name)}`}
      className="block bg-[var(--gr-bg-card)] border border-[var(--gr-border-default)] rounded-xl p-5 hover:border-[var(--gr-blue-300)] hover:shadow-[var(--gr-shadow-md)] transition-all group"
    >
      {cardContent}
    </Link>
  );
}

export default FunderCard;
