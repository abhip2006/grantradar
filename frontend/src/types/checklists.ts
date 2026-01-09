// Checklist Types for Dynamic Checklists Feature

// Categories for checklist items - matches backend enum
export type ChecklistCategory =
  | 'administrative'
  | 'scientific'
  | 'budget'
  | 'personnel'
  | 'compliance'
  | 'documents'
  | 'review'
  | 'other';

// Template item structure
export interface ChecklistTemplateItem {
  id: string;
  title: string;
  description?: string;
  required: boolean;
  weight: number;
  category: ChecklistCategory;
  order: number;
}

// Checklist template (funder-specific)
export interface ChecklistTemplate {
  id: string;
  funder: string;
  mechanism?: string;
  name: string;
  description?: string;
  items: ChecklistTemplateItem[];
  is_default?: boolean;
  created_at: string;
  updated_at?: string;
}

// Individual checklist item status in an application
export interface ChecklistItemStatus {
  item_id: string;
  completed: boolean;
  completed_at?: string;
  completed_by?: string;
  notes?: string;
}

// Application checklist (instance of template for a specific application)
export interface ApplicationChecklist {
  id: string;
  kanban_card_id: string;
  template_id: string;
  template?: ChecklistTemplate;
  items: ChecklistItemStatus[];
  progress_percent: number;
  completed_count: number;
  total_count: number;
  required_completed_count: number;
  required_total_count: number;
  created_at: string;
  updated_at: string;
}

// Combined item for UI display (template item + status)
export interface ChecklistItem {
  id: string;
  title: string;
  description?: string;
  required: boolean;
  weight: number;
  category: ChecklistCategory;
  order: number;
  completed: boolean;
  completed_at?: string;
  completed_by?: string;
  notes?: string;
}

// API request types
export interface CreateChecklistRequest {
  template_id: string;
}

export interface UpdateChecklistItemRequest {
  completed?: boolean;
  notes?: string;
}

// API response types
export interface ChecklistTemplateListResponse {
  templates: ChecklistTemplate[];
  total: number;
}

export interface ChecklistResponse {
  checklist: ApplicationChecklist;
}

// Category configuration for UI
export interface ChecklistCategoryConfig {
  key: ChecklistCategory;
  label: string;
  color: string;
  bgColor: string;
  icon: string;
}

export const CHECKLIST_CATEGORY_CONFIGS: Record<ChecklistCategory, ChecklistCategoryConfig> = {
  administrative: {
    key: 'administrative',
    label: 'Administrative',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    icon: 'ClipboardDocumentListIcon',
  },
  scientific: {
    key: 'scientific',
    label: 'Scientific',
    color: 'text-purple-600',
    bgColor: 'bg-purple-100',
    icon: 'BeakerIcon',
  },
  budget: {
    key: 'budget',
    label: 'Budget',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-100',
    icon: 'CurrencyDollarIcon',
  },
  personnel: {
    key: 'personnel',
    label: 'Personnel',
    color: 'text-cyan-600',
    bgColor: 'bg-cyan-100',
    icon: 'UserGroupIcon',
  },
  compliance: {
    key: 'compliance',
    label: 'Compliance',
    color: 'text-amber-600',
    bgColor: 'bg-amber-100',
    icon: 'ShieldCheckIcon',
  },
  documents: {
    key: 'documents',
    label: 'Documents',
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-100',
    icon: 'DocumentIcon',
  },
  review: {
    key: 'review',
    label: 'Review',
    color: 'text-rose-600',
    bgColor: 'bg-rose-100',
    icon: 'EyeIcon',
  },
  other: {
    key: 'other',
    label: 'Other',
    color: 'text-slate-600',
    bgColor: 'bg-slate-100',
    icon: 'EllipsisHorizontalIcon',
  },
};

// Helper function to calculate weighted progress
export function calculateWeightedProgress(
  items: ChecklistItem[]
): { percent: number; weightedPercent: number } {
  if (items.length === 0) {
    return { percent: 0, weightedPercent: 0 };
  }

  const completedCount = items.filter((item) => item.completed).length;
  const percent = (completedCount / items.length) * 100;

  const totalWeight = items.reduce((sum, item) => sum + item.weight, 0);
  const completedWeight = items
    .filter((item) => item.completed)
    .reduce((sum, item) => sum + item.weight, 0);
  const weightedPercent = totalWeight > 0 ? (completedWeight / totalWeight) * 100 : 0;

  return { percent, weightedPercent };
}

// Helper function to merge template items with status
export function mergeChecklistItems(
  templateItems: ChecklistTemplateItem[],
  itemStatuses: ChecklistItemStatus[]
): ChecklistItem[] {
  const statusMap = new Map(itemStatuses.map((s) => [s.item_id, s]));

  return templateItems
    .map((item) => {
      const status = statusMap.get(item.id);
      return {
        id: item.id,
        title: item.title,
        description: item.description,
        required: item.required,
        weight: item.weight,
        category: item.category,
        order: item.order,
        completed: status?.completed ?? false,
        completed_at: status?.completed_at,
        completed_by: status?.completed_by,
        notes: status?.notes,
      };
    })
    .sort((a, b) => a.order - b.order);
}

// Helper function to group items by category
export function groupItemsByCategory(
  items: ChecklistItem[]
): Record<ChecklistCategory, ChecklistItem[]> {
  const groups: Record<ChecklistCategory, ChecklistItem[]> = {
    administrative: [],
    scientific: [],
    budget: [],
    personnel: [],
    compliance: [],
    documents: [],
    review: [],
    other: [],
  };

  items.forEach((item) => {
    const category = item.category || 'other';
    if (category in groups) {
      groups[category].push(item);
    } else {
      groups.other.push(item);
    }
  });

  return groups;
}
