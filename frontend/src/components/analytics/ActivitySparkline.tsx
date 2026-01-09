import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../../services/api';
import { AreaChart, Area, ResponsiveContainer, Tooltip, XAxis } from 'recharts';
import { format, parseISO } from 'date-fns';
import { motion } from 'motion/react';
import { ArrowTrendingUpIcon, ArrowTrendingDownIcon } from '@heroicons/react/24/outline';

type MetricType = 'applications_created' | 'stage_changes' | 'matches_saved';

interface ActivitySparklineProps {
  metric: MetricType;
  title: string;
  color: string;
}

interface DailyActivity {
  date: string;
  applications_created: number;
  stage_changes: number;
  matches_saved: number;
}

interface ActivityTimelineResponse {
  daily: DailyActivity[];
  totals: Record<MetricType, number>;
  avg_daily: Record<MetricType, number>;
  period_days: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    dataKey: string;
    payload: DailyActivity;
  }>;
  metric: MetricType;
}

function CustomTooltip({ active, payload, metric }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;
  const value = data[metric];

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="tooltip-premium"
    >
      <p className="font-medium mb-0.5">
        {format(parseISO(data.date), 'MMM d, yyyy')}
      </p>
      <p className="text-gray-300">
        {value} {value === 1 ? 'activity' : 'activities'}
      </p>
    </motion.div>
  );
}

export function ActivitySparkline({ metric, title, color }: ActivitySparklineProps) {
  const { data, isLoading, error } = useQuery<ActivityTimelineResponse>({
    queryKey: ['analytics', 'activity-timeline'],
    queryFn: () => analyticsApi.getActivityTimeline(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="flex items-center justify-between mb-3">
          <div className="skeleton-premium h-4 w-28" />
          <div className="skeleton-premium h-8 w-14 rounded-lg" />
        </div>
        <div className="skeleton-premium h-[60px] w-full rounded-lg" />
        <div className="skeleton-premium h-3 w-20 mt-2" />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-[var(--gr-text-tertiary)]">{title}</span>
          <span className="text-2xl font-display font-bold text-[var(--gr-text-primary)]">--</span>
        </div>
        <div className="h-[60px] flex items-center justify-center text-xs text-[var(--gr-text-tertiary)]">
          Unable to load
        </div>
      </div>
    );
  }

  // Get last 14 days of data
  const chartData = data?.daily?.slice(-14) || [];
  const total = data?.totals?.[metric] || 0;
  const avg = data?.avg_daily?.[metric] || 0;

  // Calculate trend (compare last 7 days to previous 7 days)
  const last7 = chartData.slice(-7).reduce((sum, d) => sum + d[metric], 0);
  const prev7 = chartData.slice(0, 7).reduce((sum, d) => sum + d[metric], 0);
  const trend = prev7 > 0 ? Math.round(((last7 - prev7) / prev7) * 100) : 0;

  // Generate a unique gradient ID for each metric
  const gradientId = `gradient-sparkline-${metric}`;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[var(--gr-text-secondary)]">{title}</span>
          {trend !== 0 && (
            <span className={`trend-indicator ${trend > 0 ? 'positive' : 'negative'}`}>
              {trend > 0 ? (
                <ArrowTrendingUpIcon className="w-3 h-3" />
              ) : (
                <ArrowTrendingDownIcon className="w-3 h-3" />
              )}
              {Math.abs(trend)}%
            </span>
          )}
        </div>
        <motion.span
          key={total}
          initial={{ scale: 1.1, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="text-2xl font-display font-bold text-[var(--gr-text-primary)]"
        >
          {total.toLocaleString()}
        </motion.span>
      </div>

      {chartData.length > 0 ? (
        <div className="sparkline-animated">
          <ResponsiveContainer width="100%" height={60}>
            <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={color} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" hide />
              <Tooltip
                content={({ active, payload }) => (
                  <CustomTooltip
                    active={active}
                    payload={payload as CustomTooltipProps['payload']}
                    metric={metric}
                  />
                )}
                cursor={{
                  stroke: color,
                  strokeWidth: 1,
                  strokeDasharray: '4 2',
                }}
              />
              <Area
                type="monotone"
                dataKey={metric}
                stroke={color}
                fill={`url(#${gradientId})`}
                strokeWidth={2.5}
                dot={false}
                activeDot={{
                  r: 5,
                  fill: color,
                  strokeWidth: 2,
                  stroke: '#ffffff',
                }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="h-[60px] flex items-center justify-center text-xs text-[var(--gr-text-tertiary)]">
          No activity data
        </div>
      )}

      <div className="flex items-center justify-between mt-2 text-xs text-[var(--gr-text-tertiary)]">
        <span>Last 14 days</span>
        <span>Avg: {avg.toFixed(1)}/day</span>
      </div>
    </motion.div>
  );
}

// Preset configurations for common metrics with premium colors
export function ApplicationsCreatedSparkline() {
  return (
    <ActivitySparkline
      metric="applications_created"
      title="Applications Created"
      color="#14b8a6" // teal-500
    />
  );
}

export function StageChangesSparkline() {
  return (
    <ActivitySparkline
      metric="stage_changes"
      title="Stage Changes"
      color="#2d5a47" // forest-500
    />
  );
}

export function MatchesSavedSparkline() {
  return (
    <ActivitySparkline
      metric="matches_saved"
      title="Matches Saved"
      color="#22c55e" // green-500
    />
  );
}

export default ActivitySparkline;
