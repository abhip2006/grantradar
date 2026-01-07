import { useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeftIcon,
  ShareIcon,
  DocumentDuplicateIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { grantsApi } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { Navbar } from '../components/Navbar';
import { GrantCompare } from '../components/GrantCompare';

export function Compare() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { showToast } = useToast();

  // Get grant IDs from URL
  const grantIds = searchParams.get('grants')?.split(',').filter(Boolean) || [];

  // Fetch comparison data
  const {
    data: comparisonData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['compare', grantIds],
    queryFn: () => grantsApi.compareGrants(grantIds),
    enabled: grantIds.length >= 2 && grantIds.length <= 4,
  });

  // Redirect if not enough grants
  useEffect(() => {
    if (grantIds.length < 2) {
      navigate('/dashboard');
      showToast('Select at least 2 grants to compare', 'warning');
    }
  }, [grantIds.length, navigate, showToast]);

  // Handle removing a grant from comparison
  const handleRemoveGrant = (grantId: string) => {
    const newIds = grantIds.filter((id) => id !== grantId);
    if (newIds.length < 2) {
      navigate('/dashboard');
      showToast('Comparison requires at least 2 grants', 'info');
    } else {
      setSearchParams({ grants: newIds.join(',') });
    }
  };

  // Copy comparison URL to clipboard
  const handleShare = async () => {
    const url = window.location.href;
    try {
      await navigator.clipboard.writeText(url);
      showToast('Comparison link copied to clipboard!', 'success');
    } catch {
      showToast('Failed to copy link', 'error');
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-[var(--gr-bg-primary)]">
        <Navbar />
        <main className="max-w-7xl mx-auto px-6 py-8">
          <div className="animate-fade-in-up">
            <div className="skeleton h-8 w-48 mb-4" />
            <div className="skeleton h-4 w-64 mb-8" />
            <div className="card-elevated">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="space-y-4 p-4">
                    <div className="skeleton h-6 w-full" />
                    <div className="skeleton h-4 w-3/4" />
                    <div className="skeleton h-4 w-1/2" />
                    <div className="skeleton h-4 w-2/3" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // Error state
  if (error || !comparisonData) {
    return (
      <div className="min-h-screen bg-[var(--gr-bg-primary)]">
        <Navbar />
        <main className="max-w-7xl mx-auto px-6 py-8">
          <div className="card text-center py-16 animate-fade-in-up">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-[var(--gr-danger)]/10 flex items-center justify-center mb-6">
              <ExclamationTriangleIcon className="w-8 h-8 text-[var(--gr-danger)]" />
            </div>
            <h3 className="text-xl font-display font-medium text-[var(--gr-text-primary)] mb-2">
              Unable to load comparison
            </h3>
            <p className="text-[var(--gr-text-secondary)] max-w-sm mx-auto mb-6">
              {error instanceof Error ? error.message : 'Some grants could not be found or loaded.'}
            </p>
            <Link to="/dashboard" className="btn-primary">
              Back to Dashboard
            </Link>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      <Navbar />

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8 animate-fade-in-up">
          <div>
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 text-sm text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)] mb-2"
            >
              <ArrowLeftIcon className="w-4 h-4" />
              Back to Dashboard
            </Link>
            <h1 className="text-3xl font-display font-medium text-[var(--gr-text-primary)]">
              Grant Comparison
            </h1>
            <p className="mt-2 text-[var(--gr-text-secondary)]">
              Comparing {comparisonData.grants.length} grants side by side
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleShare}
              className="btn-secondary"
              title="Copy comparison link"
            >
              <ShareIcon className="w-4 h-4" />
              Share
            </button>
            <Link to="/dashboard" className="btn-ghost">
              <DocumentDuplicateIcon className="w-4 h-4" />
              Add More
            </Link>
          </div>
        </div>

        {/* Comparison hint */}
        {comparisonData.grants.length < 4 && (
          <div className="mb-6 p-4 rounded-xl bg-[var(--gr-blue-50)] border border-[var(--gr-blue-100)] animate-fade-in-up stagger-1">
            <p className="text-sm text-[var(--gr-blue-700)]">
              <strong>Tip:</strong> You can compare up to 4 grants at once. Return to the dashboard
              to add more grants to this comparison.
            </p>
          </div>
        )}

        {/* Comparison Table */}
        <div className="card-elevated animate-fade-in-up stagger-2">
          <GrantCompare
            grants={comparisonData.grants}
            onRemoveGrant={handleRemoveGrant}
          />
        </div>

        {/* Legend */}
        <div className="mt-6 p-4 rounded-xl bg-[var(--gr-bg-secondary)] border border-[var(--gr-border-subtle)] animate-fade-in-up stagger-3">
          <h4 className="text-sm font-medium text-[var(--gr-text-secondary)] mb-3">
            Understanding the highlights
          </h4>
          <div className="flex flex-wrap gap-4 text-sm text-[var(--gr-text-tertiary)]">
            <div className="flex items-center gap-2">
              <span className="badge badge-yellow">Highest</span>
              <span>Best funding amount</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="badge badge-yellow">Nearest</span>
              <span>Closest upcoming deadline</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="badge badge-yellow">Best</span>
              <span>Highest match score</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-4 h-4 rounded bg-[var(--gr-yellow-50)]" />
              <span>Values differ between grants</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default Compare;
