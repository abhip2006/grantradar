import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../../services/api';
import {
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  MinusIcon,
  TrophyIcon,
} from '@heroicons/react/24/outline';

interface FunderRanking {
  rank: number;
  funder: string;
  success_rate: number;
  total_awarded: number;
  total_applications: number;
  awarded_count: number;
  avg_award_amount: number;
  trend: 'up' | 'down' | 'stable';
}

interface FunderLeaderboardResponse {
  rankings: FunderRanking[];
  total_funders: number;
  period: string;
}

const TrendIcon = ({ trend }: { trend: string }) => {
  if (trend === 'up') {
    return <ArrowTrendingUpIcon className="w-4 h-4 text-emerald-500" />;
  }
  if (trend === 'down') {
    return <ArrowTrendingDownIcon className="w-4 h-4 text-red-500" />;
  }
  return <MinusIcon className="w-4 h-4 text-[var(--gr-text-tertiary)]" />;
};

const formatCurrency = (amount: number): string => {
  if (amount >= 1000000) {
    return `$${(amount / 1000000).toFixed(1)}M`;
  }
  if (amount >= 1000) {
    return `$${(amount / 1000).toFixed(0)}K`;
  }
  return `$${amount.toFixed(0)}`;
};

const getRankBadgeStyle = (rank: number): string => {
  if (rank === 1) return 'bg-amber-100 text-amber-700 ring-1 ring-amber-300';
  if (rank === 2) return 'bg-slate-100 text-slate-700 ring-1 ring-slate-300';
  if (rank === 3) return 'bg-orange-100 text-orange-700 ring-1 ring-orange-300';
  return 'bg-[var(--gr-bg-secondary)] text-[var(--gr-text-tertiary)]';
};

const getSuccessRateColor = (rate: number): string => {
  if (rate >= 50) return 'text-emerald-600';
  if (rate >= 25) return 'text-amber-600';
  return 'text-[var(--gr-text-secondary)]';
};

export function FunderLeaderboard() {
  const { data, isLoading, error } = useQuery<FunderLeaderboardResponse>({
    queryKey: ['analytics', 'funder-leaderboard'],
    queryFn: () => analyticsApi.getFunderLeaderboard(),
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)]">
        <div className="p-6 border-b border-[var(--gr-border-subtle)]">
          <div className="animate-pulse">
            <div className="h-6 w-48 bg-[var(--gr-bg-secondary)] rounded" />
          </div>
        </div>
        <div className="p-6">
          <div className="animate-pulse space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-[var(--gr-bg-secondary)] rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl border border-[var(--gr-border-default)]">
        <div className="p-6 border-b border-[var(--gr-border-subtle)]">
          <div className="flex items-center gap-2">
            <TrophyIcon className="w-5 h-5 text-amber-500" />
            <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
              Funder Leaderboard
            </h3>
          </div>
        </div>
        <div className="p-8 text-center text-[var(--gr-text-tertiary)]">
          Unable to load funder leaderboard data
        </div>
      </div>
    );
  }

  const rankings = data?.rankings || [];

  return (
    <div className="bg-white rounded-xl border border-[var(--gr-border-default)]">
      <div className="p-6 border-b border-[var(--gr-border-subtle)]">
        <div className="flex items-center gap-2">
          <TrophyIcon className="w-5 h-5 text-amber-500" />
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
            Funder Leaderboard
          </h3>
        </div>
        <p className="text-sm text-[var(--gr-text-tertiary)] mt-1">
          Ranked by success rate and total awarded
        </p>
      </div>

      {rankings.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[var(--gr-bg-secondary)] text-xs text-[var(--gr-text-tertiary)] uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Rank</th>
                <th className="px-4 py-3 text-left font-medium">Funder</th>
                <th className="px-4 py-3 text-right font-medium">Success Rate</th>
                <th className="px-4 py-3 text-right font-medium">Total Awarded</th>
                <th className="px-4 py-3 text-right font-medium">Awards</th>
                <th className="px-4 py-3 text-center font-medium">Trend</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--gr-border-subtle)]">
              {rankings.map((funder) => (
                <tr
                  key={funder.funder}
                  className="hover:bg-[var(--gr-bg-secondary)] transition-colors"
                >
                  <td className="px-4 py-3">
                    <span
                      className={`
                        inline-flex items-center justify-center w-7 h-7 rounded-full
                        text-xs font-bold ${getRankBadgeStyle(funder.rank)}
                      `}
                    >
                      {funder.rank}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-medium text-[var(--gr-text-primary)]">
                      {funder.funder}
                    </span>
                    {funder.avg_award_amount > 0 && (
                      <span className="block text-xs text-[var(--gr-text-tertiary)]">
                        Avg award: {formatCurrency(funder.avg_award_amount)}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className={`font-semibold ${getSuccessRateColor(funder.success_rate)}`}>
                      {funder.success_rate.toFixed(0)}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-[var(--gr-text-primary)] font-medium">
                    {formatCurrency(funder.total_awarded)}
                  </td>
                  <td className="px-4 py-3 text-right text-[var(--gr-text-secondary)]">
                    <span className="font-medium">{funder.awarded_count}</span>
                    <span className="text-[var(--gr-text-tertiary)]">
                      /{funder.total_applications}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center">
                      <TrendIcon trend={funder.trend} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="p-8 text-center text-[var(--gr-text-tertiary)]">
          No funder data available yet. Start tracking applications to see rankings.
        </div>
      )}
    </div>
  );
}

export default FunderLeaderboard;
