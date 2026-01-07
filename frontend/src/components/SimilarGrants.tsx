import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  CalendarIcon,
  CurrencyDollarIcon,
  BuildingLibraryIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { grantsApi } from '../services/api';
import type { SimilarGrant } from '../types';

interface SimilarGrantsProps {
  grantId: string;
  limit?: number;
}

function SimilarityBadge({ score }: { score: number }) {
  const getScoreColor = () => {
    if (score >= 70) return 'bg-[var(--gr-emerald-500)]/20 text-[var(--gr-emerald-400)] border-[var(--gr-emerald-500)]/30';
    if (score >= 50) return 'bg-[var(--gr-amber-500)]/20 text-[var(--gr-amber-400)] border-[var(--gr-amber-500)]/30';
    return 'bg-[var(--gr-slate-600)]/50 text-[var(--gr-text-secondary)] border-[var(--gr-border-subtle)]';
  };

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${getScoreColor()}`}>
      <SparklesIcon className="h-3 w-3" />
      {score}% similar
    </span>
  );
}

function SimilarityReasonBadge({ reason }: { reason: string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-[var(--gr-cyan-500)]/10 text-[var(--gr-cyan-400)] border border-[var(--gr-cyan-500)]/20">
      {reason}
    </span>
  );
}

function SimilarGrantCard({ grant, index }: { grant: SimilarGrant; index: number }) {
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
      case 'nih':
      case 'nsf':
      case 'grants_gov':
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

  return (
    <Link
      to={`/grants/${grant.id}`}
      className="block group"
      style={{ animationDelay: `${index * 0.05}s` }}
    >
      <div className="card-elevated p-5 h-full hover:border-[var(--gr-amber-500)]/30 transition-all animate-fade-in-up">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`badge ${getSourceBadgeColor(grant.source)}`}>
              {grant.source}
            </span>
            <SimilarityBadge score={grant.similarity_score} />
          </div>
        </div>

        {/* Title */}
        <h3 className="text-base font-display font-medium text-[var(--gr-text-primary)] group-hover:text-[var(--gr-amber-400)] transition-colors line-clamp-2 mb-2">
          {grant.title}
        </h3>

        {/* Agency */}
        {grant.agency && (
          <div className="flex items-center gap-2 text-sm text-[var(--gr-text-secondary)] mb-3">
            <BuildingLibraryIcon className="h-4 w-4 flex-shrink-0 text-[var(--gr-text-tertiary)]" />
            <span className="truncate">{grant.agency}</span>
          </div>
        )}

        {/* Meta info */}
        <div className="flex flex-wrap items-center gap-3 text-sm mb-3">
          {(grant.amount_min || grant.amount_max) && (
            <div className="flex items-center gap-1.5 text-[var(--gr-text-secondary)]">
              <CurrencyDollarIcon className="h-4 w-4 text-[var(--gr-amber-500)]" />
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
            <div className="flex items-center gap-1.5 text-[var(--gr-text-secondary)]">
              <CalendarIcon className="h-4 w-4 text-[var(--gr-cyan-500)]" />
              <span>{formatDate(grant.deadline)}</span>
            </div>
          )}
        </div>

        {/* Similarity reasons */}
        {grant.similarity_reasons && grant.similarity_reasons.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {grant.similarity_reasons.slice(0, 3).map((reason, i) => (
              <SimilarityReasonBadge key={i} reason={reason} />
            ))}
          </div>
        )}
      </div>
    </Link>
  );
}

export function SimilarGrants({ grantId, limit = 6 }: SimilarGrantsProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['similar-grants', grantId, limit],
    queryFn: () => grantsApi.getSimilarGrants(grantId, { limit }),
    enabled: !!grantId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  if (isLoading) {
    return (
      <div className="mt-12">
        <h2 className="text-xl font-display font-medium text-[var(--gr-text-primary)] mb-6">
          Similar Grants
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="card-elevated p-5">
              <div className="skeleton h-4 w-24 mb-3" />
              <div className="skeleton h-5 w-full mb-2" />
              <div className="skeleton h-4 w-32 mb-3" />
              <div className="skeleton h-4 w-24" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error || !data || data.similar_grants.length === 0) {
    return null; // Silently hide if no similar grants found
  }

  return (
    <div className="mt-12 animate-fade-in-up">
      <div className="flex items-center gap-2 mb-6">
        <SparklesIcon className="h-5 w-5 text-[var(--gr-amber-400)]" />
        <h2 className="text-xl font-display font-medium text-[var(--gr-text-primary)]">
          Similar Grants
        </h2>
        <span className="text-sm text-[var(--gr-text-tertiary)]">
          ({data.total} found)
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.similar_grants.map((grant, index) => (
          <SimilarGrantCard key={grant.id} grant={grant} index={index} />
        ))}
      </div>
    </div>
  );
}

export default SimilarGrants;
