import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'motion/react';
import {
  MagnifyingGlassIcon,
  AcademicCapIcon,
  BuildingLibraryIcon,
  CurrencyDollarIcon,
  UserIcon,
  DocumentTextIcon,
  ChartBarIcon,
  BeakerIcon,
  FunnelIcon,
  XMarkIcon,
  ArrowTrendingUpIcon,
  SparklesIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from '@heroicons/react/24/outline';
import { winnersApi } from '../services/api';
import type {
  FundedProject,
  WinnersFilters,
  WinnersSearchResponse,
} from '../types/winners';
import { NIH_INSTITUTES, ACTIVITY_CODES, defaultWinnersFilters } from '../types/winners';

// =============================================================================
// Utility Functions
// =============================================================================

function formatCurrency(amount: number): string {
  if (amount >= 1000000) {
    return `$${(amount / 1000000).toFixed(1)}M`;
  }
  if (amount >= 1000) {
    return `$${(amount / 1000).toFixed(0)}K`;
  }
  return `$${amount.toLocaleString()}`;
}

function formatDate(dateString?: string): string {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

// =============================================================================
// Components
// =============================================================================

function WinnerCard({ project, onClick }: { project: FundedProject; onClick: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="card-premium hover:shadow-editorial-lg transition-all cursor-pointer group"
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-display font-semibold text-[var(--gr-text-primary)] line-clamp-2 group-hover:text-[var(--gr-accent-forest)] transition-colors">
            {project.title}
          </h3>
          {project.principal_investigator?.name && (
            <p className="text-sm text-[var(--gr-text-secondary)] mt-1 flex items-center gap-1.5">
              <UserIcon className="h-3.5 w-3.5" />
              {project.principal_investigator.name}
            </p>
          )}
        </div>
        {project.activity_code && (
          <span className="flex-shrink-0 badge-mechanism">
            {project.activity_code}
          </span>
        )}
      </div>

      {/* Organization */}
      {project.organization?.name && (
        <div className="flex items-center gap-1.5 text-sm text-[var(--gr-text-tertiary)] mb-3">
          <BuildingLibraryIcon className="h-3.5 w-3.5" />
          <span className="truncate">{project.organization.name}</span>
          {project.organization.state && (
            <span className="text-[var(--gr-text-muted)]">
              ({project.organization.state})
            </span>
          )}
        </div>
      )}

      {/* Abstract Preview */}
      {project.abstract && (
        <p className="text-sm text-[var(--gr-text-secondary)] line-clamp-3 mb-4">
          {project.abstract}
        </p>
      )}

      {/* Footer Stats */}
      <div className="flex flex-wrap items-center gap-4 pt-3 border-t border-[var(--gr-border-light)]">
        {project.award_amount && (
          <div className="flex items-center gap-1.5 text-sm">
            <CurrencyDollarIcon className="h-4 w-4 text-[var(--gr-accent-gold)]" />
            <span className="font-medium text-[var(--gr-text-primary)]">
              {formatCurrency(project.award_amount)}
            </span>
          </div>
        )}
        {project.fiscal_year && (
          <div className="text-sm text-[var(--gr-text-tertiary)]">
            FY {project.fiscal_year}
          </div>
        )}
        {project.institute && (
          <div className="text-sm text-[var(--gr-text-tertiary)]">
            {project.institute}
          </div>
        )}
      </div>
    </motion.div>
  );
}

function ProjectModal({
  project,
  onClose,
}: {
  project: FundedProject;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="relative w-full max-w-3xl max-h-[85vh] overflow-auto bg-[var(--gr-bg-primary)] rounded-2xl shadow-editorial-xl"
      >
        {/* Header */}
        <div className="sticky top-0 bg-[var(--gr-bg-primary)] border-b border-[var(--gr-border-light)] p-6 z-10">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                {project.activity_code && (
                  <span className="badge-mechanism">{project.activity_code}</span>
                )}
                {project.institute && (
                  <span className="text-sm text-[var(--gr-text-tertiary)]">
                    {project.institute_name || project.institute}
                  </span>
                )}
              </div>
              <h2 className="text-xl font-display font-bold text-[var(--gr-text-primary)]">
                {project.title}
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-secondary)] rounded-lg transition-colors"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Key Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {project.award_amount && (
              <div className="stat-card-compact">
                <CurrencyDollarIcon className="h-5 w-5 text-[var(--gr-accent-gold)]" />
                <div>
                  <div className="text-xs text-[var(--gr-text-tertiary)]">Award Amount</div>
                  <div className="text-lg font-display font-bold text-[var(--gr-text-primary)]">
                    {formatCurrency(project.award_amount)}
                  </div>
                </div>
              </div>
            )}
            {project.fiscal_year && (
              <div className="stat-card-compact">
                <ChartBarIcon className="h-5 w-5 text-[var(--gr-accent-forest)]" />
                <div>
                  <div className="text-xs text-[var(--gr-text-tertiary)]">Fiscal Year</div>
                  <div className="text-lg font-display font-bold text-[var(--gr-text-primary)]">
                    {project.fiscal_year}
                  </div>
                </div>
              </div>
            )}
            {project.start_date && (
              <div className="stat-card-compact">
                <BeakerIcon className="h-5 w-5 text-[var(--gr-blue-500)]" />
                <div>
                  <div className="text-xs text-[var(--gr-text-tertiary)]">Start Date</div>
                  <div className="text-sm font-medium text-[var(--gr-text-primary)]">
                    {formatDate(project.start_date)}
                  </div>
                </div>
              </div>
            )}
            {project.end_date && (
              <div className="stat-card-compact">
                <BeakerIcon className="h-5 w-5 text-[var(--gr-text-tertiary)]" />
                <div>
                  <div className="text-xs text-[var(--gr-text-tertiary)]">End Date</div>
                  <div className="text-sm font-medium text-[var(--gr-text-primary)]">
                    {formatDate(project.end_date)}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* PI & Organization */}
          <div className="grid md:grid-cols-2 gap-4">
            {project.principal_investigator && (
              <div className="card-premium-subtle">
                <h4 className="font-display font-semibold text-[var(--gr-text-primary)] mb-2 flex items-center gap-2">
                  <UserIcon className="h-4 w-4" />
                  Principal Investigator
                </h4>
                <p className="text-[var(--gr-text-secondary)]">
                  {project.principal_investigator.name}
                </p>
                {project.principal_investigator.email && (
                  <p className="text-sm text-[var(--gr-text-tertiary)]">
                    {project.principal_investigator.email}
                  </p>
                )}
              </div>
            )}
            {project.organization && (
              <div className="card-premium-subtle">
                <h4 className="font-display font-semibold text-[var(--gr-text-primary)] mb-2 flex items-center gap-2">
                  <BuildingLibraryIcon className="h-4 w-4" />
                  Institution
                </h4>
                <p className="text-[var(--gr-text-secondary)]">
                  {project.organization.name}
                </p>
                <p className="text-sm text-[var(--gr-text-tertiary)]">
                  {[project.organization.city, project.organization.state]
                    .filter(Boolean)
                    .join(', ')}
                </p>
              </div>
            )}
          </div>

          {/* Program Officer */}
          {project.program_officer && (
            <div className="card-premium-subtle">
              <h4 className="font-display font-semibold text-[var(--gr-text-primary)] mb-2">
                Program Officer
              </h4>
              <p className="text-[var(--gr-text-secondary)]">{project.program_officer}</p>
            </div>
          )}

          {/* Abstract */}
          {project.abstract && (
            <div>
              <h4 className="font-display font-semibold text-[var(--gr-text-primary)] mb-3 flex items-center gap-2">
                <DocumentTextIcon className="h-4 w-4" />
                Abstract
              </h4>
              <div className="prose-editorial">
                <p className="text-[var(--gr-text-secondary)] leading-relaxed whitespace-pre-wrap">
                  {project.abstract}
                </p>
              </div>
            </div>
          )}

          {/* Terms/Keywords */}
          {project.terms && (
            <div>
              <h4 className="font-display font-semibold text-[var(--gr-text-primary)] mb-3">
                Keywords
              </h4>
              <div className="flex flex-wrap gap-2">
                {project.terms.split(';').map((term, i) => (
                  <span
                    key={i}
                    className="px-2.5 py-1 text-xs bg-[var(--gr-bg-secondary)] text-[var(--gr-text-secondary)] rounded-full"
                  >
                    {term.trim()}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Link to NIH Reporter */}
          {project.source_url && (
            <div className="pt-4 border-t border-[var(--gr-border-light)]">
              <a
                href={project.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary-editorial inline-flex items-center gap-2"
              >
                View on NIH Reporter
                <ArrowTrendingUpIcon className="h-4 w-4" />
              </a>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

function FilterPanel({
  filters,
  onChange,
  onReset,
}: {
  filters: WinnersFilters;
  onChange: (filters: WinnersFilters) => void;
  onReset: () => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  const currentYear = new Date().getFullYear();
  const yearOptions = Array.from({ length: 10 }, (_, i) => currentYear - i);

  return (
    <div className="card-premium mb-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FunnelIcon className="h-5 w-5 text-[var(--gr-accent-forest)]" />
          <span className="font-display font-semibold text-[var(--gr-text-primary)]">
            Filters
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onReset}
            className="text-sm text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-primary)]"
          >
            Reset
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 hover:bg-[var(--gr-bg-secondary)] rounded-lg"
          >
            {isExpanded ? (
              <ChevronUpIcon className="h-5 w-5" />
            ) : (
              <ChevronDownIcon className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>

      {isExpanded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="mt-4 pt-4 border-t border-[var(--gr-border-light)] grid gap-4 md:grid-cols-2 lg:grid-cols-3"
        >
          {/* Activity Codes */}
          <div>
            <label className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
              Activity Code
            </label>
            <select
              value={filters.activityCodes[0] || ''}
              onChange={(e) =>
                onChange({
                  ...filters,
                  activityCodes: e.target.value ? [e.target.value] : [],
                })
              }
              className="input-editorial w-full"
            >
              <option value="">All Mechanisms</option>
              {ACTIVITY_CODES.map((code) => (
                <option key={code.value} value={code.value}>
                  {code.label}
                </option>
              ))}
            </select>
          </div>

          {/* Institute */}
          <div>
            <label className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
              NIH Institute
            </label>
            <select
              value={filters.institute}
              onChange={(e) => onChange({ ...filters, institute: e.target.value })}
              className="input-editorial w-full"
            >
              <option value="">All Institutes</option>
              {NIH_INSTITUTES.map((inst) => (
                <option key={inst.value} value={inst.value}>
                  {inst.label}
                </option>
              ))}
            </select>
          </div>

          {/* Fiscal Year */}
          <div>
            <label className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
              Fiscal Year
            </label>
            <select
              value={filters.fiscalYears[0] || ''}
              onChange={(e) =>
                onChange({
                  ...filters,
                  fiscalYears: e.target.value ? [parseInt(e.target.value)] : [],
                })
              }
              className="input-editorial w-full"
            >
              <option value="">All Years</option>
              {yearOptions.map((year) => (
                <option key={year} value={year}>
                  FY {year}
                </option>
              ))}
            </select>
          </div>

          {/* Institution */}
          <div>
            <label className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
              Institution
            </label>
            <input
              type="text"
              value={filters.institution}
              onChange={(e) => onChange({ ...filters, institution: e.target.value })}
              placeholder="Search by institution..."
              className="input-editorial w-full"
            />
          </div>

          {/* PI Name */}
          <div>
            <label className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
              PI Name
            </label>
            <input
              type="text"
              value={filters.piName}
              onChange={(e) => onChange({ ...filters, piName: e.target.value })}
              placeholder="Search by PI name..."
              className="input-editorial w-full"
            />
          </div>

          {/* State */}
          <div>
            <label className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
              State
            </label>
            <input
              type="text"
              value={filters.state}
              onChange={(e) => onChange({ ...filters, state: e.target.value })}
              placeholder="e.g., CA, NY..."
              maxLength={2}
              className="input-editorial w-full"
            />
          </div>
        </motion.div>
      )}
    </div>
  );
}

function AggregationCards({ data }: { data?: WinnersSearchResponse }) {
  if (!data?.aggregations) return null;

  const { by_year, by_mechanism, by_institute } = data.aggregations;

  return (
    <div className="grid md:grid-cols-3 gap-4 mb-6">
      {/* Top Mechanisms */}
      <div className="card-premium-subtle">
        <h4 className="font-display font-semibold text-[var(--gr-text-primary)] mb-3 flex items-center gap-2">
          <BeakerIcon className="h-4 w-4 text-[var(--gr-accent-forest)]" />
          Top Mechanisms
        </h4>
        <div className="space-y-2">
          {by_mechanism.slice(0, 5).map((m) => (
            <div key={m.code} className="flex items-center justify-between text-sm">
              <span className="badge-mechanism">{m.code}</span>
              <span className="text-[var(--gr-text-tertiary)]">
                {m.count.toLocaleString()} projects
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Top Institutes */}
      <div className="card-premium-subtle">
        <h4 className="font-display font-semibold text-[var(--gr-text-primary)] mb-3 flex items-center gap-2">
          <AcademicCapIcon className="h-4 w-4 text-[var(--gr-blue-500)]" />
          Top Institutes
        </h4>
        <div className="space-y-2">
          {by_institute.slice(0, 5).map((i) => (
            <div key={i.abbreviation} className="flex items-center justify-between text-sm">
              <span className="text-[var(--gr-text-secondary)]">{i.abbreviation}</span>
              <span className="text-[var(--gr-text-tertiary)]">
                {i.count.toLocaleString()} projects
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Years */}
      <div className="card-premium-subtle">
        <h4 className="font-display font-semibold text-[var(--gr-text-primary)] mb-3 flex items-center gap-2">
          <ChartBarIcon className="h-4 w-4 text-[var(--gr-accent-gold)]" />
          By Year
        </h4>
        <div className="space-y-2">
          {by_year.slice(0, 5).map((y) => (
            <div key={y.year} className="flex items-center justify-between text-sm">
              <span className="text-[var(--gr-text-secondary)]">FY {y.year}</span>
              <span className="text-[var(--gr-text-tertiary)]">
                {formatCurrency(y.total_funding)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function Winners() {
  const [filters, setFilters] = useState<WinnersFilters>(defaultWinnersFilters);
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProject, setSelectedProject] = useState<FundedProject | null>(null);

  // Build search params
  const searchParams = useMemo(() => ({
    query: searchQuery || undefined,
    activity_codes: filters.activityCodes.length > 0 ? filters.activityCodes.join(',') : undefined,
    institute: filters.institute || undefined,
    fiscal_years: filters.fiscalYears.length > 0 ? filters.fiscalYears.join(',') : undefined,
    institution: filters.institution || undefined,
    pi_name: filters.piName || undefined,
    state: filters.state || undefined,
    min_amount: filters.minAmount || undefined,
    max_amount: filters.maxAmount || undefined,
    page,
    limit: 20,
  }), [filters, searchQuery, page]);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['winners-search', searchParams],
    queryFn: () => winnersApi.search(searchParams),
    staleTime: 5 * 60 * 1000,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    refetch();
  };

  const handleResetFilters = () => {
    setFilters(defaultWinnersFilters);
    setSearchQuery('');
    setPage(1);
  };

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      {/* Header */}
      <div className="page-header-editorial">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-3 mb-2"
          >
            <div className="p-2.5 bg-[var(--gr-accent-forest)]/10 rounded-xl">
              <SparklesIcon className="h-6 w-6 text-[var(--gr-accent-forest)]" />
            </div>
            <h1 className="text-3xl font-display font-bold text-[var(--gr-text-primary)]">
              Past Winners Intelligence
            </h1>
          </motion.div>
          <p className="text-lg text-[var(--gr-text-secondary)] max-w-2xl">
            Explore 2.6M+ funded NIH projects. Analyze successful grants, identify patterns,
            and learn from winning proposals.
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search Bar */}
        <form onSubmit={handleSearch} className="mb-6">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-[var(--gr-text-tertiary)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search funded projects by keywords, topics, or research areas..."
              className="input-editorial w-full pl-12 pr-32 h-14 text-lg"
            />
            <button
              type="submit"
              className="absolute right-2 top-1/2 -translate-y-1/2 btn-primary-editorial"
            >
              Search
            </button>
          </div>
        </form>

        {/* Filters */}
        <FilterPanel
          filters={filters}
          onChange={(f) => {
            setFilters(f);
            setPage(1);
          }}
          onReset={handleResetFilters}
        />

        {/* Aggregations */}
        {data && !isLoading && <AggregationCards data={data} />}

        {/* Results Count */}
        {data && (
          <div className="flex items-center justify-between mb-4">
            <p className="text-[var(--gr-text-secondary)]">
              <span className="font-semibold text-[var(--gr-text-primary)]">
                {data.total.toLocaleString()}
              </span>{' '}
              funded projects found
            </p>
            <p className="text-sm text-[var(--gr-text-tertiary)]">
              Page {data.page} of {data.pages}
            </p>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="grid md:grid-cols-2 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="card-premium animate-pulse">
                <div className="h-6 bg-[var(--gr-bg-secondary)] rounded w-3/4 mb-3" />
                <div className="h-4 bg-[var(--gr-bg-secondary)] rounded w-1/2 mb-4" />
                <div className="h-16 bg-[var(--gr-bg-secondary)] rounded mb-4" />
                <div className="h-4 bg-[var(--gr-bg-secondary)] rounded w-1/3" />
              </div>
            ))}
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="text-center py-12">
            <p className="text-[var(--gr-text-tertiary)]">
              Failed to load projects. Please try again.
            </p>
            <button
              onClick={() => refetch()}
              className="mt-4 btn-secondary-editorial"
            >
              Retry
            </button>
          </div>
        )}

        {/* Results Grid */}
        {data && !isLoading && (
          <>
            <div className="grid md:grid-cols-2 gap-4">
              {data.results.map((project) => (
                <WinnerCard
                  key={project.project_num}
                  project={project}
                  onClick={() => setSelectedProject(project)}
                />
              ))}
            </div>

            {/* Empty State */}
            {data.results.length === 0 && (
              <div className="text-center py-16">
                <AcademicCapIcon className="h-12 w-12 text-[var(--gr-text-muted)] mx-auto mb-4" />
                <h3 className="text-lg font-display font-semibold text-[var(--gr-text-primary)] mb-2">
                  No projects found
                </h3>
                <p className="text-[var(--gr-text-tertiary)]">
                  Try adjusting your search or filters
                </p>
              </div>
            )}

            {/* Pagination */}
            {data.pages > 1 && (
              <div className="flex justify-center items-center gap-2 mt-8">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="btn-secondary-editorial disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="px-4 text-[var(--gr-text-secondary)]">
                  Page {page} of {data.pages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                  disabled={page === data.pages}
                  className="btn-secondary-editorial disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Project Detail Modal */}
      {selectedProject && (
        <ProjectModal
          project={selectedProject}
          onClose={() => setSelectedProject(null)}
        />
      )}
    </div>
  );
}
