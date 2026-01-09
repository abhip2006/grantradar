import { useMemo, useState } from 'react';
import { UsersIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import type { CompetitionLevel } from '../types';

interface CompetitionBadgeProps {
  level: CompetitionLevel | null;
  score?: number; // 0-1
  showLabel?: boolean;
  size?: 'sm' | 'md';
  applicantsPerCycle?: number;
}

interface CompetitionConfig {
  label: string;
  shortLabel: string;
  colorClass: string;
  bgClass: string;
  borderClass: string;
  iconColor: string;
  description: string;
}

const COMPETITION_CONFIG: Record<CompetitionLevel, CompetitionConfig> = {
  low: {
    label: 'Low Competition',
    shortLabel: 'Low',
    colorClass: 'text-emerald-700',
    bgClass: 'bg-emerald-50',
    borderClass: 'border-emerald-200',
    iconColor: 'text-emerald-500',
    description: 'Fewer applicants - good success rate',
  },
  medium: {
    label: 'Moderate',
    shortLabel: 'Moderate',
    colorClass: 'text-amber-700',
    bgClass: 'bg-amber-50',
    borderClass: 'border-amber-200',
    iconColor: 'text-amber-500',
    description: 'Average number of applicants',
  },
  high: {
    label: 'Competitive',
    shortLabel: 'High',
    colorClass: 'text-orange-700',
    bgClass: 'bg-orange-50',
    borderClass: 'border-orange-200',
    iconColor: 'text-orange-500',
    description: 'Many applicants - prepare thoroughly',
  },
  very_high: {
    label: 'Highly Competitive',
    shortLabel: 'Very High',
    colorClass: 'text-red-700',
    bgClass: 'bg-red-50',
    borderClass: 'border-red-200',
    iconColor: 'text-red-500',
    description: 'Very selective - strong application required',
  },
};

export function CompetitionBadge({
  level,
  score,
  showLabel = true,
  size = 'sm',
  applicantsPerCycle,
}: CompetitionBadgeProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  const config = useMemo(() => {
    if (!level) return null;
    return COMPETITION_CONFIG[level];
  }, [level]);

  // If no level provided, show a neutral placeholder
  if (!level || !config) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-[var(--gr-gray-100)] text-[var(--gr-text-tertiary)] border border-[var(--gr-border-subtle)]">
        <UsersIcon className="w-3 h-3" />
        {showLabel && <span>--</span>}
      </span>
    );
  }

  const sizeClasses = {
    sm: {
      container: 'px-2 py-0.5 text-xs gap-1',
      icon: 'w-3 h-3',
    },
    md: {
      container: 'px-3 py-1 text-sm gap-1.5',
      icon: 'w-4 h-4',
    },
  };

  const tooltipContent = applicantsPerCycle
    ? `Based on ~${applicantsPerCycle.toLocaleString()} applications per cycle for this mechanism`
    : config.description;

  return (
    <div className="relative inline-block">
      <span
        className={`inline-flex items-center rounded-full font-medium border cursor-help ${sizeClasses[size].container} ${config.bgClass} ${config.colorClass} ${config.borderClass}`}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <UsersIcon className={`${sizeClasses[size].icon} ${config.iconColor}`} />
        {showLabel && (
          <span>{size === 'sm' ? config.shortLabel : config.label}</span>
        )}
        <InformationCircleIcon className={`${sizeClasses[size].icon} opacity-60`} />
      </span>

      {/* Tooltip */}
      {showTooltip && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 text-xs text-white bg-[var(--gr-gray-800)] rounded-lg shadow-lg whitespace-nowrap animate-fade-in">
          <div className="max-w-xs">
            <p className="font-medium mb-0.5">{config.label}</p>
            <p className="text-gray-300">{tooltipContent}</p>
            {score !== undefined && (
              <p className="text-gray-400 mt-1">
                Competition score: {Math.round(score * 100)}%
              </p>
            )}
          </div>
          {/* Arrow */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-[var(--gr-gray-800)]" />
        </div>
      )}
    </div>
  );
}

// Inline variant for use within text
export function CompetitionIndicator({
  level,
  score,
}: {
  level: CompetitionLevel | null;
  score?: number;
}) {
  const config = useMemo(() => {
    if (!level) return null;
    return COMPETITION_CONFIG[level];
  }, [level]);

  if (!level || !config) {
    return null;
  }

  // Simple colored dot indicator
  const dotColorClass = {
    low: 'bg-emerald-500',
    medium: 'bg-amber-500',
    high: 'bg-orange-500',
    very_high: 'bg-red-500',
  }[level];

  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-[var(--gr-text-secondary)]">
      <span className={`w-2 h-2 rounded-full ${dotColorClass}`} />
      <span>{config.shortLabel} competition</span>
      {score !== undefined && (
        <span className="text-[var(--gr-text-tertiary)]">
          ({Math.round(score * 100)}%)
        </span>
      )}
    </span>
  );
}

// Bar visualization for detail pages
export function CompetitionBar({
  level,
  score,
  showLabel = true,
}: {
  level: CompetitionLevel | null;
  score?: number;
  showLabel?: boolean;
}) {
  const config = useMemo(() => {
    if (!level) return null;
    return COMPETITION_CONFIG[level];
  }, [level]);

  // Calculate bar width based on score or level
  const barWidth = useMemo(() => {
    if (score !== undefined) {
      return Math.round(score * 100);
    }
    // Default widths based on level
    const levelWidths: Record<CompetitionLevel, number> = {
      low: 25,
      medium: 50,
      high: 75,
      very_high: 95,
    };
    return level ? levelWidths[level] : 0;
  }, [score, level]);

  if (!level || !config) {
    return null;
  }

  const barColorClass = {
    low: 'bg-emerald-500',
    medium: 'bg-amber-500',
    high: 'bg-orange-500',
    very_high: 'bg-red-500',
  }[level];

  return (
    <div className="space-y-1.5">
      {showLabel && (
        <div className="flex items-center justify-between text-xs">
          <span className={`font-medium ${config.colorClass}`}>
            {config.label}
          </span>
          <span className="text-[var(--gr-text-tertiary)]">
            {barWidth}%
          </span>
        </div>
      )}
      <div className="h-2 bg-[var(--gr-gray-100)] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColorClass}`}
          style={{ width: `${barWidth}%` }}
        />
      </div>
    </div>
  );
}

export default CompetitionBadge;
