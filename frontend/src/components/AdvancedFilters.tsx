/**
 * Advanced Filters Component
 * Expandable panel with comprehensive grant filtering options
 */
import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useQuery } from '@tanstack/react-query';
import {
  ChevronDownIcon,
  ChevronUpIcon,
  AdjustmentsHorizontalIcon,
  XMarkIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';
import { grantsApi } from '../services/api';
import type { AdvancedGrantFilters, FilterOptions } from '../types';

interface AdvancedFiltersProps {
  filters: AdvancedGrantFilters;
  onFiltersChange: (filters: AdvancedGrantFilters) => void;
  onClear: () => void;
}

export default function AdvancedFilters({
  filters,
  onFiltersChange,
  onClear,
}: AdvancedFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [localFilters, setLocalFilters] = useState<AdvancedGrantFilters>(filters);

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
    return count;
  }, [filters]);

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

  return (
    <div className="advanced-filters">
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

                    {/* Career Stage - Coming Soon */}
                    <FilterSection
                      title="Career Stage"
                      description="Eligibility by career level"
                      disabled
                      comingSoon
                    >
                      <MultiSelectDropdown
                        options={filterOptions?.career_stages?.map((s) => s.label) || []}
                        selected={[]}
                        onChange={() => {}}
                        placeholder="Coming soon..."
                        disabled
                      />
                    </FilterSection>

                    {/* Citizenship - Coming Soon */}
                    <FilterSection
                      title="Citizenship"
                      description="Eligibility requirements"
                      disabled
                      comingSoon
                    >
                      <MultiSelectDropdown
                        options={filterOptions?.citizenship_options?.map((c) => c.label) || []}
                        selected={[]}
                        onChange={() => {}}
                        placeholder="Coming soon..."
                        disabled
                      />
                    </FilterSection>
                  </div>

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
