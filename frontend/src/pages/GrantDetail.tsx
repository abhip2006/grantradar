import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeftIcon,
  CalendarIcon,
  CurrencyDollarIcon,
  BuildingLibraryIcon,
  GlobeAltIcon,
  BookmarkIcon,
  XMarkIcon,
  CheckCircleIcon,
  ClipboardDocumentListIcon,
  ArrowTopRightOnSquareIcon,
  RocketLaunchIcon,
  ClockIcon,
  TagIcon,
  SparklesIcon,
  DocumentTextIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';
import { BookmarkIcon as BookmarkSolidIcon, RocketLaunchIcon as RocketLaunchSolidIcon, StarIcon } from '@heroicons/react/24/solid';
import { grantsApi, pipelineApi } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { MatchScore } from '../components/MatchScore';
import { CalendarSync } from '../components/CalendarSync';
import { SimilarGrants } from '../components/SimilarGrants';
import { StageBadge } from '../components/PipelineCard';
import { GrantInsights } from '../components/GrantInsights';
import { OutcomeTracker } from '../components/OutcomeTracker';

export function GrantDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  // Fetch grant match details
  const { data: match, isLoading, error } = useQuery({
    queryKey: ['grant-match', id],
    queryFn: () => grantsApi.getMatch(id!),
    enabled: !!id,
  });

  // Check if grant is in pipeline
  const { data: pipelineItem, refetch: refetchPipeline } = useQuery({
    queryKey: ['pipeline-item', match?.grant_id],
    queryFn: () => pipelineApi.getByGrantId(match!.grant_id),
    enabled: !!match?.grant_id,
  });

  // Add to pipeline mutation
  const addToPipelineMutation = useMutation({
    mutationFn: () =>
      pipelineApi.addToPipeline({
        grant_id: match!.grant_id,
        match_id: match!.id,
        stage: 'researching',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline'] });
      queryClient.invalidateQueries({ queryKey: ['pipeline-item', match?.grant_id] });
      refetchPipeline();
      showToast('Added to pipeline', 'success');
    },
    onError: () => {
      showToast('Failed to add to pipeline', 'error');
    },
  });

  // Update status mutation
  const updateStatusMutation = useMutation({
    mutationFn: (status: 'saved' | 'dismissed' | 'applied') =>
      grantsApi.updateMatchStatus(id!, status),
    onSuccess: (updatedMatch) => {
      queryClient.setQueryData(['grant-match', id], updatedMatch);
      const message =
        updatedMatch.status === 'saved'
          ? 'Grant saved!'
          : updatedMatch.status === 'applied'
          ? 'Marked as applied'
          : 'Grant dismissed';
      showToast(message, 'success');
    },
  });

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const getDaysUntilDeadline = (dateString: string) => {
    const deadline = new Date(dateString);
    const today = new Date();
    const diffTime = deadline.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const getSourceInfo = (source: string) => {
    switch (source) {
      case 'federal':
        return { label: 'Federal Grant', color: 'text-blue-600 bg-blue-50 border-blue-200', icon: '🏛️' };
      case 'foundation':
        return { label: 'Foundation', color: 'text-emerald-600 bg-emerald-50 border-emerald-200', icon: '🏢' };
      case 'state':
        return { label: 'State Grant', color: 'text-amber-600 bg-amber-50 border-amber-200', icon: '🗺️' };
      case 'corporate':
        return { label: 'Corporate', color: 'text-slate-600 bg-slate-50 border-slate-200', icon: '💼' };
      default:
        return { label: source, color: 'text-slate-600 bg-slate-50 border-slate-200', icon: '📋' };
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[var(--gr-bg-secondary)]">
        <div className="max-w-6xl mx-auto px-6 py-8">
          {/* Back button skeleton */}
          <div className="skeleton h-10 w-24 mb-8 rounded-lg" />

          {/* Hero skeleton */}
          <div className="bg-white rounded-2xl border border-[var(--gr-border-default)] p-8 mb-6">
            <div className="skeleton h-6 w-32 mb-4 rounded-full" />
            <div className="skeleton h-12 w-3/4 mb-4" />
            <div className="skeleton h-6 w-1/3 mb-6" />
            <div className="flex gap-4">
              <div className="skeleton h-20 w-40 rounded-xl" />
              <div className="skeleton h-20 w-40 rounded-xl" />
              <div className="skeleton h-20 w-40 rounded-xl" />
            </div>
          </div>

          {/* Content skeleton */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <div className="bg-white rounded-2xl border border-[var(--gr-border-default)] p-6">
                <div className="skeleton h-6 w-32 mb-4" />
                <div className="skeleton h-32 w-full" />
              </div>
            </div>
            <div className="space-y-6">
              <div className="skeleton h-48 w-full rounded-2xl" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !match) {
    return (
      <div className="min-h-screen bg-[var(--gr-bg-secondary)] flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-6">
          <div className="w-20 h-20 mx-auto rounded-2xl bg-[var(--gr-gray-100)] flex items-center justify-center mb-6">
            <XMarkIcon className="w-10 h-10 text-[var(--gr-text-tertiary)]" />
          </div>
          <h2 className="text-2xl font-display font-medium text-[var(--gr-text-primary)] mb-3">
            Grant not found
          </h2>
          <p className="text-[var(--gr-text-secondary)] mb-8">
            This grant may have been removed or is no longer available.
          </p>
          <Link to="/dashboard" className="btn-primary inline-flex items-center gap-2">
            <ArrowLeftIcon className="h-4 w-4" />
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const { grant, score, reasoning, status } = match;
  const isSaved = status === 'saved';
  const isApplied = status === 'applied';
  const sourceInfo = getSourceInfo(grant.source);
  const daysUntilDeadline = grant.deadline ? getDaysUntilDeadline(grant.deadline) : null;

  return (
    <div className="min-h-screen bg-[var(--gr-bg-secondary)]">
      {/* Subtle background pattern */}
      <div className="absolute inset-0 bg-mesh pointer-events-none opacity-50" />

      <div className="relative max-w-6xl mx-auto px-6 py-8">
        {/* Back navigation */}
        <button
          onClick={() => navigate(-1)}
          className="group inline-flex items-center gap-2 px-4 py-2 rounded-xl text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] hover:bg-white/80 transition-all duration-200 mb-8 animate-fade-in-up"
        >
          <ArrowLeftIcon className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
          <span className="font-medium">Back to grants</span>
        </button>

        {/* Hero Section */}
        <div className="bg-white rounded-2xl border border-[var(--gr-border-default)] shadow-sm overflow-hidden mb-6 animate-fade-in-up stagger-1">
          {/* Gradient accent bar */}
          <div className="h-1.5 bg-gradient-to-r from-blue-500 via-blue-400 to-emerald-400" />

          <div className="p-8">
            {/* Header row */}
            <div className="flex flex-wrap items-start justify-between gap-6 mb-6">
              <div className="flex-1 min-w-0">
                {/* Source badge & status */}
                <div className="flex flex-wrap items-center gap-2 mb-4">
                  <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold border ${sourceInfo.color}`}>
                    <span>{sourceInfo.icon}</span>
                    {sourceInfo.label}
                  </span>
                  {isSaved && (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold bg-emerald-50 text-emerald-600 border border-emerald-200">
                      <BookmarkSolidIcon className="w-3.5 h-3.5" />
                      Saved
                    </span>
                  )}
                  {isApplied && (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold bg-blue-50 text-blue-600 border border-blue-200">
                      <CheckCircleIcon className="w-3.5 h-3.5" />
                      Applied
                    </span>
                  )}
                </div>

                {/* Title */}
                <h1 className="text-3xl lg:text-4xl font-display font-medium text-[var(--gr-text-primary)] leading-tight mb-4 text-balance">
                  {grant.title}
                </h1>

                {/* Funder */}
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[var(--gr-gray-100)] flex items-center justify-center">
                    <BuildingLibraryIcon className="h-5 w-5 text-[var(--gr-text-tertiary)]" />
                  </div>
                  <div>
                    <p className="text-xs text-[var(--gr-text-tertiary)] uppercase tracking-wider font-medium">Funder</p>
                    <p className="text-lg font-medium text-[var(--gr-text-primary)]">{grant.funder_name}</p>
                  </div>
                </div>
              </div>

              {/* Match Score */}
              <div className="flex-shrink-0">
                <MatchScore score={score} reasoning={reasoning} size="lg" />
              </div>
            </div>

            {/* Key metrics row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Funding Amount */}
              {(grant.funding_amount_min || grant.funding_amount_max) && (
                <div className="group relative bg-gradient-to-br from-amber-50 to-amber-50/50 rounded-xl p-4 border border-amber-100 hover:border-amber-200 transition-colors">
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-amber-100">
                      <CurrencyDollarIcon className="h-5 w-5 text-amber-600" />
                    </div>
                    <div>
                      <p className="text-xs text-amber-600/80 uppercase tracking-wider font-semibold mb-1">
                        Funding
                      </p>
                      <p className="text-lg font-bold text-amber-900">
                        {grant.funding_amount_min && grant.funding_amount_max
                          ? `${formatCurrency(grant.funding_amount_min)} - ${formatCurrency(grant.funding_amount_max)}`
                          : grant.funding_amount_max
                          ? `Up to ${formatCurrency(grant.funding_amount_max)}`
                          : formatCurrency(grant.funding_amount_min!)}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Deadline */}
              {grant.deadline && (
                <div className={`group relative rounded-xl p-4 border transition-colors ${
                  daysUntilDeadline !== null && daysUntilDeadline <= 14
                    ? 'bg-gradient-to-br from-red-50 to-red-50/50 border-red-100 hover:border-red-200'
                    : daysUntilDeadline !== null && daysUntilDeadline <= 30
                    ? 'bg-gradient-to-br from-orange-50 to-orange-50/50 border-orange-100 hover:border-orange-200'
                    : 'bg-gradient-to-br from-blue-50 to-blue-50/50 border-blue-100 hover:border-blue-200'
                }`}>
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-lg ${
                      daysUntilDeadline !== null && daysUntilDeadline <= 14
                        ? 'bg-red-100'
                        : daysUntilDeadline !== null && daysUntilDeadline <= 30
                        ? 'bg-orange-100'
                        : 'bg-blue-100'
                    }`}>
                      <CalendarIcon className={`h-5 w-5 ${
                        daysUntilDeadline !== null && daysUntilDeadline <= 14
                          ? 'text-red-600'
                          : daysUntilDeadline !== null && daysUntilDeadline <= 30
                          ? 'text-orange-600'
                          : 'text-blue-600'
                      }`} />
                    </div>
                    <div>
                      <p className={`text-xs uppercase tracking-wider font-semibold mb-1 ${
                        daysUntilDeadline !== null && daysUntilDeadline <= 14
                          ? 'text-red-600/80'
                          : daysUntilDeadline !== null && daysUntilDeadline <= 30
                          ? 'text-orange-600/80'
                          : 'text-blue-600/80'
                      }`}>
                        Deadline
                      </p>
                      <p className={`text-lg font-bold ${
                        daysUntilDeadline !== null && daysUntilDeadline <= 14
                          ? 'text-red-900'
                          : daysUntilDeadline !== null && daysUntilDeadline <= 30
                          ? 'text-orange-900'
                          : 'text-blue-900'
                      }`}>
                        {new Date(grant.deadline).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </p>
                      {daysUntilDeadline !== null && (
                        <p className={`text-xs mt-1 font-medium ${
                          daysUntilDeadline <= 14
                            ? 'text-red-600'
                            : daysUntilDeadline <= 30
                            ? 'text-orange-600'
                            : 'text-blue-600'
                        }`}>
                          {daysUntilDeadline > 0 ? `${daysUntilDeadline} days remaining` : daysUntilDeadline === 0 ? 'Due today!' : 'Past deadline'}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Source URL */}
              {grant.url && (
                <div className="group relative bg-gradient-to-br from-emerald-50 to-emerald-50/50 rounded-xl p-4 border border-emerald-100 hover:border-emerald-200 transition-colors">
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-emerald-100">
                      <GlobeAltIcon className="h-5 w-5 text-emerald-600" />
                    </div>
                    <div>
                      <p className="text-xs text-emerald-600/80 uppercase tracking-wider font-semibold mb-1">
                        Source
                      </p>
                      <a
                        href={grant.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-lg font-bold text-emerald-700 hover:text-emerald-800 inline-flex items-center gap-1.5 transition-colors"
                      >
                        View Original
                        <ArrowTopRightOnSquareIcon className="h-4 w-4" />
                      </a>
                    </div>
                  </div>
                </div>
              )}

              {/* Calendar Sync */}
              {grant.deadline && (
                <div className="group relative bg-gradient-to-br from-violet-50 to-violet-50/50 rounded-xl p-4 border border-violet-100 hover:border-violet-200 transition-colors">
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-violet-100">
                      <ClockIcon className="h-5 w-5 text-violet-600" />
                    </div>
                    <div>
                      <p className="text-xs text-violet-600/80 uppercase tracking-wider font-semibold mb-2">
                        Calendar
                      </p>
                      <CalendarSync
                        grantId={grant.id}
                        grantTitle={grant.title}
                        hasDeadline={true}
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Description */}
            <section className="bg-white rounded-2xl border border-[var(--gr-border-default)] shadow-sm overflow-hidden animate-fade-in-up stagger-2">
              <div className="p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 rounded-lg bg-[var(--gr-gray-100)]">
                    <DocumentTextIcon className="h-5 w-5 text-[var(--gr-text-tertiary)]" />
                  </div>
                  <h2 className="text-xl font-display font-medium text-[var(--gr-text-primary)]">
                    About This Grant
                  </h2>
                </div>
                <div className="prose prose-slate max-w-none">
                  <p className="text-[var(--gr-text-secondary)] whitespace-pre-wrap leading-relaxed text-[15px]">
                    {grant.description}
                  </p>
                </div>
              </div>
            </section>

            {/* Eligibility */}
            {grant.eligibility && Object.keys(grant.eligibility).length > 0 && (
              <section className="bg-white rounded-2xl border border-[var(--gr-border-default)] shadow-sm overflow-hidden animate-fade-in-up stagger-3">
                <div className="p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 rounded-lg bg-emerald-50">
                      <ShieldCheckIcon className="h-5 w-5 text-emerald-600" />
                    </div>
                    <h2 className="text-xl font-display font-medium text-[var(--gr-text-primary)]">
                      Eligibility Requirements
                    </h2>
                  </div>
                  <div className="grid gap-3">
                    {Object.entries(grant.eligibility).map(([key, value], index) => (
                      <div
                        key={index}
                        className="flex items-start gap-3 p-3 rounded-xl bg-[var(--gr-gray-50)] border border-[var(--gr-border-subtle)]"
                      >
                        <CheckCircleIcon className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold text-[var(--gr-text-primary)] capitalize">
                            {key.replace(/_/g, ' ')}
                          </span>
                          <span className="text-[var(--gr-text-secondary)]">: {String(value)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            )}

            {/* Focus Areas */}
            {grant.focus_areas && grant.focus_areas.length > 0 && (
              <section className="bg-white rounded-2xl border border-[var(--gr-border-default)] shadow-sm overflow-hidden animate-fade-in-up stagger-4">
                <div className="p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 rounded-lg bg-amber-50">
                      <TagIcon className="h-5 w-5 text-amber-600" />
                    </div>
                    <h2 className="text-xl font-display font-medium text-[var(--gr-text-primary)]">
                      Focus Areas
                    </h2>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {grant.focus_areas.map((area) => (
                      <span
                        key={area}
                        className="inline-flex items-center px-4 py-2 rounded-full text-sm font-medium bg-gradient-to-r from-amber-50 to-yellow-50 text-amber-800 border border-amber-200 capitalize"
                      >
                        {area}
                      </span>
                    ))}
                  </div>
                </div>
              </section>
            )}

            {/* Match Reasoning */}
            {reasoning && (
              <section className="bg-gradient-to-br from-blue-50 via-blue-50/80 to-indigo-50 rounded-2xl border border-blue-100 shadow-sm overflow-hidden animate-fade-in-up stagger-5">
                <div className="p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 rounded-lg bg-blue-100">
                      <SparklesIcon className="h-5 w-5 text-blue-600" />
                    </div>
                    <h2 className="text-xl font-display font-medium text-blue-900">
                      Why This Matches Your Profile
                    </h2>
                  </div>
                  <p className="text-blue-800/90 leading-relaxed text-[15px]">{reasoning}</p>
                </div>
              </section>
            )}

            {/* AI Grant Insights */}
            <div className="animate-fade-in-up stagger-6">
              <GrantInsights
                grantId={grant.id}
                grantTitle={grant.title}
                funderName={grant.agency}
              />
            </div>
          </div>

          {/* Right Column - Actions & Sidebar */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <section className="bg-white rounded-2xl border border-[var(--gr-border-default)] shadow-sm overflow-hidden animate-fade-in-up stagger-2">
              <div className="p-6">
                <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-4">
                  Quick Actions
                </h3>
                <div className="space-y-3">
                  {/* Save button */}
                  <button
                    onClick={() => updateStatusMutation.mutate(isSaved ? 'dismissed' : 'saved')}
                    disabled={updateStatusMutation.isPending}
                    className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-all duration-200 ${
                      isSaved
                        ? 'bg-emerald-50 text-emerald-700 border-2 border-emerald-200 hover:bg-emerald-100'
                        : 'bg-[var(--gr-gray-50)] text-[var(--gr-text-primary)] border border-[var(--gr-border-default)] hover:bg-[var(--gr-gray-100)] hover:border-[var(--gr-border-strong)]'
                    }`}
                  >
                    {isSaved ? (
                      <>
                        <BookmarkSolidIcon className="h-5 w-5" />
                        Saved to Library
                      </>
                    ) : (
                      <>
                        <BookmarkIcon className="h-5 w-5" />
                        Save Grant
                      </>
                    )}
                  </button>

                  {/* Mark as Applied */}
                  <button
                    onClick={() => updateStatusMutation.mutate('applied')}
                    disabled={updateStatusMutation.isPending || isApplied}
                    className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-all duration-200 ${
                      isApplied
                        ? 'bg-blue-50 text-blue-700 border-2 border-blue-200'
                        : 'bg-blue-600 text-white hover:bg-blue-700'
                    }`}
                  >
                    <ClipboardDocumentListIcon className="h-5 w-5" />
                    {isApplied ? 'Application Submitted' : 'Mark as Applied'}
                  </button>

                  {/* Track in Pipeline */}
                  {pipelineItem ? (
                    <div className="flex items-center justify-between p-4 rounded-xl bg-cyan-50 border border-cyan-200">
                      <div className="flex items-center gap-2">
                        <RocketLaunchSolidIcon className="h-5 w-5 text-cyan-600" />
                        <span className="text-sm font-medium text-cyan-800">Tracking</span>
                      </div>
                      <StageBadge stage={pipelineItem.stage} />
                    </div>
                  ) : (
                    <button
                      onClick={() => addToPipelineMutation.mutate()}
                      disabled={addToPipelineMutation.isPending}
                      className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium bg-[var(--gr-gray-50)] text-[var(--gr-text-primary)] border border-[var(--gr-border-default)] hover:bg-[var(--gr-gray-100)] hover:border-[var(--gr-border-strong)] transition-all duration-200"
                    >
                      <RocketLaunchIcon className="h-5 w-5" />
                      Track Application
                    </button>
                  )}

                  {/* Dismiss */}
                  {!isSaved && !isApplied && (
                    <button
                      onClick={() => updateStatusMutation.mutate('dismissed')}
                      disabled={updateStatusMutation.isPending}
                      className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium text-[var(--gr-text-tertiary)] hover:text-red-600 hover:bg-red-50 border border-transparent hover:border-red-200 transition-all duration-200"
                    >
                      <XMarkIcon className="h-5 w-5" />
                      Not Interested
                    </button>
                  )}
                </div>
              </div>
            </section>

            {/* Apply Button */}
            {grant.url && (
              <a
                href={grant.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full animate-fade-in-up stagger-3"
              >
                <div className="relative group bg-gradient-to-r from-blue-600 to-blue-500 rounded-2xl p-6 text-white overflow-hidden shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
                  {/* Decorative elements */}
                  <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2" />
                  <div className="absolute bottom-0 left-0 w-24 h-24 bg-white/5 rounded-full translate-y-1/2 -translate-x-1/2" />

                  <div className="relative flex items-center justify-between">
                    <div>
                      <p className="text-blue-100 text-sm font-medium mb-1">Ready to apply?</p>
                      <p className="text-xl font-display font-semibold">Apply Now</p>
                    </div>
                    <div className="p-3 bg-white/20 rounded-xl group-hover:bg-white/30 transition-colors">
                      <ArrowTopRightOnSquareIcon className="h-6 w-6" />
                    </div>
                  </div>
                </div>
              </a>
            )}

            {/* Match Score Card */}
            <section className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-2xl border border-slate-200 overflow-hidden animate-fade-in-up stagger-4">
              <div className="p-6 text-center">
                <div className="flex justify-center mb-3">
                  <div className="flex">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <StarIcon
                        key={star}
                        className={`h-5 w-5 ${
                          star <= Math.round(score / 20) ? 'text-amber-400' : 'text-slate-200'
                        }`}
                      />
                    ))}
                  </div>
                </div>
                <p className="text-4xl font-display font-bold text-[var(--gr-text-primary)] mb-1">
                  {score}%
                </p>
                <p className="text-sm text-[var(--gr-text-secondary)]">Match Score</p>
              </div>
            </section>

            {/* Outcome Tracker - Show for saved or applied grants */}
            {(isSaved || isApplied) && (
              <div className="animate-fade-in-up stagger-5">
                <OutcomeTracker
                  matchId={match.id}
                  initialStatus={isApplied ? 'submitted' : 'not_applied'}
                />
              </div>
            )}
          </div>
        </div>

        {/* Similar Grants */}
        {grant.id && (
          <div className="mt-8 animate-fade-in-up stagger-7">
            <SimilarGrants grantId={grant.id} limit={6} />
          </div>
        )}
      </div>
    </div>
  );
}

export default GrantDetail;
