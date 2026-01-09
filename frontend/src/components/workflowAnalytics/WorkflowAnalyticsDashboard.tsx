import React, { useState } from 'react';
import { Tab } from '@headlessui/react';
import {
  ChartBarIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CalendarDaysIcon,
  ArrowPathIcon,
  ArrowTrendingUpIcon,
} from '@heroicons/react/24/outline';
import {
  useWorkflowAnalytics,
  useTimePerStage,
  useBottlenecks,
  useCompletionRates,
  useDeadlineRiskForecast,
  useRecalculateAnalytics,
} from '../../hooks/useWorkflowAnalytics';
import { TimePerStageChart } from './TimePerStageChart';
import { BottleneckIndicator } from './BottleneckIndicator';
import { CompletionRateCard } from './CompletionRateCard';
import { DeadlineRiskForecast } from './DeadlineRiskForecast';
import type { WorkflowAnalyticsSummary } from '../../types/workflowAnalytics';

interface WorkflowAnalyticsDashboardProps {
  onApplicationClick?: (cardId: string) => void;
}

const TABS = [
  { name: 'Overview', icon: ChartBarIcon },
  { name: 'Time Analysis', icon: ClockIcon },
  { name: 'Bottlenecks', icon: ExclamationTriangleIcon },
  { name: 'Deadlines', icon: CalendarDaysIcon },
];

function SummaryCard({
  label,
  value,
  subValue,
  icon,
  accentColor,
}: {
  label: string;
  value: string | number;
  subValue?: string;
  icon: React.ReactNode;
  accentColor: 'blue' | 'green' | 'amber' | 'violet' | 'cyan' | 'red';
}) {
  const colorClasses = {
    blue: { bg: 'bg-blue-50', border: 'border-blue-200', icon: 'text-blue-600', value: 'text-blue-700' },
    green: { bg: 'bg-emerald-50', border: 'border-emerald-200', icon: 'text-emerald-600', value: 'text-emerald-700' },
    amber: { bg: 'bg-amber-50', border: 'border-amber-200', icon: 'text-amber-600', value: 'text-amber-700' },
    violet: { bg: 'bg-violet-50', border: 'border-violet-200', icon: 'text-violet-600', value: 'text-violet-700' },
    cyan: { bg: 'bg-cyan-50', border: 'border-cyan-200', icon: 'text-cyan-600', value: 'text-cyan-700' },
    red: { bg: 'bg-red-50', border: 'border-red-200', icon: 'text-red-600', value: 'text-red-700' },
  };

  const colors = colorClasses[accentColor];

  return (
    <div className={`rounded-xl p-5 border transition-all duration-200 hover:shadow-md ${colors.bg} ${colors.border}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium text-[var(--gr-text-tertiary)] uppercase tracking-wider mb-1">
            {label}
          </p>
          <p className={`text-2xl font-display font-bold ${colors.value}`}>{value}</p>
          {subValue && <p className="text-xs text-[var(--gr-text-secondary)] mt-1">{subValue}</p>}
        </div>
        <div className={`p-2 rounded-lg ${colors.bg}`}>
          <div className={`h-5 w-5 ${colors.icon}`}>{icon}</div>
        </div>
      </div>
    </div>
  );
}

function OverviewSummary({ summary }: { summary: WorkflowAnalyticsSummary }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <SummaryCard
        label="Total Applications"
        value={summary.total_applications}
        icon={<ChartBarIcon className="h-5 w-5" />}
        accentColor="blue"
      />
      <SummaryCard
        label="Avg Cycle Time"
        value={`${summary.avg_cycle_time_days.toFixed(1)}d`}
        subValue="From start to completion"
        icon={<ClockIcon className="h-5 w-5" />}
        accentColor="violet"
      />
      <SummaryCard
        label="Completion Rate"
        value={`${summary.completion_rate.toFixed(1)}%`}
        icon={<ArrowTrendingUpIcon className="h-5 w-5" />}
        accentColor="green"
      />
      <SummaryCard
        label="Active Bottlenecks"
        value={summary.bottleneck_count}
        subValue={summary.most_problematic_stage ? `Worst: ${summary.most_problematic_stage}` : undefined}
        icon={<ExclamationTriangleIcon className="h-5 w-5" />}
        accentColor={summary.bottleneck_count > 0 ? 'amber' : 'green'}
      />
      <SummaryCard
        label="At-Risk Deadlines"
        value={summary.at_risk_deadlines}
        icon={<CalendarDaysIcon className="h-5 w-5" />}
        accentColor={summary.at_risk_deadlines > 0 ? 'red' : 'green'}
      />
      <SummaryCard
        label="Deadline Success"
        value={`${summary.deadline_success_rate.toFixed(1)}%`}
        subValue="Met on time"
        icon={<CalendarDaysIcon className="h-5 w-5" />}
        accentColor="cyan"
      />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-20 h-20 mx-auto rounded-2xl bg-gradient-to-br from-blue-50 to-blue-100 flex items-center justify-center mb-8 animate-float">
        <ChartBarIcon className="w-10 h-10 text-blue-500" />
      </div>
      <h3 className="text-2xl font-display font-semibold text-gray-900 mb-3">
        No workflow data yet
      </h3>
      <p className="text-gray-500 max-w-md mx-auto mb-8 leading-relaxed">
        Start tracking grant applications to see workflow analytics, bottleneck detection, and deadline risk forecasts.
      </p>
      <a
        href="/pipeline"
        className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-xl text-sm font-semibold hover:from-blue-700 hover:to-blue-600 transition-all shadow-lg shadow-blue-500/25 hover:-translate-y-0.5"
      >
        <ArrowTrendingUpIcon className="w-4 h-4" />
        Go to Pipeline
      </a>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="h-28 bg-gray-100 rounded-xl" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="h-80 bg-gray-100 rounded-xl" />
        <div className="h-80 bg-gray-100 rounded-xl" />
      </div>
    </div>
  );
}

export const WorkflowAnalyticsDashboard = React.memo(function WorkflowAnalyticsDashboard({ onApplicationClick }: WorkflowAnalyticsDashboardProps) {
  const [selectedTab, setSelectedTab] = useState(0);

  // Fetch all data
  const { data: summary, isLoading: loadingSummary, error: summaryError } = useWorkflowAnalytics();
  const { data: timePerStage, isLoading: loadingTime } = useTimePerStage();
  const { data: bottlenecks, isLoading: loadingBottlenecks } = useBottlenecks();
  const { data: completionRates, isLoading: loadingCompletion } = useCompletionRates();
  const { data: deadlineRisk, isLoading: loadingDeadlines } = useDeadlineRiskForecast();

  const recalculateMutation = useRecalculateAnalytics();

  const isLoading = loadingSummary || loadingTime || loadingBottlenecks || loadingCompletion || loadingDeadlines;
  const hasNoData = summary?.total_applications === 0;

  // Handle errors
  if (summaryError) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <ExclamationTriangleIcon className="h-12 w-12 text-red-500 mb-4" />
          <h3 className="text-lg font-medium text-[var(--gr-text-primary)] mb-2">
            Failed to load analytics
          </h3>
          <p className="text-sm text-[var(--gr-text-tertiary)] mb-4">
            There was an error loading workflow analytics data.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            <ArrowPathIcon className="h-4 w-4" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Empty state
  if (!isLoading && hasNoData) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-6">
        <EmptyState />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-semibold text-[var(--gr-text-primary)]">
            Workflow Analytics
          </h1>
          <p className="text-sm text-[var(--gr-text-secondary)] mt-1">
            Track application progress, identify bottlenecks, and forecast deadline risks
          </p>
        </div>
        <button
          onClick={() => recalculateMutation.mutate({})}
          disabled={recalculateMutation.isPending}
          className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-[var(--gr-border-default)] rounded-lg text-sm font-medium text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-secondary)] disabled:opacity-50"
        >
          <ArrowPathIcon className={`h-4 w-4 ${recalculateMutation.isPending ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <Tab.Group selectedIndex={selectedTab} onChange={setSelectedTab}>
        <Tab.List className="inline-flex p-1.5 bg-white/80 backdrop-blur-sm rounded-2xl shadow-sm border border-gray-100">
          {TABS.map((tab) => (
            <Tab
              key={tab.name}
              className={({ selected }) =>
                `flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-xl transition-all ${
                  selected
                    ? 'bg-blue-50 text-blue-600 shadow-sm'
                    : 'text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)]'
                }`
              }
            >
              <tab.icon className="w-4 h-4" />
              <span>{tab.name}</span>
            </Tab>
          ))}
        </Tab.List>

        <Tab.Panels className="mt-6">
          {/* Overview Tab */}
          <Tab.Panel className="space-y-6">
            {isLoading ? (
              <LoadingState />
            ) : (
              <>
                {summary && <OverviewSummary summary={summary} />}

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {completionRates && <CompletionRateCard data={completionRates} />}
                  {bottlenecks && <BottleneckIndicator data={bottlenecks} compact />}
                </div>

                {deadlineRisk && deadlineRisk.at_risk.length > 0 && (
                  <DeadlineRiskForecast
                    data={{
                      ...deadlineRisk,
                      at_risk: deadlineRisk.at_risk.slice(0, 3),
                    }}
                    onApplicationClick={onApplicationClick}
                  />
                )}
              </>
            )}
          </Tab.Panel>

          {/* Time Analysis Tab */}
          <Tab.Panel className="space-y-6">
            {timePerStage && <TimePerStageChart data={timePerStage} isLoading={loadingTime} />}
            {completionRates && <CompletionRateCard data={completionRates} isLoading={loadingCompletion} />}
          </Tab.Panel>

          {/* Bottlenecks Tab */}
          <Tab.Panel className="space-y-6">
            {bottlenecks && <BottleneckIndicator data={bottlenecks} isLoading={loadingBottlenecks} />}
          </Tab.Panel>

          {/* Deadlines Tab */}
          <Tab.Panel className="space-y-6">
            {deadlineRisk && (
              <DeadlineRiskForecast
                data={deadlineRisk}
                isLoading={loadingDeadlines}
                onApplicationClick={onApplicationClick}
              />
            )}
          </Tab.Panel>
        </Tab.Panels>
      </Tab.Group>
    </div>
  );
});

export default WorkflowAnalyticsDashboard;
