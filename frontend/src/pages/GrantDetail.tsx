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
} from '@heroicons/react/24/outline';
import { BookmarkIcon as BookmarkSolidIcon } from '@heroicons/react/24/solid';
import { grantsApi } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { MatchScore } from '../components/MatchScore';
import { GrantCard } from '../components/GrantCard';
import { CalendarSync } from '../components/CalendarSync';
import type { GrantMatch } from '../types';

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

  // Similar grants - feature not implemented yet
  const similarGrants = null as GrantMatch[] | null;

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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getSourceBadgeColor = (source: string) => {
    switch (source) {
      case 'federal':
        return 'badge-cyan';
      case 'foundation':
        return 'badge-emerald';
      case 'state':
        return 'badge-amber';
      case 'corporate':
        return 'badge-slate';
      default:
        return 'badge-slate';
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[var(--gr-bg-primary)]">
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="skeleton h-8 w-32 mb-6" />
          <div className="card-elevated space-y-6 p-6">
            <div className="skeleton h-6 w-24" />
            <div className="skeleton h-10 w-full" />
            <div className="skeleton h-5 w-1/2" />
            <div className="skeleton h-32 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !match) {
    return (
      <div className="min-h-screen bg-[var(--gr-bg-primary)] flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-[var(--gr-slate-700)] flex items-center justify-center mb-6">
            <XMarkIcon className="w-8 h-8 text-[var(--gr-text-tertiary)]" />
          </div>
          <h2 className="text-xl font-display font-medium text-[var(--gr-text-primary)] mb-2">Grant not found</h2>
          <p className="text-[var(--gr-text-secondary)] mb-6">
            This grant may have been removed or is no longer available.
          </p>
          <Link to="/dashboard" className="btn-primary">
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

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Back button */}
        <button
          onClick={() => navigate(-1)}
          className="btn-ghost text-[var(--gr-text-secondary)] mb-6 animate-fade-in-up"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          Back
        </button>

        {/* Main content */}
        <div className="card-elevated overflow-hidden animate-fade-in-up stagger-1">
          {/* Header */}
          <div className="p-6 border-b border-[var(--gr-border-subtle)]">
            <div className="flex items-start justify-between gap-6">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-4">
                  <span className={`badge ${getSourceBadgeColor(grant.source)}`}>
                    {grant.source}
                  </span>
                  <span className="badge badge-emerald">
                    Active
                  </span>
                </div>
                <h1 className="text-2xl lg:text-3xl font-display font-medium text-[var(--gr-text-primary)] mb-3">
                  {grant.title}
                </h1>
                <div className="flex items-center gap-2 text-[var(--gr-text-secondary)]">
                  <BuildingLibraryIcon className="h-5 w-5 text-[var(--gr-text-tertiary)]" />
                  <span className="font-medium">{grant.funder_name}</span>
                </div>
              </div>
              <div className="flex-shrink-0">
                <MatchScore score={score} reasoning={reasoning} size="lg" />
              </div>
            </div>
          </div>

          {/* Key details */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 p-6 bg-[var(--gr-bg-card)] border-b border-[var(--gr-border-subtle)]">
            {(grant.funding_amount_min || grant.funding_amount_max) && (
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-[var(--gr-amber-500)]/10">
                  <CurrencyDollarIcon className="h-5 w-5 text-[var(--gr-amber-400)]" />
                </div>
                <div>
                  <p className="text-xs text-[var(--gr-text-tertiary)] uppercase tracking-wider font-medium mb-1">
                    Funding Amount
                  </p>
                  <p className="text-sm font-semibold text-[var(--gr-text-primary)]">
                    {grant.funding_amount_min && grant.funding_amount_max
                      ? `${formatCurrency(grant.funding_amount_min)} - ${formatCurrency(grant.funding_amount_max)}`
                      : grant.funding_amount_max
                      ? `Up to ${formatCurrency(grant.funding_amount_max)}`
                      : formatCurrency(grant.funding_amount_min!)}
                  </p>
                </div>
              </div>
            )}
            {grant.deadline && (
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-[var(--gr-cyan-500)]/10">
                  <CalendarIcon className="h-5 w-5 text-[var(--gr-cyan-400)]" />
                </div>
                <div>
                  <p className="text-xs text-[var(--gr-text-tertiary)] uppercase tracking-wider font-medium mb-1">
                    Deadline
                  </p>
                  <p className="text-sm font-semibold text-[var(--gr-text-primary)] mb-2">
                    {formatDate(grant.deadline)}
                  </p>
                  <CalendarSync
                    grantId={grant.id}
                    grantTitle={grant.title}
                    hasDeadline={true}
                  />
                </div>
              </div>
            )}
            {grant.url && (
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-[var(--gr-emerald-500)]/10">
                  <GlobeAltIcon className="h-5 w-5 text-[var(--gr-emerald-400)]" />
                </div>
                <div>
                  <p className="text-xs text-[var(--gr-text-tertiary)] uppercase tracking-wider font-medium mb-1">
                    Source
                  </p>
                  <a
                    href={grant.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-semibold text-[var(--gr-amber-400)] hover:text-[var(--gr-amber-300)] flex items-center gap-1"
                  >
                    View Original
                    <ArrowTopRightOnSquareIcon className="h-3 w-3" />
                  </a>
                </div>
              </div>
            )}
          </div>

          {/* Description */}
          <div className="p-6 border-b border-[var(--gr-border-subtle)]">
            <h2 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-4">
              Description
            </h2>
            <p className="text-[var(--gr-text-secondary)] whitespace-pre-wrap leading-relaxed">
              {grant.description}
            </p>
          </div>

          {/* Eligibility */}
          {grant.eligibility && Object.keys(grant.eligibility).length > 0 && (
            <div className="p-6 border-b border-[var(--gr-border-subtle)]">
              <h2 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-4">
                Eligibility Requirements
              </h2>
              <ul className="space-y-3">
                {Object.entries(grant.eligibility).map(([key, value], index) => (
                  <li key={index} className="flex items-start gap-3">
                    <CheckCircleIcon className="h-5 w-5 text-[var(--gr-emerald-400)] flex-shrink-0 mt-0.5" />
                    <span className="text-[var(--gr-text-secondary)]">
                      <strong className="capitalize">{key.replace(/_/g, ' ')}:</strong> {String(value)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Focus areas */}
          {grant.focus_areas && grant.focus_areas.length > 0 && (
            <div className="p-6 border-b border-[var(--gr-border-subtle)]">
              <h2 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-4">
                Focus Areas
              </h2>
              <div className="flex flex-wrap gap-2">
                {grant.focus_areas.map((area) => (
                  <span
                    key={area}
                    className="badge badge-amber"
                  >
                    {area}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Match reasoning */}
          {reasoning && (
            <div className="p-6 bg-gradient-to-r from-[var(--gr-amber-500)]/10 to-transparent border-b border-[var(--gr-border-subtle)]">
              <h2 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-4">
                Why This Matches Your Profile
              </h2>
              <p className="text-[var(--gr-text-secondary)] leading-relaxed">{reasoning}</p>
            </div>
          )}

          {/* Actions */}
          <div className="p-6 bg-[var(--gr-bg-card)]">
            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={() => updateStatusMutation.mutate(isSaved ? 'dismissed' : 'saved')}
                disabled={updateStatusMutation.isPending}
                className={`btn-secondary ${
                  isSaved
                    ? 'border-[var(--gr-emerald-500)]/30 text-[var(--gr-emerald-400)]'
                    : ''
                }`}
              >
                {isSaved ? (
                  <>
                    <BookmarkSolidIcon className="h-5 w-5" />
                    Saved
                  </>
                ) : (
                  <>
                    <BookmarkIcon className="h-5 w-5" />
                    Save Grant
                  </>
                )}
              </button>

              <button
                onClick={() => updateStatusMutation.mutate('applied')}
                disabled={updateStatusMutation.isPending || isApplied}
                className={
                  isApplied
                    ? 'btn-secondary border-[var(--gr-emerald-500)]/30 text-[var(--gr-emerald-400)]'
                    : 'btn-primary'
                }
              >
                <ClipboardDocumentListIcon className="h-5 w-5" />
                {isApplied ? 'Applied' : 'Mark as Applied'}
              </button>

              {!isSaved && !isApplied && (
                <button
                  onClick={() => updateStatusMutation.mutate('dismissed')}
                  disabled={updateStatusMutation.isPending}
                  className="btn-secondary"
                >
                  <XMarkIcon className="h-5 w-5" />
                  Dismiss
                </button>
              )}

              {grant.url && (
                <a
                  href={grant.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary ml-auto"
                >
                  <GlobeAltIcon className="h-5 w-5" />
                  Apply on Source
                  <ArrowTopRightOnSquareIcon className="h-4 w-4" />
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Similar grants */}
        {similarGrants && similarGrants.length > 0 && (
          <div className="mt-12 animate-fade-in-up stagger-2">
            <h2 className="text-xl font-display font-medium text-[var(--gr-text-primary)] mb-6">
              Similar Grants
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {similarGrants.slice(0, 4).map((similarMatch, index) => (
                <GrantCard key={similarMatch.id} match={similarMatch} delay={index} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default GrantDetail;
