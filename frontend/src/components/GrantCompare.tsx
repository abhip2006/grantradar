import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  CalendarIcon,
  CurrencyDollarIcon,
  BuildingLibraryIcon,
  ArrowTopRightOnSquareIcon,
  CheckCircleIcon,
  XMarkIcon,
  StarIcon,
} from '@heroicons/react/24/outline';
import { StarIcon as StarSolidIcon } from '@heroicons/react/24/solid';
import type { ComparisonGrant } from '../types';

interface GrantCompareProps {
  grants: ComparisonGrant[];
  onRemoveGrant?: (grantId: string) => void;
}

export function GrantCompare({ grants, onRemoveGrant }: GrantCompareProps) {
  // Format currency
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  // Format date
  const formatDate = (dateString?: string) => {
    if (!dateString) return 'No deadline';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  // Get days until deadline
  const getDaysUntilDeadline = (deadline?: string) => {
    if (!deadline) return null;
    const deadlineDate = new Date(deadline);
    const today = new Date();
    const diffTime = deadlineDate.getTime() - today.getTime();
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  };

  // Calculate best values for highlighting
  const highlights = useMemo(() => {
    const maxFunding = Math.max(
      ...grants.map((g) => g.amount_max || g.amount_min || 0)
    );
    const nearestDeadline = grants
      .filter((g) => g.deadline)
      .reduce<string | null>((nearest, g) => {
        if (!g.deadline) return nearest;
        const days = getDaysUntilDeadline(g.deadline);
        if (days === null || days < 0) return nearest;
        if (!nearest) return g.deadline;
        const nearestDays = getDaysUntilDeadline(nearest);
        if (nearestDays === null) return g.deadline;
        return days < nearestDays ? g.deadline : nearest;
      }, null);
    const highestScore = Math.max(
      ...grants.map((g) => g.match_score || 0)
    );

    return { maxFunding, nearestDeadline, highestScore };
  }, [grants]);

  // Check if a value should be highlighted
  const isHighlighted = (
    type: 'funding' | 'deadline' | 'score',
    grant: ComparisonGrant
  ) => {
    switch (type) {
      case 'funding':
        return (
          (grant.amount_max || grant.amount_min || 0) === highlights.maxFunding &&
          highlights.maxFunding > 0
        );
      case 'deadline':
        return (
          grant.deadline === highlights.nearestDeadline &&
          highlights.nearestDeadline !== null
        );
      case 'score':
        return (
          (grant.match_score || 0) === highlights.highestScore &&
          highlights.highestScore > 0
        );
    }
  };

  // Get source badge color
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

  // Check if values differ across grants
  const valuesDiffer = (
    extractor: (g: ComparisonGrant) => string | number | undefined | null
  ) => {
    const values = grants.map(extractor).filter((v) => v !== undefined && v !== null);
    const uniqueValues = new Set(values);
    return uniqueValues.size > 1;
  };

  const rowClasses = (
    differ: boolean,
    isHighlight?: boolean
  ) =>
    `py-4 px-4 ${differ ? 'bg-[var(--gr-yellow-50)]/50' : ''} ${
      isHighlight ? 'ring-2 ring-inset ring-[var(--gr-yellow-400)]/50 rounded-lg' : ''
    }`;

  return (
    <div className="overflow-hidden">
      {/* Desktop: Side-by-side table */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="text-left py-4 px-4 text-sm font-medium text-[var(--gr-text-tertiary)] w-40">
                Attribute
              </th>
              {grants.map((grant) => (
                <th
                  key={grant.id}
                  className="text-left py-4 px-4 min-w-[250px] max-w-[320px]"
                >
                  <div className="flex items-start justify-between gap-2">
                    <Link
                      to={`/grants/${grant.id}`}
                      className="text-lg font-display font-medium text-[var(--gr-text-primary)] hover:text-[var(--gr-blue-600)] transition-colors line-clamp-2"
                    >
                      {grant.title}
                    </Link>
                    {onRemoveGrant && (
                      <button
                        onClick={() => onRemoveGrant(grant.id)}
                        className="flex-shrink-0 p-1 rounded-lg hover:bg-[var(--gr-gray-100)] text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)] transition-colors"
                        aria-label="Remove from comparison"
                      >
                        <XMarkIcon className="w-5 h-5" />
                      </button>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--gr-border-subtle)]">
            {/* Source */}
            <tr>
              <td className="py-4 px-4 text-sm text-[var(--gr-text-tertiary)]">Source</td>
              {grants.map((grant) => (
                <td key={grant.id} className={rowClasses(valuesDiffer((g) => g.source))}>
                  <span className={`badge ${getSourceBadgeColor(grant.source)}`}>
                    {grant.source}
                  </span>
                </td>
              ))}
            </tr>

            {/* Agency */}
            <tr>
              <td className="py-4 px-4 text-sm text-[var(--gr-text-tertiary)]">
                <div className="flex items-center gap-2">
                  <BuildingLibraryIcon className="w-4 h-4" />
                  Agency
                </div>
              </td>
              {grants.map((grant) => (
                <td key={grant.id} className={rowClasses(valuesDiffer((g) => g.agency))}>
                  <span className="text-sm text-[var(--gr-text-primary)]">
                    {grant.agency || 'Not specified'}
                  </span>
                </td>
              ))}
            </tr>

            {/* Funding Amount */}
            <tr>
              <td className="py-4 px-4 text-sm text-[var(--gr-text-tertiary)]">
                <div className="flex items-center gap-2">
                  <CurrencyDollarIcon className="w-4 h-4" />
                  Funding
                </div>
              </td>
              {grants.map((grant) => (
                <td
                  key={grant.id}
                  className={rowClasses(
                    valuesDiffer((g) => g.amount_max || g.amount_min),
                    isHighlighted('funding', grant)
                  )}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-[var(--gr-text-primary)]">
                      {grant.amount_min && grant.amount_max
                        ? `${formatCurrency(grant.amount_min)} - ${formatCurrency(grant.amount_max)}`
                        : grant.amount_max
                        ? `Up to ${formatCurrency(grant.amount_max)}`
                        : grant.amount_min
                        ? formatCurrency(grant.amount_min)
                        : 'Not specified'}
                    </span>
                    {isHighlighted('funding', grant) && (
                      <span className="badge badge-yellow text-xs">Highest</span>
                    )}
                  </div>
                </td>
              ))}
            </tr>

            {/* Deadline */}
            <tr>
              <td className="py-4 px-4 text-sm text-[var(--gr-text-tertiary)]">
                <div className="flex items-center gap-2">
                  <CalendarIcon className="w-4 h-4" />
                  Deadline
                </div>
              </td>
              {grants.map((grant) => {
                const days = getDaysUntilDeadline(grant.deadline);
                const isUrgent = days !== null && days <= 7 && days > 0;
                return (
                  <td
                    key={grant.id}
                    className={rowClasses(
                      valuesDiffer((g) => g.deadline),
                      isHighlighted('deadline', grant)
                    )}
                  >
                    <div className="flex flex-col gap-1">
                      <span
                        className={`text-sm font-medium ${
                          isUrgent ? 'text-[var(--gr-danger)]' : 'text-[var(--gr-text-primary)]'
                        }`}
                      >
                        {formatDate(grant.deadline)}
                      </span>
                      {days !== null && days > 0 && (
                        <span className="text-xs text-[var(--gr-text-tertiary)]">
                          {days} days remaining
                          {isHighlighted('deadline', grant) && (
                            <span className="ml-2 text-[var(--gr-yellow-600)]">
                              (Nearest)
                            </span>
                          )}
                        </span>
                      )}
                      {days !== null && days <= 0 && (
                        <span className="text-xs text-[var(--gr-danger)]">Expired</span>
                      )}
                    </div>
                  </td>
                );
              })}
            </tr>

            {/* Match Score */}
            <tr>
              <td className="py-4 px-4 text-sm text-[var(--gr-text-tertiary)]">
                <div className="flex items-center gap-2">
                  <StarIcon className="w-4 h-4" />
                  Match Score
                </div>
              </td>
              {grants.map((grant) => {
                const score = grant.match_score ? Math.round(grant.match_score * 100) : null;
                return (
                  <td
                    key={grant.id}
                    className={rowClasses(
                      valuesDiffer((g) => g.match_score),
                      isHighlighted('score', grant)
                    )}
                  >
                    {score !== null ? (
                      <div className="flex items-center gap-2">
                        <div
                          className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${
                            score >= 80
                              ? 'bg-[var(--gr-green-500)]/10 text-[var(--gr-green-600)]'
                              : score >= 60
                              ? 'bg-[var(--gr-blue-500)]/10 text-[var(--gr-blue-600)]'
                              : 'bg-[var(--gr-gray-200)] text-[var(--gr-text-secondary)]'
                          }`}
                        >
                          {score >= 80 ? (
                            <StarSolidIcon className="w-4 h-4" />
                          ) : (
                            <StarIcon className="w-4 h-4" />
                          )}
                          {score}%
                        </div>
                        {isHighlighted('score', grant) && (
                          <span className="badge badge-yellow text-xs">Best</span>
                        )}
                      </div>
                    ) : (
                      <span className="text-sm text-[var(--gr-text-tertiary)]">
                        Not scored
                      </span>
                    )}
                  </td>
                );
              })}
            </tr>

            {/* Focus Areas / Categories */}
            <tr>
              <td className="py-4 px-4 text-sm text-[var(--gr-text-tertiary)]">
                Focus Areas
              </td>
              {grants.map((grant) => (
                <td key={grant.id} className="py-4 px-4">
                  {grant.categories && grant.categories.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {grant.categories.slice(0, 4).map((cat) => (
                        <span
                          key={cat}
                          className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-[var(--gr-gray-100)] text-[var(--gr-text-secondary)] border border-[var(--gr-border-subtle)]"
                        >
                          {cat}
                        </span>
                      ))}
                      {grant.categories.length > 4 && (
                        <span className="text-xs text-[var(--gr-text-tertiary)]">
                          +{grant.categories.length - 4} more
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="text-sm text-[var(--gr-text-tertiary)]">
                      Not specified
                    </span>
                  )}
                </td>
              ))}
            </tr>

            {/* Eligibility (simplified) */}
            <tr>
              <td className="py-4 px-4 text-sm text-[var(--gr-text-tertiary)]">
                Eligibility
              </td>
              {grants.map((grant) => (
                <td key={grant.id} className="py-4 px-4">
                  {grant.eligibility ? (
                    <div className="text-sm text-[var(--gr-text-secondary)]">
                      {Object.keys(grant.eligibility).length > 0 ? (
                        <div className="flex items-center gap-1 text-[var(--gr-green-600)]">
                          <CheckCircleIcon className="w-4 h-4" />
                          Criteria available
                        </div>
                      ) : (
                        'See details'
                      )}
                    </div>
                  ) : (
                    <span className="text-sm text-[var(--gr-text-tertiary)]">
                      Not specified
                    </span>
                  )}
                </td>
              ))}
            </tr>

            {/* Link */}
            <tr>
              <td className="py-4 px-4 text-sm text-[var(--gr-text-tertiary)]">
                Link
              </td>
              {grants.map((grant) => (
                <td key={grant.id} className="py-4 px-4">
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/grants/${grant.id}`}
                      className="btn-ghost text-sm"
                    >
                      View Details
                    </Link>
                    {grant.url && (
                      <a
                        href={grant.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-ghost text-sm"
                      >
                        <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                        Apply
                      </a>
                    )}
                  </div>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      {/* Mobile: Stacked cards */}
      <div className="md:hidden space-y-6">
        {grants.map((grant) => (
          <div key={grant.id} className="card-elevated">
            <div className="flex items-start justify-between gap-2 mb-4">
              <Link
                to={`/grants/${grant.id}`}
                className="text-lg font-display font-medium text-[var(--gr-text-primary)] hover:text-[var(--gr-blue-600)] transition-colors"
              >
                {grant.title}
              </Link>
              {onRemoveGrant && (
                <button
                  onClick={() => onRemoveGrant(grant.id)}
                  className="p-1 rounded-lg hover:bg-[var(--gr-gray-100)] text-[var(--gr-text-tertiary)]"
                  aria-label="Remove from comparison"
                >
                  <XMarkIcon className="w-5 h-5" />
                </button>
              )}
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--gr-text-tertiary)]">Source</span>
                <span className={`badge ${getSourceBadgeColor(grant.source)}`}>
                  {grant.source}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--gr-text-tertiary)]">Agency</span>
                <span className="text-sm text-[var(--gr-text-primary)]">
                  {grant.agency || 'Not specified'}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--gr-text-tertiary)]">Funding</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-[var(--gr-text-primary)]">
                    {grant.amount_min && grant.amount_max
                      ? `${formatCurrency(grant.amount_min)} - ${formatCurrency(grant.amount_max)}`
                      : grant.amount_max
                      ? `Up to ${formatCurrency(grant.amount_max)}`
                      : grant.amount_min
                      ? formatCurrency(grant.amount_min)
                      : 'Not specified'}
                  </span>
                  {isHighlighted('funding', grant) && (
                    <span className="badge badge-yellow text-xs">Highest</span>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--gr-text-tertiary)]">Deadline</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-[var(--gr-text-primary)]">
                    {formatDate(grant.deadline)}
                  </span>
                  {isHighlighted('deadline', grant) && (
                    <span className="badge badge-yellow text-xs">Nearest</span>
                  )}
                </div>
              </div>

              {grant.match_score !== undefined && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[var(--gr-text-tertiary)]">Match Score</span>
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-3 py-1 rounded-full text-sm font-medium ${
                        Math.round(grant.match_score * 100) >= 80
                          ? 'bg-[var(--gr-green-500)]/10 text-[var(--gr-green-600)]'
                          : Math.round(grant.match_score * 100) >= 60
                          ? 'bg-[var(--gr-blue-500)]/10 text-[var(--gr-blue-600)]'
                          : 'bg-[var(--gr-gray-200)] text-[var(--gr-text-secondary)]'
                      }`}
                    >
                      {Math.round(grant.match_score * 100)}%
                    </span>
                    {isHighlighted('score', grant) && (
                      <span className="badge badge-yellow text-xs">Best</span>
                    )}
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2 pt-3 border-t border-[var(--gr-border-subtle)]">
                <Link to={`/grants/${grant.id}`} className="btn-primary flex-1 text-center">
                  View Details
                </Link>
                {grant.url && (
                  <a
                    href={grant.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-secondary"
                  >
                    <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                  </a>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default GrantCompare;
