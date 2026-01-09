/**
 * Advanced Filters Component
 * Expandable panel with comprehensive grant filtering options
 */
import { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useQuery } from '@tanstack/react-query';
import {
  ChevronDownIcon,
  ChevronUpIcon,
  AdjustmentsHorizontalIcon,
  XMarkIcon,
  FunnelIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { StarIcon } from '@heroicons/react/24/solid';
import { grantsApi } from '../services/api';
import type { AdvancedGrantFilters, MatchScoreRange } from '../types';
import { MATCH_SCORE_RANGES } from '../types';

interface AdvancedFiltersProps {
  filters: AdvancedGrantFilters;
  onFiltersChange: (filters: AdvancedGrantFilters) => void;
  onClear: () => void;
}

// Career stage options (static for now, will be populated from backend)
const CAREER_STAGE_OPTIONS = [
  'Graduate Student',
  'Postdoctoral Fellow',
  'Early Career Faculty',
  'Mid-Career Faculty',
  'Senior Faculty',
  'Research Scientist',
  'Independent Researcher',
];

// Citizenship options
const CITIZENSHIP_OPTIONS = [
  'U.S. Citizen',
  'U.S. Permanent Resident',
  'Non-U.S. Citizen (with visa)',
  'International',
  'No Restriction',
];

// Institution type options
const INSTITUTION_TYPE_OPTIONS = [
  'Research University',
  'Liberal Arts College',
  'Community College',
  'Medical School',
  'Non-profit Organization',
  'Government Agency',
  'For-profit Company',
  'International Institution',
];

// Award type options
const AWARD_TYPE_OPTIONS = [
  'Research',
  'Training',
  'Fellowship',
  'Career Development',
  'Equipment',
  'Conference',
  'Seed',
];

// Award duration options
const AWARD_DURATION_OPTIONS = [
  { value: 'less_than_1', label: '< 1 year' },
  { value: '1_to_2', label: '1-2 years' },
  { value: '2_to_3', label: '2-3 years' },
  { value: '3_to_5', label: '3-5 years' },
  { value: '5_plus', label: '5+ years' },
];

// Indirect cost policy options
const INDIRECT_COST_OPTIONS = [
  { value: 'full', label: 'Full' },
  { value: 'capped', label: 'Capped' },
  { value: 'none', label: 'None' },
  { value: 'training_rate', label: 'Training Rate' },
];

// Submission type options
const SUBMISSION_TYPE_OPTIONS = [
  'New',
  'Resubmission',
  'Renewal',
  'Supplement',
];

// Deadline proximity quick filter options
const DEADLINE_PROXIMITY_OPTIONS = [
  { value: '30', label: 'Due in 30 days' },
  { value: '60', label: 'Due in 60 days' },
  { value: '90', label: 'Due in 90 days' },
];

export default function AdvancedFilters({
  filters,
  onFiltersChange,
  onClear,
}: AdvancedFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [localFilters, setLocalFilters] = useState<AdvancedGrantFilters>(filters);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    eligibility: true,
    awardDetails: true,
  });

  // Sync localFilters when parent filters change (e.g., on clear)
  useEffect(() => {
    setLocalFilters(filters);
  }, [filters]);

  // Fetch filter options from backend
  const { data: filterOptions, isLoading } = useQuery({
    queryKey: ['filterOptions'],
    queryFn: () => grantsApi.getFilterOptions(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  // Count active filters
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.agencies?.length) count++;
    if (filters.categories?.length) count++;
    if (filters.min_amount || filters.max_amount) count++;
    if (filters.deadline_after || filters.deadline_before) count++;
    if (filters.deadline_proximity) count++;
    // Match score filter
    if (filters.score_range && filters.score_range !== 'all') count++;
    // Eligibility filters
    if (filters.career_stages?.length) count++;
    if (filters.citizenship?.length) count++;
    if (filters.institution_types?.length) count++;
    if (filters.postdocs_eligible !== undefined) count++;
    if (filters.students_eligible !== undefined) count++;
    return count;
  }, [filters]);

  // Handle match score range change
  const handleScoreRangeChange = (range: MatchScoreRange) => {
    const selectedRange = MATCH_SCORE_RANGES.find((r) => r.value === range);
    const newFilters = {
      ...localFilters,
      score_range: range === 'all' ? undefined : range,
      min_score: selectedRange?.minScore,
      max_score: selectedRange?.maxScore,
    };
    setLocalFilters(newFilters);
    onFiltersChange(newFilters);
  };

  // Get current score range label
  const getScoreRangeLabel = () => {
    const range = MATCH_SCORE_RANGES.find((r) => r.value === (localFilters.score_range || 'all'));
    return range?.label || 'All Matches';
  };

  // Update local filter and propagate to parent
  const updateFilter = <K extends keyof AdvancedGrantFilters>(
    key: K,
    value: AdvancedGrantFilters[K]
  ) => {
    const newFilters = { ...localFilters, [key]: value };
    setLocalFilters(newFilters);
    onFiltersChange(newFilters);
  };

  // Handle multi-select changes
  const handleMultiSelect = (
    key: 'agencies' | 'categories',
    value: string,
    checked: boolean
  ) => {
    const current = localFilters[key] || [];
    const newValues = checked
      ? [...current, value]
      : current.filter((v) => v !== value);
    updateFilter(key, newValues.length > 0 ? newValues : undefined);
  };

  // Clear all filters
  const handleClearAll = () => {
    setLocalFilters({});
    onClear();
  };

  // Format currency for display
  const formatCurrency = (value: number | undefined) => {
    if (!value) return '';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Toggle collapsible sections
  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  // Handle deadline proximity quick filter toggle
  const handleDeadlineProximityToggle = (value: string) => {
    const newValue = localFilters.deadline_proximity === value ? undefined : value;
    const newFilters = {
      ...localFilters,
      deadline_proximity: newValue,
      // Clear manual deadline filters when using proximity
      deadline_after: newValue ? undefined : localFilters.deadline_after,
      deadline_before: newValue ? undefined : localFilters.deadline_before,
    };
    setLocalFilters(newFilters);
    onFiltersChange(newFilters);
  };

  return (
    <div className="advanced-filters">
      {/* Quick Filters Row */}
      <div className="quick-filters-row">
        {/* Deadline Proximity Quick Filters */}
        <div className="deadline-quick-filters">
          <div className="quick-filter-label">
            <ClockIcon className="quick-filter-icon" />
            <span>Deadline:</span>
          </div>
          <div className="quick-filter-chips">
            {DEADLINE_PROXIMITY_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => handleDeadlineProximityToggle(option.value)}
                className={`quick-filter-chip ${
                  localFilters.deadline_proximity === option.value ? 'active' : ''
                }`}
                aria-pressed={localFilters.deadline_proximity === option.value}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {/* Match Score Quick Filters */}
        <div className="match-score-quick-filters">
          <div className="quick-filter-label">
            <StarIcon className="quick-filter-icon text-amber-500" />
            <span>Match:</span>
          </div>
          <div className="quick-filter-chips">
            <button
              type="button"
              onClick={() => handleScoreRangeChange('excellent')}
              className={`quick-filter-chip match-excellent ${
                localFilters.score_range === 'excellent' ? 'active' : ''
              }`}
              aria-pressed={localFilters.score_range === 'excellent'}
            >
              High Match 90%+
            </button>
            <button
              type="button"
              onClick={() => handleScoreRangeChange('good')}
              className={`quick-filter-chip match-good ${
                localFilters.score_range === 'good' ? 'active' : ''
              }`}
              aria-pressed={localFilters.score_range === 'good'}
            >
              Good Match 75%+
            </button>
          </div>
        </div>
      </div>

      {/* Toggle Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="advanced-filters-toggle"
        aria-expanded={isExpanded}
      >
        <AdjustmentsHorizontalIcon className="toggle-icon" />
        <span className="toggle-text">More Filters</span>
        {activeFilterCount > 0 && (
          <span className="filter-badge">{activeFilterCount}</span>
        )}
        {isExpanded ? (
          <ChevronUpIcon className="chevron-icon" />
        ) : (
          <ChevronDownIcon className="chevron-icon" />
        )}
      </button>

      {/* Expandable Panel */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="filter-panel-wrapper"
          >
            <div className="filter-panel">
              {isLoading ? (
                <div className="filter-loading">
                  <div className="loading-spinner" />
                  <span>Loading filter options...</span>
                </div>
              ) : (
                <>
                  <div className="filter-grid">
                    {/* Agency Filter */}
                    <FilterSection
                      title="Funding Agency"
                      description="Filter by grant source"
                    >
                      <MultiSelectDropdown
                        options={filterOptions?.agencies || []}
                        selected={localFilters.agencies || []}
                        onChange={(values) => updateFilter('agencies', values.length > 0 ? values : undefined)}
                        placeholder="Select agencies..."
                        maxDisplay={3}
                      />
                    </FilterSection>

                    {/* Categories Filter */}
                    <FilterSection
                      title="Categories"
                      description="Research focus areas"
                    >
                      <MultiSelectDropdown
                        options={filterOptions?.categories || []}
                        selected={localFilters.categories || []}
                        onChange={(values) => updateFilter('categories', values.length > 0 ? values : undefined)}
                        placeholder="Select categories..."
                        maxDisplay={3}
                      />
                    </FilterSection>

                    {/* Deadline Range */}
                    <FilterSection
                      title="Deadline Range"
                      description="Filter by due date"
                    >
                      <div className="date-range-inputs">
                        <div className="date-input-group">
                          <label htmlFor="deadline-from">From</label>
                          <input
                            type="date"
                            id="deadline-from"
                            value={localFilters.deadline_after?.split('T')[0] || ''}
                            onChange={(e) =>
                              updateFilter(
                                'deadline_after',
                                e.target.value ? `${e.target.value}T00:00:00Z` : undefined
                              )
                            }
                          />
                        </div>
                        <span className="date-separator">to</span>
                        <div className="date-input-group">
                          <label htmlFor="deadline-to">To</label>
                          <input
                            type="date"
                            id="deadline-to"
                            value={localFilters.deadline_before?.split('T')[0] || ''}
                            onChange={(e) =>
                              updateFilter(
                                'deadline_before',
                                e.target.value ? `${e.target.value}T23:59:59Z` : undefined
                              )
                            }
                          />
                        </div>
                      </div>
                    </FilterSection>

                    {/* Funding Amount Range */}
                    <FilterSection
                      title="Funding Amount"
                      description="Min and max award size"
                    >
                      <div className="amount-range-inputs">
                        <div className="amount-input-group">
                          <label htmlFor="amount-min">Min</label>
                          <div className="currency-input">
                            <span className="currency-prefix">$</span>
                            <input
                              type="number"
                              id="amount-min"
                              placeholder={formatCurrency(filterOptions?.amount_range?.min) || '0'}
                              value={localFilters.min_amount || ''}
                              onChange={(e) =>
                                updateFilter(
                                  'min_amount',
                                  e.target.value ? parseInt(e.target.value) : undefined
                                )
                              }
                              min={0}
                              step={10000}
                            />
                          </div>
                        </div>
                        <span className="amount-separator">-</span>
                        <div className="amount-input-group">
                          <label htmlFor="amount-max">Max</label>
                          <div className="currency-input">
                            <span className="currency-prefix">$</span>
                            <input
                              type="number"
                              id="amount-max"
                              placeholder={formatCurrency(filterOptions?.amount_range?.max) || 'Any'}
                              value={localFilters.max_amount || ''}
                              onChange={(e) =>
                                updateFilter(
                                  'max_amount',
                                  e.target.value ? parseInt(e.target.value) : undefined
                                )
                              }
                              min={0}
                              step={10000}
                            />
                          </div>
                        </div>
                      </div>
                    </FilterSection>

                    {/* Match Score Range */}
                    <FilterSection
                      title="Match Score Range"
                      description="Filter by profile match quality"
                    >
                      <div className="score-range-options">
                        {MATCH_SCORE_RANGES.map((range) => (
                          <label
                            key={range.value}
                            className={`score-range-option ${
                              (localFilters.score_range || 'all') === range.value ? 'selected' : ''
                            }`}
                          >
                            <input
                              type="radio"
                              name="score_range"
                              value={range.value}
                              checked={(localFilters.score_range || 'all') === range.value}
                              onChange={() => handleScoreRangeChange(range.value)}
                            />
                            <div className="score-range-content">
                              <span className="score-range-label">{range.label}</span>
                              <span className="score-range-desc">{range.description}</span>
                            </div>
                          </label>
                        ))}
                      </div>
                    </FilterSection>

                  </div>

                  {/* AWARD DETAILS Section - Collapsible */}
                  <CollapsibleSection
                    title="AWARD DETAILS"
                    isExpanded={expandedSections.awardDetails}
                    onToggle={() => toggleSection('awardDetails')}
                  >
                    <div className="filter-grid">
                      {/* Funding Amount Range - Active filter */}
                      <FilterSection
                        title="Funding Amount"
                        description="Min and max award size"
                      >
                        <div className="amount-range-inputs">
                          <div className="amount-input-group">
                            <label htmlFor="amount-min-award">Min</label>
                            <div className="currency-input">
                              <span className="currency-prefix">$</span>
                              <input
                                type="number"
                                id="amount-min-award"
                                placeholder={formatCurrency(filterOptions?.amount_range?.min) || '0'}
                                value={localFilters.min_amount || ''}
                                onChange={(e) =>
                                  updateFilter(
                                    'min_amount',
                                    e.target.value ? parseInt(e.target.value) : undefined
                                  )
                                }
                                min={0}
                                step={10000}
                              />
                            </div>
                          </div>
                          <span className="amount-separator">-</span>
                          <div className="amount-input-group">
                            <label htmlFor="amount-max-award">Max</label>
                            <div className="currency-input">
                              <span className="currency-prefix">$</span>
                              <input
                                type="number"
                                id="amount-max-award"
                                placeholder={formatCurrency(filterOptions?.amount_range?.max) || 'Any'}
                                value={localFilters.max_amount || ''}
                                onChange={(e) =>
                                  updateFilter(
                                    'max_amount',
                                    e.target.value ? parseInt(e.target.value) : undefined
                                  )
                                }
                                min={0}
                                step={10000}
                              />
                            </div>
                          </div>
                        </div>
                      </FilterSection>

                      {/* Award Type - Coming Soon */}
                      <FilterSection
                        title="Award Type"
                        description="Type of funding mechanism"
                        disabled
                        comingSoon
                      >
                        <MultiSelectDropdown
                          options={AWARD_TYPE_OPTIONS}
                          selected={localFilters.award_types || []}
                          onChange={(values) => updateFilter('award_types', values.length > 0 ? values : undefined)}
                          placeholder="Select award types..."
                          disabled
                        />
                      </FilterSection>

                      {/* Award Duration - Coming Soon */}
                      <FilterSection
                        title="Award Duration"
                        description="Length of funding period"
                        disabled
                        comingSoon
                      >
                        <select
                          className="filter-select disabled"
                          disabled
                          value={localFilters.award_duration || ''}
                          onChange={(e) => updateFilter('award_duration', e.target.value || undefined)}
                        >
                          <option value="">Select duration...</option>
                          {AWARD_DURATION_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </FilterSection>

                      {/* Indirect Cost Policy - Coming Soon */}
                      <FilterSection
                        title="Indirect Cost Policy"
                        description="F&A reimbursement policy"
                        disabled
                        comingSoon
                      >
                        <select
                          className="filter-select disabled"
                          disabled
                          value={localFilters.indirect_cost_policy || ''}
                          onChange={(e) => updateFilter('indirect_cost_policy', e.target.value || undefined)}
                        >
                          <option value="">Select policy...</option>
                          {INDIRECT_COST_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </FilterSection>

                      {/* Submission Type - Coming Soon */}
                      <FilterSection
                        title="Submission Type"
                        description="Application submission category"
                        disabled
                        comingSoon
                      >
                        <MultiSelectDropdown
                          options={SUBMISSION_TYPE_OPTIONS}
                          selected={localFilters.submission_types || []}
                          onChange={(values) => updateFilter('submission_types', values.length > 0 ? values : undefined)}
                          placeholder="Select submission types..."
                          disabled
                        />
                      </FilterSection>
                    </div>
                  </CollapsibleSection>

                  {/* ELIGIBILITY Section - Collapsible */}
                  <CollapsibleSection
                    title="ELIGIBILITY"
                    isExpanded={expandedSections.eligibility}
                    onToggle={() => toggleSection('eligibility')}
                    badge="Coming Soon"
                  >
                    <div className="filter-grid">
                      {/* Career Stage */}
                      <FilterSection
                        title="Career Stage"
                        description="Eligibility by career level"
                        disabled
                        comingSoon
                      >
                        <MultiSelectDropdown
                          options={filterOptions?.career_stages?.map((s) => s.label) || CAREER_STAGE_OPTIONS}
                          selected={localFilters.career_stages || []}
                          onChange={(values) => updateFilter('career_stages', values.length > 0 ? values : undefined)}
                          placeholder="Select career stages..."
                          disabled
                        />
                      </FilterSection>

                      {/* Citizenship */}
                      <FilterSection
                        title="Citizenship"
                        description="Eligibility requirements"
                        disabled
                        comingSoon
                      >
                        <MultiSelectDropdown
                          options={filterOptions?.citizenship_options?.map((c) => c.label) || CITIZENSHIP_OPTIONS}
                          selected={localFilters.citizenship || []}
                          onChange={(values) => updateFilter('citizenship', values.length > 0 ? values : undefined)}
                          placeholder="Select citizenship..."
                          disabled
                        />
                      </FilterSection>

                      {/* Institution Type */}
                      <FilterSection
                        title="Institution Type"
                        description="Type of eligible institution"
                        disabled
                        comingSoon
                      >
                        <MultiSelectDropdown
                          options={filterOptions?.institution_types?.map((i) => i.label) || INSTITUTION_TYPE_OPTIONS}
                          selected={localFilters.institution_types || []}
                          onChange={(values) => updateFilter('institution_types', values.length > 0 ? values : undefined)}
                          placeholder="Select institution types..."
                          disabled
                        />
                      </FilterSection>

                      {/* PI Status - Checkboxes */}
                      <FilterSection
                        title="PI Status"
                        description="Who can apply as PI"
                        disabled
                        comingSoon
                      >
                        <div className="checkbox-group">
                          <label className="checkbox-label disabled">
                            <input
                              type="checkbox"
                              checked={localFilters.postdocs_eligible || false}
                              onChange={(e) => updateFilter('postdocs_eligible', e.target.checked ? true : undefined)}
                              disabled
                            />
                            <span>Postdocs can apply</span>
                          </label>
                          <label className="checkbox-label disabled">
                            <input
                              type="checkbox"
                              checked={localFilters.students_eligible || false}
                              onChange={(e) => updateFilter('students_eligible', e.target.checked ? true : undefined)}
                              disabled
                            />
                            <span>Students can apply</span>
                          </label>
                        </div>
                      </FilterSection>
                    </div>
                  </CollapsibleSection>

                  {/* Actions */}
                  <div className="filter-actions">
                    <button
                      onClick={handleClearAll}
                      className="clear-filters-btn"
                      disabled={activeFilterCount === 0}
                    >
                      <XMarkIcon className="action-icon" />
                      Clear all filters
                    </button>

                    {activeFilterCount > 0 && (
                      <div className="active-filters-summary">
                        <FunnelIcon className="summary-icon" />
                        <span>{activeFilterCount} filter{activeFilterCount !== 1 ? 's' : ''} active</span>
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Active Filter Pills (shown when collapsed) */}
      {!isExpanded && activeFilterCount > 0 && (
        <div className="active-filter-pills">
          {filters.agencies?.map((agency) => (
            <FilterPill
              key={`agency-${agency}`}
              label={agency}
              onRemove={() => handleMultiSelect('agencies', agency, false)}
            />
          ))}
          {filters.categories?.map((category) => (
            <FilterPill
              key={`category-${category}`}
              label={category}
              onRemove={() => handleMultiSelect('categories', category, false)}
            />
          ))}
          {(filters.min_amount || filters.max_amount) && (
            <FilterPill
              label={`${formatCurrency(filters.min_amount) || '$0'} - ${formatCurrency(filters.max_amount) || 'Any'}`}
              onRemove={() => {
                updateFilter('min_amount', undefined);
                updateFilter('max_amount', undefined);
              }}
            />
          )}
          {(filters.deadline_after || filters.deadline_before) && (
            <FilterPill
              label={`Deadline: ${filters.deadline_after?.split('T')[0] || 'Any'} - ${filters.deadline_before?.split('T')[0] || 'Any'}`}
              onRemove={() => {
                updateFilter('deadline_after', undefined);
                updateFilter('deadline_before', undefined);
              }}
            />
          )}
          {filters.deadline_proximity && (
            <FilterPill
              label={`Due in ${filters.deadline_proximity} days`}
              onRemove={() => updateFilter('deadline_proximity', undefined)}
            />
          )}
          {filters.score_range && filters.score_range !== 'all' && (
            <FilterPill
              label={getScoreRangeLabel()}
              onRemove={() => handleScoreRangeChange('all')}
            />
          )}
        </div>
      )}
    </div>
  );
}

// Filter Section Component
function FilterSection({
  title,
  description,
  children,
  disabled = false,
  comingSoon = false,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  disabled?: boolean;
  comingSoon?: boolean;
}) {
  return (
    <div className={`filter-section ${disabled ? 'disabled' : ''}`}>
      <div className="filter-section-header">
        <h4 className="filter-title">{title}</h4>
        {comingSoon && <span className="coming-soon-badge">Soon</span>}
      </div>
      {description && <p className="filter-description">{description}</p>}
      <div className="filter-content">{children}</div>
    </div>
  );
}

// Multi-Select Dropdown Component
function MultiSelectDropdown({
  options,
  selected,
  onChange,
  placeholder,
  maxDisplay = 3,
  disabled = false,
}: {
  options: string[];
  selected: string[];
  onChange: (values: string[]) => void;
  placeholder: string;
  maxDisplay?: number;
  disabled?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');

  const filteredOptions = useMemo(() => {
    if (!search) return options.slice(0, 100); // Limit display
    return options
      .filter((opt) => opt.toLowerCase().includes(search.toLowerCase()))
      .slice(0, 50);
  }, [options, search]);

  const displayText = useMemo(() => {
    if (selected.length === 0) return placeholder;
    if (selected.length <= maxDisplay) return selected.join(', ');
    return `${selected.slice(0, maxDisplay).join(', ')} +${selected.length - maxDisplay} more`;
  }, [selected, placeholder, maxDisplay]);

  const toggleOption = (option: string) => {
    if (selected.includes(option)) {
      onChange(selected.filter((s) => s !== option));
    } else {
      onChange([...selected, option]);
    }
  };

  return (
    <div className={`multi-select-dropdown ${disabled ? 'disabled' : ''}`}>
      <button
        type="button"
        className={`dropdown-trigger ${selected.length > 0 ? 'has-selection' : ''}`}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
      >
        <span className="dropdown-text">{displayText}</span>
        <ChevronDownIcon className={`dropdown-chevron ${isOpen ? 'open' : ''}`} />
      </button>

      <AnimatePresence>
        {isOpen && !disabled && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.15 }}
            className="dropdown-menu"
          >
            {options.length > 10 && (
              <div className="dropdown-search">
                <input
                  type="text"
                  placeholder="Search..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
            )}
            <div className="dropdown-options">
              {filteredOptions.length === 0 ? (
                <div className="dropdown-empty">No options found</div>
              ) : (
                filteredOptions.map((option) => (
                  <label key={option} className="dropdown-option">
                    <input
                      type="checkbox"
                      checked={selected.includes(option)}
                      onChange={() => toggleOption(option)}
                    />
                    <span className="option-label">{option}</span>
                  </label>
                ))
              )}
            </div>
            {selected.length > 0 && (
              <div className="dropdown-footer">
                <button
                  type="button"
                  className="clear-selection-btn"
                  onClick={() => onChange([])}
                >
                  Clear selection
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Click outside to close */}
      {isOpen && (
        <div
          className="dropdown-backdrop"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
}

// Filter Pill Component
function FilterPill({
  label,
  onRemove,
}: {
  label: string;
  onRemove: () => void;
}) {
  return (
    <span className="filter-pill">
      <span className="pill-label">{label}</span>
      <button
        type="button"
        className="pill-remove"
        onClick={onRemove}
        aria-label={`Remove filter: ${label}`}
      >
        <XMarkIcon className="pill-remove-icon" />
      </button>
    </span>
  );
}

// Collapsible Section Component for grouping filters
function CollapsibleSection({
  title,
  isExpanded,
  onToggle,
  badge,
  children,
}: {
  title: string;
  isExpanded: boolean;
  onToggle: () => void;
  badge?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="collapsible-section">
      <button
        type="button"
        className="collapsible-section-header"
        onClick={onToggle}
        aria-expanded={isExpanded}
      >
        <div className="collapsible-section-title">
          <span className="section-title-text">{title}</span>
          {badge && <span className="section-badge">{badge}</span>}
        </div>
        {isExpanded ? (
          <ChevronUpIcon className="section-chevron" />
        ) : (
          <ChevronDownIcon className="section-chevron" />
        )}
      </button>
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="collapsible-section-content"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
