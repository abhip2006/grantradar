import { useState, useEffect, Fragment, useMemo } from 'react';
import { Tab } from '@headlessui/react';
import { Dialog, Transition, RadioGroup } from '@headlessui/react';
import {
  UserGroupIcon,
  UserPlusIcon,
  EnvelopeIcon,
  ClockIcon,
  XMarkIcon,
  CheckCircleIcon,
  UsersIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';
import {
  TeamMembersList,
  InviteMemberModal,
  PendingInvitations,
  ActivityFeed,
  TeamStats,
  BulkInviteModal,
  MemberSearch,
  PermissionTemplatesContainer,
} from '../components/team';
import {
  useTeamMembers,
  useTeamStats,
  useTeamActivities,
  useInviteMember,
  useResendInvitation,
  useCancelInvitation,
  useUpdateMember,
  useRemoveMember,
  useBulkInvite,
  useSearchMembers,
} from '../hooks/useTeam';
import { usePermissionTemplates } from '../hooks/usePermissionTemplates';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import type { TeamMember, TeamInviteRequest, MemberRole, BulkInviteItem } from '../types/team';
import { ROLE_CONFIGS } from '../types/team';

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

const ROLES: MemberRole[] = ['admin', 'member', 'viewer'];

export function Team() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [mounted, setMounted] = useState(false);
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [bulkInviteModalOpen, setBulkInviteModalOpen] = useState(false);
  const [editRoleModalOpen, setEditRoleModalOpen] = useState(false);
  const [selectedMember, setSelectedMember] = useState<TeamMember | null>(null);
  const [newRole, setNewRole] = useState<MemberRole>('member');
  const [resendingId, setResendingId] = useState<string | undefined>();
  const [cancellingId, setCancellingId] = useState<string | undefined>();

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchFilter, setSearchFilter] = useState<'all' | 'active' | 'pending'>('all');

  // Data fetching
  const { data: members = [], isLoading: membersLoading } = useTeamMembers();
  const { data: stats, isLoading: statsLoading } = useTeamStats();
  const { data: activities = [], isLoading: activitiesLoading } = useTeamActivities();
  const { data: templates = [] } = usePermissionTemplates();

  // Mutations
  const inviteMember = useInviteMember();
  const resendInvitation = useResendInvitation();
  const cancelInvitation = useCancelInvitation();
  const updateMember = useUpdateMember();
  const removeMember = useRemoveMember();
  const bulkInvite = useBulkInvite();

  useEffect(() => {
    setMounted(true);
  }, []);

  // Filter members by status
  const activeMembers = members.filter((m) => m.invitation_status === 'accepted');
  const pendingInvitations = members.filter((m) => m.invitation_status === 'pending');

  // Search and filter members
  const filteredMembers = useMemo(() => {
    let filtered = members;

    // Apply status filter
    if (searchFilter === 'active') {
      filtered = filtered.filter((m) => m.invitation_status === 'accepted');
    } else if (searchFilter === 'pending') {
      filtered = filtered.filter((m) => m.invitation_status === 'pending');
    }

    // Apply search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (m) =>
          m.member_email.toLowerCase().includes(query) ||
          (m.member_name && m.member_name.toLowerCase().includes(query))
      );
    }

    return filtered;
  }, [members, searchQuery, searchFilter]);

  const filteredActiveMembers = filteredMembers.filter((m) => m.invitation_status === 'accepted');
  const filteredPendingInvitations = filteredMembers.filter((m) => m.invitation_status === 'pending');

  // Handlers
  const handleInvite = async (data: TeamInviteRequest) => {
    try {
      await inviteMember.mutateAsync(data);
      showToast(`Invitation sent to ${data.email}`, 'success');
    } catch (error: any) {
      showToast(error.response?.data?.detail || 'Failed to send invitation', 'error');
      throw error;
    }
  };

  const handleResendInvitation = async (memberId: string) => {
    setResendingId(memberId);
    try {
      await resendInvitation.mutateAsync(memberId);
      showToast('Invitation resent successfully', 'success');
    } catch (error: any) {
      showToast(error.response?.data?.detail || 'Failed to resend invitation', 'error');
    } finally {
      setResendingId(undefined);
    }
  };

  const handleCancelInvitation = async (memberId: string) => {
    setCancellingId(memberId);
    try {
      await cancelInvitation.mutateAsync(memberId);
      showToast('Invitation cancelled', 'success');
    } catch (error: any) {
      showToast(error.response?.data?.detail || 'Failed to cancel invitation', 'error');
    } finally {
      setCancellingId(undefined);
    }
  };

  const handleEditRole = (member: TeamMember) => {
    setSelectedMember(member);
    setNewRole(member.role);
    setEditRoleModalOpen(true);
  };

  const handleSaveRole = async () => {
    if (!selectedMember) return;

    try {
      await updateMember.mutateAsync({
        memberId: selectedMember.id,
        data: { role: newRole },
      });
      showToast('Member role updated successfully', 'success');
      setEditRoleModalOpen(false);
      setSelectedMember(null);
    } catch (error: any) {
      showToast(error.response?.data?.detail || 'Failed to update role', 'error');
    }
  };

  const handleRemoveMember = async (member: TeamMember) => {
    try {
      await removeMember.mutateAsync(member.id);
      showToast(`${member.member_name || member.member_email} has been removed`, 'success');
    } catch (error: any) {
      showToast(error.response?.data?.detail || 'Failed to remove member', 'error');
    }
  };

  const handleBulkInvite = async (invitations: BulkInviteItem[]) => {
    try {
      const result = await bulkInvite.mutateAsync({ invitations });
      const successCount = result.successful.length;
      const failCount = result.failed.length;

      if (successCount > 0 && failCount === 0) {
        showToast(`Successfully sent ${successCount} invitation${successCount > 1 ? 's' : ''}`, 'success');
      } else if (successCount > 0 && failCount > 0) {
        showToast(`Sent ${successCount} invitation${successCount > 1 ? 's' : ''}, ${failCount} failed`, 'warning');
      } else {
        showToast('Failed to send invitations', 'error');
      }

      return result;
    } catch (error: any) {
      showToast(error.response?.data?.detail || 'Failed to send invitations', 'error');
      throw error;
    }
  };

  const handleSearchChange = (query: string) => {
    setSearchQuery(query);
  };

  const handleFilterChange = (filter: 'all' | 'active' | 'pending') => {
    setSearchFilter(filter);
  };

  const tabs = [
    { name: 'Members', count: activeMembers.length, icon: UserGroupIcon },
    { name: 'Invitations', count: pendingInvitations.length, icon: EnvelopeIcon },
    { name: 'Activity', count: activities.length, icon: ClockIcon },
    { name: 'Permissions', count: templates.length, icon: ShieldCheckIcon },
  ];

  return (
    <div className="min-h-screen bg-mesh">
      {/* Header */}
      <div className="analytics-header">
        <div className="px-6 py-5">
          <div className={`flex items-center justify-between ${mounted ? 'animate-fade-in-up' : 'opacity-0'}`}>
            <div className="flex items-center gap-4">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-purple-100 to-purple-50 flex items-center justify-center shadow-sm">
                <UserGroupIcon className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <h1 className="text-2xl font-display font-semibold text-gray-900">
                  Team Management
                </h1>
                <p className="text-sm text-gray-500 mt-0.5">
                  Collaborate with your team on grant applications
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setBulkInviteModalOpen(true)}
                className="group inline-flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-200 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50 hover:border-gray-300 transition-all shadow-sm"
              >
                <UsersIcon className="w-4 h-4 transition-transform group-hover:scale-110" />
                Bulk Invite
              </button>
              <button
                onClick={() => setInviteModalOpen(true)}
                className="group inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-xl text-sm font-semibold hover:from-blue-700 hover:to-blue-600 transition-all shadow-lg shadow-blue-500/25 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-blue-500/30"
              >
                <UserPlusIcon className="w-4 h-4 transition-transform group-hover:scale-110" />
                Invite Member
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* Stats */}
        <div className={mounted ? 'animate-fade-in-up' : 'opacity-0'} style={{ animationDelay: '100ms' }}>
          <TeamStats stats={stats} isLoading={statsLoading} />
        </div>

        {/* Search */}
        <div className={mounted ? 'animate-fade-in-up' : 'opacity-0'} style={{ animationDelay: '150ms' }}>
          <MemberSearch
            value={searchQuery}
            onChange={handleSearchChange}
            filter={searchFilter}
            onFilterChange={handleFilterChange}
          />
        </div>

        {/* Tabs */}
        <div className={`bg-white rounded-xl border border-gray-200 overflow-hidden ${mounted ? 'animate-fade-in-up' : 'opacity-0'}`} style={{ animationDelay: '200ms' }}>
          <Tab.Group>
            <Tab.List className="flex border-b border-gray-200">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <Tab
                    key={tab.name}
                    className={({ selected }) =>
                      classNames(
                        'flex-1 flex items-center justify-center gap-2 py-4 text-sm font-medium transition-colors focus:outline-none',
                        selected
                          ? 'text-blue-600 border-b-2 border-blue-600 -mb-px'
                          : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                      )
                    }
                  >
                    <Icon className="w-4 h-4" />
                    {tab.name}
                    {tab.count > 0 && (
                      <span className={classNames(
                        'inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-medium',
                        'bg-gray-100 text-gray-600'
                      )}>
                        {tab.count}
                      </span>
                    )}
                  </Tab>
                );
              })}
            </Tab.List>

            <Tab.Panels className="p-6">
              {/* Members Panel */}
              <Tab.Panel>
                {searchQuery || searchFilter !== 'all' ? (
                  <TeamMembersList
                    members={filteredActiveMembers}
                    currentUserId={user?.id}
                    isLoading={membersLoading}
                    onEditRole={handleEditRole}
                    onRemove={handleRemoveMember}
                  />
                ) : (
                  <TeamMembersList
                    members={activeMembers}
                    currentUserId={user?.id}
                    isLoading={membersLoading}
                    onEditRole={handleEditRole}
                    onRemove={handleRemoveMember}
                  />
                )}
              </Tab.Panel>

              {/* Invitations Panel */}
              <Tab.Panel>
                {searchQuery || searchFilter !== 'all' ? (
                  <PendingInvitations
                    invitations={filteredPendingInvitations}
                    onResend={handleResendInvitation}
                    onCancel={handleCancelInvitation}
                    isResending={resendingId}
                    isCancelling={cancellingId}
                  />
                ) : (
                  <PendingInvitations
                    invitations={pendingInvitations}
                    onResend={handleResendInvitation}
                    onCancel={handleCancelInvitation}
                    isResending={resendingId}
                    isCancelling={cancellingId}
                  />
                )}
              </Tab.Panel>

              {/* Activity Panel */}
              <Tab.Panel>
                <ActivityFeed
                  activities={activities}
                  isLoading={activitiesLoading}
                />
              </Tab.Panel>

              {/* Permissions Panel */}
              <Tab.Panel>
                <PermissionTemplatesContainer />
              </Tab.Panel>
            </Tab.Panels>
          </Tab.Group>
        </div>
      </div>

      {/* Invite Modal */}
      <InviteMemberModal
        isOpen={inviteModalOpen}
        onClose={() => setInviteModalOpen(false)}
        onInvite={handleInvite}
        isLoading={inviteMember.isPending}
      />

      {/* Bulk Invite Modal */}
      <BulkInviteModal
        isOpen={bulkInviteModalOpen}
        onClose={() => setBulkInviteModalOpen(false)}
        onInvite={handleBulkInvite}
        isLoading={bulkInvite.isPending}
        templates={templates}
      />

      {/* Edit Role Modal */}
      <Transition appear show={editRoleModalOpen} as={Fragment}>
        <Dialog as="div" className="relative z-50" onClose={() => setEditRoleModalOpen(false)}>
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-black/25 backdrop-blur-sm" />
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
                <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white shadow-xl transition-all">
                  {/* Header */}
                  <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                    <Dialog.Title className="text-lg font-semibold text-gray-900">
                      Edit Member Role
                    </Dialog.Title>
                    <button
                      onClick={() => setEditRoleModalOpen(false)}
                      className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
                    >
                      <XMarkIcon className="w-5 h-5" />
                    </button>
                  </div>

                  {/* Content */}
                  <div className="p-6 space-y-5">
                    {/* Member info */}
                    {selectedMember && (
                      <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white font-semibold">
                          {(selectedMember.member_name || selectedMember.member_email).substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">
                            {selectedMember.member_name || selectedMember.member_email.split('@')[0]}
                          </p>
                          <p className="text-xs text-gray-500">{selectedMember.member_email}</p>
                        </div>
                      </div>
                    )}

                    {/* Role selector */}
                    <RadioGroup value={newRole} onChange={setNewRole}>
                      <RadioGroup.Label className="block text-sm font-medium text-gray-700 mb-2">
                        Select Role
                      </RadioGroup.Label>
                      <div className="space-y-2">
                        {ROLES.map((r) => {
                          const config = ROLE_CONFIGS[r];
                          return (
                            <RadioGroup.Option
                              key={r}
                              value={r}
                              className={({ checked }) =>
                                classNames(
                                  'relative flex cursor-pointer rounded-xl border p-4 transition-all',
                                  checked
                                    ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-500'
                                    : 'border-gray-200 hover:border-gray-300 bg-white'
                                )
                              }
                            >
                              {({ checked }) => (
                                <div className="flex w-full items-center justify-between">
                                  <div className="flex items-center gap-3">
                                    <div className={classNames(
                                      'w-10 h-10 rounded-lg flex items-center justify-center',
                                      config.bgColor
                                    )}>
                                      <span className={classNames('text-sm font-semibold', config.color)}>
                                        {config.label.charAt(0)}
                                      </span>
                                    </div>
                                    <div>
                                      <RadioGroup.Label
                                        as="span"
                                        className={classNames(
                                          'block text-sm font-medium',
                                          checked ? 'text-blue-900' : 'text-gray-900'
                                        )}
                                      >
                                        {config.label}
                                      </RadioGroup.Label>
                                      <RadioGroup.Description
                                        as="span"
                                        className="text-xs text-gray-500"
                                      >
                                        {config.description}
                                      </RadioGroup.Description>
                                    </div>
                                  </div>
                                  {checked && (
                                    <CheckCircleIcon className="w-5 h-5 text-blue-600 flex-shrink-0" />
                                  )}
                                </div>
                              )}
                            </RadioGroup.Option>
                          );
                        })}
                      </div>
                    </RadioGroup>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-100">
                    <button
                      onClick={() => setEditRoleModalOpen(false)}
                      className="px-4 py-2.5 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveRole}
                      disabled={updateMember.isPending || (selectedMember?.role === newRole)}
                      className={classNames(
                        'inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all',
                        'bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600',
                        'shadow-lg shadow-blue-500/25',
                        (updateMember.isPending || selectedMember?.role === newRole)
                          ? 'opacity-50 cursor-not-allowed'
                          : 'hover:-translate-y-0.5 hover:shadow-xl hover:shadow-blue-500/30'
                      )}
                    >
                      {updateMember.isPending ? (
                        <>
                          <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          Saving...
                        </>
                      ) : (
                        'Save Changes'
                      )}
                    </button>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </Dialog>
      </Transition>
    </div>
  );
}

export default Team;
