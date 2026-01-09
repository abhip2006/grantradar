import type { User } from './index';

// Role types for team members in a review workflow
export type TeamMemberRole = 'pi' | 'co_i' | 'grant_writer' | 'reviewer' | 'admin';

// Review status types
export type ReviewStatus = 'pending' | 'in_review' | 'approved' | 'rejected' | 'escalated';

// Review action types
export type ReviewAction = 'approved' | 'rejected' | 'returned' | 'commented';

// Review stage configuration
export interface ReviewStage {
  order: number;
  name: string;
  required_role: TeamMemberRole;
  sla_hours: number;
  auto_escalate: boolean;
}

// Review workflow template
export interface ReviewWorkflow {
  id: string;
  name: string;
  stages: ReviewStage[];
  is_default: boolean;
  created_at: string;
}

// Application-specific review instance
export interface ApplicationReview {
  id: string;
  kanban_card_id: string;
  workflow_id: string;
  workflow?: ReviewWorkflow;
  current_stage: number;
  status: ReviewStatus;
  started_at: string;
  completed_at?: string;
  /**
   * Computed fields - calculated by the backend based on workflow and current state.
   * These should NOT be computed on the frontend; they are returned from the API response.
   */
  /** Current stage name derived from workflow.stages[current_stage] on backend */
  current_stage_name?: string;
  /** SLA deadline calculated from started_at + stage.sla_hours on backend */
  sla_deadline?: string;
  /** Whether the review is past its SLA deadline, calculated on backend */
  is_overdue?: boolean;
  /** Progress percentage through the workflow stages, calculated on backend */
  progress_percent?: number;
}

// Individual review action record
export interface ReviewStageAction {
  id: string;
  review_id: string;
  stage_order: number;
  stage_name?: string;
  reviewer_id: string;
  reviewer?: User;
  action: ReviewAction;
  comments?: string;
  acted_at: string;
}

// Team member permissions
export interface TeamMemberPermissions {
  can_edit: boolean;
  can_approve: boolean;
  can_submit: boolean;
  sections?: string[];
}

// Team member assigned to an application
export interface ApplicationTeamMember {
  id: string;
  kanban_card_id: string;
  user_id: string;
  user?: User;
  role: TeamMemberRole;
  permissions: TeamMemberPermissions;
  added_at: string;
}

// API request types
export interface StartReviewRequest {
  workflow_id?: string;
}

export interface SubmitReviewActionRequest {
  action: ReviewAction;
  comments?: string;
}

export interface AddTeamMemberRequest {
  user_id?: string;
  email?: string;
  role: TeamMemberRole;
  permissions?: Partial<TeamMemberPermissions>;
}

export interface UpdateTeamMemberRequest {
  role?: TeamMemberRole;
  permissions?: Partial<TeamMemberPermissions>;
}

// API response types
export interface ReviewWorkflowListResponse {
  workflows: ReviewWorkflow[];
  total: number;
}

export interface ReviewHistoryResponse {
  actions: ReviewStageAction[];
  total: number;
}

export interface TeamMembersResponse {
  members: ApplicationTeamMember[];
  total: number;
}

// UI configuration for roles
export interface RoleConfig {
  key: TeamMemberRole;
  label: string;
  color: string;
  bgColor: string;
  description: string;
}

export const ROLE_CONFIGS: Record<TeamMemberRole, RoleConfig> = {
  pi: {
    key: 'pi',
    label: 'Principal Investigator',
    color: 'text-purple-700',
    bgColor: 'bg-purple-100',
    description: 'Lead researcher and primary contact',
  },
  co_i: {
    key: 'co_i',
    label: 'Co-Investigator',
    color: 'text-blue-700',
    bgColor: 'bg-blue-100',
    description: 'Supporting researcher with shared responsibility',
  },
  grant_writer: {
    key: 'grant_writer',
    label: 'Grant Writer',
    color: 'text-emerald-700',
    bgColor: 'bg-emerald-100',
    description: 'Professional writer assisting with application',
  },
  reviewer: {
    key: 'reviewer',
    label: 'Reviewer',
    color: 'text-amber-700',
    bgColor: 'bg-amber-100',
    description: 'Internal reviewer providing feedback',
  },
  admin: {
    key: 'admin',
    label: 'Administrator',
    color: 'text-slate-700',
    bgColor: 'bg-slate-100',
    description: 'Administrative support and oversight',
  },
};

// UI configuration for review status
export interface StatusConfig {
  key: ReviewStatus;
  label: string;
  color: string;
  bgColor: string;
  icon: string;
}

export const REVIEW_STATUS_CONFIGS: Record<ReviewStatus, StatusConfig> = {
  pending: {
    key: 'pending',
    label: 'Pending',
    color: 'text-gray-600',
    bgColor: 'bg-gray-100',
    icon: 'ClockIcon',
  },
  in_review: {
    key: 'in_review',
    label: 'In Review',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    icon: 'EyeIcon',
  },
  approved: {
    key: 'approved',
    label: 'Approved',
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    icon: 'CheckCircleIcon',
  },
  rejected: {
    key: 'rejected',
    label: 'Rejected',
    color: 'text-red-600',
    bgColor: 'bg-red-100',
    icon: 'XCircleIcon',
  },
  escalated: {
    key: 'escalated',
    label: 'Escalated',
    color: 'text-orange-600',
    bgColor: 'bg-orange-100',
    icon: 'ExclamationTriangleIcon',
  },
};

// UI configuration for review actions
export interface ActionConfig {
  key: ReviewAction;
  label: string;
  color: string;
  bgColor: string;
  icon: string;
  description: string;
}

export const REVIEW_ACTION_CONFIGS: Record<ReviewAction, ActionConfig> = {
  approved: {
    key: 'approved',
    label: 'Approve',
    color: 'text-green-700',
    bgColor: 'bg-green-100',
    icon: 'CheckIcon',
    description: 'Approve and advance to next stage',
  },
  rejected: {
    key: 'rejected',
    label: 'Reject',
    color: 'text-red-700',
    bgColor: 'bg-red-100',
    icon: 'XMarkIcon',
    description: 'Reject the application at this stage',
  },
  returned: {
    key: 'returned',
    label: 'Return for Revision',
    color: 'text-amber-700',
    bgColor: 'bg-amber-100',
    icon: 'ArrowUturnLeftIcon',
    description: 'Return to previous stage for changes',
  },
  commented: {
    key: 'commented',
    label: 'Add Comment',
    color: 'text-blue-700',
    bgColor: 'bg-blue-100',
    icon: 'ChatBubbleLeftIcon',
    description: 'Add feedback without changing status',
  },
};
