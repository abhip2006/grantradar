import { useState, useEffect } from 'react';
import { Tab } from '@headlessui/react';
import { useQuery } from '@tanstack/react-query';
import {
  ChartBarIcon,
  ClockIcon,
  TrophyIcon,
  SparklesIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  ArrowTrendingUpIcon,
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

// Animated counter hook
function useAnimatedNumber(value: number, duration: number = 1000) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    if (value === 0) {
      setDisplayValue(0);
      return;
    }

    const startTime = Date.now();
    const startValue = displayValue;

    const animate = () => {
      const now = Date.now();
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // Cubic ease out
      setDisplayValue(Math.round(startValue + (value - startValue) * eased));

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [value, duration]);

  return displayValue;
}

export function Analytics() {
  const [selectedTab, setSelectedTab] = useState(0);
  const [fundingPeriod, setFundingPeriod] = useState<'monthly' | 'quarterly' | 'yearly'>('monthly');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

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

  // Animated values
  const animatedTotal = useAnimatedNumber(successRates?.total_applications || 0);
  const animatedSubmitted = useAnimatedNumber(totalSubmitted);
  const animatedAwarded = useAnimatedNumber(totalAwarded);
  const animatedRate = useAnimatedNumber(Math.round(successRates?.overall_success_rate || 0));

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

  // Render loading state with animated skeleton
  if (isLoading && !successRates && !fundingTrends && !pipelineMetrics) {
    return (
      <div className="min-h-screen bg-mesh">
        <div className="analytics-header">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="skeleton h-10 w-64 mb-3 rounded-lg" />
            <div className="skeleton h-5 w-96 rounded-lg" />
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="skeleton h-14 w-full rounded-2xl mb-8" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-8">
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton h-32 rounded-2xl" style={{ animationDelay: `${i * 0.1}s` }} />
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="skeleton h-80 rounded-2xl" />
            <div className="skeleton h-80 rounded-2xl" />
          </div>
        </div>
      </div>
    );
  }

  // Render error state
  if (hasError) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center">
        <div className="text-center animate-fade-in-up">
          <div className="w-20 h-20 mx-auto rounded-2xl bg-red-50 flex items-center justify-center mb-6">
            <ExclamationTriangleIcon className="h-10 w-10 text-red-500" />
          </div>
          <h2 className="text-2xl font-display font-semibold text-gray-900 mb-3">
            Failed to load analytics
          </h2>
          <p className="text-gray-500 mb-6 max-w-md">
            There was an error loading your analytics data. Please try again.
          </p>
          <button
            onClick={refetchAll}
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 transition-all hover:shadow-lg hover:-translate-y-0.5"
          >
            <ArrowPathIcon className="h-4 w-4" />
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-mesh">
      {/* Premium Header with gradient accent */}
      <div className="analytics-header">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className={`flex items-center justify-between ${mounted ? 'animate-fade-in-up' : 'opacity-0'}`}>
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-display font-semibold text-gray-900">
                  Analytics
                </h1>
                <span className="live-indicator text-sm text-gray-500 font-medium">
                  Live
                </span>
              </div>
              <p className="text-gray-500">
                Track your grant application performance and funding trends
              </p>
            </div>
            <button
              onClick={refetchAll}
              disabled={isFetching}
              className="group inline-flex items-center gap-2 px-5 py-2.5 bg-white border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 disabled:opacity-50 transition-all shadow-sm hover:shadow"
            >
              <ArrowPathIcon className={`w-4 h-4 transition-transform ${isFetching ? 'animate-spin' : 'group-hover:rotate-180'}`} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Empty state */}
      {hasNoData && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="glass-card-elevated rounded-2xl p-16 text-center animate-fade-in-up">
            <div className="w-20 h-20 mx-auto rounded-2xl bg-gradient-to-br from-blue-50 to-blue-100 flex items-center justify-center mb-8 animate-float">
              <ChartBarIcon className="w-10 h-10 text-blue-500" />
            </div>
            <h3 className="text-2xl font-display font-semibold text-gray-900 mb-3">
              No analytics data yet
            </h3>
            <p className="text-gray-500 max-w-md mx-auto mb-8 leading-relaxed">
              Start tracking grant applications in your pipeline to see success rates,
              funding trends, and conversion metrics.
            </p>
            <a
              href="/pipeline"
              className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-xl text-sm font-semibold hover:from-blue-700 hover:to-blue-600 transition-all shadow-lg shadow-blue-500/25 hover:-translate-y-0.5"
            >
              <ArrowTrendingUpIcon className="w-4 h-4" />
              Go to Pipeline
            </a>
          </div>
        </div>
      )}

      {/* Tabs */}
      {!hasNoData && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Tab.Group selectedIndex={selectedTab} onChange={setSelectedTab}>
            {/* Premium Tab Pills */}
            <div className={`${mounted ? 'animate-fade-in-up stagger-1' : 'opacity-0'}`}>
              <Tab.List className="inline-flex p-1.5 bg-white/80 backdrop-blur-sm rounded-2xl shadow-sm border border-gray-100 mb-8">
                {TABS.map((tab, idx) => (
                  <Tab
                    key={tab.name}
                    className={({ selected }) =>
                      `tab-pill ${selected ? 'tab-pill-active' : ''}`
                    }
                    style={{ animationDelay: `${idx * 0.05}s` }}
                  >
                    <tab.icon className="w-4 h-4" />
                    <span>{tab.name}</span>
                  </Tab>
                ))}
              </Tab.List>
            </div>

            <Tab.Panels>
              {/* Overview Tab */}
              <Tab.Panel className="tab-panel-enter space-y-8">
                {/* Activity Sparklines */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                  <div className="animate-fade-in-up stagger-1">
                    <ApplicationsCreatedSparkline />
                  </div>
                  <div className="animate-fade-in-up stagger-2">
                    <StageChangesSparkline />
                  </div>
                  <div className="animate-fade-in-up stagger-3">
                    <MatchesSavedSparkline />
                  </div>
                </div>

                {/* Stats Summary */}
                <div className="animate-fade-in-up stagger-4">
                  {summary && <StatsSummary data={summary} />}
                </div>

                {/* Two column layout */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="animate-fade-in-up stagger-5">
                    <DeadlineHeatmap />
                  </div>
                  {successRates && (
                    <div className="animate-fade-in-up stagger-6">
                      <div className="stat-card-animated rounded-2xl">
                        <div className="flex items-center justify-between mb-6">
                          <h3 className="text-lg font-display font-semibold text-gray-900">
                            Quick Stats
                          </h3>
                          <span className="live-indicator text-xs text-gray-400">Live</span>
                        </div>
                        <div className="space-y-5">
                          <div className="flex items-center justify-between py-2 border-b border-gray-100">
                            <span className="text-gray-600">Total Applications</span>
                            <span className="text-2xl font-display font-semibold text-gray-900 animate-count">
                              {animatedTotal}
                            </span>
                          </div>
                          <div className="flex items-center justify-between py-2 border-b border-gray-100">
                            <span className="text-gray-600">Submitted</span>
                            <span className="text-2xl font-display font-semibold text-gray-900 animate-count">
                              {animatedSubmitted}
                            </span>
                          </div>
                          <div className="flex items-center justify-between py-2 border-b border-gray-100">
                            <span className="text-gray-600">Awarded</span>
                            <span className="text-2xl font-display font-semibold text-emerald-600 animate-count">
                              {animatedAwarded}
                            </span>
                          </div>
                          <div className="flex items-center justify-between py-2">
                            <span className="text-gray-600">Win Rate</span>
                            <div className="flex items-baseline gap-1">
                              <span className="big-number text-3xl">{animatedRate}</span>
                              <span className="text-xl text-blue-500 font-display font-semibold">%</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </Tab.Panel>

              {/* Performance Tab */}
              <Tab.Panel className="tab-panel-enter space-y-8">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="animate-fade-in-up stagger-1">
                    <TimeToAwardChart />
                  </div>
                  <div className="animate-fade-in-up stagger-2">
                    <div className="stat-card-animated rounded-2xl h-full">
                      <h3 className="text-lg font-display font-semibold text-gray-900 mb-6">
                        Overall Win Rate
                      </h3>
                      {successRates ? (
                        <div className="flex items-center justify-center h-64">
                          <div className="text-center">
                            {/* Animated ring */}
                            <div className="win-rate-ring mx-auto mb-4">
                              <svg width="200" height="200" viewBox="0 0 200 200">
                                <defs>
                                  <linearGradient id="winRateGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                                    <stop offset="0%" stopColor="#3b82f6" />
                                    <stop offset="100%" stopColor="#22c55e" />
                                  </linearGradient>
                                </defs>
                                <circle
                                  className="win-rate-ring-bg"
                                  cx="100"
                                  cy="100"
                                  r="85"
                                />
                                <circle
                                  className="win-rate-ring-progress progress-ring-animated"
                                  cx="100"
                                  cy="100"
                                  r="85"
                                  strokeDasharray={534}
                                  strokeDashoffset={534 - (534 * (successRates.overall_success_rate || 0)) / 100}
                                />
                              </svg>
                              <div className="absolute inset-0 flex items-center justify-center">
                                <div className="big-number text-5xl">{animatedRate}%</div>
                              </div>
                            </div>
                            <div className="text-gray-500 mt-4">
                              <span className="font-semibold text-emerald-600">{animatedAwarded}</span> of{' '}
                              <span className="font-semibold">{animatedSubmitted}</span> submitted
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center justify-center h-64">
                          <div className="skeleton w-48 h-48 rounded-full" />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                <div className="animate-fade-in-up stagger-3">
                  <FunderLeaderboard />
                </div>
                <div className="animate-fade-in-up stagger-4">
                  {successRates && <SuccessRateChart data={successRates} />}
                </div>
              </Tab.Panel>

              {/* Matches Tab */}
              <Tab.Panel className="tab-panel-enter space-y-8">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="animate-fade-in-up stagger-1">
                    <MatchQualityChart />
                  </div>
                  <div className="animate-fade-in-up stagger-2">
                    {pipelineMetrics && <StageConversionFunnel data={pipelineMetrics} />}
                  </div>
                </div>
                <div className="animate-fade-in-up stagger-3">
                  {pipelineMetrics && <PipelineMetrics data={pipelineMetrics} />}
                </div>
              </Tab.Panel>

              {/* Trends Tab */}
              <Tab.Panel className="tab-panel-enter space-y-8">
                <div className="animate-fade-in-up stagger-1">
                  {fundingTrends && (
                    <FundingTrendChart
                      data={fundingTrends}
                      onPeriodChange={setFundingPeriod}
                    />
                  )}
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="animate-fade-in-up stagger-2">
                    {pipelineMetrics && <PipelineMetrics data={pipelineMetrics} />}
                  </div>
                  <div className="animate-fade-in-up stagger-3">
                    {pipelineMetrics && <StageConversionFunnel data={pipelineMetrics} />}
                  </div>
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
