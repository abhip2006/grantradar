import { useNavigate } from 'react-router-dom';
import { XMarkIcon, ScaleIcon, ArrowRightIcon } from '@heroicons/react/24/outline';

interface CompareBarProps {
  selectedGrants: Array<{
    id: string;
    title: string;
  }>;
  onRemove: (grantId: string) => void;
  onClear: () => void;
  maxGrants?: number;
}

export function CompareBar({
  selectedGrants,
  onRemove,
  onClear,
  maxGrants = 4,
}: CompareBarProps) {
  const navigate = useNavigate();

  if (selectedGrants.length === 0) {
    return null;
  }

  const canCompare = selectedGrants.length >= 2;

  const handleCompare = () => {
    if (canCompare) {
      const grantIds = selectedGrants.map((g) => g.id).join(',');
      navigate(`/compare?grants=${grantIds}`);
    }
  };

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 animate-fade-in-up">
      <div className="compare-bar flex items-center gap-4 px-4 py-3 bg-[var(--gr-bg-card)] border border-[var(--gr-border-default)] rounded-2xl shadow-xl">
        {/* Icon */}
        <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-[var(--gr-blue-600)]/10">
          <ScaleIcon className="w-5 h-5 text-[var(--gr-blue-600)]" />
        </div>

        {/* Selected grants pills */}
        <div className="flex items-center gap-2 max-w-md overflow-x-auto">
          {selectedGrants.map((grant) => (
            <div
              key={grant.id}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--gr-bg-secondary)] rounded-lg border border-[var(--gr-border-subtle)] group"
            >
              <span className="text-sm font-medium text-[var(--gr-text-primary)] truncate max-w-[120px]">
                {grant.title}
              </span>
              <button
                onClick={() => onRemove(grant.id)}
                className="flex-shrink-0 p-0.5 rounded hover:bg-[var(--gr-gray-200)] text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)] transition-colors"
                aria-label={`Remove ${grant.title} from comparison`}
              >
                <XMarkIcon className="w-4 h-4" />
              </button>
            </div>
          ))}

          {/* Empty slots indicator */}
          {selectedGrants.length < maxGrants && (
            <div className="flex items-center gap-1">
              {[...Array(maxGrants - selectedGrants.length)].map((_, i) => (
                <div
                  key={i}
                  className="w-8 h-8 rounded-lg border-2 border-dashed border-[var(--gr-border-default)] flex items-center justify-center"
                >
                  <span className="text-xs text-[var(--gr-text-muted)]">+</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="w-px h-8 bg-[var(--gr-border-default)]" />

        {/* Actions */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-[var(--gr-text-tertiary)]">
            {selectedGrants.length}/{maxGrants}
          </span>

          <button
            onClick={onClear}
            className="btn-ghost text-sm text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)]"
          >
            Clear
          </button>

          <button
            onClick={handleCompare}
            disabled={!canCompare}
            className={`btn-primary flex items-center gap-2 ${
              !canCompare ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            Compare
            <ArrowRightIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Helper text */}
      {selectedGrants.length === 1 && (
        <p className="text-center text-sm text-[var(--gr-text-tertiary)] mt-2">
          Select at least 2 grants to compare
        </p>
      )}
    </div>
  );
}

export default CompareBar;
