import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useInfiniteQuery, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Tab, TabGroup, TabList } from '@headlessui/react';
import {
  MagnifyingGlassIcon,
  BookmarkIcon,
  ClockIcon,
  SparklesIcon,
  ArrowTrendingUpIcon,
  FunnelIcon,
  QuestionMarkCircleIcon,
} from '@heroicons/react/24/outline';
import { BookmarkIcon as BookmarkSolidIcon } from '@heroicons/react/24/solid';
import { grantsApi } from '../services/api';
import { socketService } from '../services/socket';
import { useToast } from '../contexts/ToastContext';
import { GrantCard } from '../components/GrantCard';
import { WelcomeModal } from '../components/WelcomeModal';
import { SavedSearches } from '../components/SavedSearches';
import { CompareBar } from '../components/CompareBar';
import AdvancedFilters from '../components/AdvancedFilters';
import type { GrantMatch, GrantSource, DashboardStats, SavedSearchFilters, AdvancedGrantFilters } from '../types';

/* ═══════════════════════════════════════════════════════════════════════════
   GRANTRADAR DASHBOARD
   Aesthetic: Sophisticated Dark Intelligence Theme
   ═══════════════════════════════════════════════════════════════════════════ */

const sourceFilters: { name: string; value: GrantSource | 'all' }[] = [
  { name: 'All', value: 'all' },
  { name: 'Federal', value: 'federal' },
  { name: 'Foundation', value: 'foundation' },
  { name: 'State', value: 'state' },
];

// Stat Card Component
function StatCard({
  icon: Icon,
  label,
  value,
  trend,
  color,
  delay,
}: {
  icon: React.ElementType;
  label: string;
  value: number | string;
  trend?: string;
  color: 'amber' | 'emerald' | 'cyan' | 'slate';
  delay: number;
}) {
  const colorClasses = {
    amber: {
      bg: 'bg-[var(--gr-blue-600)]/10',
      icon: 'text-[var(--gr-blue-600)]',
      glow: 'stat-card-blue',
    },
    emerald: {
      bg: 'bg-[var(--gr-emerald-500)]/10',
      icon: 'text-[var(--gr-emerald-400)]',
      glow: 'stat-card-emerald',
    },
    cyan: {
      bg: 'bg-[var(--gr-cyan-500)]/10',
      icon: 'text-[var(--gr-cyan-400)]',
      glow: 'stat-card-cyan',
    },
    slate: {
      bg: 'bg-[var(--gr-slate-600)]/30',
      icon: 'text-[var(--gr-text-secondary)]',
      glow: '',
    },
  };

  return (
    <div
      className={`stat-card ${colorClasses[color].glow} animate-fade-in-up`}
      style={{ animationDelay: `${delay * 0.1}s` }}
    >
      <div className="flex items-start justify-between">
        <div className={`w-10 h-10 rounded-xl ${colorClasses[color].bg} flex items-center justify-center`}>
          <Icon className={`w-5 h-5 ${colorClasses[color].icon}`} />
        </div>
        {trend && (
          <span className="flex items-center gap-1 text-xs font-medium text-[var(--gr-emerald-400)]">
            <ArrowTrendingUpIcon className="w-3 h-3" />
            {trend}
          </span>
        )}
      </div>
      <div className="mt-4">
        <div className="text-3xl font-display font-semibold text-[var(--gr-text-primary)]">
          {value}
        </div>
        <div className="mt-1 text-sm text-[var(--gr-text-tertiary)]">{label}</div>
      </div>
    </div>
  );
}

// Stats Bar Component
function StatsBar({ stats, isLoading }: { stats?: DashboardStats; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="stat-card">
            <div className="skeleton w-10 h-10 rounded-xl mb-4" />
            <div className="skeleton h-8 w-16 mb-2" />
            <div className="skeleton h-4 w-24" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        icon={SparklesIcon}
        label="New Matches"
        value={stats?.new_grants ?? 0}
        trend="+12%"
        color="amber"
        delay={1}
      />
      <StatCard
        icon={ArrowTrendingUpIcon}
        label="High Matches (90+)"
        value={stats?.high_matches ?? 0}
        color="emerald"
        delay={2}
      />
      <StatCard
        icon={ClockIcon}
        label="Due This Week"
        value={stats?.upcoming_deadline_count ?? stats?.upcoming_deadlines?.length ?? 0}
        color="cyan"
        delay={3}
      />
      <StatCard
        icon={BookmarkSolidIcon}
        label="Saved Grants"
        value={stats?.saved_grants ?? 0}
        color="slate"
        delay={4}
      />
    </div>
  );
}

// Empty State Component
function EmptyState({ showSavedOnly, searchQuery }: { showSavedOnly: boolean; searchQuery: string }) {
  if (showSavedOnly) {
    return (
      <div className="card text-center py-16">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-[var(--gr-blue-50)] flex items-center justify-center mb-6">
          <BookmarkIcon className="w-8 h-8 text-[var(--gr-blue-500)]" />
        </div>
        <h3 className="text-xl font-display font-medium text-[var(--gr-text-primary)] mb-2">
          No saved grants yet
        </h3>
        <p className="text-[var(--gr-text-secondary)] max-w-sm mx-auto">
          Browse your matches and click the bookmark icon to save grants you're interested in.
        </p>
      </div>
    );
  }

  if (searchQuery) {
    return (
      <div className="card text-center py-16">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-[var(--gr-gray-100)] flex items-center justify-center mb-6">
          <MagnifyingGlassIcon className="w-8 h-8 text-[var(--gr-text-tertiary)]" />
        </div>
        <h3 className="text-xl font-display font-medium text-[var(--gr-text-primary)] mb-2">
          No results for "{searchQuery}"
        </h3>
        <p className="text-[var(--gr-text-secondary)] max-w-sm mx-auto">
          Try adjusting your search terms or filters to find more grants.
        </p>
      </div>
    );
  }

  // Default: First-time user or loading state
  return (
    <div className="card text-center py-16">
      <div className="w-16 h-16 mx-auto rounded-2xl bg-[var(--gr-blue-50)] flex items-center justify-center mb-6">
        <SparklesIcon className="w-8 h-8 text-[var(--gr-blue-500)] animate-pulse" />
      </div>
      <h3 className="text-xl font-display font-medium text-[var(--gr-text-primary)] mb-2">
        Finding Your Matches
      </h3>
      <p className="text-[var(--gr-text-secondary)] max-w-md mx-auto mb-6">
        We're analyzing 86,000+ grants against your profile. This typically takes <strong>2-5 minutes</strong> for first-time users.
      </p>
      <p className="text-sm text-[var(--gr-text-tertiary)]">
        While you wait, try searching for specific keywords above.
      </p>
      <div className="mt-6">
        <Link
          to="/faq"
          className="inline-flex items-center gap-2 text-sm text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-700)]"
        >
          <QuestionMarkCircleIcon className="w-4 h-4" />
          Learn how matching works
        </Link>
      </div>
    </div>
  );
}

// Loading Grid Component
function LoadingGrid() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="grant-card">
          <div className="flex items-start gap-4 mb-4">
            <div className="skeleton w-14 h-14 rounded-full" />
            <div className="flex-1">
              <div className="skeleton h-5 w-3/4 mb-2" />
              <div className="skeleton h-4 w-1/2" />
            </div>
          </div>
          <div className="skeleton h-4 w-full mb-2" />
          <div className="skeleton h-4 w-5/6 mb-4" />
          <div className="flex gap-2">
            <div className="skeleton h-6 w-20 rounded-full" />
            <div className="skeleton h-6 w-24 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSource, setSelectedSource] = useState<GrantSource | 'all'>('all');
  const [showSavedOnly, setShowSavedOnly] = useState(searchParams.get('filter') === 'saved');
  const [showWelcomeModal, setShowWelcomeModal] = useState(false);
  const [minScore, setMinScore] = useState<number | undefined>(undefined);
  const [compareSelection, setCompareSelection] = useState<Array<{ id: string; title: string }>>([]);
  const [advancedFilters, setAdvancedFilters] = useState<AdvancedGrantFilters>({});

  // Build current filters object for saved searches
  const currentFilters: SavedSearchFilters = {
    source: selectedSource !== 'all' ? selectedSource : undefined,
    show_saved_only: showSavedOnly || undefined,
    min_score: minScore,
    search_query: searchQuery || undefined,
  };

  // Handler to apply a saved search's filters
  const handleApplySavedSearch = useCallback((filters: SavedSearchFilters) => {
    if (filters.source) {
      setSelectedSource(filters.source as GrantSource | 'all');
    } else {
      setSelectedSource('all');
    }
    setShowSavedOnly(filters.show_saved_only || false);
    setMinScore(filters.min_score);
    if (filters.search_query) {
      setSearchQuery(filters.search_query);
    } else {
      setSearchQuery('');
    }
  }, []);

  // Check if first-time user and show welcome modal
  useEffect(() => {
    const dismissed = localStorage.getItem('grantradar_welcome_dismissed');
    const hasSeenWelcome = localStorage.getItem('grantradar_welcome_seen');

    if (!dismissed && !hasSeenWelcome) {
      // Small delay to let the page load first
      const timer = setTimeout(() => {
        setShowWelcomeModal(true);
        localStorage.setItem('grantradar_welcome_seen', 'true');
      }, 500);
      return () => clearTimeout(timer);
    }
  }, []);

  // Update URL when filter changes
  useEffect(() => {
    if (showSavedOnly) {
      setSearchParams({ filter: 'saved' });
    } else {
      setSearchParams({});
    }
  }, [showSavedOnly, setSearchParams]);

  // Stats query
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: grantsApi.getDashboardStats,
  });

  // Count active advanced filters
  const advancedFilterCount = [
    advancedFilters.agencies?.length,
    advancedFilters.categories?.length,
    advancedFilters.min_amount || advancedFilters.max_amount,
    advancedFilters.deadline_after || advancedFilters.deadline_before,
  ].filter(Boolean).length;

  // Clear advanced filters handler
  const handleClearAdvancedFilters = useCallback(() => {
    setAdvancedFilters({});
  }, []);

  // Infinite grants query
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading: grantsLoading,
  } = useInfiniteQuery({
    queryKey: ['grants', selectedSource, showSavedOnly, minScore, advancedFilters],
    queryFn: ({ pageParam = 1 }) =>
      grantsApi.getMatches({
        page: pageParam,
        per_page: 12,
        source: selectedSource === 'all' ? undefined : selectedSource,
        status: showSavedOnly ? 'saved' : undefined,
        min_score: minScore,
        advancedFilters: advancedFilterCount > 0 ? advancedFilters : undefined,
      }),
    getNextPageParam: (lastPage) =>
      lastPage.has_more ? lastPage.page + 1 : undefined,
    initialPageParam: 1,
  });

  // Flatten pages into single array
  const matches = data?.pages.flatMap((page) => page.items) ?? [];

  // Filter by search query
  const filteredMatches = searchQuery
    ? matches.filter(
        (match) =>
          match.grant.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          match.grant.funder_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          match.grant.description?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : matches;

  // Save/Dismiss mutations
  const updateStatusMutation = useMutation({
    mutationFn: ({ matchId, status }: { matchId: string; status: 'saved' | 'dismissed' }) =>
      grantsApi.updateMatchStatus(matchId, status),
    onSuccess: (updatedMatch) => {
      queryClient.setQueryData(
        ['grants', selectedSource, showSavedOnly],
        (oldData: typeof data) => {
          if (!oldData) return oldData;
          return {
            ...oldData,
            pages: oldData.pages.map((page) => ({
              ...page,
              items: page.items.map((match: GrantMatch) =>
                match.id === updatedMatch.id ? updatedMatch : match
              ),
            })),
          };
        }
      );
      showToast(
        updatedMatch.status === 'saved' ? 'Grant saved!' : 'Grant dismissed',
        updatedMatch.status === 'saved' ? 'success' : 'info'
      );
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
    },
  });

  const handleSave = useCallback(
    (matchId: string) => {
      const match = matches.find((m) => m.id === matchId);
      const newStatus = match?.status === 'saved' ? 'dismissed' : 'saved';
      updateStatusMutation.mutate({ matchId, status: newStatus as 'saved' | 'dismissed' });
    },
    [matches, updateStatusMutation]
  );

  const handleDismiss = useCallback(
    (matchId: string) => {
      updateStatusMutation.mutate({ matchId, status: 'dismissed' });
    },
    [updateStatusMutation]
  );

  // Comparison handlers
  const handleToggleCompare = useCallback(
    (grantId: string) => {
      setCompareSelection((prev) => {
        const existing = prev.find((g) => g.id === grantId);
        if (existing) {
          return prev.filter((g) => g.id !== grantId);
        }
        if (prev.length >= 4) {
          showToast('You can compare up to 4 grants at a time', 'warning');
          return prev;
        }
        const match = matches.find((m) => m.grant.id === grantId);
        if (match) {
          return [...prev, { id: grantId, title: match.grant.title }];
        }
        return prev;
      });
    },
    [matches, showToast]
  );

  const handleRemoveFromCompare = useCallback((grantId: string) => {
    setCompareSelection((prev) => prev.filter((g) => g.id !== grantId));
  }, []);

  const handleClearCompare = useCallback(() => {
    setCompareSelection([]);
  }, []);

  // WebSocket subscription for real-time updates
  useEffect(() => {
    const unsubscribe = socketService.subscribe<GrantMatch>('new_match', (newMatch) => {
      queryClient.setQueryData(
        ['grants', selectedSource, showSavedOnly],
        (oldData: typeof data) => {
          if (!oldData) return oldData;
          return {
            ...oldData,
            pages: oldData.pages.map((page, index) =>
              index === 0
                ? { ...page, items: [newMatch, ...page.items] }
                : page
            ),
          };
        }
      );
      showToast('New matching grant found!', 'info');
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
    });

    return () => unsubscribe();
  }, [queryClient, selectedSource, showSavedOnly, showToast]);

  // Infinite scroll handler
  useEffect(() => {
    const handleScroll = () => {
      if (
        window.innerHeight + document.documentElement.scrollTop >=
        document.documentElement.offsetHeight - 500
      ) {
        if (hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [fetchNextPage, hasNextPage, isFetchingNextPage]);

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      {/* Welcome Modal for first-time users */}
      <WelcomeModal
        isOpen={showWelcomeModal}
        onClose={() => setShowWelcomeModal(false)}
      />

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8 animate-fade-in-up">
          <h1 className="text-3xl font-display font-medium text-[var(--gr-text-primary)]">
            Grant Dashboard
          </h1>
          <p className="mt-2 text-[var(--gr-text-secondary)]">
            Opportunities matched to your organization's profile
          </p>
        </div>

        {/* Stats Bar */}
        <div className="mb-8">
          <StatsBar stats={stats} isLoading={statsLoading} />
        </div>

        {/* Filters Section */}
        <div className="card p-4 mb-8 animate-fade-in-up stagger-5">
          <div className="flex flex-col lg:flex-row lg:items-center gap-4">
            {/* Search Input */}
            <div className="relative flex-1 max-w-md">
              <MagnifyingGlassIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--gr-text-tertiary)]" />
              <input
                type="text"
                placeholder="Search grants..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input pl-12"
              />
            </div>

            {/* Source Tabs */}
            <TabGroup
              selectedIndex={sourceFilters.findIndex(f => f.value === selectedSource)}
              onChange={(index) => setSelectedSource(sourceFilters[index].value)}
            >
              <TabList className="flex p-1 bg-[var(--gr-bg-card)] rounded-xl border border-[var(--gr-border-subtle)]">
                {sourceFilters.map((filter) => (
                  <Tab
                    key={filter.value}
                    className={({ selected }) =>
                      `px-4 py-2 text-sm font-medium rounded-lg transition-all outline-none ${
                        selected
                          ? 'bg-[var(--gr-blue-600)]/10 text-[var(--gr-blue-600)]'
                          : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)]'
                      }`
                    }
                  >
                    {filter.name}
                  </Tab>
                ))}
              </TabList>
            </TabGroup>

            {/* Saved Toggle */}
            <button
              onClick={() => setShowSavedOnly(!showSavedOnly)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                showSavedOnly
                  ? 'bg-[var(--gr-emerald-500)]/20 text-[var(--gr-emerald-400)] border border-[var(--gr-emerald-500)]/30'
                  : 'bg-[var(--gr-bg-card)] text-[var(--gr-text-secondary)] border border-[var(--gr-border-default)] hover:border-[var(--gr-border-strong)]'
              }`}
            >
              {showSavedOnly ? (
                <BookmarkSolidIcon className="w-4 h-4" />
              ) : (
                <BookmarkIcon className="w-4 h-4" />
              )}
              {showSavedOnly ? 'Showing Saved' : 'Show Saved'}
            </button>
          </div>

          {/* Advanced Filters */}
          <div className="mt-4 pt-4 border-t border-[var(--gr-border-subtle)]">
            <AdvancedFilters
              filters={advancedFilters}
              onFiltersChange={setAdvancedFilters}
              onClear={handleClearAdvancedFilters}
            />
          </div>

          {/* Active Filters Indicator */}
          {(selectedSource !== 'all' || showSavedOnly || searchQuery || minScore || advancedFilterCount > 0) && (
            <div className="flex items-center flex-wrap gap-2 mt-4 pt-4 border-t border-[var(--gr-border-subtle)]">
              <FunnelIcon className="w-4 h-4 text-[var(--gr-text-tertiary)]" />
              <span className="text-sm text-[var(--gr-text-tertiary)]">Active filters:</span>
              {selectedSource !== 'all' && (
                <span className="badge badge-blue">{selectedSource}</span>
              )}
              {showSavedOnly && (
                <span className="badge badge-emerald">Saved Only</span>
              )}
              {minScore && (
                <span className="badge badge-cyan">{minScore}%+ score</span>
              )}
              {searchQuery && (
                <span className="badge badge-slate">"{searchQuery}"</span>
              )}
              {advancedFilterCount > 0 && (
                <span className="badge badge-blue">{advancedFilterCount} advanced filter{advancedFilterCount !== 1 ? 's' : ''}</span>
              )}
              <button
                onClick={() => {
                  setSelectedSource('all');
                  setShowSavedOnly(false);
                  setMinScore(undefined);
                  setSearchQuery('');
                  setAdvancedFilters({});
                }}
                className="text-xs text-[var(--gr-text-tertiary)] hover:text-[var(--gr-danger)] ml-2"
              >
                Clear all
              </button>
            </div>
          )}
        </div>

        {/* Main Content with Saved Searches Sidebar */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Grants Grid - Main Content */}
          <div className="lg:col-span-3">
            {grantsLoading ? (
              <LoadingGrid />
            ) : filteredMatches.length === 0 ? (
              <EmptyState showSavedOnly={showSavedOnly} searchQuery={searchQuery} />
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                  {filteredMatches.map((match, index) => (
                    <GrantCard
                      key={match.id}
                      match={match}
                      onSave={handleSave}
                      onDismiss={handleDismiss}
                      onToggleCompare={handleToggleCompare}
                      isSelectedForCompare={compareSelection.some((g) => g.id === match.grant.id)}
                      compareDisabled={compareSelection.length >= 4}
                      delay={index}
                    />
                  ))}
                </div>

                {/* Loading More Indicator */}
                {isFetchingNextPage && (
                  <div className="flex justify-center py-12">
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-[var(--gr-blue-600)] animate-pulse" />
                      <div className="w-2 h-2 rounded-full bg-[var(--gr-blue-600)] animate-pulse" style={{ animationDelay: '0.2s' }} />
                      <div className="w-2 h-2 rounded-full bg-[var(--gr-blue-600)] animate-pulse" style={{ animationDelay: '0.4s' }} />
                    </div>
                  </div>
                )}

                {/* End of List */}
                {!hasNextPage && filteredMatches.length > 0 && (
                  <div className="text-center py-12 text-[var(--gr-text-tertiary)]">
                    You've seen all {filteredMatches.length} matching grants
                  </div>
                )}
              </>
            )}
          </div>

          {/* Saved Searches Sidebar */}
          <div className="lg:col-span-1 order-first lg:order-last">
            <div className="card p-4 sticky top-24">
              <SavedSearches
                currentFilters={currentFilters}
                onApplySearch={handleApplySavedSearch}
              />
            </div>
          </div>
        </div>
      </main>

      {/* Floating Compare Bar */}
      <CompareBar
        selectedGrants={compareSelection}
        onRemove={handleRemoveFromCompare}
        onClear={handleClearCompare}
      />
    </div>
  );
}

export default Dashboard;
