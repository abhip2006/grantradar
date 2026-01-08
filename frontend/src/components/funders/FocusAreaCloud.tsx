import { useMemo } from 'react';
import { TagIcon } from '@heroicons/react/24/outline';

interface FocusAreaCloudProps {
  focusAreas: string[];
  focusAreaCounts: Record<string, number>;
}

// Color palette for tags
const TAG_COLORS = [
  { bg: 'bg-[var(--gr-blue-50)]', text: 'text-[var(--gr-blue-700)]', border: 'border-[var(--gr-blue-200)]' },
  { bg: 'bg-[var(--gr-yellow-50)]', text: 'text-[var(--gr-yellow-700)]', border: 'border-[var(--gr-yellow-200)]' },
  { bg: 'bg-[rgba(34,197,94,0.1)]', text: 'text-[var(--gr-green-600)]', border: 'border-[rgba(34,197,94,0.2)]' },
  { bg: 'bg-[var(--gr-gray-100)]', text: 'text-[var(--gr-gray-700)]', border: 'border-[var(--gr-gray-200)]' },
];

export function FocusAreaCloud({ focusAreas, focusAreaCounts }: FocusAreaCloudProps) {
  // Sort areas by count and compute sizes
  const sortedAreas = useMemo(() => {
    return focusAreas
      .map((area) => ({
        name: area,
        count: focusAreaCounts[area] || 0,
      }))
      .sort((a, b) => b.count - a.count);
  }, [focusAreas, focusAreaCounts]);

  const maxCount = useMemo(
    () => Math.max(...sortedAreas.map((a) => a.count), 1),
    [sortedAreas]
  );

  const minCount = useMemo(
    () => Math.min(...sortedAreas.filter((a) => a.count > 0).map((a) => a.count), 1),
    [sortedAreas]
  );

  // Get font size class based on count
  const getSizeClass = (count: number): string => {
    const ratio = (count - minCount) / (maxCount - minCount || 1);
    if (ratio >= 0.8) return 'text-lg px-4 py-2';
    if (ratio >= 0.6) return 'text-base px-3 py-1.5';
    if (ratio >= 0.4) return 'text-sm px-3 py-1.5';
    if (ratio >= 0.2) return 'text-sm px-2.5 py-1';
    return 'text-xs px-2 py-1';
  };

  // Get color based on index (for variety)
  const getColor = (index: number) => TAG_COLORS[index % TAG_COLORS.length];

  // Get prominence badge for top areas
  const getProminenceBadge = (rank: number): React.ReactNode => {
    if (rank === 0) {
      return (
        <span className="absolute -top-1 -right-1 w-4 h-4 bg-[var(--gr-yellow-400)] rounded-full flex items-center justify-center text-[10px] font-bold text-[var(--gr-gray-900)]">
          1
        </span>
      );
    }
    if (rank === 1) {
      return (
        <span className="absolute -top-1 -right-1 w-4 h-4 bg-[var(--gr-gray-300)] rounded-full flex items-center justify-center text-[10px] font-bold text-[var(--gr-gray-700)]">
          2
        </span>
      );
    }
    if (rank === 2) {
      return (
        <span className="absolute -top-1 -right-1 w-4 h-4 bg-[#CD7F32] rounded-full flex items-center justify-center text-[10px] font-bold text-white">
          3
        </span>
      );
    }
    return null;
  };

  if (sortedAreas.length === 0) {
    return (
      <div className="bg-[var(--gr-bg-card)] rounded-xl p-6 border border-[var(--gr-border-default)]">
        <div className="flex items-center gap-2 mb-4">
          <TagIcon className="h-5 w-5 text-[var(--gr-green-600)]" />
          <h3 className="text-base font-display font-medium text-[var(--gr-text-primary)]">
            Focus Areas
          </h3>
        </div>
        <div className="text-center py-8 text-[var(--gr-text-tertiary)]">
          <p>No focus areas available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[var(--gr-bg-card)] rounded-xl p-6 border border-[var(--gr-border-default)]">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <TagIcon className="h-5 w-5 text-[var(--gr-green-600)]" />
          <h3 className="text-base font-display font-medium text-[var(--gr-text-primary)]">
            Focus Areas
          </h3>
        </div>
        <div className="text-sm text-[var(--gr-text-tertiary)]">
          {sortedAreas.length} categories
        </div>
      </div>

      {/* Tag Cloud */}
      <div className="flex flex-wrap gap-2 mb-6">
        {sortedAreas.map((area, index) => {
          const color = getColor(index);
          return (
            <div
              key={area.name}
              className={`relative inline-flex items-center gap-1.5 ${getSizeClass(area.count)}
                ${color.bg} ${color.text} border ${color.border}
                rounded-lg font-medium transition-all hover:scale-105 cursor-default`}
              title={`${area.name}: ${area.count} grants`}
            >
              {area.name}
              <span className="opacity-60 text-xs">({area.count})</span>
              {getProminenceBadge(index)}
            </div>
          );
        })}
      </div>

      {/* Top 5 Summary List */}
      <div className="border-t border-[var(--gr-border-subtle)] pt-4">
        <h4 className="text-sm font-medium text-[var(--gr-text-secondary)] mb-3">
          Top Focus Areas
        </h4>
        <div className="space-y-2">
          {sortedAreas.slice(0, 5).map((area, index) => {
            const percentage = (area.count / maxCount) * 100;
            return (
              <div key={area.name} className="flex items-center gap-3">
                <span className="w-6 text-sm font-medium text-[var(--gr-text-tertiary)]">
                  #{index + 1}
                </span>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-[var(--gr-text-primary)] truncate max-w-[200px]">
                      {area.name}
                    </span>
                    <span className="text-sm font-medium text-[var(--gr-text-secondary)]">
                      {area.count}
                    </span>
                  </div>
                  <div className="h-1.5 bg-[var(--gr-gray-100)] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[var(--gr-blue-500)] rounded-full transition-all duration-500"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default FocusAreaCloud;
