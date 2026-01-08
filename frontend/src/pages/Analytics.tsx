import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ChartBarIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  ChartPieIcon,
  CurrencyDollarIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';
import { analyticsApi } from '../services/api';
import {
  SuccessRateChart,
  FundingTrendChart,
  PipelineMetrics,
  StatsSummary,
  StageConversionFunnel,
} from '../components/analytics';

type AnalyticsTab = 'overview' | 'success' | 'funding' | 'pipeline';

const TABS: { key: AnalyticsTab; label: string; icon: React.ReactNode }[] = [
  { key: 'overview', label: 'Overview', icon: <ChartBarIcon className="h-4 w-4" /> },
  { key: 'success', label: 'Success Rates', icon: <ChartPieIcon className="h-4 w-4" /> },
  { key: 'funding', label: 'Funding Trends', icon: <CurrencyDollarIcon className="h-4 w-4" /> },
  { key: 'pipeline', label: 'Pipeline', icon: <FunnelIcon className="h-4 w-4" /> },
];

export function Analytics() {
  const [activeTab, setActiveTab] = useState<AnalyticsTab>('overview');
  const [fundingPeriod, setFundingPeriod] = useState<'monthly' | 'quarterly' | 'yearly'>('monthly');

  // Fetch all analytics data
  const {
    data: successRates,
    isLoading: loadingSuccess,
    error: successError,
    refetch: refetchSuccess,
  } = useQuery({
    queryKey: ['analytics', 'success-rates'],
    queryFn: analyticsApi.getSuccessRates,
  });

  const {
    data: fundingTrends,
    isLoading: loadingFunding,
    error: fundingError,
    refetch: refetchFunding,
  } = useQuery({
    queryKey: ['analytics', 'funding-trends', fundingPeriod],
    queryFn: () => analyticsApi.getFundingTrends({ period: fundingPeriod }),
  });

  const {
    data: pipelineMetrics,
    isLoading: loadingPipeline,
    error: pipelineError,
    refetch: refetchPipeline,
  } = useQuery({
    queryKey: ['analytics', 'pipeline-metrics'],
    queryFn: analyticsApi.getPipelineMetrics,
  });

  const {
    data: summary,
    isLoading: loadingSummary,
    error: summaryError,
    refetch: refetchSummary,
  } = useQuery({
    queryKey: ['analytics', 'summary'],
    queryFn: analyticsApi.getSummary,
  });

  const isLoading = loadingSuccess || loadingFunding || loadingPipeline || loadingSummary;
  const hasError = successError || fundingError || pipelineError || summaryError;

  const refetchAll = () => {
    refetchSuccess();
    refetchFunding();
    refetchPipeline();
    refetchSummary();
  };

  // Render loading state
  if (isLoading && !successRates && !fundingTrends && !pipelineMetrics) {
    return (
      <div className="min-h-screen bg-[var(--gr-bg-secondary)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="skeleton h-8 w-48 mb-6" />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="skeleton h-80 rounded-xl" />
            <div className="skeleton h-80 rounded-xl" />
            <div className="skeleton h-80 rounded-xl" />
            <div className="skeleton h-80 rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  // Render error state
  if (hasError) {
    return (
      <div className="min-h-screen bg-[var(--gr-bg-secondary)] flex items-center justify-center">
        <div className="text-center">
          <ExclamationTriangleIcon className="h-12 w-12 text-[var(--gr-danger)] mx-auto mb-4" />
          <h2 className="text-xl font-display font-medium text-[var(--gr-text-primary)] mb-2">
            Failed to load analytics
          </h2>
          <p className="text-[var(--gr-text-secondary)] mb-4">
            There was an error loading your analytics data.
          </p>
          <button onClick={refetchAll} className="btn-primary">
            <ArrowPathIcon className="h-4 w-4" />
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Check if user has any data
  const hasNoData =
    successRates?.total_applications === 0 &&
    pipelineMetrics?.total_in_pipeline === 0;

  return (
    <div className="min-h-screen bg-[var(--gr-bg-secondary)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-display font-semibold text-[var(--gr-text-primary)]">
              Analytics
            </h1>
            <p className="text-sm text-[var(--gr-text-secondary)] mt-1">
              Track your grant application performance and funding trends
            </p>
          </div>

          <button
            onClick={refetchAll}
            disabled={isLoading}
            className="btn-secondary"
          >
            <ArrowPathIcon className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Empty state */}
        {hasNoData && (
          <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-12 text-center mb-6">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-[var(--gr-bg-secondary)] flex items-center justify-center mb-6">
              <ChartBarIcon className="w-8 h-8 text-[var(--gr-text-tertiary)]" />
            </div>
            <h3 className="text-xl font-display font-medium text-[var(--gr-text-primary)] mb-2">
              No analytics data yet
            </h3>
            <p className="text-[var(--gr-text-secondary)] max-w-md mx-auto mb-6">
              Start tracking grant applications in your pipeline to see success rates,
              funding trends, and conversion metrics.
            </p>
            <a href="/pipeline" className="btn-primary inline-flex">
              Go to Pipeline
            </a>
          </div>
        )}

        {/* Tab navigation */}
        {!hasNoData && (
          <>
            <div className="flex gap-1 p-1 bg-white rounded-xl border border-[var(--gr-border-default)] mb-6 overflow-x-auto">
              {TABS.map(({ key, label, icon }) => (
                <button
                  key={key}
                  onClick={() => setActiveTab(key)}
                  className={`
                    flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap
                    ${activeTab === key
                      ? 'bg-[var(--gr-blue-600)] text-white'
                      : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-hover)]'
                    }
                  `}
                >
                  {icon}
                  {label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div className="space-y-6">
              {/* Overview Tab */}
              {activeTab === 'overview' && (
                <>
                  {/* Summary Stats Cards */}
                  {summary && <StatsSummary data={summary} />}

                  {/* Charts Grid */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {successRates && <SuccessRateChart data={successRates} />}
                    {pipelineMetrics && <StageConversionFunnel data={pipelineMetrics} />}
                  </div>

                  {/* Funding Trend Preview */}
                  {fundingTrends && (
                    <FundingTrendChart
                      data={fundingTrends}
                      onPeriodChange={setFundingPeriod}
                    />
                  )}
                </>
              )}

              {/* Success Rates Tab */}
              {activeTab === 'success' && successRates && (
                <SuccessRateChart data={successRates} />
              )}

              {/* Funding Trends Tab */}
              {activeTab === 'funding' && fundingTrends && (
                <FundingTrendChart
                  data={fundingTrends}
                  onPeriodChange={setFundingPeriod}
                />
              )}

              {/* Pipeline Tab */}
              {activeTab === 'pipeline' && pipelineMetrics && (
                <>
                  <StageConversionFunnel data={pipelineMetrics} />
                  <PipelineMetrics data={pipelineMetrics} />
                </>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default Analytics;
