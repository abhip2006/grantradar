import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../../services/api';
import { AreaChart, Area, ResponsiveContainer, Tooltip, XAxis } from 'recharts';
import { format, parseISO } from 'date-fns';

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
    <div className="bg-white border border-[var(--gr-border-default)] rounded-lg shadow-lg px-2 py-1 text-xs">
      <p className="font-medium text-[var(--gr-text-primary)]">
        {format(parseISO(data.date), 'MMM d')}
      </p>
      <p className="text-[var(--gr-text-secondary)]">
        {value} {value === 1 ? 'activity' : 'activities'}
      </p>
    </div>
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
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-4">
        <div className="animate-pulse">
          <div className="flex items-center justify-between mb-2">
            <div className="h-4 w-24 bg-[var(--gr-bg-secondary)] rounded" />
            <div className="h-6 w-12 bg-[var(--gr-bg-secondary)] rounded" />
          </div>
          <div className="h-[50px] bg-[var(--gr-bg-secondary)] rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-[var(--gr-text-tertiary)]">{title}</span>
          <span className="text-lg font-semibold text-[var(--gr-text-primary)]">--</span>
        </div>
        <div className="h-[50px] flex items-center justify-center text-xs text-[var(--gr-text-tertiary)]">
          Unable to load
        </div>
      </div>
    );
  }

  // Get last 14 days of data
  const chartData = data?.daily?.slice(-14) || [];
  const total = data?.totals?.[metric] || 0;
  const avg = data?.avg_daily?.[metric] || 0;

  // Generate a unique gradient ID for each metric
  const gradientId = `gradient-${metric}-${Math.random().toString(36).slice(2, 9)}`;

  return (
    <div className="bg-white rounded-xl border border-[var(--gr-border-default)] p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-[var(--gr-text-tertiary)]">{title}</span>
        <span className="text-lg font-display font-semibold text-[var(--gr-text-primary)]">
          {total.toLocaleString()}
        </span>
      </div>

      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={50}>
          <AreaChart data={chartData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
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
            />
            <Area
              type="monotone"
              dataKey={metric}
              stroke={color}
              fill={`url(#${gradientId})`}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: color, strokeWidth: 0 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <div className="h-[50px] flex items-center justify-center text-xs text-[var(--gr-text-tertiary)]">
          No activity data
        </div>
      )}

      <div className="text-xs text-[var(--gr-text-tertiary)] mt-1">
        Avg: {avg.toFixed(1)}/day
      </div>
    </div>
  );
}

// Preset configurations for common metrics
export function ApplicationsCreatedSparkline() {
  return (
    <ActivitySparkline
      metric="applications_created"
      title="Applications Created"
      color="#3b82f6"
    />
  );
}

export function StageChangesSparkline() {
  return (
    <ActivitySparkline
      metric="stage_changes"
      title="Stage Changes"
      color="#f59e0b"
    />
  );
}

export function MatchesSavedSparkline() {
  return (
    <ActivitySparkline
      metric="matches_saved"
      title="Matches Saved"
      color="#22c55e"
    />
  );
}

export default ActivitySparkline;
