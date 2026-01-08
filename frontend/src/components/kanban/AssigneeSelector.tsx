import { useState } from 'react';
import { useTeamMembers, useUpdateAssignees } from '../../hooks/useKanban';
import { UserPlusIcon, XMarkIcon } from '@heroicons/react/24/outline';
import type { Assignee, LabMember } from '../../types/kanban';

interface AssigneeSelectorProps {
  applicationId: string;
  currentAssignees: Assignee[];
}

export function AssigneeSelector({ applicationId, currentAssignees }: AssigneeSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { data: teamMembers = [] } = useTeamMembers();
  const updateAssigneesMutation = useUpdateAssignees();

  const handleToggle = (userId: string) => {
    const currentIds = currentAssignees.map(a => a.user_id);
    const newIds = currentIds.includes(userId)
      ? currentIds.filter(id => id !== userId)
      : [...currentIds, userId];

    updateAssigneesMutation.mutate({ appId: applicationId, userIds: newIds });
  };

  const getAssigneeName = (assignee: Assignee): string => {
    return assignee.user?.name || assignee.user?.email || 'Unknown';
  };

  const getMemberName = (member: LabMember): string => {
    return member.member_user?.name || member.member_email;
  };

  return (
    <div className="space-y-2">
      {/* Current assignees */}
      <div className="flex flex-wrap gap-2">
        {currentAssignees.map((assignee) => (
          <div
            key={assignee.user_id}
            className="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded-full text-sm"
          >
            <span className="w-5 h-5 rounded-full bg-gray-300 flex items-center justify-center text-xs">
              {getAssigneeName(assignee)[0].toUpperCase()}
            </span>
            <span className="text-gray-700 truncate max-w-[100px]">
              {getAssigneeName(assignee)}
            </span>
            <button
              onClick={() => handleToggle(assignee.user_id)}
              className="p-0.5 hover:bg-gray-200 rounded"
            >
              <XMarkIcon className="w-3 h-3 text-gray-500" />
            </button>
          </div>
        ))}
      </div>

      {/* Add assignee button */}
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
        >
          <UserPlusIcon className="w-4 h-4" />
          Add assignee
        </button>

        {isOpen && (
          <>
            {/* Click outside to close */}
            <div
              className="fixed inset-0 z-10"
              onClick={() => setIsOpen(false)}
            />
            <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-20">
              {teamMembers.length === 0 ? (
                <p className="p-3 text-sm text-gray-500">No team members</p>
              ) : (
                <div className="max-h-48 overflow-y-auto">
                  {teamMembers.map((member: LabMember) => {
                    const isAssigned = currentAssignees.some(
                      a => a.user_id === member.member_user_id
                    );

                    if (!member.member_user_id) return null;

                    return (
                      <button
                        key={member.id}
                        onClick={() => {
                          if (member.member_user_id) {
                            handleToggle(member.member_user_id);
                          }
                        }}
                        className={`w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2 ${
                          isAssigned ? 'bg-blue-50' : ''
                        }`}
                      >
                        <span className="w-6 h-6 rounded-full bg-gray-300 flex items-center justify-center text-xs">
                          {getMemberName(member)[0].toUpperCase()}
                        </span>
                        <span className="truncate">{getMemberName(member)}</span>
                        {isAssigned && (
                          <span className="ml-auto text-blue-600">&#10003;</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default AssigneeSelector;
