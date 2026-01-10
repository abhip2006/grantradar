import { motion } from 'motion/react';
import {
  BuildingLibraryIcon,
  CurrencyDollarIcon,
  UserIcon,
} from '@heroicons/react/24/outline';
import type { FundedProject } from '../../types/winners';

// Utility function
export function formatCurrency(amount: number): string {
  if (amount >= 1000000) {
    return `$${(amount / 1000000).toFixed(1)}M`;
  }
  if (amount >= 1000) {
    return `$${(amount / 1000).toFixed(0)}K`;
  }
  return `$${amount.toLocaleString()}`;
}

interface WinnerCardProps {
  project: FundedProject;
  onClick: () => void;
}

export function WinnerCard({ project, onClick }: WinnerCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="card-premium hover:shadow-editorial-lg transition-all cursor-pointer group"
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-display font-semibold text-[var(--gr-text-primary)] line-clamp-2 group-hover:text-[var(--gr-accent-forest)] transition-colors">
            {project.title}
          </h3>
          {project.principal_investigator?.name && (
            <p className="text-sm text-[var(--gr-text-secondary)] mt-1 flex items-center gap-1.5">
              <UserIcon className="h-3.5 w-3.5" />
              {project.principal_investigator.name}
            </p>
          )}
        </div>
        {project.activity_code && (
          <span className="flex-shrink-0 badge-mechanism">
            {project.activity_code}
          </span>
        )}
      </div>

      {/* Organization */}
      {project.organization?.name && (
        <div className="flex items-center gap-1.5 text-sm text-[var(--gr-text-tertiary)] mb-3">
          <BuildingLibraryIcon className="h-3.5 w-3.5" />
          <span className="truncate">{project.organization.name}</span>
          {project.organization.state && (
            <span className="text-[var(--gr-text-muted)]">
              ({project.organization.state})
            </span>
          )}
        </div>
      )}

      {/* Abstract Preview */}
      {project.abstract && (
        <p className="text-sm text-[var(--gr-text-secondary)] line-clamp-3 mb-4">
          {project.abstract}
        </p>
      )}

      {/* Footer Stats */}
      <div className="flex flex-wrap items-center gap-4 pt-3 border-t border-[var(--gr-border-light)]">
        {project.award_amount && (
          <div className="flex items-center gap-1.5 text-sm">
            <CurrencyDollarIcon className="h-4 w-4 text-[var(--gr-accent-gold)]" />
            <span className="font-medium text-[var(--gr-text-primary)]">
              {formatCurrency(project.award_amount)}
            </span>
          </div>
        )}
        {project.fiscal_year && (
          <div className="text-sm text-[var(--gr-text-tertiary)]">
            FY {project.fiscal_year}
          </div>
        )}
        {project.institute && (
          <div className="text-sm text-[var(--gr-text-tertiary)]">
            {project.institute}
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default WinnerCard;
