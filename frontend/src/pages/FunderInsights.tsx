import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams, Link, useNavigate } from 'react-router-dom';
import {
  MagnifyingGlassIcon,
  BuildingLibraryIcon,
  ArrowPathIcon,
  ChevronLeftIcon,
  CalendarIcon,
  CurrencyDollarIcon,
  SparklesIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { funderInsightsApi } from '../services/api';
import { FunderCard } from '../components/insights/FunderCard';
import type { FunderGrant } from '../types';

function formatCurrency(amount: number): string {
  if (amount >= 1000000) {
    return `$${(amount / 1000000).toFixed(1)}M`;
  }
  if (amount >= 1000) {
    return `$${(amount / 1000).toFixed(0)}K`;
  }
  return `$${amount.toLocaleString()}`;
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function FunderGrantCard({ grant }: { grant: FunderGrant }) {
  return (
    <Link
      to={`/grants/${grant.id}`}
      className="block bg-[var(--gr-bg-card)] border border-[var(--gr-border-default)] rounded-xl p-4 hover:border-[var(--gr-blue-300)] hover:shadow-[var(--gr-shadow-md)] transition-all group"
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <h4 className="text-sm font-medium text-[var(--gr-text-primary)] group-hover:text-[var(--gr-blue-600)] transition-colors line-clamp-2">
          {grant.title}
        </h4>
        {grant.is_active && (
          <span className="flex-shrink-0 inline-flex items-center px-2 py-0.5 rounded text-xs bg-[rgba(34,197,94,0.1)] text-[var(--gr-green-600)] border border-[rgba(34,197,94,0.2)]">
            Active
          </span>
        )}
      </div>

      {grant.description && (
        <p className="text-xs text-[var(--gr-text-tertiary)] line-clamp-2 mb-3">
          {grant.description}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--gr-text-secondary)]">
        {(grant.amount_min || grant.amount_max) && (
          <div className="flex items-center gap-1">
            <CurrencyDollarIcon className="h-3.5 w-3.5 text-[var(--gr-yellow-600)]" />
            <span>
              {grant.amount_min && grant.amount_max
                ? `${formatCurrency(grant.amount_min)} - ${formatCurrency(grant.amount_max)}`
                : grant.amount_max
                ? `Up to ${formatCurrency(grant.amount_max)}`
                : formatCurrency(grant.amount_min!)}
            </span>
          </div>
        )}
        {grant.deadline && (
          <div className="flex items-center gap-1">
            <CalendarIcon className="h-3.5 w-3.5 text-[var(--gr-blue-500)]" />
            <span>{formatDate(grant.deadline)}</span>
          </div>
        )}
      </div>

      {grant.categories && grant.categories.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3">
          {grant.categories.slice(0, 3).map((category, index) => (
            <span
              key={index}
              className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-[var(--gr-gray-100)] text-[var(--gr-text-tertiary)]"
            >
              {category}
            </span>
          ))}
        </div>
      )}
    </Link>
  );
}

function FunderGrantsList({ funderName }: { funderName: string }) {
  const [activeOnly, setActiveOnly] = useState(true);
  const [page, setPage] = useState(1);

  const { data, isLoading, error } = useQuery({
    queryKey: ['funder-grants', funderName, page, activeOnly],
    queryFn: () =>
      funderInsightsApi.getFunderGrants(funderName, {
        page,
        page_size: 12,
        active_only: activeOnly,
      }),
    enabled: !!funderName,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="skeleton h-40 rounded-xl" />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-12 text-[var(--gr-text-tertiary)]">
        <p>Failed to load grants</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-[var(--gr-text-tertiary)]">
          {data.total} {data.total === 1 ? 'grant' : 'grants'} found
        </p>
        <label className="flex items-center gap-2 text-sm text-[var(--gr-text-secondary)] cursor-pointer">
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={(e) => {
              setActiveOnly(e.target.checked);
              setPage(1);
            }}
            className="rounded border-[var(--gr-border-default)] bg-[var(--gr-bg-primary)] text-[var(--gr-blue-600)] focus:ring-[var(--gr-blue-500)]"
          />
          Active only
        </label>
      </div>

      {/* Grants grid */}
      {data.grants.length === 0 ? (
        <div className="text-center py-12 text-[var(--gr-text-tertiary)]">
          <DocumentTextIcon className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p>No grants found</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.grants.map((grant) => (
              <FunderGrantCard key={grant.id} grant={grant} />
            ))}
          </div>

          {/* Pagination */}
          {data.total > 12 && (
            <div className="flex items-center justify-center gap-2 pt-4">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 text-sm rounded-lg bg-[var(--gr-bg-secondary)] text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <span className="text-sm text-[var(--gr-text-tertiary)]">
                Page {page} of {Math.ceil(data.total / 12)}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={!data.has_more}
                className="px-4 py-2 text-sm rounded-lg bg-[var(--gr-bg-secondary)] text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// Top funders section component
function TopFundersSection() {
  const { data, isLoading } = useQuery({
    queryKey: ['top-funders'],
    queryFn: () => funderInsightsApi.getTopFunders({ sort_by: 'grant_count', limit: 5 }),
    staleTime: 10 * 60 * 1000,
  });

  if (isLoading || !data?.funders.length) {
    return null;
  }

  return (
    <div className="mb-8 bg-[var(--gr-bg-secondary)] rounded-xl p-6 border border-[var(--gr-border-default)]">
      <div className="flex items-center gap-2 mb-4">
        <SparklesIcon className="h-5 w-5 text-[var(--gr-yellow-500)]" />
        <h2 className="text-lg font-display font-semibold text-[var(--gr-text-primary)]">
          Top Funders
        </h2>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {data.funders.map((funder, index) => (
          <Link
            key={funder.funder_name}
            to={`/funders/${encodeURIComponent(funder.funder_name)}`}
            className="flex items-center gap-3 p-3 bg-[var(--gr-bg-card)] rounded-lg border border-[var(--gr-border-subtle)] hover:border-[var(--gr-blue-300)] hover:shadow-[var(--gr-shadow-sm)] transition-all group"
          >
            <span className="flex-shrink-0 w-7 h-7 rounded-full bg-[var(--gr-yellow-50)] text-[var(--gr-yellow-700)] flex items-center justify-center text-sm font-bold">
              {index + 1}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-[var(--gr-text-primary)] truncate group-hover:text-[var(--gr-blue-600)] transition-colors">
                {funder.funder_name}
              </p>
              <p className="text-xs text-[var(--gr-text-tertiary)]">
                {funder.total_grants} grants
              </p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function FunderInsights() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const searchQuery = searchParams.get('search') || '';
  const [searchInput, setSearchInput] = useState(searchQuery);

  // If we have a search query, we're viewing a specific funder's grants
  const viewingFunderGrants = searchQuery.length > 0;

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['funders', viewingFunderGrants ? '' : searchInput],
    queryFn: () =>
      funderInsightsApi.listFunders({
        search: viewingFunderGrants ? '' : searchInput || undefined,
        limit: 50,
      }),
    enabled: !viewingFunderGrants,
    staleTime: 5 * 60 * 1000,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // Trigger refetch with current search input
    refetch();
  };

  const handleClearFunderView = () => {
    setSearchParams({});
    setSearchInput('');
  };

  const sortedFunders = useMemo(() => {
    if (!data?.funders) return [];
    return [...data.funders].sort((a, b) => b.total_grants - a.total_grants);
  }, [data?.funders]);

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          {viewingFunderGrants ? (
            <div className="flex items-center gap-4 mb-4">
              <button
                onClick={handleClearFunderView}
                className="inline-flex items-center gap-2 text-sm text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] transition-colors"
              >
                <ChevronLeftIcon className="h-4 w-4" />
                Back to all funders
              </button>
            </div>
          ) : null}

          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-[var(--gr-blue-50)] rounded-xl flex items-center justify-center">
              <BuildingLibraryIcon className="h-6 w-6 text-[var(--gr-blue-600)]" />
            </div>
            <div>
              <h1 className="text-2xl font-display font-bold text-[var(--gr-text-primary)]">
                {viewingFunderGrants ? searchQuery : 'Funder Insights'}
              </h1>
              <p className="text-sm text-[var(--gr-text-tertiary)]">
                {viewingFunderGrants
                  ? 'Browse grants from this funder'
                  : 'Historical data and analytics on grant funders'}
              </p>
            </div>
          </div>
        </div>

        {viewingFunderGrants ? (
          /* Funder-specific grants view */
          <div>
            <div className="flex items-center gap-3 mb-6">
              <Link
                to={`/funders/${encodeURIComponent(searchQuery)}`}
                className="btn-primary inline-flex items-center gap-2"
              >
                <SparklesIcon className="h-4 w-4" />
                View Full Insights
              </Link>
            </div>
            <FunderGrantsList funderName={searchQuery} />
          </div>
        ) : (
          /* Funder directory view */
          <>
            {/* Top Funders Section */}
            <TopFundersSection />

            {/* Search bar */}
            <form onSubmit={handleSearch} className="mb-6">
              <div className="relative max-w-xl">
                <MagnifyingGlassIcon className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-[var(--gr-text-tertiary)]" />
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search funders by name..."
                  className="w-full pl-12 pr-4 py-3 bg-[var(--gr-bg-secondary)] border border-[var(--gr-border-default)] rounded-xl text-[var(--gr-text-primary)] placeholder-[var(--gr-text-tertiary)] focus:outline-none focus:ring-2 focus:ring-[var(--gr-blue-500)] focus:border-transparent"
                />
                {searchInput && (
                  <button
                    type="button"
                    onClick={() => setSearchInput('')}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)]"
                  >
                    <span className="sr-only">Clear</span>
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                )}
              </div>
            </form>

            {/* Stats summary */}
            {data && (
              <div className="mb-6 flex items-center justify-between">
                <p className="text-sm text-[var(--gr-text-tertiary)]">
                  Showing {sortedFunders.length} of {data.total} funders
                </p>
                <button
                  onClick={() => refetch()}
                  disabled={isFetching}
                  className="inline-flex items-center gap-2 text-sm text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] transition-colors disabled:opacity-50"
                >
                  <ArrowPathIcon
                    className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`}
                  />
                  Refresh
                </button>
              </div>
            )}

            {/* Funders grid */}
            {isLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[...Array(9)].map((_, i) => (
                  <div key={i} className="skeleton h-48 rounded-xl" />
                ))}
              </div>
            ) : error ? (
              <div className="text-center py-16">
                <BuildingLibraryIcon className="h-16 w-16 mx-auto mb-4 text-[var(--gr-text-tertiary)] opacity-50" />
                <h3 className="text-lg font-medium text-[var(--gr-text-primary)] mb-2">
                  Failed to load funders
                </h3>
                <p className="text-sm text-[var(--gr-text-tertiary)] mb-4">
                  There was an error loading the funder directory.
                </p>
                <button onClick={() => refetch()} className="btn-secondary">
                  Try Again
                </button>
              </div>
            ) : sortedFunders.length === 0 ? (
              <div className="text-center py-16">
                <BuildingLibraryIcon className="h-16 w-16 mx-auto mb-4 text-[var(--gr-text-tertiary)] opacity-50" />
                <h3 className="text-lg font-medium text-[var(--gr-text-primary)] mb-2">
                  No funders found
                </h3>
                <p className="text-sm text-[var(--gr-text-tertiary)]">
                  {searchInput
                    ? `No funders match "${searchInput}"`
                    : 'No funders have been indexed yet.'}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {sortedFunders.map((funder) => (
                  <FunderCard
                    key={funder.funder_name}
                    funder={funder}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default FunderInsights;
