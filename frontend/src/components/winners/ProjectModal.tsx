import { motion } from 'motion/react';
import {
  BuildingLibraryIcon,
  CurrencyDollarIcon,
  UserIcon,
  DocumentTextIcon,
  ChartBarIcon,
  BeakerIcon,
  XMarkIcon,
  ArrowTrendingUpIcon,
} from '@heroicons/react/24/outline';
import type { FundedProject } from '../../types/winners';
import { formatCurrency } from './WinnerCard';

function formatDate(dateString?: string): string {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

interface ProjectModalProps {
  project: FundedProject;
  onClose: () => void;
}

export function ProjectModal({ project, onClose }: ProjectModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="relative w-full max-w-3xl max-h-[85vh] overflow-auto bg-[var(--gr-bg-primary)] rounded-2xl shadow-editorial-xl"
      >
        {/* Header */}
        <div className="sticky top-0 bg-[var(--gr-bg-primary)] border-b border-[var(--gr-border-light)] p-6 z-10">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                {project.activity_code && (
                  <span className="badge-mechanism">{project.activity_code}</span>
                )}
                {project.institute && (
                  <span className="text-sm text-[var(--gr-text-tertiary)]">
                    {project.institute_name || project.institute}
                  </span>
                )}
              </div>
              <h2 className="text-xl font-display font-bold text-[var(--gr-text-primary)]">
                {project.title}
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-secondary)] rounded-lg transition-colors"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Key Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {project.award_amount && (
              <div className="stat-card-compact">
                <CurrencyDollarIcon className="h-5 w-5 text-[var(--gr-accent-gold)]" />
                <div>
                  <div className="text-xs text-[var(--gr-text-tertiary)]">Award Amount</div>
                  <div className="text-lg font-display font-bold text-[var(--gr-text-primary)]">
                    {formatCurrency(project.award_amount)}
                  </div>
                </div>
              </div>
            )}
            {project.fiscal_year && (
              <div className="stat-card-compact">
                <ChartBarIcon className="h-5 w-5 text-[var(--gr-accent-forest)]" />
                <div>
                  <div className="text-xs text-[var(--gr-text-tertiary)]">Fiscal Year</div>
                  <div className="text-lg font-display font-bold text-[var(--gr-text-primary)]">
                    {project.fiscal_year}
                  </div>
                </div>
              </div>
            )}
            {project.start_date && (
              <div className="stat-card-compact">
                <BeakerIcon className="h-5 w-5 text-[var(--gr-blue-500)]" />
                <div>
                  <div className="text-xs text-[var(--gr-text-tertiary)]">Start Date</div>
                  <div className="text-sm font-medium text-[var(--gr-text-primary)]">
                    {formatDate(project.start_date)}
                  </div>
                </div>
              </div>
            )}
            {project.end_date && (
              <div className="stat-card-compact">
                <BeakerIcon className="h-5 w-5 text-[var(--gr-text-tertiary)]" />
                <div>
                  <div className="text-xs text-[var(--gr-text-tertiary)]">End Date</div>
                  <div className="text-sm font-medium text-[var(--gr-text-primary)]">
                    {formatDate(project.end_date)}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* PI & Organization */}
          <div className="grid md:grid-cols-2 gap-4">
            {project.principal_investigator && (
              <div className="card-premium-subtle">
                <h4 className="font-display font-semibold text-[var(--gr-text-primary)] mb-2 flex items-center gap-2">
                  <UserIcon className="h-4 w-4" />
                  Principal Investigator
                </h4>
                <p className="text-[var(--gr-text-secondary)]">
                  {project.principal_investigator.name}
                </p>
                {project.principal_investigator.email && (
                  <p className="text-sm text-[var(--gr-text-tertiary)]">
                    {project.principal_investigator.email}
                  </p>
                )}
              </div>
            )}
            {project.organization && (
              <div className="card-premium-subtle">
                <h4 className="font-display font-semibold text-[var(--gr-text-primary)] mb-2 flex items-center gap-2">
                  <BuildingLibraryIcon className="h-4 w-4" />
                  Institution
                </h4>
                <p className="text-[var(--gr-text-secondary)]">
                  {project.organization.name}
                </p>
                <p className="text-sm text-[var(--gr-text-tertiary)]">
                  {[project.organization.city, project.organization.state]
                    .filter(Boolean)
                    .join(', ')}
                </p>
              </div>
            )}
          </div>

          {/* Program Officer */}
          {project.program_officer && (
            <div className="card-premium-subtle">
              <h4 className="font-display font-semibold text-[var(--gr-text-primary)] mb-2">
                Program Officer
              </h4>
              <p className="text-[var(--gr-text-secondary)]">{project.program_officer}</p>
            </div>
          )}

          {/* Abstract */}
          {project.abstract && (
            <div>
              <h4 className="font-display font-semibold text-[var(--gr-text-primary)] mb-3 flex items-center gap-2">
                <DocumentTextIcon className="h-4 w-4" />
                Abstract
              </h4>
              <div className="prose-editorial">
                <p className="text-[var(--gr-text-secondary)] leading-relaxed whitespace-pre-wrap">
                  {project.abstract}
                </p>
              </div>
            </div>
          )}

          {/* Terms/Keywords */}
          {project.terms && (
            <div>
              <h4 className="font-display font-semibold text-[var(--gr-text-primary)] mb-3">
                Keywords
              </h4>
              <div className="flex flex-wrap gap-2">
                {project.terms.split(';').map((term, i) => (
                  <span
                    key={i}
                    className="px-2.5 py-1 text-xs bg-[var(--gr-bg-secondary)] text-[var(--gr-text-secondary)] rounded-full"
                  >
                    {term.trim()}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Link to NIH Reporter */}
          {project.source_url && (
            <div className="pt-4 border-t border-[var(--gr-border-light)]">
              <a
                href={project.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary-editorial inline-flex items-center gap-2"
              >
                View on NIH Reporter
                <ArrowTrendingUpIcon className="h-4 w-4" />
              </a>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

export default ProjectModal;
