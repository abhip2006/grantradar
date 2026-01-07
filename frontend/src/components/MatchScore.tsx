import { useMemo } from 'react';

interface MatchScoreProps {
  score: number;
  reasoning?: string;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export function MatchScore({
  score,
  reasoning,
  size = 'md',
  showLabel = true,
}: MatchScoreProps) {
  const { colorClass, label, glowClass } = useMemo(() => {
    if (score >= 85) {
      return {
        colorClass: 'text-[var(--gr-emerald-400)]',
        glowClass: 'score-ring-high',
        label: 'Excellent Match',
      };
    } else if (score >= 70) {
      return {
        colorClass: 'text-[var(--gr-blue-600)]',
        glowClass: 'score-ring-medium',
        label: 'Good Match',
      };
    } else {
      return {
        colorClass: 'text-[var(--gr-text-secondary)]',
        glowClass: 'score-ring-low',
        label: 'Fair Match',
      };
    }
  }, [score]);

  const sizeClasses = {
    sm: { container: 'w-10 h-10', text: 'text-xs' },
    md: { container: 'w-14 h-14', text: 'text-sm' },
    lg: { container: 'w-20 h-20', text: 'text-lg' },
  };

  const circumference = 2 * Math.PI * 20;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className={`score-ring ${glowClass} ${sizeClasses[size].container}`}>
        <svg viewBox="0 0 48 48">
          <circle
            cx="24"
            cy="24"
            r="20"
            className="score-ring-bg"
          />
          <circle
            cx="24"
            cy="24"
            r="20"
            className="score-ring-progress"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
          />
        </svg>
        <span className={`score-value ${sizeClasses[size].text}`}>
          {Math.round(score)}
        </span>
      </div>
      {showLabel && (
        <span className={`${sizeClasses[size].text === 'text-xs' ? 'text-[10px]' : 'text-xs'} ${colorClass} font-medium uppercase tracking-wider`}>
          {label}
        </span>
      )}
      {reasoning && (
        <p className="text-xs text-[var(--gr-text-tertiary)] mt-1 max-w-xs text-center">
          {reasoning}
        </p>
      )}
    </div>
  );
}

// Badge version for cards
export function MatchScoreBadge({ score }: { score: number }) {
  const { colorClass, bgClass } = useMemo(() => {
    if (score >= 85) {
      return {
        colorClass: 'text-[var(--gr-emerald-400)]',
        bgClass: 'bg-[var(--gr-emerald-500)]/15 border-[var(--gr-emerald-500)]/30',
      };
    } else if (score >= 70) {
      return {
        colorClass: 'text-[var(--gr-blue-600)]',
        bgClass: 'bg-[var(--gr-blue-600)]/15 border-[var(--gr-blue-600)]/30',
      };
    } else {
      return {
        colorClass: 'text-[var(--gr-text-secondary)]',
        bgClass: 'bg-[var(--gr-slate-700)] border-[var(--gr-border-default)]',
      };
    }
  }, [score]);

  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${bgClass} ${colorClass}`}
    >
      {Math.round(score)}% Match
    </span>
  );
}

export default MatchScore;
