import { useState } from 'react';
import { Tab } from '@headlessui/react';
import { useQuery } from '@tanstack/react-query';
import {
  ChartBarIcon,
  ClockIcon,
  TrophyIcon,
  SparklesIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import {
  StatsSummary,
  SuccessRateChart,
  FundingTrendChart,
  PipelineMetrics,
  StageConversionFunnel,
  TimeToAwardChart,
  FunderLeaderboard,
  MatchQualityChart,
  DeadlineHeatmap,
  ApplicationsCreatedSparkline,
  StageChangesSparkline,
  MatchesSavedSparkline,
} from '../components/analytics';
import { analyticsApi } from '../services/api';

const TABS = [
  { name: 'Overview', icon: ChartBarIcon },
  { name: 'Performance', icon: TrophyIcon },
  { name: 'Matches', icon: SparklesIcon },
  { name: 'Trends', icon: ClockIcon },
];

export function Analytics() {
  const [selectedTab, setSelectedTab] = useState(0);
  const [fundingPeriod, setFundingPeriod] = useState<'monthly' | 'quarterly' | 'yearly'>('monthly');

  // Fetch analytics data needed for components that require props
  const {
    data: summary,
    isLoading: loadingSummary,
    error: summaryError,
    refetch: refetchSummary,
  } = useQuery({
    queryKey: ['analytics', 'summary'],
    queryFn: analyticsApi.getSummary,
  });

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

  const isLoading = loadingSummary || loadingSuccess || loadingFunding || loadingPipeline;
  const hasError = summaryError || successError || fundingError || pipelineError;
  const isFetching = isLoading;

  // Compute derived metrics from by_stage data
  const getStageCount = (stage: string) => {
    return successRates?.by_stage?.find((s) => s.stage.toLowerCase() === stage)?.count || 0;
  };
  const totalSubmitted = getStageCount('submitted');
  const totalAwarded = getStageCount('awarded');

  const refetchAll = () => {
    refetchSummary();
    refetchSuccess();
    refetchFunding();
    refetchPipeline();
  };

  // Check if user has any data
  const hasNoData =
    successRates?.total_applications === 0 &&
    pipelineMetrics?.total_in_pipeline === 0;

  // Render loading state
  if (isLoading && !successRates && !fundingTrends && !pipelineMetrics) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="skeleton h-8 w-48 mb-2" />
            <div className="skeleton h-4 w-64" />
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="skeleton h-12 w-full rounded-xl mb-6" />
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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <ExclamationTriangleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-display font-medium text-gray-900 mb-2">
            Failed to load analytics
          </h2>
          <p className="text-gray-500 mb-4">
            There was an error loading your analytics data.
          </p>
          <button
            onClick={refetchAll}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            <ArrowPathIcon className="h-4 w-4" />
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
              <p className="mt-1 text-sm text-gray-500">
                Track your grant application performance and trends
              </p>
            </div>
            <button
              onClick={refetchAll}
              disabled={isFetching}
              className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              <ArrowPathIcon className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Empty state */}
      {hasNoData && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-gray-100 flex items-center justify-center mb-6">
              <ChartBarIcon className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-xl font-display font-medium text-gray-900 mb-2">
              No analytics data yet
            </h3>
            <p className="text-gray-500 max-w-md mx-auto mb-6">
              Start tracking grant applications in your pipeline to see success rates,
              funding trends, and conversion metrics.
            </p>
            <a
              href="/pipeline"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              Go to Pipeline
            </a>
          </div>
        </div>
      )}

      {/* Tabs */}
      {!hasNoData && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <Tab.Group selectedIndex={selectedTab} onChange={setSelectedTab}>
            <Tab.List className="flex space-x-1 bg-white rounded-xl p-1 shadow mb-6">
              {TABS.map((tab) => (
                <Tab
                  key={tab.name}
                  className={({ selected }) =>
                    `w-full flex items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium leading-5 transition-colors
                    ${selected
                      ? 'bg-blue-600 text-white shadow'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }`
                  }
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.name}
                </Tab>
              ))}
            </Tab.List>

            <Tab.Panels>
              {/* Overview Tab */}
              <Tab.Panel className="space-y-6">
                {/* Activity Sparklines */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <ApplicationsCreatedSparkline />
                  <StageChangesSparkline />
                  <MatchesSavedSparkline />
                </div>

                {/* Stats Summary */}
                {summary && <StatsSummary data={summary} />}

                {/* Two column layout */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <DeadlineHeatmap />
                  {successRates && (
                    <div className="bg-white rounded-xl border border-gray-200 p-6">
                      <h3 className="text-lg font-display font-medium text-gray-900 mb-4">
                        Quick Stats
                      </h3>
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600">Total Applications</span>
                          <span className="font-semibold text-gray-900">
                            {successRates.total_applications}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600">Submitted</span>
                          <span className="font-semibold text-gray-900">
                            {totalSubmitted}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600">Awarded</span>
                          <span className="font-semibold text-emerald-600">
                            {totalAwarded}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600">Win Rate</span>
                          <span className="font-semibold text-blue-600">
                            {successRates.overall_success_rate.toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </Tab.Panel>

              {/* Performance Tab */}
              <Tab.Panel className="space-y-6">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <TimeToAwardChart />
                  <div className="bg-white rounded-xl border border-gray-200 p-6">
                    <h3 className="text-lg font-display font-medium text-gray-900 mb-4">
                      Overall Win Rate
                    </h3>
                    {successRates ? (
                      <div className="flex items-center justify-center h-64">
                        <div className="text-center">
                          <div className="text-5xl font-display font-bold text-blue-600">
                            {successRates.overall_success_rate.toFixed(0)}%
                          </div>
                          <div className="text-gray-500 mt-2">
                            {totalAwarded} of {totalSubmitted} submitted
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center h-64 text-gray-400">
                        Loading...
                      </div>
                    )}
                  </div>
                </div>
                <FunderLeaderboard />
                {successRates && <SuccessRateChart data={successRates} />}
              </Tab.Panel>

              {/* Matches Tab */}
              <Tab.Panel className="space-y-6">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <MatchQualityChart />
                  {pipelineMetrics && <StageConversionFunnel data={pipelineMetrics} />}
                </div>
                {pipelineMetrics && <PipelineMetrics data={pipelineMetrics} />}
              </Tab.Panel>

              {/* Trends Tab */}
              <Tab.Panel className="space-y-6">
                {fundingTrends && (
                  <FundingTrendChart
                    data={fundingTrends}
                    onPeriodChange={setFundingPeriod}
                  />
                )}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {pipelineMetrics && <PipelineMetrics data={pipelineMetrics} />}
                  {pipelineMetrics && <StageConversionFunnel data={pipelineMetrics} />}
                </div>
              </Tab.Panel>
            </Tab.Panels>
          </Tab.Group>
        </div>
      )}
    </div>
  );
}

export default Analytics;
