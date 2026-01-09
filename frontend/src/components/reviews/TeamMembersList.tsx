import { useState } from 'react';
import {
  UserGroupIcon,
  PlusIcon,
  EllipsisVerticalIcon,
  TrashIcon,
  PencilIcon,
  UserIcon,
} from '@heroicons/react/24/outline';
import { Menu, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import { useTeamMembers, useRemoveTeamMember, useUpdateTeamMember } from '../../hooks/useReviews';
import { AddTeamMemberModal } from './AddTeamMemberModal';
import { ROLE_CONFIGS } from '../../types/reviews';
import type { ApplicationTeamMember, TeamMemberRole } from '../../types/reviews';

interface TeamMembersListProps {
  cardId: string;
  isEditable?: boolean;
}

export function TeamMembersList({ cardId, isEditable = true }: TeamMembersListProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingMember, setEditingMember] = useState<ApplicationTeamMember | null>(null);

  const { data, isLoading, error } = useTeamMembers(cardId);
  const removeTeamMemberMutation = useRemoveTeamMember();
  const updateTeamMemberMutation = useUpdateTeamMember();

  const members = data?.members || [];

  const handleRemoveMember = (member: ApplicationTeamMember) => {
    if (window.confirm(`Remove ${member.user?.name || member.user?.email} from the team?`)) {
      removeTeamMemberMutation.mutate({ cardId, memberId: member.id });
    }
  };

  const handleRoleChange = (member: ApplicationTeamMember, newRole: TeamMemberRole) => {
    updateTeamMemberMutation.mutate({
      cardId,
      memberId: member.id,
      data: { role: newRole },
    });
    setEditingMember(null);
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="h-5 bg-gray-200 rounded w-24 animate-pulse" />
          <div className="h-8 bg-gray-200 rounded w-20 animate-pulse" />
        </div>
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center gap-3 animate-pulse">
            <div className="w-10 h-10 rounded-full bg-gray-200" />
            <div className="flex-1 space-y-1">
              <div className="h-4 bg-gray-200 rounded w-1/3" />
              <div className="h-3 bg-gray-200 rounded w-1/4" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-6 text-sm text-red-500">
        Failed to load team members
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <UserGroupIcon className="w-5 h-5 text-gray-500" />
          <h3 className="text-sm font-medium text-gray-900">Team Members</h3>
          <span className="px-1.5 py-0.5 text-xs bg-gray-100 text-gray-600 rounded-full">
            {members.length}
          </span>
        </div>
        {isEditable && (
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
          >
            <PlusIcon className="w-4 h-4" />
            Add
          </button>
        )}
      </div>

      {/* Members list */}
      {members.length === 0 ? (
        <div className="text-center py-8 bg-gray-50 rounded-lg border border-dashed border-gray-200">
          <UserGroupIcon className="w-10 h-10 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">No team members yet</p>
          {isEditable && (
            <button
              onClick={() => setShowAddModal(true)}
              className="mt-2 text-sm text-blue-600 hover:text-blue-700"
            >
              Add the first member
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {members.map((member) => (
            <MemberItem
              key={member.id}
              member={member}
              isEditing={editingMember?.id === member.id}
              isEditable={isEditable}
              onEdit={() => setEditingMember(member)}
              onCancelEdit={() => setEditingMember(null)}
              onRoleChange={(role) => handleRoleChange(member, role)}
              onRemove={() => handleRemoveMember(member)}
              isUpdating={updateTeamMemberMutation.isPending}
              isRemoving={removeTeamMemberMutation.isPending}
            />
          ))}
        </div>
      )}

      {/* Add member modal */}
      {showAddModal && (
        <AddTeamMemberModal cardId={cardId} onClose={() => setShowAddModal(false)} />
      )}
    </div>
  );
}

interface MemberItemProps {
  member: ApplicationTeamMember;
  isEditing: boolean;
  isEditable: boolean;
  onEdit: () => void;
  onCancelEdit: () => void;
  onRoleChange: (role: TeamMemberRole) => void;
  onRemove: () => void;
  isUpdating: boolean;
  isRemoving: boolean;
}

function MemberItem({
  member,
  isEditing,
  isEditable,
  onEdit,
  onCancelEdit,
  onRoleChange,
  onRemove,
  isUpdating,
  isRemoving,
}: MemberItemProps) {
  const roleConfig = ROLE_CONFIGS[member.role];
  const displayName = member.user?.name || member.user?.email || 'Unknown User';
  const initials = displayName
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  return (
    <div className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-lg hover:border-gray-300 transition-colors">
      {/* Avatar */}
      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-sm font-medium flex-shrink-0">
        {initials || <UserIcon className="w-5 h-5" />}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">{displayName}</p>
        {isEditing ? (
          <select
            value={member.role}
            onChange={(e) => onRoleChange(e.target.value as TeamMemberRole)}
            disabled={isUpdating}
            className="mt-1 w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            {Object.values(ROLE_CONFIGS).map((config) => (
              <option key={config.key} value={config.key}>
                {config.label}
              </option>
            ))}
          </select>
        ) : (
          <span
            className={`inline-flex items-center mt-0.5 px-2 py-0.5 rounded-full text-xs font-medium ${roleConfig.bgColor} ${roleConfig.color}`}
          >
            {roleConfig.label}
          </span>
        )}
      </div>

      {/* Permissions indicators */}
      <div className="flex items-center gap-1">
        {member.permissions.can_edit && (
          <span className="w-5 h-5 rounded bg-blue-100 text-blue-600 flex items-center justify-center" title="Can edit">
            <PencilIcon className="w-3 h-3" />
          </span>
        )}
        {member.permissions.can_approve && (
          <span className="w-5 h-5 rounded bg-green-100 text-green-600 flex items-center justify-center" title="Can approve">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          </span>
        )}
      </div>

      {/* Actions menu */}
      {isEditable && (
        <Menu as="div" className="relative">
          <Menu.Button className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
            <EllipsisVerticalIcon className="w-5 h-5 text-gray-400" />
          </Menu.Button>
          <Transition
            as={Fragment}
            enter="transition ease-out duration-100"
            enterFrom="transform opacity-0 scale-95"
            enterTo="transform opacity-100 scale-100"
            leave="transition ease-in duration-75"
            leaveFrom="transform opacity-100 scale-100"
            leaveTo="transform opacity-0 scale-95"
          >
            <Menu.Items className="absolute right-0 mt-1 w-40 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-10">
              <Menu.Item>
                {({ active }) => (
                  <button
                    onClick={isEditing ? onCancelEdit : onEdit}
                    className={`w-full px-3 py-2 text-sm text-left flex items-center gap-2 ${
                      active ? 'bg-gray-50' : ''
                    }`}
                  >
                    <PencilIcon className="w-4 h-4 text-gray-500" />
                    {isEditing ? 'Cancel' : 'Change Role'}
                  </button>
                )}
              </Menu.Item>
              <Menu.Item>
                {({ active }) => (
                  <button
                    onClick={onRemove}
                    disabled={isRemoving}
                    className={`w-full px-3 py-2 text-sm text-left flex items-center gap-2 text-red-600 ${
                      active ? 'bg-red-50' : ''
                    } disabled:opacity-50`}
                  >
                    <TrashIcon className="w-4 h-4" />
                    Remove
                  </button>
                )}
              </Menu.Item>
            </Menu.Items>
          </Transition>
        </Menu>
      )}
    </div>
  );
}

export default TeamMembersList;
