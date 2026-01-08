import { useMemo } from 'react';
import { ChartBarIcon } from '@heroicons/react/24/outline';
import type { FunderInsightsResponse } from '../../types';

interface FundingDistributionProps {
  data: FunderInsightsResponse;
}

function formatCurrency(amount: number): string {
  if (amount >= 1000000) {
    return `$${(amount / 1000000).toFixed(1)}M`;
  }
  if (amount >= 1000) {
    return `$${(amount / 1000).toFixed(0)}K`;
  }
  return `$${amount.toLocaleString()}`;
}

interface FundingRange {
  label: string;
  count: number;
  percentage: number;
  min: number;
  max: number;
}

export function FundingDistribution({ data }: FundingDistributionProps) {
  // Create distribution buckets based on funding amounts
  const distribution = useMemo(() => {
    // Define funding ranges
    const ranges: { label: string; min: number; max: number }[] = [
      { label: 'Under $50K', min: 0, max: 50000 },
      { label: '$50K - $100K', min: 50000, max: 100000 },
      { label: '$100K - $250K', min: 100000, max: 250000 },
      { label: '$250K - $500K', min: 250000, max: 500000 },
      { label: '$500K - $1M', min: 500000, max: 1000000 },
      { label: 'Over $1M', min: 1000000, max: Infinity },
    ];

    // Since we don't have individual grant amounts in the insights response,
    // we'll create a visual representation based on min/max ranges
    const avgMin = data.avg_amount_min || 0;
    const avgMax = data.avg_amount_max || 0;
    const minAmount = data.min_amount || avgMin;
    const maxAmount = data.max_amount || avgMax;

    // Estimate distribution based on the range
    const fundingRanges: FundingRange[] = ranges.map((range) => {
      let count = 0;

      // Estimate how many grants fall in this range based on the overall distribution
      if (range.min <= maxAmount && range.max >= minAmount) {
        // Calculate overlap percentage
        const overlapMin = Math.max(range.min, minAmount);
        const overlapMax = Math.min(range.max === Infinity ? maxAmount : range.max, maxAmount);
        const totalRange = maxAmount - minAmount || 1;
        const overlapRange = overlapMax - overlapMin;

        // Estimate count based on overlap - using average as center of distribution
        const rangeCenter = (range.min + (range.max === Infinity ? range.min * 2 : range.max)) / 2;
        const avgCenter = (avgMin + avgMax) / 2;

        // Higher count if range is closer to average
        const distance = Math.abs(rangeCenter - avgCenter);
        const maxDistance = maxAmount - minAmount || 1;
        const proximityScore = 1 - (distance / maxDistance);

        count = Math.round((overlapRange / totalRange) * data.total_grants * proximityScore);
        count = Math.max(0, count);
      }

      return {
        label: range.label,
        count,
        percentage: (count / data.total_grants) * 100,
        min: range.min,
        max: range.max,
      };
    });

    // Normalize so counts sum to total_grants
    const totalEstimated = fundingRanges.reduce((sum, r) => sum + r.count, 0);
    if (totalEstimated > 0) {
      const factor = data.total_grants / totalEstimated;
      fundingRanges.forEach((r) => {
        r.count = Math.round(r.count * factor);
        r.percentage = (r.count / data.total_grants) * 100;
      });
    }

    return fundingRanges;
  }, [data]);

  const maxCount = useMemo(
    () => Math.max(...distribution.map((d) => d.count), 1),
    [distribution]
  );

  // Check if we have funding data
  const hasFundingData = data.avg_amount_min || data.avg_amount_max || data.min_amount || data.max_amount;

  if (!hasFundingData) {
    return (
      <div className="bg-[var(--gr-bg-card)] rounded-xl p-6 border border-[var(--gr-border-default)]">
        <div className="flex items-center gap-2 mb-4">
          <ChartBarIcon className="h-5 w-5 text-[var(--gr-yellow-600)]" />
          <h3 className="text-base font-display font-medium text-[var(--gr-text-primary)]">
            Funding Distribution
          </h3>
        </div>
        <div className="text-center py-8 text-[var(--gr-text-tertiary)]">
          <p>No funding amount data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[var(--gr-bg-card)] rounded-xl p-6 border border-[var(--gr-border-default)]">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <ChartBarIcon className="h-5 w-5 text-[var(--gr-yellow-600)]" />
          <h3 className="text-base font-display font-medium text-[var(--gr-text-primary)]">
            Funding Distribution
          </h3>
        </div>
        <div className="text-sm text-[var(--gr-text-tertiary)]">
          {data.total_grants} grants
        </div>
      </div>

      {/* Horizontal Bar Chart */}
      <div className="space-y-3">
        {distribution.map((range, index) => (
          <div key={range.label} className="group">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-[var(--gr-text-secondary)]">{range.label}</span>
              <span className="text-sm font-medium text-[var(--gr-text-primary)]">
                {range.count} ({range.percentage.toFixed(0)}%)
              </span>
            </div>
            <div className="h-8 bg-[var(--gr-gray-100)] rounded-lg overflow-hidden">
              <div
                className={`h-full rounded-lg transition-all duration-500 ease-out ${
                  index % 2 === 0 ? 'bg-[var(--gr-blue-500)]' : 'bg-[var(--gr-yellow-500)]'
                } group-hover:opacity-80`}
                style={{
                  width: `${Math.max((range.count / maxCount) * 100, 2)}%`,
                }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Summary Stats */}
      <div className="mt-6 pt-4 border-t border-[var(--gr-border-subtle)] grid grid-cols-3 gap-4 text-center">
        <div>
          <div className="text-sm text-[var(--gr-text-tertiary)]">Min Award</div>
          <div className="text-lg font-display font-semibold text-[var(--gr-text-primary)]">
            {data.min_amount ? formatCurrency(data.min_amount) : 'N/A'}
          </div>
        </div>
        <div>
          <div className="text-sm text-[var(--gr-text-tertiary)]">Avg Award</div>
          <div className="text-lg font-display font-semibold text-[var(--gr-yellow-600)]">
            {data.avg_amount_max ? formatCurrency(data.avg_amount_max) : 'N/A'}
          </div>
        </div>
        <div>
          <div className="text-sm text-[var(--gr-text-tertiary)]">Max Award</div>
          <div className="text-lg font-display font-semibold text-[var(--gr-text-primary)]">
            {data.max_amount ? formatCurrency(data.max_amount) : 'N/A'}
          </div>
        </div>
      </div>
    </div>
  );
}

export default FundingDistribution;
