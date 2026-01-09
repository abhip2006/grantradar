import { useMemo, useState } from 'react';
import { ClockIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import type { EffortComplexity } from '../types';

interface EffortEstimateProps {
  mechanism?: string;
  hoursEstimate?: number;
  complexity?: EffortComplexity;
  showDetails?: boolean;
  size?: 'sm' | 'md';
}

interface ComplexityConfig {
  label: string;
  colorClass: string;
  bgClass: string;
  borderClass: string;
  iconColor: string;
  description: string;
  defaultHours: { min: number; max: number };
  defaultWeeks: string;
}

const COMPLEXITY_CONFIG: Record<EffortComplexity, ComplexityConfig> = {
  simple: {
    label: 'Simple',
    colorClass: 'text-emerald-700',
    bgClass: 'bg-emerald-50',
    borderClass: 'border-emerald-200',
    iconColor: 'text-emerald-500',
    description: 'Straightforward application with standard requirements',
    defaultHours: { min: 10, max: 30 },
    defaultWeeks: '1-2 weeks',
  },
  moderate: {
    label: 'Moderate',
    colorClass: 'text-blue-700',
    bgClass: 'bg-blue-50',
    borderClass: 'border-blue-200',
    iconColor: 'text-blue-500',
    description: 'Requires detailed proposal and supporting documents',
    defaultHours: { min: 40, max: 80 },
    defaultWeeks: '2-4 weeks',
  },
  complex: {
    label: 'Complex',
    colorClass: 'text-purple-700',
    bgClass: 'bg-purple-50',
    borderClass: 'border-purple-200',
    iconColor: 'text-purple-500',
    description: 'Extensive documentation, multiple reviewers, detailed budget',
    defaultHours: { min: 80, max: 200 },
    defaultWeeks: '4-8 weeks',
  },
};

// Estimate complexity based on mechanism type
function estimateComplexityFromMechanism(mechanism?: string): EffortComplexity {
  if (!mechanism) return 'moderate';

  const mechanismUpper = mechanism.toUpperCase();

  // NIH mechanisms - generally complex
  if (mechanismUpper.includes('R01') || mechanismUpper.includes('U01') || mechanismUpper.includes('P01')) {
    return 'complex';
  }
  if (mechanismUpper.includes('R21') || mechanismUpper.includes('R03') || mechanismUpper.includes('K')) {
    return 'moderate';
  }

  // NSF mechanisms
  if (mechanismUpper.includes('CAREER') || mechanismUpper.includes('CENTER')) {
    return 'complex';
  }

  // Foundation grants are often simpler
  if (mechanismUpper.includes('LOI') || mechanismUpper.includes('LETTER')) {
    return 'simple';
  }

  // Fellowships
  if (mechanismUpper.includes('FELLOWSHIP') || mechanismUpper.includes('F31') || mechanismUpper.includes('F32')) {
    return 'moderate';
  }

  // Default to moderate
  return 'moderate';
}

export function EffortEstimate({
  mechanism,
  hoursEstimate,
  complexity,
  showDetails = false,
  size = 'sm',
}: EffortEstimateProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  // Determine complexity either from prop or mechanism
  const effectiveComplexity = useMemo(() => {
    if (complexity) return complexity;
    return estimateComplexityFromMechanism(mechanism);
  }, [complexity, mechanism]);

  const config = COMPLEXITY_CONFIG[effectiveComplexity];

  // Calculate hours/weeks display
  const timeDisplay = useMemo(() => {
    if (hoursEstimate) {
      if (hoursEstimate < 40) {
        return `~${hoursEstimate} hours`;
      }
      const weeks = Math.round(hoursEstimate / 40);
      if (weeks <= 1) {
        return `~${hoursEstimate} hours`;
      }
      return `~${weeks} weeks`;
    }
    return config.defaultWeeks;
  }, [hoursEstimate, config]);

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

  return (
    <div className="relative inline-block">
      <span
        className={`inline-flex items-center rounded-full font-medium border cursor-help ${sizeClasses[size].container} ${config.bgClass} ${config.colorClass} ${config.borderClass}`}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <ClockIcon className={`${sizeClasses[size].icon} ${config.iconColor}`} />
        <span>{timeDisplay}</span>
        <InformationCircleIcon className={`${sizeClasses[size].icon} opacity-60`} />
      </span>

      {/* Tooltip */}
      {showTooltip && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 text-xs text-white bg-[var(--gr-gray-800)] rounded-lg shadow-lg whitespace-nowrap animate-fade-in">
          <div className="max-w-xs">
            <p className="font-medium mb-0.5">{config.label} Application</p>
            <p className="text-gray-300">{config.description}</p>
            {mechanism && (
              <p className="text-gray-400 mt-1">Mechanism: {mechanism}</p>
            )}
          </div>
          {/* Arrow */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-[var(--gr-gray-800)]" />
        </div>
      )}
    </div>
  );
}

// Detailed card version for grant detail pages
export function EffortEstimateCard({
  mechanism,
  hoursEstimate,
  complexity,
}: {
  mechanism?: string;
  hoursEstimate?: number;
  complexity?: EffortComplexity;
}) {
  const effectiveComplexity = useMemo(() => {
    if (complexity) return complexity;
    return estimateComplexityFromMechanism(mechanism);
  }, [complexity, mechanism]);

  const config = COMPLEXITY_CONFIG[effectiveComplexity];

  // Calculate hours display
  const hoursDisplay = useMemo(() => {
    if (hoursEstimate) {
      return `${hoursEstimate} hours`;
    }
    return `${config.defaultHours.min}-${config.defaultHours.max} hours`;
  }, [hoursEstimate, config]);

  const weeksDisplay = useMemo(() => {
    if (hoursEstimate) {
      const weeks = Math.round(hoursEstimate / 40);
      if (weeks < 1) return 'Less than 1 week';
      if (weeks === 1) return '~1 week';
      return `~${weeks} weeks`;
    }
    return config.defaultWeeks;
  }, [hoursEstimate, config]);

  // Progress indicator (1-3 bars)
  const effortLevel = effectiveComplexity === 'simple' ? 1 : effectiveComplexity === 'moderate' ? 2 : 3;

  return (
    <div className={`rounded-xl p-4 border ${config.bgClass} ${config.borderClass}`}>
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg ${config.bgClass} border ${config.borderClass}`}>
          <ClockIcon className={`h-5 w-5 ${config.iconColor}`} />
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <p className={`text-xs uppercase tracking-wider font-semibold ${config.colorClass}`}>
              Estimated Effort
            </p>
            {/* Effort level indicator */}
            <div className="flex gap-1">
              {[1, 2, 3].map((level) => (
                <div
                  key={level}
                  className={`w-2 h-4 rounded-sm ${
                    level <= effortLevel
                      ? effectiveComplexity === 'simple'
                        ? 'bg-emerald-500'
                        : effectiveComplexity === 'moderate'
                        ? 'bg-blue-500'
                        : 'bg-purple-500'
                      : 'bg-gray-200'
                  }`}
                />
              ))}
            </div>
          </div>
          <p className={`text-lg font-bold ${config.colorClass.replace('700', '900')}`}>
            {weeksDisplay}
          </p>
          <p className="text-xs text-[var(--gr-text-tertiary)] mt-1">
            {hoursDisplay} typical work time
          </p>
          <div className="mt-2 flex items-center gap-2">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${config.bgClass} ${config.colorClass} border ${config.borderClass}`}
            >
              {config.label}
            </span>
            {mechanism && (
              <span className="text-xs text-[var(--gr-text-tertiary)]">
                {mechanism}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Inline text version
export function EffortIndicator({
  mechanism,
  hoursEstimate,
  complexity,
}: {
  mechanism?: string;
  hoursEstimate?: number;
  complexity?: EffortComplexity;
}) {
  const effectiveComplexity = useMemo(() => {
    if (complexity) return complexity;
    return estimateComplexityFromMechanism(mechanism);
  }, [complexity, mechanism]);

  const config = COMPLEXITY_CONFIG[effectiveComplexity];

  const timeDisplay = useMemo(() => {
    if (hoursEstimate) {
      if (hoursEstimate < 40) {
        return `~${hoursEstimate}h`;
      }
      const weeks = Math.round(hoursEstimate / 40);
      return `~${weeks}w`;
    }
    return config.defaultWeeks;
  }, [hoursEstimate, config]);

  return (
    <span className="inline-flex items-center gap-1 text-xs text-[var(--gr-text-secondary)]">
      <ClockIcon className={`w-3 h-3 ${config.iconColor}`} />
      <span>{timeDisplay}</span>
    </span>
  );
}

export default EffortEstimate;
