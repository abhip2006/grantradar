import { useState, Fragment, useMemo } from 'react';
import { Dialog, Transition, Listbox } from '@headlessui/react';
import {
  XMarkIcon,
  MagnifyingGlassIcon,
  UserPlusIcon,
  CheckIcon,
  ChevronUpDownIcon,
} from '@heroicons/react/24/outline';
import { useAddTeamMember, useAvailableUsers } from '../../hooks/useReviews';
import { ROLE_CONFIGS, TeamMemberRole } from '../../types/reviews';

interface AddTeamMemberModalProps {
  cardId: string;
  onClose: () => void;
}

const DEFAULT_PERMISSIONS = {
  pi: { can_edit: true, can_approve: true, can_submit: true },
  co_i: { can_edit: true, can_approve: false, can_submit: false },
  grant_writer: { can_edit: true, can_approve: false, can_submit: false },
  reviewer: { can_edit: false, can_approve: true, can_submit: false },
  admin: { can_edit: true, can_approve: true, can_submit: true },
};

export function AddTeamMemberModal({ cardId, onClose }: AddTeamMemberModalProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState<TeamMemberRole>('reviewer');
  const [emailInput, setEmailInput] = useState('');
  const [addByEmail, setAddByEmail] = useState(false);

  const { data: availableUsersData, isLoading: loadingUsers } = useAvailableUsers(cardId, {
    search: searchQuery,
    limit: 20,
  });
  const addTeamMemberMutation = useAddTeamMember();

  const availableUsers = availableUsersData?.users || [];

  const filteredUsers = useMemo(() => {
    if (!searchQuery.trim()) return availableUsers;
    const query = searchQuery.toLowerCase();
    return availableUsers.filter(
      (user) =>
        user.name?.toLowerCase().includes(query) || user.email.toLowerCase().includes(query)
    );
  }, [availableUsers, searchQuery]);

  const selectedUser = availableUsers.find((u) => u.id === selectedUserId);
  const roleConfig = ROLE_CONFIGS[selectedRole];

  const handleSubmit = () => {
    if (addByEmail) {
      if (!emailInput.trim()) return;
      addTeamMemberMutation.mutate(
        {
          cardId,
          data: {
            email: emailInput.trim(),
            role: selectedRole,
            permissions: DEFAULT_PERMISSIONS[selectedRole],
          },
        },
        { onSuccess: () => onClose() }
      );
    } else {
      if (!selectedUserId) return;
      addTeamMemberMutation.mutate(
        {
          cardId,
          data: {
            user_id: selectedUserId,
            role: selectedRole,
            permissions: DEFAULT_PERMISSIONS[selectedRole],
          },
        },
        { onSuccess: () => onClose() }
      );
    }
  };

  const canSubmit = addByEmail
    ? emailInput.trim().length > 0 && emailInput.includes('@')
    : selectedUserId !== null;

  return (
    <Transition appear show as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-md bg-white rounded-xl shadow-xl">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b">
                  <div className="flex items-center gap-2">
                    <UserPlusIcon className="w-5 h-5 text-blue-600" />
                    <Dialog.Title className="text-lg font-semibold text-gray-900">
                      Add Team Member
                    </Dialog.Title>
                  </div>
                  <button
                    onClick={onClose}
                    className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <XMarkIcon className="w-5 h-5 text-gray-500" />
                  </button>
                </div>

                <div className="p-4 space-y-4">
                  {/* Toggle between existing user and email */}
                  <div className="flex gap-2 p-1 bg-gray-100 rounded-lg">
                    <button
                      onClick={() => setAddByEmail(false)}
                      className={`flex-1 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                        !addByEmail
                          ? 'bg-white text-gray-900 shadow-sm'
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      Existing User
                    </button>
                    <button
                      onClick={() => setAddByEmail(true)}
                      className={`flex-1 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                        addByEmail
                          ? 'bg-white text-gray-900 shadow-sm'
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      Invite by Email
                    </button>
                  </div>

                  {addByEmail ? (
                    /* Email input */
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Email Address
                      </label>
                      <input
                        type="email"
                        value={emailInput}
                        onChange={(e) => setEmailInput(e.target.value)}
                        placeholder="colleague@institution.edu"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                      <p className="mt-1 text-xs text-gray-500">
                        An invitation will be sent to this email address
                      </p>
                    </div>
                  ) : (
                    /* User search and select */
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Search Users
                      </label>
                      <div className="relative">
                        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                          type="text"
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          placeholder="Search by name or email..."
                          className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>

                      {/* User list */}
                      <div className="mt-2 max-h-48 overflow-y-auto border border-gray-200 rounded-lg divide-y divide-gray-100">
                        {loadingUsers ? (
                          <div className="p-4 text-center text-sm text-gray-500">
                            Loading users...
                          </div>
                        ) : filteredUsers.length === 0 ? (
                          <div className="p-4 text-center text-sm text-gray-500">
                            {searchQuery ? 'No users found' : 'Start typing to search'}
                          </div>
                        ) : (
                          filteredUsers.map((user) => (
                            <button
                              key={user.id}
                              onClick={() => setSelectedUserId(user.id)}
                              className={`w-full px-3 py-2 flex items-center gap-3 text-left transition-colors ${
                                selectedUserId === user.id
                                  ? 'bg-blue-50'
                                  : 'hover:bg-gray-50'
                              }`}
                            >
                              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xs font-medium flex-shrink-0">
                                {(user.name || user.email)
                                  .split(' ')
                                  .map((n) => n[0])
                                  .join('')
                                  .toUpperCase()
                                  .slice(0, 2)}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-900 truncate">
                                  {user.name || user.email}
                                </p>
                                {user.name && (
                                  <p className="text-xs text-gray-500 truncate">{user.email}</p>
                                )}
                              </div>
                              {selectedUserId === user.id && (
                                <CheckIcon className="w-4 h-4 text-blue-600 flex-shrink-0" />
                              )}
                            </button>
                          ))
                        )}
                      </div>

                      {/* Selected user display */}
                      {selectedUser && (
                        <div className="mt-2 p-2 bg-blue-50 border border-blue-100 rounded-lg">
                          <p className="text-sm text-blue-900">
                            Selected: <span className="font-medium">{selectedUser.name || selectedUser.email}</span>
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Role selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Role
                    </label>
                    <Listbox value={selectedRole} onChange={setSelectedRole}>
                      <div className="relative">
                        <Listbox.Button className="relative w-full px-3 py-2 text-left bg-white border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer">
                          <span className="flex items-center gap-2">
                            <span
                              className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${roleConfig.bgColor} ${roleConfig.color}`}
                            >
                              {roleConfig.label}
                            </span>
                          </span>
                          <ChevronUpDownIcon className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        </Listbox.Button>
                        <Transition
                          as={Fragment}
                          leave="transition ease-in duration-100"
                          leaveFrom="opacity-100"
                          leaveTo="opacity-0"
                        >
                          <Listbox.Options className="absolute z-10 mt-1 w-full bg-white rounded-lg shadow-lg border border-gray-200 py-1 max-h-60 overflow-auto">
                            {Object.values(ROLE_CONFIGS).map((config) => (
                              <Listbox.Option
                                key={config.key}
                                value={config.key}
                                className={({ active }) =>
                                  `px-3 py-2 cursor-pointer ${active ? 'bg-gray-50' : ''}`
                                }
                              >
                                {({ selected }) => (
                                  <div className="flex items-start gap-3">
                                    <span
                                      className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${config.bgColor} ${config.color}`}
                                    >
                                      {config.label}
                                    </span>
                                    <div className="flex-1">
                                      <p className="text-xs text-gray-500">{config.description}</p>
                                    </div>
                                    {selected && (
                                      <CheckIcon className="w-4 h-4 text-blue-600 flex-shrink-0" />
                                    )}
                                  </div>
                                )}
                              </Listbox.Option>
                            ))}
                          </Listbox.Options>
                        </Transition>
                      </div>
                    </Listbox>
                  </div>

                  {/* Permissions preview */}
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-xs font-medium text-gray-700 mb-2">Default Permissions</p>
                    <div className="flex flex-wrap gap-2">
                      {DEFAULT_PERMISSIONS[selectedRole].can_edit && (
                        <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
                          Can Edit
                        </span>
                      )}
                      {DEFAULT_PERMISSIONS[selectedRole].can_approve && (
                        <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded-full">
                          Can Approve
                        </span>
                      )}
                      {DEFAULT_PERMISSIONS[selectedRole].can_submit && (
                        <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full">
                          Can Submit
                        </span>
                      )}
                      {!DEFAULT_PERMISSIONS[selectedRole].can_edit &&
                        !DEFAULT_PERMISSIONS[selectedRole].can_approve &&
                        !DEFAULT_PERMISSIONS[selectedRole].can_submit && (
                          <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded-full">
                            View Only
                          </span>
                        )}
                    </div>
                  </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-2 p-4 border-t bg-gray-50">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSubmit}
                    disabled={!canSubmit || addTeamMemberMutation.isPending}
                    className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {addTeamMemberMutation.isPending ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Adding...
                      </>
                    ) : (
                      <>
                        <UserPlusIcon className="w-4 h-4" />
                        {addByEmail ? 'Send Invite' : 'Add Member'}
                      </>
                    )}
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}

export default AddTeamMemberModal;
