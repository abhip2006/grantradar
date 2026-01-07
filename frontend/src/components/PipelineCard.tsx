import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CalendarIcon,
  CurrencyDollarIcon,
  BuildingLibraryIcon,
  PencilSquareIcon,
  TrashIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ClockIcon,
  DocumentTextIcon,
  ArrowTopRightOnSquareIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from '@heroicons/react/24/outline';
import type { PipelineItem, ApplicationStage } from '../types';

interface PipelineCardProps {
  item: PipelineItem;
  onEdit?: (item: PipelineItem) => void;
  onDelete?: (itemId: string) => void;
  onMoveStage?: (itemId: string, stage: ApplicationStage) => void;
  isDragging?: boolean;
}

// Stage configuration
const STAGE_CONFIG: Record<
  ApplicationStage,
  { label: string; color: string; bgColor: string; borderColor: string }
> = {
  researching: {
    label: 'Researching',
    color: 'text-cyan-600',
    bgColor: 'bg-cyan-50',
    borderColor: 'border-cyan-200',
  },
  writing: {
    label: 'Writing',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
  },
  submitted: {
    label: 'Submitted',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
  awarded: {
    label: 'Awarded',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
  },
  rejected: {
    label: 'Rejected',
    color: 'text-slate-500',
    bgColor: 'bg-slate-50',
    borderColor: 'border-slate-200',
  },
};

export function PipelineCard({
  item,
  onEdit,
  onDelete,
  onMoveStage,
  isDragging = false,
}: PipelineCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { grant, stage, notes, days_until_deadline, target_date } = item;
  const stageConfig = STAGE_CONFIG[stage];

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatShortDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  // Deadline warning states
  const isDeadlinePast = days_until_deadline !== undefined && days_until_deadline < 0;
  const isDeadlineUrgent =
    days_until_deadline !== undefined && days_until_deadline >= 0 && days_until_deadline <= 7;
  const isDeadlineWarning =
    days_until_deadline !== undefined && days_until_deadline > 7 && days_until_deadline <= 14;

  const getDeadlineBadge = () => {
    if (days_until_deadline === undefined || days_until_deadline === null) return null;

    if (isDeadlinePast) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 border border-red-200">
          <XCircleIcon className="h-3 w-3" />
          Past due
        </span>
      );
    }

    if (isDeadlineUrgent) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 border border-red-200 animate-pulse">
          <ExclamationTriangleIcon className="h-3 w-3" />
          {days_until_deadline} days left
        </span>
      );
    }

    if (isDeadlineWarning) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 border border-amber-200">
          <ClockIcon className="h-3 w-3" />
          {days_until_deadline} days left
        </span>
      );
    }

    return null;
  };

  // Stage move options (exclude current stage)
  const moveOptions = (Object.keys(STAGE_CONFIG) as ApplicationStage[]).filter((s) => s !== stage);

  return (
    <div
      className={`
        bg-white rounded-lg border shadow-sm transition-all duration-200
        ${isDragging ? 'shadow-lg ring-2 ring-blue-500 rotate-2 scale-105' : 'hover:shadow-md'}
        ${stageConfig.borderColor}
      `}
    >
      {/* Header */}
      <div className="p-3">
        <div className="flex items-start justify-between gap-2 mb-2">
          <Link
            to={`/grants/${item.match_id || item.grant_id}`}
            className="flex-1 min-w-0 group"
          >
            <h4 className="text-sm font-medium text-[var(--gr-text-primary)] line-clamp-2 group-hover:text-[var(--gr-blue-600)] transition-colors">
              {grant.title}
            </h4>
          </Link>
          {getDeadlineBadge()}
        </div>

        {/* Agency */}
        {grant.agency && (
          <div className="flex items-center gap-1.5 text-xs text-[var(--gr-text-secondary)] mb-2">
            <BuildingLibraryIcon className="h-3.5 w-3.5 text-[var(--gr-text-tertiary)]" />
            <span className="truncate">{grant.agency}</span>
          </div>
        )}

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--gr-text-secondary)]">
          {(grant.amount_min || grant.amount_max) && (
            <div className="flex items-center gap-1">
              <CurrencyDollarIcon className="h-3.5 w-3.5 text-[var(--gr-yellow-500)]" />
              <span>
                {grant.amount_min && grant.amount_max
                  ? `${formatCurrency(grant.amount_min)} - ${formatCurrency(grant.amount_max)}`
                  : grant.amount_max
                  ? `Up to ${formatCurrency(grant.amount_max)}`
                  : formatCurrency(grant.amount_min!)}
              </span>
            </div>
          )}
          {grant.deadline && (
            <div className="flex items-center gap-1">
              <CalendarIcon className="h-3.5 w-3.5 text-[var(--gr-blue-500)]" />
              <span>{formatShortDate(grant.deadline)}</span>
            </div>
          )}
        </div>

        {/* Notes preview */}
        {notes && !isExpanded && (
          <div className="mt-2 text-xs text-[var(--gr-text-tertiary)] line-clamp-1 italic">
            {notes}
          </div>
        )}
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-3 pb-2 space-y-3 border-t border-[var(--gr-border-subtle)]">
          {/* Notes section */}
          {notes && (
            <div className="pt-2">
              <div className="flex items-center gap-1.5 text-xs font-medium text-[var(--gr-text-secondary)] mb-1">
                <DocumentTextIcon className="h-3.5 w-3.5" />
                Notes
              </div>
              <p className="text-xs text-[var(--gr-text-secondary)] whitespace-pre-wrap bg-[var(--gr-bg-secondary)] rounded p-2">
                {notes}
              </p>
            </div>
          )}

          {/* Target date */}
          {target_date && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-[var(--gr-text-tertiary)]">Target:</span>
              <span className="text-[var(--gr-text-secondary)]">{formatDate(target_date)}</span>
            </div>
          )}

          {/* Move stage buttons */}
          {onMoveStage && (
            <div className="pt-2">
              <div className="text-xs font-medium text-[var(--gr-text-tertiary)] mb-1.5">
                Move to:
              </div>
              <div className="flex flex-wrap gap-1.5">
                {moveOptions.map((targetStage) => {
                  const targetConfig = STAGE_CONFIG[targetStage];
                  return (
                    <button
                      key={targetStage}
                      onClick={() => onMoveStage(item.id, targetStage)}
                      className={`
                        px-2 py-1 rounded text-xs font-medium transition-colors
                        ${targetConfig.bgColor} ${targetConfig.color} ${targetConfig.borderColor}
                        border hover:opacity-80
                      `}
                    >
                      {targetConfig.label}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex items-center justify-between pt-2 border-t border-[var(--gr-border-subtle)]">
            <div className="flex items-center gap-2">
              {onEdit && (
                <button
                  onClick={() => onEdit(item)}
                  className="btn-ghost text-xs text-[var(--gr-text-tertiary)] hover:text-[var(--gr-blue-600)]"
                >
                  <PencilSquareIcon className="h-3.5 w-3.5" />
                  Edit
                </button>
              )}
              {onDelete && (
                <button
                  onClick={() => onDelete(item.id)}
                  className="btn-ghost text-xs text-[var(--gr-text-tertiary)] hover:text-[var(--gr-danger)]"
                >
                  <TrashIcon className="h-3.5 w-3.5" />
                  Remove
                </button>
              )}
            </div>
            {grant.url && (
              <a
                href={grant.url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-ghost text-xs text-[var(--gr-text-tertiary)] hover:text-[var(--gr-blue-600)]"
              >
                <ArrowTopRightOnSquareIcon className="h-3.5 w-3.5" />
                Source
              </a>
            )}
          </div>
        </div>
      )}

      {/* Expand/collapse toggle */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-1.5 text-xs text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-hover)] border-t border-[var(--gr-border-subtle)] flex items-center justify-center gap-1 transition-colors"
      >
        {isExpanded ? (
          <>
            <ChevronUpIcon className="h-3.5 w-3.5" />
            Less
          </>
        ) : (
          <>
            <ChevronDownIcon className="h-3.5 w-3.5" />
            More
          </>
        )}
      </button>
    </div>
  );
}

// Stage badge component for use elsewhere
export function StageBadge({ stage }: { stage: ApplicationStage }) {
  const config = STAGE_CONFIG[stage];
  return (
    <span
      className={`
        inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
        ${config.bgColor} ${config.color} ${config.borderColor} border
      `}
    >
      {config.label}
    </span>
  );
}

// Export stage config for use in pipeline page
export { STAGE_CONFIG };

export default PipelineCard;
