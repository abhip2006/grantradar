import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ChevronLeftIcon,
  BuildingLibraryIcon,
  ArrowPathIcon,
  DocumentTextIcon,
  CalendarIcon,
  CurrencyDollarIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';
import { funderInsightsApi } from '../services/api';
import { FunderStats, FundingDistribution, DeadlineHeatmap, FocusAreaCloud } from '../components/funders';
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
      className="block bg-[var(--gr-bg-card)] p-4 rounded-xl border border-[var(--gr-border-default)] hover:border-[var(--gr-blue-300)] hover:shadow-[var(--gr-shadow-md)] transition-all group"
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
          {grant.categories.length > 3 && (
            <span className="text-[10px] text-[var(--gr-text-tertiary)]">
              +{grant.categories.length - 3}
            </span>
          )}
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

export function FunderDetail() {
  const { funderName } = useParams<{ funderName: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'insights' | 'grants'>('insights');

  const decodedName = funderName ? decodeURIComponent(funderName) : '';

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['funder-insights', decodedName],
    queryFn: () => funderInsightsApi.getFunderInsights(decodedName),
    enabled: !!decodedName,
    staleTime: 5 * 60 * 1000,
  });

  if (!funderName) {
    return (
      <div className="min-h-screen bg-[var(--gr-bg-primary)] flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-xl font-display font-semibold text-[var(--gr-text-primary)] mb-2">
            Funder not found
          </h1>
          <Link to="/funders" className="btn-primary">
            Browse Funders
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Back Button */}
        <button
          onClick={() => navigate('/funders')}
          className="inline-flex items-center gap-2 text-sm text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] transition-colors mb-6"
        >
          <ChevronLeftIcon className="h-4 w-4" />
          Back to Funders
        </button>

        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-[var(--gr-blue-50)] rounded-xl flex items-center justify-center">
              <BuildingLibraryIcon className="h-7 w-7 text-[var(--gr-blue-600)]" />
            </div>
            <div>
              <h1 className="text-2xl font-display font-bold text-[var(--gr-text-primary)]">
                {decodedName}
              </h1>
              {data && (
                <p className="text-sm text-[var(--gr-text-tertiary)] mt-1">
                  {data.active_grants} active / {data.total_grants} total grants
                </p>
              )}
            </div>
          </div>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-[var(--gr-bg-secondary)] text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-hover)] disabled:opacity-50 transition-colors"
          >
            <ArrowPathIcon className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 border-b border-[var(--gr-border-default)]">
          <button
            onClick={() => setActiveTab('insights')}
            className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === 'insights'
                ? 'text-[var(--gr-blue-600)] border-[var(--gr-blue-600)]'
                : 'text-[var(--gr-text-secondary)] border-transparent hover:text-[var(--gr-text-primary)]'
            }`}
          >
            Insights & Analytics
          </button>
          <button
            onClick={() => setActiveTab('grants')}
            className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === 'grants'
                ? 'text-[var(--gr-blue-600)] border-[var(--gr-blue-600)]'
                : 'text-[var(--gr-text-secondary)] border-transparent hover:text-[var(--gr-text-primary)]'
            }`}
          >
            All Grants
          </button>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="skeleton h-28 rounded-xl" />
              ))}
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="skeleton h-64 rounded-xl" />
              <div className="skeleton h-64 rounded-xl" />
            </div>
          </div>
        ) : error ? (
          <div className="text-center py-16">
            <BuildingLibraryIcon className="h-16 w-16 mx-auto mb-4 text-[var(--gr-text-tertiary)] opacity-50" />
            <h3 className="text-lg font-medium text-[var(--gr-text-primary)] mb-2">
              Failed to load funder data
            </h3>
            <p className="text-sm text-[var(--gr-text-tertiary)] mb-4">
              There was an error loading insights for this funder.
            </p>
            <button onClick={() => refetch()} className="btn-secondary">
              Try Again
            </button>
          </div>
        ) : data ? (
          activeTab === 'insights' ? (
            <div className="space-y-8">
              {/* Key Statistics */}
              <FunderStats data={data} />

              {/* Charts Row */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Funding Distribution */}
                <FundingDistribution data={data} />

                {/* Deadline Heatmap */}
                <DeadlineHeatmap
                  deadlineMonths={data.deadline_months}
                  typicalDeadlineMonths={data.typical_deadline_months}
                />
              </div>

              {/* Focus Areas */}
              <FocusAreaCloud
                focusAreas={data.focus_areas}
                focusAreaCounts={data.focus_area_counts}
              />

              {/* Quick Actions */}
              <div className="flex items-center justify-center gap-4 pt-4">
                <button
                  onClick={() => setActiveTab('grants')}
                  className="btn-primary inline-flex items-center gap-2"
                >
                  <DocumentTextIcon className="h-4 w-4" />
                  View All Grants
                </button>
                <Link
                  to={`/funders?search=${encodeURIComponent(decodedName)}`}
                  className="btn-secondary inline-flex items-center gap-2"
                >
                  <FunnelIcon className="h-4 w-4" />
                  Filter by Funder
                </Link>
              </div>
            </div>
          ) : (
            <FunderGrantsList funderName={decodedName} />
          )
        ) : null}
      </div>
    </div>
  );
}

export default FunderDetail;
