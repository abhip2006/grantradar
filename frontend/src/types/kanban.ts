import type { Grant, User } from './index';

// Application stages (matching backend enum)
export type ApplicationStage = 'researching' | 'writing' | 'submitted' | 'awarded' | 'rejected';

// Priority levels
export type Priority = 'low' | 'medium' | 'high' | 'critical';

// Subtask for checklist
export interface Subtask {
  id: string;
  application_id: string;
  title: string;
  description?: string;
  is_completed: boolean;
  completed_at?: string;
  completed_by?: string;
  due_date?: string;
  position: number;
  created_at: string;
  updated_at: string;
}

// Activity log entry
export type ActivityAction =
  | 'created'
  | 'stage_changed'
  | 'subtask_added'
  | 'subtask_completed'
  | 'subtask_deleted'
  | 'attachment_added'
  | 'attachment_deleted'
  | 'field_updated'
  | 'comment_added'
  | 'assignee_added'
  | 'assignee_removed'
  | 'priority_changed';

export interface Activity {
  id: string;
  application_id: string;
  user_id?: string;
  user?: User;
  action: ActivityAction;
  details: Record<string, any>;
  created_at: string;
}

// File attachment
export type AttachmentCategory = 'budget' | 'biosketch' | 'letter' | 'draft' | 'other';

export interface Attachment {
  id: string;
  application_id: string;
  user_id: string;
  user?: User;
  filename: string;
  file_type?: string;
  file_size?: number;
  storage_path: string;
  description?: string;
  category?: AttachmentCategory;
  template_id?: string;
  created_at: string;
}

// Custom field definition
export type FieldType = 'text' | 'number' | 'date' | 'select' | 'multiselect' | 'url' | 'checkbox';

export interface FieldOption {
  value: string;
  label: string;
  color?: string;
}

export interface CustomFieldDefinition {
  id: string;
  user_id: string;
  name: string;
  field_type: FieldType;
  options?: FieldOption[];
  is_required: boolean;
  show_in_card: boolean;
  position: number;
  created_at: string;
}

export interface CustomFieldValue {
  id: string;
  application_id: string;
  field_id: string;
  field?: CustomFieldDefinition;
  value: any;
  updated_at: string;
}

// Lab team member
export type MemberRole = 'admin' | 'member' | 'viewer';

export interface LabMember {
  id: string;
  lab_owner_id: string;
  member_email: string;
  member_user_id?: string;
  member_user?: User;
  role: MemberRole;
  invited_at: string;
  accepted_at?: string;
}

// Application assignee
export interface Assignee {
  application_id: string;
  user_id: string;
  user: User;
  assigned_at: string;
  assigned_by?: string;
}

// Kanban card (application with all data)
export interface KanbanCard {
  id: string;
  user_id: string;
  grant_id?: string;
  match_id?: string;
  grant?: Grant;
  // Flat fields returned by API (in addition to nested grant object)
  grant_title?: string;
  grant_agency?: string;
  grant_deadline?: string;
  stage: ApplicationStage;
  position: number;
  priority: Priority;
  color?: string;
  notes?: string;
  target_date?: string;
  archived: boolean;
  subtasks: Subtask[];
  subtask_progress: { completed: number; total: number };
  attachments_count: number;
  assignees: Assignee[];
  custom_fields: Record<string, any>;
  created_at: string;
  updated_at: string;
}

// Board column
export interface KanbanColumn {
  stage: ApplicationStage;
  cards: KanbanCard[];
  count: number;
}

// Full board data
export interface KanbanBoard {
  columns: Record<ApplicationStage, KanbanCard[]>;
  field_definitions: CustomFieldDefinition[];
  team_members: LabMember[];
  totals: {
    total: number;
    by_stage: Record<ApplicationStage, number>;
    overdue: number;
  };
}

// API request/response types
export interface ReorderRequest {
  card_id: string;
  from_stage: ApplicationStage;
  to_stage: ApplicationStage;
  new_position: number;
}

export interface SubtaskCreate {
  title: string;
  description?: string;
  due_date?: string;
}

export interface SubtaskUpdate {
  title?: string;
  description?: string;
  is_completed?: boolean;
  due_date?: string;
  position?: number;
}

export interface AttachmentUpload {
  file: File;
  description?: string;
  category?: AttachmentCategory;
  template_id?: string;
}

export interface FieldDefinitionCreate {
  name: string;
  field_type: FieldType;
  options?: FieldOption[];
  is_required?: boolean;
  show_in_card?: boolean;
}

export interface FieldDefinitionUpdate {
  name?: string;
  options?: FieldOption[];
  is_required?: boolean;
  show_in_card?: boolean;
  position?: number;
}

export interface TeamInvite {
  email: string;
  role?: MemberRole;
}

export interface CardUpdate {
  stage?: ApplicationStage;
  position?: number;
  priority?: Priority;
  color?: string;
  notes?: string;
  target_date?: string;
  archived?: boolean;
}

// Filter params
export interface KanbanFilters {
  stages?: ApplicationStage[];
  priorities?: Priority[];
  assignee_ids?: string[];
  search?: string;
  show_archived?: boolean;
  has_overdue?: boolean;
}

// Stage configuration for UI
export interface StageConfig {
  key: ApplicationStage;
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  icon: string;
}

export const STAGE_CONFIGS: StageConfig[] = [
  { key: 'researching', label: 'Researching', color: 'text-cyan-600', bgColor: 'bg-cyan-50', borderColor: 'border-cyan-200', icon: 'MagnifyingGlassIcon' },
  { key: 'writing', label: 'Writing', color: 'text-amber-600', bgColor: 'bg-amber-50', borderColor: 'border-amber-200', icon: 'PencilIcon' },
  { key: 'submitted', label: 'Submitted', color: 'text-blue-600', bgColor: 'bg-blue-50', borderColor: 'border-blue-200', icon: 'PaperAirplaneIcon' },
  { key: 'awarded', label: 'Awarded', color: 'text-emerald-600', bgColor: 'bg-emerald-50', borderColor: 'border-emerald-200', icon: 'CheckBadgeIcon' },
  { key: 'rejected', label: 'Rejected', color: 'text-slate-500', bgColor: 'bg-slate-50', borderColor: 'border-slate-200', icon: 'XCircleIcon' },
];

export const PRIORITY_CONFIGS: Record<Priority, { label: string; color: string; bgColor: string }> = {
  low: { label: 'Low', color: 'text-slate-500', bgColor: 'bg-slate-100' },
  medium: { label: 'Medium', color: 'text-blue-600', bgColor: 'bg-blue-100' },
  high: { label: 'High', color: 'text-amber-600', bgColor: 'bg-amber-100' },
  critical: { label: 'Critical', color: 'text-red-600', bgColor: 'bg-red-100' },
};
