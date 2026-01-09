import React from 'react';
import { CheckCircleIcon } from '@heroicons/react/24/solid';

interface ChecklistProgressProps {
  /** Total number of items */
  total: number;
  /** Number of completed items */
  completed: number;
  /** Progress percentage (0-100) */
  progressPercent?: number;
  /** Whether to show the count text */
  showCount?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Whether to use weighted percentage */
  weighted?: boolean;
  /** Custom class name */
  className?: string;
}

export const ChecklistProgress = React.memo(function ChecklistProgress({
  total,
  completed,
  progressPercent,
  showCount = true,
  size = 'md',
  weighted = false,
  className = '',
}: ChecklistProgressProps) {
  // Calculate progress if not provided
  const percent = progressPercent ?? (total > 0 ? (completed / total) * 100 : 0);
  const isComplete = completed === total && total > 0;

  // Size-based styles
  const sizeStyles = {
    sm: {
      bar: 'h-1.5',
      text: 'text-xs',
      icon: 'w-3 h-3',
      gap: 'gap-2',
    },
    md: {
      bar: 'h-2',
      text: 'text-sm',
      icon: 'w-4 h-4',
      gap: 'gap-3',
    },
    lg: {
      bar: 'h-3',
      text: 'text-base',
      icon: 'w-5 h-5',
      gap: 'gap-4',
    },
  };

  const styles = sizeStyles[size];

  // Color based on progress
  const getProgressColor = () => {
    if (isComplete) return 'bg-emerald-500';
    if (percent >= 75) return 'bg-emerald-400';
    if (percent >= 50) return 'bg-amber-400';
    if (percent >= 25) return 'bg-amber-500';
    return 'bg-slate-400';
  };

  const getTextColor = () => {
    if (isComplete) return 'text-emerald-600';
    if (percent >= 75) return 'text-emerald-600';
    if (percent >= 50) return 'text-amber-600';
    if (percent >= 25) return 'text-amber-600';
    return 'text-slate-500';
  };

  return (
    <div className={`flex items-center ${styles.gap} ${className}`}>
      {/* Progress bar */}
      <div className={`flex-1 bg-gray-200 rounded-full ${styles.bar} overflow-hidden`}>
        <div
          className={`${styles.bar} rounded-full transition-all duration-300 ${getProgressColor()}`}
          style={{ width: `${Math.min(percent, 100)}%` }}
        />
      </div>

      {/* Count/percentage text */}
      {showCount && (
        <div className={`flex items-center gap-1 ${styles.text} ${getTextColor()} font-medium`}>
          {isComplete && <CheckCircleIcon className={`${styles.icon} text-emerald-500`} />}
          {weighted ? (
            <span>{Math.round(percent)}%</span>
          ) : (
            <span>
              {completed}/{total}
            </span>
          )}
        </div>
      )}
    </div>
  );
});

/**
 * Compact progress indicator for card views
 */
export const ChecklistProgressBadge = React.memo(function ChecklistProgressBadge({
  total,
  completed,
  className = '',
}: {
  total: number;
  completed: number;
  className?: string;
}) {
  const percent = total > 0 ? (completed / total) * 100 : 0;
  const isComplete = completed === total && total > 0;

  const getBgColor = () => {
    if (isComplete) return 'bg-emerald-100 text-emerald-700';
    if (percent >= 75) return 'bg-emerald-50 text-emerald-600';
    if (percent >= 50) return 'bg-amber-50 text-amber-600';
    if (percent >= 25) return 'bg-amber-50 text-amber-700';
    return 'bg-slate-100 text-slate-600';
  };

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${getBgColor()} ${className}`}
    >
      {isComplete ? (
        <>
          <CheckCircleIcon className="w-3 h-3" />
          <span>Complete</span>
        </>
      ) : (
        <span>
          {completed}/{total}
        </span>
      )}
    </span>
  );
});

/**
 * Circular progress indicator
 */
export const ChecklistProgressCircle = React.memo(function ChecklistProgressCircle({
  total,
  completed,
  size = 40,
  strokeWidth = 4,
  className = '',
}: {
  total: number;
  completed: number;
  size?: number;
  strokeWidth?: number;
  className?: string;
}) {
  const percent = total > 0 ? (completed / total) * 100 : 0;
  const isComplete = completed === total && total > 0;

  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percent / 100) * circumference;

  const getStrokeColor = () => {
    if (isComplete) return '#10b981'; // emerald-500
    if (percent >= 75) return '#34d399'; // emerald-400
    if (percent >= 50) return '#fbbf24'; // amber-400
    if (percent >= 25) return '#f59e0b'; // amber-500
    return '#94a3b8'; // slate-400
  };

  return (
    <div className={`relative inline-flex items-center justify-center ${className}`}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="#e5e7eb"
          strokeWidth={strokeWidth}
          fill="none"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={getStrokeColor()}
          strokeWidth={strokeWidth}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-300"
        />
      </svg>
      {/* Center text */}
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-xs font-medium text-gray-700">{Math.round(percent)}%</span>
      </div>
    </div>
  );
});

export default ChecklistProgress;
