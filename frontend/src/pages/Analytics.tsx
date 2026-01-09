import { useState, useEffect, useRef } from 'react';
import { Tab } from '@headlessui/react';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'motion/react';
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

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: [0.16, 1, 0.3, 1] as [number, number, number, number],
    },
  },
};

// tabContentVariants removed - kept for potential future use

// Animated counter hook with easing
function useAnimatedNumber(value: number, duration: number = 1200) {
  const [displayValue, setDisplayValue] = useState(0);
  const previousValue = useRef(0);

  useEffect(() => {
    if (value === 0 && previousValue.current === 0) {
      setDisplayValue(0);
      return;
    }

    const startTime = Date.now();
    const startValue = previousValue.current;

    const animate = () => {
      const now = Date.now();
      const progress = Math.min((now - startTime) / duration, 1);
      // Cubic ease out for smooth deceleration
      const eased = 1 - Math.pow(1 - progress, 3);
      const currentValue = Math.round(startValue + (value - startValue) * eased);
      setDisplayValue(currentValue);

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        previousValue.current = value;
      }
    };

    requestAnimationFrame(animate);
  }, [value, duration]);

  return displayValue;
}


// Premium skeleton loader
function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`skeleton-card-premium ${className}`}>
      <div className="skeleton-premium h-5 w-32 mb-4" />
      <div className="skeleton-premium h-10 w-24 mb-2" />
      <div className="skeleton-premium h-4 w-48" />
    </div>
  );
}

function SkeletonChart({ className = '' }: { className?: string }) {
  return (
    <div className={`skeleton-card-premium ${className}`}>
      <div className="skeleton-premium h-6 w-48 mb-6" />
      <div className="skeleton-premium h-64 w-full rounded-xl" />
    </div>
  );
}

export function Analytics() {
  const [selectedTab, setSelectedTab] = useState(0);
  const [fundingPeriod, setFundingPeriod] = useState<'monthly' | 'quarterly' | 'yearly'>('monthly');
  const [_mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Fetch analytics data
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

  // Compute derived metrics
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

  const hasNoData =
    successRates?.total_applications === 0 &&
    pipelineMetrics?.total_in_pipeline === 0;

  // Premium Loading State
  if (isLoading && !successRates && !fundingTrends && !pipelineMetrics) {
    return (
      <div className="bg-mesh-premium relative">
        <div className="analytics-header-premium">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10">
            <div className="skeleton-premium h-10 w-64 mb-3 rounded-lg" />
            <div className="skeleton-premium h-5 w-96 rounded-lg" />
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10">
          <div className="skeleton-premium h-14 w-96 rounded-2xl mb-8" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-8">
            {[1, 2, 3].map((i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <SkeletonChart />
            <SkeletonChart />
          </div>
        </div>
      </div>
    );
  }

  // Error State
  if (hasError) {
    return (
      <div className="bg-mesh-premium relative flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4 }}
          className="text-center relative z-10"
        >
          <div className="empty-state-icon">
            <ExclamationTriangleIcon className="h-10 w-10 text-red-500" />
          </div>
          <h2 className="empty-state-title">Failed to load analytics</h2>
          <p className="empty-state-description">
            There was an error loading your analytics data. Please try again.
          </p>
          <button onClick={refetchAll} className="btn-premium">
            <ArrowPathIcon className="h-4 w-4" />
            Try Again
          </button>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="bg-mesh-premium relative">
      {/* Premium Header */}
      <div className="analytics-header-premium">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="flex items-center justify-between"
          >
            <div>
              <div className="flex items-center gap-4 mb-2">
                <h1 className="text-3xl font-display font-semibold text-gray-900 tracking-tight">
                  Analytics
                </h1>
                <span className="live-badge-premium">Live</span>
              </div>
              <p className="text-gray-500 text-base">
                Track your grant application performance and funding trends
              </p>
            </div>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={refetchAll}
              disabled={isFetching}
              className="btn-refresh-premium"
            >
              <ArrowPathIcon className={`w-4 h-4 transition-transform ${isFetching ? 'animate-spin' : ''}`} />
              Refresh
            </motion.button>
          </motion.div>
        </div>
      </div>

      {/* Empty State */}
      {hasNoData && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="chart-card-premium empty-state-premium"
          >
            <div className="empty-state-icon">
              <ChartBarIcon className="w-10 h-10" />
            </div>
            <h3 className="empty-state-title">No analytics data yet</h3>
            <p className="empty-state-description">
              Start tracking grant applications in your pipeline to see success rates,
              funding trends, and conversion metrics.
            </p>
            <a href="/pipeline" className="btn-premium">
              <ArrowTrendingUpIcon className="w-4 h-4" />
              Go to Pipeline
            </a>
          </motion.div>
        </div>
      )}

      {/* Main Content with Tabs */}
      {!hasNoData && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10">
          <Tab.Group selectedIndex={selectedTab} onChange={setSelectedTab}>
            {/* Premium Tab Navigation */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 }}
            >
              <Tab.List className="tabs-premium mb-8">
                {TABS.map((tab) => (
                  <Tab
                    key={tab.name}
                    className={({ selected }) =>
                      `tab-item-premium ${selected ? 'active' : ''}`
                    }
                  >
                    <tab.icon className="w-4 h-4" />
                    <span>{tab.name}</span>
                  </Tab>
                ))}
              </Tab.List>
            </motion.div>

            <Tab.Panels>
              {/* Overview Tab */}
              <Tab.Panel>
                <AnimatePresence mode="wait">
                  <motion.div
                    key="overview"
                    variants={containerVariants}
                    initial="hidden"
                    animate="visible"
                    className="space-y-8"
                  >
                    {/* Activity Sparklines */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                      <motion.div variants={itemVariants} className="sparkline-card-premium">
                        <div className="sparkline-live-dot" />
                        <ApplicationsCreatedSparkline />
                      </motion.div>
                      <motion.div variants={itemVariants} className="sparkline-card-premium">
                        <div className="sparkline-live-dot" />
                        <StageChangesSparkline />
                      </motion.div>
                      <motion.div variants={itemVariants} className="sparkline-card-premium">
                        <div className="sparkline-live-dot" />
                        <MatchesSavedSparkline />
                      </motion.div>
                    </div>

                    {/* Stats Summary */}
                    <motion.div variants={itemVariants}>
                      {summary && <StatsSummary data={summary} />}
                    </motion.div>

                    {/* Two column layout */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <motion.div variants={itemVariants}>
                        <DeadlineHeatmap />
                      </motion.div>
                      {successRates && (
                        <motion.div variants={itemVariants}>
                          <div className="chart-card-premium">
                            <div className="chart-header-premium">
                              <h3 className="chart-title-premium">Quick Stats</h3>
                              <span className="live-badge-premium">Live</span>
                            </div>
                            <div className="space-y-0">
                              <div className="quick-stat-item">
                                <span className="quick-stat-label">Total Applications</span>
                                <span className="quick-stat-value">{animatedTotal}</span>
                              </div>
                              <div className="quick-stat-item">
                                <span className="quick-stat-label">Submitted</span>
                                <span className="quick-stat-value">{animatedSubmitted}</span>
                              </div>
                              <div className="quick-stat-item">
                                <span className="quick-stat-label">Awarded</span>
                                <span className="quick-stat-value counter-value emerald">{animatedAwarded}</span>
                              </div>
                              <div className="quick-stat-item">
                                <span className="quick-stat-label">Win Rate</span>
                                <div className="flex items-baseline gap-1">
                                  <span className="win-rate-value">{animatedRate}%</span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </div>
                  </motion.div>
                </AnimatePresence>
              </Tab.Panel>

              {/* Performance Tab */}
              <Tab.Panel>
                <AnimatePresence mode="wait">
                  <motion.div
                    key="performance"
                    variants={containerVariants}
                    initial="hidden"
                    animate="visible"
                    className="space-y-8"
                  >
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <motion.div variants={itemVariants}>
                        <TimeToAwardChart />
                      </motion.div>
                      <motion.div variants={itemVariants}>
                        <div className="chart-card-premium h-full">
                          <div className="chart-header-premium">
                            <h3 className="chart-title-premium">Overall Win Rate</h3>
                          </div>
                          {successRates ? (
                            <div className="flex items-center justify-center h-64">
                              <div className="text-center">
                                {/* Animated ring */}
                                <div className="win-rate-ring-premium mx-auto mb-4">
                                  <svg width="180" height="180" viewBox="0 0 180 180">
                                    <defs>
                                      <linearGradient id="winRateGradientPremium" x1="0%" y1="0%" x2="100%" y2="100%">
                                        <stop offset="0%" stopColor="#14b8a6" />
                                        <stop offset="100%" stopColor="#2d5a47" />
                                      </linearGradient>
                                    </defs>
                                    <circle
                                      className="win-rate-ring-bg-premium"
                                      cx="90"
                                      cy="90"
                                      r="76"
                                    />
                                    <circle
                                      className="win-rate-ring-progress-premium"
                                      cx="90"
                                      cy="90"
                                      r="76"
                                      strokeDasharray={478}
                                      strokeDashoffset={478 - (478 * (successRates.overall_success_rate || 0)) / 100}
                                    />
                                  </svg>
                                  <div className="win-rate-center">
                                    <span className="win-rate-value">{animatedRate}%</span>
                                    <span className="win-rate-label">Win Rate</span>
                                  </div>
                                </div>
                                <p className="text-gray-500 text-sm">
                                  <span className="font-semibold text-emerald-600">{animatedAwarded}</span> of{' '}
                                  <span className="font-semibold">{animatedSubmitted}</span> submitted
                                </p>
                              </div>
                            </div>
                          ) : (
                            <div className="flex items-center justify-center h-64">
                              <div className="skeleton-premium w-48 h-48 rounded-full" />
                            </div>
                          )}
                        </div>
                      </motion.div>
                    </div>
                    <motion.div variants={itemVariants}>
                      <FunderLeaderboard />
                    </motion.div>
                    <motion.div variants={itemVariants}>
                      {successRates && <SuccessRateChart data={successRates} />}
                    </motion.div>
                  </motion.div>
                </AnimatePresence>
              </Tab.Panel>

              {/* Matches Tab */}
              <Tab.Panel>
                <AnimatePresence mode="wait">
                  <motion.div
                    key="matches"
                    variants={containerVariants}
                    initial="hidden"
                    animate="visible"
                    className="space-y-8"
                  >
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <motion.div variants={itemVariants}>
                        <MatchQualityChart />
                      </motion.div>
                      <motion.div variants={itemVariants}>
                        {pipelineMetrics && <StageConversionFunnel data={pipelineMetrics} />}
                      </motion.div>
                    </div>
                    <motion.div variants={itemVariants}>
                      {pipelineMetrics && <PipelineMetrics data={pipelineMetrics} />}
                    </motion.div>
                  </motion.div>
                </AnimatePresence>
              </Tab.Panel>

              {/* Trends Tab */}
              <Tab.Panel>
                <AnimatePresence mode="wait">
                  <motion.div
                    key="trends"
                    variants={containerVariants}
                    initial="hidden"
                    animate="visible"
                    className="space-y-8"
                  >
                    <motion.div variants={itemVariants}>
                      {fundingTrends && (
                        <FundingTrendChart
                          data={fundingTrends}
                          onPeriodChange={setFundingPeriod}
                        />
                      )}
                    </motion.div>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <motion.div variants={itemVariants}>
                        {pipelineMetrics && <PipelineMetrics data={pipelineMetrics} />}
                      </motion.div>
                      <motion.div variants={itemVariants}>
                        {pipelineMetrics && <StageConversionFunnel data={pipelineMetrics} />}
                      </motion.div>
                    </div>
                  </motion.div>
                </AnimatePresence>
              </Tab.Panel>
            </Tab.Panels>
          </Tab.Group>
        </div>
      )}
    </div>
  );
}

export default Analytics;
