import { TeamMemberCard } from './TeamMemberCard';
import { UserGroupIcon } from '@heroicons/react/24/outline';
import type { TeamMember } from '../../types/team';

interface TeamMembersListProps {
  members: TeamMember[];
  currentUserId?: string;
  isLoading?: boolean;
  onEditRole: (member: TeamMember) => void;
  onRemove: (member: TeamMember) => void;
}

// Loading skeleton component
function TeamMemberSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-xl bg-gray-200" />
        <div className="flex-1">
          <div className="h-4 bg-gray-200 rounded w-32 mb-2" />
          <div className="h-3 bg-gray-200 rounded w-48 mb-3" />
          <div className="flex gap-2">
            <div className="h-6 bg-gray-200 rounded w-16" />
            <div className="h-6 bg-gray-200 rounded w-16" />
          </div>
        </div>
      </div>
    </div>
  );
}

export function TeamMembersList({
  members,
  currentUserId,
  isLoading = false,
  onEditRole,
  onRemove,
}: TeamMembersListProps) {
  // Show loading skeletons
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <TeamMemberSkeleton key={i} />
        ))}
      </div>
    );
  }

  // Show empty state
  if (members.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="w-16 h-16 mx-auto mb-4 rounded-xl bg-gray-100 flex items-center justify-center">
          <UserGroupIcon className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-1">No team members yet</h3>
        <p className="text-sm text-gray-500 max-w-sm mx-auto">
          Invite collaborators to help manage grant applications. Team members can view, edit, and track applications together.
        </p>
      </div>
    );
  }

  // Sort members: current user first, then active members, then pending
  const sortedMembers = [...members].sort((a, b) => {
    // Current user first
    if (a.member_user_id === currentUserId) return -1;
    if (b.member_user_id === currentUserId) return 1;
    // Then by status (accepted before pending)
    if (a.invitation_status === 'accepted' && b.invitation_status !== 'accepted') return -1;
    if (a.invitation_status !== 'accepted' && b.invitation_status === 'accepted') return 1;
    // Then by name/email
    const nameA = a.member_name || a.member_email;
    const nameB = b.member_name || b.member_email;
    return nameA.localeCompare(nameB);
  });

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {sortedMembers.map((member) => (
        <TeamMemberCard
          key={member.id}
          member={member}
          isCurrentUser={member.member_user_id === currentUserId}
          onEditRole={onEditRole}
          onRemove={onRemove}
        />
      ))}
    </div>
  );
}

export default TeamMembersList;
