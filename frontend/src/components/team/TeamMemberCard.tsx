import { Fragment, useState } from 'react';
import { Menu, Transition } from '@headlessui/react';
import {
  EllipsisVerticalIcon,
  PencilIcon,
  TrashIcon,
  EnvelopeIcon,
  DocumentDuplicateIcon,
} from '@heroicons/react/24/outline';
import type { TeamMember } from '../../types/team';
import { ROLE_CONFIGS, INVITATION_STATUS_CONFIGS } from '../../types/team';

interface TeamMemberCardProps {
  member: TeamMember;
  onEditRole: (member: TeamMember) => void;
  onRemove: (member: TeamMember) => void;
  isCurrentUser?: boolean;
}

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

export function TeamMemberCard({ member, onEditRole, onRemove, isCurrentUser = false }: TeamMemberCardProps) {
  const [showRemoveConfirm, setShowRemoveConfirm] = useState(false);

  const roleConfig = ROLE_CONFIGS[member.role];
  const statusConfig = INVITATION_STATUS_CONFIGS[member.invitation_status];
  const isActive = member.invitation_status === 'accepted';
  const isPending = member.invitation_status === 'pending';

  // Generate initials from name or email
  const getInitials = () => {
    if (member.member_name) {
      const parts = member.member_name.split(' ');
      return parts.length > 1
        ? `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
        : member.member_name.substring(0, 2).toUpperCase();
    }
    return member.member_email.substring(0, 2).toUpperCase();
  };

  const handleRemove = () => {
    if (showRemoveConfirm) {
      onRemove(member);
      setShowRemoveConfirm(false);
    } else {
      setShowRemoveConfirm(true);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-all duration-200">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          {/* Avatar */}
          <div className={classNames(
            'w-12 h-12 rounded-xl flex items-center justify-center text-white font-semibold text-lg',
            isActive
              ? 'bg-gradient-to-br from-blue-500 to-blue-600'
              : 'bg-gradient-to-br from-gray-400 to-gray-500'
          )}>
            {getInitials()}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-gray-900 truncate">
                {member.member_name || member.member_email.split('@')[0]}
              </h3>
              {isCurrentUser && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700">
                  You
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500 truncate flex items-center gap-1">
              <EnvelopeIcon className="w-3.5 h-3.5" />
              {member.member_email}
            </p>

            {/* Role and Status badges */}
            <div className="flex items-center gap-2 mt-2">
              <span className={classNames(
                'inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium',
                roleConfig.bgColor,
                roleConfig.color
              )}>
                {roleConfig.label}
              </span>
              {!isActive && (
                <span className={classNames(
                  'inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium',
                  statusConfig.bgColor,
                  statusConfig.color
                )}>
                  {statusConfig.label}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Actions menu */}
        {!isCurrentUser && (
          <Menu as="div" className="relative">
            <Menu.Button className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
              <EllipsisVerticalIcon className="w-5 h-5" />
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
              <Menu.Items className="absolute right-0 z-10 mt-2 w-48 origin-top-right rounded-xl bg-white shadow-lg ring-1 ring-black/5 focus:outline-none py-1">
                <Menu.Item>
                  {({ active }) => (
                    <button
                      onClick={() => onEditRole(member)}
                      className={classNames(
                        active ? 'bg-gray-50' : '',
                        'flex items-center gap-3 w-full px-4 py-2.5 text-sm text-gray-700'
                      )}
                    >
                      <PencilIcon className="w-4 h-4" />
                      Edit Role
                    </button>
                  )}
                </Menu.Item>
                <Menu.Item>
                  {({ active }) => (
                    <button
                      onClick={handleRemove}
                      className={classNames(
                        active ? 'bg-red-50' : '',
                        'flex items-center gap-3 w-full px-4 py-2.5 text-sm',
                        showRemoveConfirm ? 'text-red-600 font-medium' : 'text-gray-700'
                      )}
                    >
                      <TrashIcon className="w-4 h-4" />
                      {showRemoveConfirm ? 'Click to confirm' : 'Remove'}
                    </button>
                  )}
                </Menu.Item>
              </Menu.Items>
            </Transition>
          </Menu>
        )}
      </div>

      {/* Stats row */}
      {isActive && member.applications_assigned > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <DocumentDuplicateIcon className="w-4 h-4" />
            <span>{member.applications_assigned} application{member.applications_assigned !== 1 ? 's' : ''} assigned</span>
          </div>
        </div>
      )}

      {/* Pending invitation info */}
      {isPending && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <p className="text-xs text-gray-500">
            Invited {new Date(member.invited_at).toLocaleDateString()}
          </p>
        </div>
      )}
    </div>
  );
}

export default TeamMemberCard;
