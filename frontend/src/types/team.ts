export type InvitationStatus = 'pending' | 'accepted' | 'declined' | 'expired' | 'cancelled';
export type MemberRole = 'admin' | 'member' | 'viewer';

export interface MemberPermissions {
  can_view: boolean;
  can_edit: boolean;
  can_create: boolean;
  can_delete: boolean;
  can_invite: boolean;
  can_manage_grants?: boolean;
  can_export?: boolean;
}

export interface TeamMember {
  id: string;
  lab_owner_id: string;
  member_email: string;
  member_user_id?: string;
  member_name?: string;
  role: MemberRole;
  permissions: MemberPermissions;
  invitation_status: InvitationStatus;
  invited_at: string;
  accepted_at?: string;
  applications_assigned: number;
}

export interface TeamActivity {
  id: string;
  actor_id?: string;
  actor_name?: string;
  action_type: string;
  entity_type: string;
  entity_id?: string;
  entity_name?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface TeamStats {
  total_members: number;
  active_members: number;
  pending_invitations: number;
  applications_in_progress: number;
  activity_count_7d: number;
}

// Request types
export interface TeamInviteRequest {
  email: string;
  role: MemberRole;
  message?: string;
}

export interface TeamMemberUpdate {
  role?: MemberRole;
  permissions?: MemberPermissions;
}

export interface TeamActivityFilters {
  action_types?: string[];
  actor_ids?: string[];
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}

// Role configuration for UI
export const ROLE_CONFIGS: Record<MemberRole, { label: string; color: string; bgColor: string; description: string }> = {
  admin: { label: 'Admin', color: 'text-purple-700', bgColor: 'bg-purple-100', description: 'Full access including inviting members' },
  member: { label: 'Member', color: 'text-blue-700', bgColor: 'bg-blue-100', description: 'Can view and edit applications' },
  viewer: { label: 'Viewer', color: 'text-gray-700', bgColor: 'bg-gray-100', description: 'Read-only access' },
};

export const INVITATION_STATUS_CONFIGS: Record<InvitationStatus, { label: string; color: string; bgColor: string }> = {
  pending: { label: 'Pending', color: 'text-yellow-700', bgColor: 'bg-yellow-100' },
  accepted: { label: 'Active', color: 'text-green-700', bgColor: 'bg-green-100' },
  declined: { label: 'Declined', color: 'text-red-700', bgColor: 'bg-red-100' },
  expired: { label: 'Expired', color: 'text-gray-700', bgColor: 'bg-gray-100' },
  cancelled: { label: 'Cancelled', color: 'text-gray-700', bgColor: 'bg-gray-100' },
};

// ============================================
// Permission Template Types
// ============================================

export interface PermissionTemplate {
  id: string;
  owner_id: string;
  name: string;
  description?: string;
  permissions: MemberPermissions;
  is_default: boolean;
  created_at: string;
  updated_at?: string;
}

export interface PermissionTemplateCreate {
  name: string;
  description?: string;
  permissions: MemberPermissions;
}

export interface PermissionTemplateUpdate {
  name?: string;
  description?: string;
  permissions?: MemberPermissions;
}

// ============================================
// Notification Types
// ============================================

export type NotificationType =
  | 'team_invite_received'
  | 'team_invite_accepted'
  | 'team_invite_declined'
  | 'team_role_changed'
  | 'team_member_removed'
  | 'team_member_joined';

export interface Notification {
  id: string;
  user_id: string;
  type: NotificationType;
  title: string;
  message: string;
  metadata?: Record<string, unknown>;
  read: boolean;
  read_at?: string;
  action_url?: string;
  created_at: string;
}

// ============================================
// Bulk Invite Types
// ============================================

export interface BulkInviteItem {
  email: string;
  role: MemberRole;
  message?: string;
  permission_template_id?: string;
}

export interface BulkInviteRequest {
  invitations: BulkInviteItem[];
}

export interface BulkInviteResult {
  email: string;
  success: boolean;
  error?: string;
  member?: TeamMember;
}

export interface BulkInviteResponse {
  successful: BulkInviteResult[];
  failed: BulkInviteResult[];
}

// ============================================
// Extended MemberPermissions
// ============================================

// Note: The base MemberPermissions interface is defined above.
// These are optional extended permissions that may be added:
export interface ExtendedMemberPermissions extends MemberPermissions {
  can_manage_grants?: boolean;
  can_export?: boolean;
}
