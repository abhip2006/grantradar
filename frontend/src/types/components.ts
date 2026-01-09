// Document Component Library Types

/**
 * Category for document components
 */
export type ComponentCategory =
  | 'facilities'
  | 'equipment'
  | 'biosketch'
  | 'boilerplate'
  | 'human_subjects'
  | 'vertebrate_animals'
  | 'institution'
  | 'other';

/**
 * Component category metadata for display
 */
export const COMPONENT_CATEGORY_CONFIG: Record<ComponentCategory, { label: string; description: string; icon: string }> = {
  facilities: {
    label: 'Facilities',
    description: 'Lab and research facility descriptions',
    icon: 'BuildingOffice2Icon'
  },
  equipment: {
    label: 'Equipment',
    description: 'Scientific equipment and instrumentation',
    icon: 'WrenchScrewdriverIcon'
  },
  biosketch: {
    label: 'Biosketch',
    description: 'Personal statements and biosketches',
    icon: 'UserIcon'
  },
  boilerplate: {
    label: 'Boilerplate',
    description: 'Standard sections and language',
    icon: 'DocumentTextIcon'
  },
  human_subjects: {
    label: 'Human Subjects',
    description: 'Human subjects research protections',
    icon: 'UsersIcon'
  },
  vertebrate_animals: {
    label: 'Vertebrate Animals',
    description: 'Animal research justifications',
    icon: 'BugAntIcon'
  },
  institution: {
    label: 'Institution',
    description: 'Institutional descriptions and resources',
    icon: 'AcademicCapIcon'
  },
  other: {
    label: 'Other',
    description: 'Miscellaneous components',
    icon: 'FolderIcon'
  },
};

/**
 * Metadata associated with a document component
 */
export interface ComponentMetadata {
  funder?: string;
  mechanism?: string;
  word_limit?: number;
  page_limit?: number;
  last_reviewed?: string;
  tags?: string[];
  author?: string;
  notes?: string;
}

/**
 * Document component - reusable content block for grant applications
 */
export interface DocumentComponent {
  id: string;
  user_id: string;
  category: ComponentCategory;
  name: string;
  content: string;
  metadata: ComponentMetadata;
  version: number;
  is_current: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Request to create a new document component
 */
export interface DocumentComponentCreate {
  category: ComponentCategory;
  name: string;
  content: string;
  metadata?: ComponentMetadata;
}

/**
 * Request to update an existing document component
 */
export interface DocumentComponentUpdate {
  category?: ComponentCategory;
  name?: string;
  content?: string;
  metadata?: ComponentMetadata;
}

/**
 * List response for document components
 */
export interface DocumentComponentListResponse {
  items: DocumentComponent[];
  total: number;
}

/**
 * Filters for listing document components
 */
export interface DocumentComponentFilters {
  category?: ComponentCategory;
  search?: string;
}

/**
 * Component usage record - tracks where a component was used
 */
export interface ComponentUsage {
  id: string;
  component_id: string;
  kanban_card_id: string;
  section: string;
  used_at: string;
}

/**
 * Component usage response with related card info
 */
export interface ComponentUsageResponse {
  usages: ComponentUsage[];
  total: number;
}

// Document Version Types

/**
 * Document version - snapshot of document content at a point in time
 */
export interface DocumentVersion {
  id: string;
  kanban_card_id: string;
  section: string;
  version_number: number;
  content: string;
  snapshot_name?: string;
  created_by?: string;
  created_by_name?: string;
  created_at: string;
}

/**
 * Request to create a new document version
 */
export interface DocumentVersionCreate {
  kanban_card_id: string;
  section: string;
  content: string;
  snapshot_name?: string;
}

/**
 * List response for document versions
 */
export interface DocumentVersionListResponse {
  items: DocumentVersion[];
  total: number;
}

/**
 * Diff result between two versions
 */
export interface VersionDiffResult {
  version_a: DocumentVersion;
  version_b: DocumentVersion;
  additions: number;
  deletions: number;
  changes: DiffChange[];
}

/**
 * Individual change in a diff
 */
export interface DiffChange {
  type: 'add' | 'remove' | 'unchanged';
  content: string;
  line_number_a?: number;
  line_number_b?: number;
}

/**
 * Request to compare two versions
 */
export interface VersionCompareRequest {
  version_a_id: string;
  version_b_id: string;
}

/**
 * Insert component into document request
 */
export interface InsertComponentRequest {
  component_id: string;
  kanban_card_id: string;
  section: string;
  position?: 'start' | 'end' | 'cursor';
}

/**
 * Insert component response
 */
export interface InsertComponentResponse {
  success: boolean;
  usage_id: string;
  message?: string;
}
