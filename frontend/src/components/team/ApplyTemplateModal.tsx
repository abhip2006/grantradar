import { Fragment, useState, useMemo } from 'react';
import { Dialog, Transition, Listbox } from '@headlessui/react';
import {
  XMarkIcon,
  ShieldCheckIcon,
  ChevronUpDownIcon,
  CheckIcon,
  ArrowRightIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import type {
  TeamMember,
  PermissionTemplate,
  MemberPermissions,
} from '../../types/team';

interface ApplyTemplateModalProps {
  isOpen: boolean;
  onClose: () => void;
  member: TeamMember | null;
  templates: PermissionTemplate[];
  onApply: (memberId: string, templateId: string) => Promise<void>;
  isLoading?: boolean;
}

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

// Permission definitions for display
const PERMISSION_DEFINITIONS: {
  key: keyof MemberPermissions;
  label: string;
}[] = [
  { key: 'can_view', label: 'View' },
  { key: 'can_edit', label: 'Edit' },
  { key: 'can_create', label: 'Create' },
  { key: 'can_delete', label: 'Delete' },
  { key: 'can_invite', label: 'Invite' },
  { key: 'can_manage_grants', label: 'Manage Grants' },
  { key: 'can_export', label: 'Export' },
];

// Permission Badge Component
function PermissionBadge({
  label,
  enabled,
  variant,
}: {
  label: string;
  enabled: boolean;
  variant?: 'current' | 'new' | 'unchanged' | 'added' | 'removed';
}) {
  const getColors = () => {
    switch (variant) {
      case 'added':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'removed':
        return 'bg-red-100 text-red-700 border-red-200 line-through';
      case 'unchanged':
        return enabled ? 'bg-gray-100 text-gray-700 border-gray-200' : 'hidden';
      case 'current':
        return enabled ? 'bg-blue-50 text-blue-700 border-blue-200' : 'hidden';
      case 'new':
        return enabled ? 'bg-purple-50 text-purple-700 border-purple-200' : 'hidden';
      default:
        return enabled ? 'bg-gray-100 text-gray-700 border-gray-200' : 'hidden';
    }
  };

  if (!enabled && variant !== 'removed') {
    return null;
  }

  return (
    <span
      className={classNames(
        'inline-flex items-center px-2 py-1 rounded-lg text-xs font-medium border',
        getColors()
      )}
    >
      {label}
    </span>
  );
}

// Permission Changes Preview Component
function PermissionChangesPreview({
  currentPermissions,
  newPermissions,
}: {
  currentPermissions: MemberPermissions;
  newPermissions: MemberPermissions;
}) {
  const changes = useMemo(() => {
    const added: string[] = [];
    const removed: string[] = [];
    const unchanged: string[] = [];

    PERMISSION_DEFINITIONS.forEach((perm) => {
      const current = currentPermissions[perm.key];
      const next = newPermissions[perm.key];

      if (!current && next) {
        added.push(perm.label);
      } else if (current && !next) {
        removed.push(perm.label);
      } else if (current && next) {
        unchanged.push(perm.label);
      }
    });

    return { added, removed, unchanged };
  }, [currentPermissions, newPermissions]);

  const hasChanges = changes.added.length > 0 || changes.removed.length > 0;

  return (
    <div className="space-y-4">
      {/* Added Permissions */}
      {changes.added.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-green-700 uppercase tracking-wider mb-2 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            Permissions to Add
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {changes.added.map((label) => (
              <PermissionBadge key={label} label={label} enabled variant="added" />
            ))}
          </div>
        </div>
      )}

      {/* Removed Permissions */}
      {changes.removed.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-red-700 uppercase tracking-wider mb-2 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" />
            Permissions to Remove
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {changes.removed.map((label) => (
              <PermissionBadge key={label} label={label} enabled variant="removed" />
            ))}
          </div>
        </div>
      )}

      {/* Unchanged Permissions */}
      {changes.unchanged.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
            Unchanged Permissions
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {changes.unchanged.map((label) => (
              <PermissionBadge key={label} label={label} enabled variant="unchanged" />
            ))}
          </div>
        </div>
      )}

      {/* No Changes */}
      {!hasChanges && (
        <div className="text-center py-4 text-sm text-gray-500">
          No permission changes will be made
        </div>
      )}
    </div>
  );
}

export function ApplyTemplateModal({
  isOpen,
  onClose,
  member,
  templates,
  onApply,
  isLoading = false,
}: ApplyTemplateModalProps) {
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('');
  const [isApplying, setIsApplying] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const selectedTemplate = templates.find((t) => t.id === selectedTemplateId);

  const handleApply = async () => {
    if (!member || !selectedTemplateId) return;

    setIsApplying(true);
    try {
      await onApply(member.id, selectedTemplateId);
      handleClose();
    } catch (error) {
      console.error('Failed to apply template:', error);
    } finally {
      setIsApplying(false);
      setShowConfirm(false);
    }
  };

  const handleClose = () => {
    if (!isApplying && !isLoading) {
      setSelectedTemplateId('');
      setShowConfirm(false);
      onClose();
    }
  };

  // Reset selection when modal opens with a new member
  const memberName = member?.member_name || member?.member_email.split('@')[0] || 'Member';

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={handleClose}>
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
              <Dialog.Panel className="w-full max-w-lg transform overflow-hidden rounded-2xl bg-white shadow-xl transition-all">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center">
                      <ShieldCheckIcon className="w-5 h-5 text-purple-600" />
                    </div>
                    <div>
                      <Dialog.Title className="text-lg font-semibold text-gray-900">
                        Apply Permission Template
                      </Dialog.Title>
                      <p className="text-sm text-gray-500">
                        to {memberName}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleClose}
                    className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
                  >
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>

                <div className="p-6 space-y-6">
                  {/* Current Permissions */}
                  {member && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-700 mb-2">
                        Current Permissions
                      </h3>
                      <div className="p-3 bg-gray-50 rounded-xl">
                        <div className="flex flex-wrap gap-1.5">
                          {PERMISSION_DEFINITIONS.map((perm) => (
                            <PermissionBadge
                              key={perm.key}
                              label={perm.label}
                              enabled={member.permissions[perm.key] || false}
                              variant="current"
                            />
                          ))}
                          {!PERMISSION_DEFINITIONS.some(
                            (perm) => member.permissions[perm.key]
                          ) && (
                            <span className="text-sm text-gray-400">No permissions</span>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Template Selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Select Template
                    </label>
                    <Listbox value={selectedTemplateId} onChange={setSelectedTemplateId}>
                      <div className="relative">
                        <Listbox.Button className="relative w-full py-3 pl-4 pr-10 text-left bg-white rounded-xl border border-gray-300 hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-sm transition-colors">
                          <span className="block truncate">
                            {selectedTemplate
                              ? selectedTemplate.name
                              : 'Choose a permission template...'}
                          </span>
                          <span className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                            <ChevronUpDownIcon className="w-5 h-5 text-gray-400" />
                          </span>
                        </Listbox.Button>
                        <Transition
                          as={Fragment}
                          leave="transition ease-in duration-100"
                          leaveFrom="opacity-100"
                          leaveTo="opacity-0"
                        >
                          <Listbox.Options className="absolute z-10 w-full mt-1 bg-white rounded-xl shadow-lg border border-gray-100 py-1 focus:outline-none text-sm max-h-60 overflow-auto">
                            {templates.map((template) => (
                              <Listbox.Option
                                key={template.id}
                                value={template.id}
                                className={({ active }) =>
                                  classNames(
                                    'relative cursor-pointer select-none py-3 pl-10 pr-4',
                                    active ? 'bg-purple-50 text-purple-900' : 'text-gray-900'
                                  )
                                }
                              >
                                {({ selected }) => (
                                  <>
                                    <div>
                                      <span
                                        className={classNames(
                                          'block truncate',
                                          selected ? 'font-medium' : 'font-normal'
                                        )}
                                      >
                                        {template.name}
                                        {template.is_default && (
                                          <span className="ml-2 text-xs text-purple-600">
                                            (Default)
                                          </span>
                                        )}
                                      </span>
                                      {template.description && (
                                        <span className="block truncate text-xs text-gray-500 mt-0.5">
                                          {template.description}
                                        </span>
                                      )}
                                    </div>
                                    {selected && (
                                      <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-purple-600">
                                        <CheckIcon className="w-5 h-5" />
                                      </span>
                                    )}
                                  </>
                                )}
                              </Listbox.Option>
                            ))}
                          </Listbox.Options>
                        </Transition>
                      </div>
                    </Listbox>
                  </div>

                  {/* Permission Changes Preview */}
                  {selectedTemplate && member && (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <ArrowPathIcon className="w-4 h-4 text-gray-400" />
                        <h3 className="text-sm font-medium text-gray-700">
                          Permission Changes Preview
                        </h3>
                      </div>
                      <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                        <PermissionChangesPreview
                          currentPermissions={member.permissions}
                          newPermissions={selectedTemplate.permissions}
                        />
                      </div>
                    </div>
                  )}

                  {/* Confirmation Warning */}
                  {showConfirm && (
                    <div className="p-4 bg-yellow-50 rounded-xl border border-yellow-100">
                      <div className="flex items-start gap-3">
                        <ExclamationTriangleIcon className="w-5 h-5 text-yellow-500 flex-shrink-0" />
                        <div>
                          <p className="text-sm font-medium text-yellow-800">
                            Confirm permission changes
                          </p>
                          <p className="text-xs text-yellow-700 mt-1">
                            This will replace {memberName}'s current permissions with the
                            selected template. This action can be undone by applying a
                            different template.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-100 bg-gray-50">
                  <button
                    type="button"
                    onClick={handleClose}
                    className="px-4 py-2.5 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-200 transition-colors"
                    disabled={isApplying}
                  >
                    Cancel
                  </button>
                  {showConfirm ? (
                    <button
                      onClick={handleApply}
                      disabled={isApplying || isLoading}
                      className={classNames(
                        'inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all',
                        'bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-700 hover:to-purple-600',
                        'shadow-lg shadow-purple-500/25 hover:shadow-xl hover:shadow-purple-500/30',
                        isApplying ? 'opacity-50 cursor-not-allowed' : 'hover:-translate-y-0.5'
                      )}
                    >
                      {isApplying ? (
                        <>
                          <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24">
                            <circle
                              className="opacity-25"
                              cx="12"
                              cy="12"
                              r="10"
                              stroke="currentColor"
                              strokeWidth="4"
                              fill="none"
                            />
                            <path
                              className="opacity-75"
                              fill="currentColor"
                              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                            />
                          </svg>
                          Applying...
                        </>
                      ) : (
                        <>
                          <CheckIcon className="w-4 h-4" />
                          Confirm & Apply
                        </>
                      )}
                    </button>
                  ) : (
                    <button
                      onClick={() => setShowConfirm(true)}
                      disabled={!selectedTemplateId || isLoading}
                      className={classNames(
                        'inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all',
                        'bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-700 hover:to-purple-600',
                        'shadow-lg shadow-purple-500/25 hover:shadow-xl hover:shadow-purple-500/30',
                        !selectedTemplateId
                          ? 'opacity-50 cursor-not-allowed'
                          : 'hover:-translate-y-0.5'
                      )}
                    >
                      <ArrowRightIcon className="w-4 h-4" />
                      Apply Template
                    </button>
                  )}
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}

export default ApplyTemplateModal;
