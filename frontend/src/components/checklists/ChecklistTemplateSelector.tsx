import { useState, useRef, useEffect } from 'react';
import {
  ChevronUpDownIcon,
  CheckIcon,
  DocumentTextIcon,
  BuildingLibraryIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { useChecklistTemplates } from '../../hooks/useChecklists';
import type { ChecklistTemplate } from '../../types/checklists';

interface ChecklistTemplateSelectorProps {
  /** Currently selected template ID */
  selectedTemplateId?: string;
  /** Callback when template is selected */
  onSelect: (template: ChecklistTemplate) => void;
  /** Optional funder filter */
  funder?: string;
  /** Placeholder text */
  placeholder?: string;
  /** Disabled state */
  disabled?: boolean;
  /** Additional class name */
  className?: string;
}

export function ChecklistTemplateSelector({
  selectedTemplateId,
  onSelect,
  funder,
  placeholder = 'Select a checklist template...',
  disabled = false,
  className = '',
}: ChecklistTemplateSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const { data, isLoading } = useChecklistTemplates({ funder });
  const templates = data?.templates || [];

  // Find selected template
  const selectedTemplate = templates.find((t) => t.id === selectedTemplateId);

  // Filter templates by search query
  const filteredTemplates = templates.filter((template) => {
    const query = searchQuery.toLowerCase();
    return (
      template.name.toLowerCase().includes(query) ||
      template.funder.toLowerCase().includes(query) ||
      template.mechanism?.toLowerCase().includes(query)
    );
  });

  // Group templates by funder
  const groupedTemplates = filteredTemplates.reduce(
    (groups, template) => {
      const group = groups[template.funder] || [];
      group.push(template);
      groups[template.funder] = group;
      return groups;
    },
    {} as Record<string, ChecklistTemplate[]>
  );

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen]);

  const handleSelect = (template: ChecklistTemplate) => {
    onSelect(template);
    setIsOpen(false);
    setSearchQuery('');
  };

  return (
    <div ref={dropdownRef} className={`relative ${className}`}>
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={`w-full flex items-center justify-between px-3 py-2.5 text-left border rounded-lg transition-colors ${
          disabled
            ? 'bg-gray-100 border-gray-200 cursor-not-allowed text-gray-400'
            : isOpen
            ? 'border-blue-500 ring-2 ring-blue-100 bg-white'
            : 'border-gray-300 bg-white hover:border-gray-400'
        }`}
      >
        <div className="flex items-center gap-2 min-w-0">
          <DocumentTextIcon className="w-5 h-5 text-gray-400 flex-shrink-0" />
          {selectedTemplate ? (
            <div className="truncate">
              <span className="text-sm font-medium text-gray-900">{selectedTemplate.name}</span>
              <span className="text-sm text-gray-500 ml-2">({selectedTemplate.funder})</span>
            </div>
          ) : (
            <span className="text-sm text-gray-500">{placeholder}</span>
          )}
        </div>
        <ChevronUpDownIcon className="w-5 h-5 text-gray-400 flex-shrink-0" />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-96 overflow-hidden">
          {/* Search input */}
          <div className="p-2 border-b border-gray-100">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search templates..."
                className="w-full pl-9 pr-8 py-2 text-sm border border-gray-200 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <XMarkIcon className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          {/* Template list */}
          <div className="overflow-y-auto max-h-72">
            {isLoading ? (
              <div className="p-4 text-center text-sm text-gray-500">Loading templates...</div>
            ) : filteredTemplates.length === 0 ? (
              <div className="p-4 text-center text-sm text-gray-500">
                {searchQuery
                  ? 'No templates match your search'
                  : 'No templates available'}
              </div>
            ) : (
              Object.entries(groupedTemplates).map(([funderName, funderTemplates]) => (
                <div key={funderName}>
                  {/* Funder header */}
                  <div className="px-3 py-1.5 bg-gray-50 border-b border-gray-100 sticky top-0">
                    <div className="flex items-center gap-2">
                      <BuildingLibraryIcon className="w-4 h-4 text-gray-400" />
                      <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">
                        {funderName}
                      </span>
                    </div>
                  </div>

                  {/* Templates */}
                  {funderTemplates.map((template) => (
                    <button
                      key={template.id}
                      type="button"
                      onClick={() => handleSelect(template)}
                      className={`w-full flex items-center justify-between px-3 py-2.5 hover:bg-gray-50 transition-colors ${
                        template.id === selectedTemplateId ? 'bg-blue-50' : ''
                      }`}
                    >
                      <div className="text-left min-w-0">
                        <div className="text-sm font-medium text-gray-900 truncate">
                          {template.name}
                        </div>
                        <div className="text-xs text-gray-500 truncate">
                          {template.mechanism && (
                            <span className="mr-2">{template.mechanism}</span>
                          )}
                          <span>{template.items.length} items</span>
                        </div>
                      </div>
                      {template.id === selectedTemplateId && (
                        <CheckIcon className="w-5 h-5 text-blue-600 flex-shrink-0" />
                      )}
                    </button>
                  ))}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Compact template selector for inline use
 */
export function ChecklistTemplateSelectorCompact({
  selectedTemplateId,
  onSelect,
  templates,
  disabled = false,
  className = '',
}: {
  selectedTemplateId?: string;
  onSelect: (templateId: string) => void;
  templates: ChecklistTemplate[];
  disabled?: boolean;
  className?: string;
}) {
  return (
    <select
      value={selectedTemplateId || ''}
      onChange={(e) => onSelect(e.target.value)}
      disabled={disabled}
      className={`block w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
        disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white'
      } ${className}`}
    >
      <option value="">Select template...</option>
      {templates.map((template) => (
        <option key={template.id} value={template.id}>
          {template.name} ({template.funder})
        </option>
      ))}
    </select>
  );
}

export default ChecklistTemplateSelector;
