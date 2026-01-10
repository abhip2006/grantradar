import { useState } from 'react';
import { motion } from 'motion/react';
import {
  FunnelIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from '@heroicons/react/24/outline';
import type { WinnersFilters } from '../../types/winners';
import { NIH_INSTITUTES, ACTIVITY_CODES } from '../../types/winners';

interface WinnersFilterPanelProps {
  filters: WinnersFilters;
  onChange: (filters: WinnersFilters) => void;
  onReset: () => void;
}

export function WinnersFilterPanel({ filters, onChange, onReset }: WinnersFilterPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const currentYear = new Date().getFullYear();
  const yearOptions = Array.from({ length: 10 }, (_, i) => currentYear - i);

  return (
    <div className="card-premium mb-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FunnelIcon className="h-5 w-5 text-[var(--gr-accent-forest)]" />
          <span className="font-display font-semibold text-[var(--gr-text-primary)]">
            Filters
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onReset}
            className="text-sm text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-primary)]"
          >
            Reset
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 hover:bg-[var(--gr-bg-secondary)] rounded-lg"
          >
            {isExpanded ? (
              <ChevronUpIcon className="h-5 w-5" />
            ) : (
              <ChevronDownIcon className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>

      {isExpanded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="mt-4 pt-4 border-t border-[var(--gr-border-light)] grid gap-4 md:grid-cols-2 lg:grid-cols-3"
        >
          {/* Activity Codes */}
          <div>
            <label className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
              Activity Code
            </label>
            <select
              value={filters.activityCodes[0] || ''}
              onChange={(e) =>
                onChange({
                  ...filters,
                  activityCodes: e.target.value ? [e.target.value] : [],
                })
              }
              className="input-editorial w-full"
            >
              <option value="">All Mechanisms</option>
              {ACTIVITY_CODES.map((code) => (
                <option key={code.value} value={code.value}>
                  {code.label}
                </option>
              ))}
            </select>
          </div>

          {/* Institute */}
          <div>
            <label className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
              NIH Institute
            </label>
            <select
              value={filters.institute}
              onChange={(e) => onChange({ ...filters, institute: e.target.value })}
              className="input-editorial w-full"
            >
              <option value="">All Institutes</option>
              {NIH_INSTITUTES.map((inst) => (
                <option key={inst.value} value={inst.value}>
                  {inst.label}
                </option>
              ))}
            </select>
          </div>

          {/* Fiscal Year */}
          <div>
            <label className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
              Fiscal Year
            </label>
            <select
              value={filters.fiscalYears[0] || ''}
              onChange={(e) =>
                onChange({
                  ...filters,
                  fiscalYears: e.target.value ? [parseInt(e.target.value)] : [],
                })
              }
              className="input-editorial w-full"
            >
              <option value="">All Years</option>
              {yearOptions.map((year) => (
                <option key={year} value={year}>
                  FY {year}
                </option>
              ))}
            </select>
          </div>

          {/* Institution */}
          <div>
            <label className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
              Institution
            </label>
            <input
              type="text"
              value={filters.institution}
              onChange={(e) => onChange({ ...filters, institution: e.target.value })}
              placeholder="Search by institution..."
              className="input-editorial w-full"
            />
          </div>

          {/* PI Name */}
          <div>
            <label className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
              PI Name
            </label>
            <input
              type="text"
              value={filters.piName}
              onChange={(e) => onChange({ ...filters, piName: e.target.value })}
              placeholder="Search by PI name..."
              className="input-editorial w-full"
            />
          </div>

          {/* State */}
          <div>
            <label className="block text-sm font-medium text-[var(--gr-text-secondary)] mb-2">
              State
            </label>
            <input
              type="text"
              value={filters.state}
              onChange={(e) => onChange({ ...filters, state: e.target.value })}
              placeholder="e.g., CA, NY..."
              maxLength={2}
              className="input-editorial w-full"
            />
          </div>
        </motion.div>
      )}
    </div>
  );
}

export default WinnersFilterPanel;
