import {
  BuildingOffice2Icon,
  WrenchScrewdriverIcon,
  UserIcon,
  DocumentTextIcon,
  UsersIcon,
  AcademicCapIcon,
  FolderIcon,
  Squares2X2Icon,
} from '@heroicons/react/24/outline';
import type { ComponentCategory } from '../../types/components';
import { COMPONENT_CATEGORY_CONFIG } from '../../types/components';

interface ComponentCategoryTabsProps {
  selectedCategory: ComponentCategory | 'all';
  onCategoryChange: (category: ComponentCategory | 'all') => void;
  categoryCounts?: Record<ComponentCategory | 'all', number>;
}

// Map category to icon component
const categoryIcons: Record<ComponentCategory | 'all', React.ComponentType<{ className?: string }>> = {
  all: Squares2X2Icon,
  facilities: BuildingOffice2Icon,
  equipment: WrenchScrewdriverIcon,
  biosketch: UserIcon,
  boilerplate: DocumentTextIcon,
  human_subjects: UsersIcon,
  vertebrate_animals: DocumentTextIcon, // Using DocumentTextIcon as fallback (BugAntIcon doesn't exist in standard)
  institution: AcademicCapIcon,
  other: FolderIcon,
};

const categories: Array<ComponentCategory | 'all'> = [
  'all',
  'facilities',
  'equipment',
  'biosketch',
  'boilerplate',
  'human_subjects',
  'vertebrate_animals',
  'institution',
  'other',
];

export function ComponentCategoryTabs({
  selectedCategory,
  onCategoryChange,
  categoryCounts,
}: ComponentCategoryTabsProps) {
  return (
    <div className="border-b border-[var(--gr-border-subtle)]">
      <nav className="-mb-px flex space-x-1 overflow-x-auto px-4 py-2" aria-label="Category tabs">
        {categories.map((category) => {
          const Icon = categoryIcons[category];
          const isSelected = selectedCategory === category;
          const count = categoryCounts?.[category];
          const label = category === 'all' ? 'All' : COMPONENT_CATEGORY_CONFIG[category]?.label || category;

          return (
            <button
              key={category}
              onClick={() => onCategoryChange(category)}
              className={`
                group flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg whitespace-nowrap transition-colors
                ${
                  isSelected
                    ? 'bg-[var(--gr-blue-100)] text-[var(--gr-blue-700)]'
                    : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-tertiary)]'
                }
              `}
            >
              <Icon className={`h-4 w-4 ${isSelected ? 'text-[var(--gr-blue-600)]' : ''}`} />
              <span>{label}</span>
              {count !== undefined && (
                <span
                  className={`
                    inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1.5 rounded-full text-xs font-medium
                    ${
                      isSelected
                        ? 'bg-[var(--gr-blue-200)] text-[var(--gr-blue-800)]'
                        : 'bg-[var(--gr-bg-tertiary)] text-[var(--gr-text-tertiary)]'
                    }
                  `}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </nav>
    </div>
  );
}

/**
 * Vertical variant for sidebar use
 */
export function ComponentCategoryList({
  selectedCategory,
  onCategoryChange,
  categoryCounts,
}: ComponentCategoryTabsProps) {
  return (
    <nav className="space-y-1" aria-label="Category list">
      {categories.map((category) => {
        const Icon = categoryIcons[category];
        const isSelected = selectedCategory === category;
        const count = categoryCounts?.[category];
        const label = category === 'all' ? 'All Components' : COMPONENT_CATEGORY_CONFIG[category]?.label || category;
        const description = category === 'all' ? 'View all components' : COMPONENT_CATEGORY_CONFIG[category]?.description;

        return (
          <button
            key={category}
            onClick={() => onCategoryChange(category)}
            className={`
              w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors
              ${
                isSelected
                  ? 'bg-[var(--gr-blue-100)] text-[var(--gr-blue-700)]'
                  : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-tertiary)]'
              }
            `}
          >
            <div
              className={`
                flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center
                ${isSelected ? 'bg-[var(--gr-blue-200)]' : 'bg-[var(--gr-bg-tertiary)]'}
              `}
            >
              <Icon className={`h-4 w-4 ${isSelected ? 'text-[var(--gr-blue-700)]' : ''}`} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium truncate">{label}</span>
                {count !== undefined && (
                  <span
                    className={`
                      ml-2 inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1.5 rounded-full text-xs font-medium
                      ${
                        isSelected
                          ? 'bg-[var(--gr-blue-200)] text-[var(--gr-blue-800)]'
                          : 'bg-[var(--gr-bg-secondary)] text-[var(--gr-text-tertiary)]'
                      }
                    `}
                  >
                    {count}
                  </span>
                )}
              </div>
              {description && (
                <p className="text-xs text-[var(--gr-text-tertiary)] truncate mt-0.5">
                  {description}
                </p>
              )}
            </div>
          </button>
        );
      })}
    </nav>
  );
}

export default ComponentCategoryTabs;
