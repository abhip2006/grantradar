import { Fragment, useState, useCallback } from 'react';
import { Dialog, Transition, Listbox } from '@headlessui/react';
import {
  XMarkIcon,
  PlusIcon,
  TrashIcon,
  UserPlusIcon,
  EnvelopeIcon,
  CheckIcon,
  ChevronUpDownIcon,
  ExclamationCircleIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import type {
  MemberRole,
  BulkInviteItem,
  BulkInviteResponse,
  PermissionTemplate,
} from '../../types/team';
import { ROLE_CONFIGS } from '../../types/team';

interface InviteRow {
  id: string;
  email: string;
  role: MemberRole;
  message: string;
  permission_template_id: string;
  error?: string;
}

interface BulkInviteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onInvite: (invitations: BulkInviteItem[]) => Promise<BulkInviteResponse>;
  permissionTemplates?: PermissionTemplate[];
  isLoading?: boolean;
}

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

const ROLES: MemberRole[] = ['admin', 'member', 'viewer'];

function generateId() {
  return Math.random().toString(36).substring(2, 9);
}

function createEmptyRow(): InviteRow {
  return {
    id: generateId(),
    email: '',
    role: 'member',
    message: '',
    permission_template_id: '',
  };
}

export function BulkInviteModal({
  isOpen,
  onClose,
  onInvite,
  permissionTemplates = [],
  isLoading = false,
}: BulkInviteModalProps) {
  const [rows, setRows] = useState<InviteRow[]>([createEmptyRow()]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [results, setResults] = useState<BulkInviteResponse | null>(null);
  const [showResults, setShowResults] = useState(false);

  const validateEmail = (email: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const addRow = useCallback(() => {
    setRows((prev) => [...prev, createEmptyRow()]);
  }, []);

  const removeRow = useCallback((id: string) => {
    setRows((prev) => {
      if (prev.length === 1) {
        return [createEmptyRow()];
      }
      return prev.filter((row) => row.id !== id);
    });
  }, []);

  const updateRow = useCallback((id: string, field: keyof InviteRow, value: string) => {
    setRows((prev) =>
      prev.map((row) => {
        if (row.id === id) {
          return { ...row, [field]: value, error: undefined };
        }
        return row;
      })
    );
  }, []);

  const validateRows = useCallback(() => {
    let hasErrors = false;
    const emails = new Set<string>();

    const validatedRows = rows.map((row) => {
      let error: string | undefined;

      if (!row.email.trim()) {
        error = 'Email is required';
        hasErrors = true;
      } else if (!validateEmail(row.email)) {
        error = 'Invalid email format';
        hasErrors = true;
      } else if (emails.has(row.email.toLowerCase())) {
        error = 'Duplicate email';
        hasErrors = true;
      } else {
        emails.add(row.email.toLowerCase());
      }

      return { ...row, error };
    });

    setRows(validatedRows);
    return !hasErrors;
  }, [rows]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateRows()) {
      return;
    }

    // Filter out empty rows
    const validRows = rows.filter((row) => row.email.trim());

    if (validRows.length === 0) {
      return;
    }

    setIsSubmitting(true);

    try {
      const invitations: BulkInviteItem[] = validRows.map((row) => ({
        email: row.email.trim(),
        role: row.role,
        message: row.message.trim() || undefined,
        permission_template_id: row.permission_template_id || undefined,
      }));

      const response = await onInvite(invitations);
      setResults(response);
      setShowResults(true);
    } catch (error) {
      console.error('Failed to send invitations:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting && !isLoading) {
      setRows([createEmptyRow()]);
      setResults(null);
      setShowResults(false);
      onClose();
    }
  };

  const handleBackToForm = () => {
    setShowResults(false);
    // Keep failed emails, clear successful ones
    if (results) {
      const failedEmails = new Set(results.failed.map((f) => f.email));
      const newRows = rows.filter((row) => failedEmails.has(row.email));
      setRows(newRows.length > 0 ? newRows : [createEmptyRow()]);
    }
    setResults(null);
  };

  const totalEmails = rows.filter((row) => row.email.trim()).length;

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
              <Dialog.Panel className="w-full max-w-3xl transform overflow-hidden rounded-2xl bg-white shadow-xl transition-all">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
                      <UserPlusIcon className="w-5 h-5 text-blue-600" />
                    </div>
                    <div>
                      <Dialog.Title className="text-lg font-semibold text-gray-900">
                        Bulk Invite Team Members
                      </Dialog.Title>
                      <p className="text-sm text-gray-500">
                        Invite multiple team members at once
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

                {showResults && results ? (
                  // Results View
                  <div className="p-6">
                    <div className="space-y-6">
                      {/* Success Section */}
                      {results.successful.length > 0 && (
                        <div className="bg-green-50 rounded-xl p-4">
                          <div className="flex items-center gap-2 mb-3">
                            <CheckCircleIcon className="w-5 h-5 text-green-600" />
                            <h4 className="font-medium text-green-900">
                              Successfully Invited ({results.successful.length})
                            </h4>
                          </div>
                          <ul className="space-y-2">
                            {results.successful.map((result) => (
                              <li
                                key={result.email}
                                className="flex items-center gap-2 text-sm text-green-700"
                              >
                                <CheckIcon className="w-4 h-4" />
                                {result.email}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Failed Section */}
                      {results.failed.length > 0 && (
                        <div className="bg-red-50 rounded-xl p-4">
                          <div className="flex items-center gap-2 mb-3">
                            <XCircleIcon className="w-5 h-5 text-red-600" />
                            <h4 className="font-medium text-red-900">
                              Failed ({results.failed.length})
                            </h4>
                          </div>
                          <ul className="space-y-2">
                            {results.failed.map((result) => (
                              <li key={result.email} className="text-sm">
                                <span className="text-red-700">{result.email}</span>
                                {result.error && (
                                  <span className="text-red-500 ml-2">- {result.error}</span>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center justify-end gap-3 mt-6 pt-4 border-t border-gray-100">
                      {results.failed.length > 0 && (
                        <button
                          onClick={handleBackToForm}
                          className="px-4 py-2.5 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
                        >
                          Retry Failed
                        </button>
                      )}
                      <button
                        onClick={handleClose}
                        className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 shadow-lg shadow-blue-500/25"
                      >
                        Done
                      </button>
                    </div>
                  </div>
                ) : (
                  // Form View
                  <form onSubmit={handleSubmit} className="p-6">
                    {/* Invite Rows */}
                    <div className="space-y-3 max-h-[400px] overflow-y-auto">
                      {rows.map((row, index) => (
                        <div
                          key={row.id}
                          className={classNames(
                            'p-4 rounded-xl border transition-colors',
                            row.error
                              ? 'border-red-200 bg-red-50'
                              : 'border-gray-200 hover:border-gray-300'
                          )}
                        >
                          <div className="flex items-start gap-3">
                            {/* Row Number */}
                            <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs font-medium text-gray-500 mt-2">
                              {index + 1}
                            </div>

                            {/* Fields */}
                            <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-3">
                              {/* Email */}
                              <div className="md:col-span-1">
                                <label className="block text-xs font-medium text-gray-500 mb-1">
                                  Email *
                                </label>
                                <div className="relative">
                                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <EnvelopeIcon className="h-4 w-4 text-gray-400" />
                                  </div>
                                  <input
                                    type="email"
                                    value={row.email}
                                    onChange={(e) =>
                                      updateRow(row.id, 'email', e.target.value)
                                    }
                                    placeholder="email@example.com"
                                    className={classNames(
                                      'block w-full pl-9 pr-3 py-2 rounded-lg border text-sm transition-colors',
                                      'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                                      row.error
                                        ? 'border-red-300 bg-white'
                                        : 'border-gray-300 hover:border-gray-400'
                                    )}
                                    disabled={isSubmitting}
                                  />
                                </div>
                                {row.error && (
                                  <p className="mt-1 text-xs text-red-600 flex items-center gap-1">
                                    <ExclamationCircleIcon className="w-3 h-3" />
                                    {row.error}
                                  </p>
                                )}
                              </div>

                              {/* Role */}
                              <div>
                                <label className="block text-xs font-medium text-gray-500 mb-1">
                                  Role
                                </label>
                                <Listbox
                                  value={row.role}
                                  onChange={(value) => updateRow(row.id, 'role', value)}
                                  disabled={isSubmitting}
                                >
                                  <div className="relative">
                                    <Listbox.Button className="relative w-full py-2 pl-3 pr-10 text-left bg-white rounded-lg border border-gray-300 hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm">
                                      <span className="block truncate">
                                        {ROLE_CONFIGS[row.role].label}
                                      </span>
                                      <span className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
                                        <ChevronUpDownIcon className="w-4 h-4 text-gray-400" />
                                      </span>
                                    </Listbox.Button>
                                    <Transition
                                      as={Fragment}
                                      leave="transition ease-in duration-100"
                                      leaveFrom="opacity-100"
                                      leaveTo="opacity-0"
                                    >
                                      <Listbox.Options className="absolute z-10 w-full mt-1 bg-white rounded-lg shadow-lg border border-gray-200 py-1 focus:outline-none text-sm">
                                        {ROLES.map((r) => (
                                          <Listbox.Option
                                            key={r}
                                            value={r}
                                            className={({ active }) =>
                                              classNames(
                                                'relative cursor-pointer select-none py-2 pl-10 pr-4',
                                                active ? 'bg-blue-50 text-blue-900' : 'text-gray-900'
                                              )
                                            }
                                          >
                                            {({ selected }) => (
                                              <>
                                                <span
                                                  className={classNames(
                                                    'block truncate',
                                                    selected ? 'font-medium' : 'font-normal'
                                                  )}
                                                >
                                                  {ROLE_CONFIGS[r].label}
                                                </span>
                                                {selected && (
                                                  <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-blue-600">
                                                    <CheckIcon className="w-4 h-4" />
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

                              {/* Permission Template (optional) */}
                              {permissionTemplates.length > 0 && (
                                <div>
                                  <label className="block text-xs font-medium text-gray-500 mb-1">
                                    Template
                                  </label>
                                  <Listbox
                                    value={row.permission_template_id}
                                    onChange={(value) =>
                                      updateRow(row.id, 'permission_template_id', value)
                                    }
                                    disabled={isSubmitting}
                                  >
                                    <div className="relative">
                                      <Listbox.Button className="relative w-full py-2 pl-3 pr-10 text-left bg-white rounded-lg border border-gray-300 hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm">
                                        <span className="block truncate text-gray-500">
                                          {row.permission_template_id
                                            ? permissionTemplates.find(
                                                (t) => t.id === row.permission_template_id
                                              )?.name || 'Select template'
                                            : 'Default permissions'}
                                        </span>
                                        <span className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
                                          <ChevronUpDownIcon className="w-4 h-4 text-gray-400" />
                                        </span>
                                      </Listbox.Button>
                                      <Transition
                                        as={Fragment}
                                        leave="transition ease-in duration-100"
                                        leaveFrom="opacity-100"
                                        leaveTo="opacity-0"
                                      >
                                        <Listbox.Options className="absolute z-10 w-full mt-1 bg-white rounded-lg shadow-lg border border-gray-200 py-1 focus:outline-none text-sm max-h-40 overflow-auto">
                                          <Listbox.Option
                                            value=""
                                            className={({ active }) =>
                                              classNames(
                                                'relative cursor-pointer select-none py-2 pl-10 pr-4',
                                                active ? 'bg-blue-50 text-blue-900' : 'text-gray-900'
                                              )
                                            }
                                          >
                                            {({ selected }) => (
                                              <>
                                                <span
                                                  className={classNames(
                                                    'block truncate',
                                                    selected ? 'font-medium' : 'font-normal'
                                                  )}
                                                >
                                                  Default permissions
                                                </span>
                                                {selected && (
                                                  <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-blue-600">
                                                    <CheckIcon className="w-4 h-4" />
                                                  </span>
                                                )}
                                              </>
                                            )}
                                          </Listbox.Option>
                                          {permissionTemplates.map((template) => (
                                            <Listbox.Option
                                              key={template.id}
                                              value={template.id}
                                              className={({ active }) =>
                                                classNames(
                                                  'relative cursor-pointer select-none py-2 pl-10 pr-4',
                                                  active
                                                    ? 'bg-blue-50 text-blue-900'
                                                    : 'text-gray-900'
                                                )
                                              }
                                            >
                                              {({ selected }) => (
                                                <>
                                                  <span
                                                    className={classNames(
                                                      'block truncate',
                                                      selected ? 'font-medium' : 'font-normal'
                                                    )}
                                                  >
                                                    {template.name}
                                                  </span>
                                                  {selected && (
                                                    <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-blue-600">
                                                      <CheckIcon className="w-4 h-4" />
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
                              )}
                            </div>

                            {/* Remove Button */}
                            <button
                              type="button"
                              onClick={() => removeRow(row.id)}
                              className="p-2 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors mt-1"
                              disabled={isSubmitting}
                            >
                              <TrashIcon className="w-4 h-4" />
                            </button>
                          </div>

                          {/* Optional Message */}
                          <div className="mt-3 ml-9">
                            <input
                              type="text"
                              value={row.message}
                              onChange={(e) => updateRow(row.id, 'message', e.target.value)}
                              placeholder="Add a personal message (optional)"
                              className="block w-full px-3 py-2 rounded-lg border border-gray-200 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 hover:border-gray-300"
                              disabled={isSubmitting}
                            />
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Add Row Button */}
                    <button
                      type="button"
                      onClick={addRow}
                      className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl border-2 border-dashed border-gray-200 text-sm font-medium text-gray-500 hover:border-blue-300 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                      disabled={isSubmitting}
                    >
                      <PlusIcon className="w-4 h-4" />
                      Add Another Person
                    </button>

                    {/* Actions */}
                    <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-100">
                      <p className="text-sm text-gray-500">
                        {totalEmails > 0 ? (
                          <>
                            <span className="font-medium text-gray-700">{totalEmails}</span>{' '}
                            invitation{totalEmails !== 1 ? 's' : ''} ready to send
                          </>
                        ) : (
                          'Add emails to invite team members'
                        )}
                      </p>
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          onClick={handleClose}
                          className="px-4 py-2.5 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
                          disabled={isSubmitting}
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          disabled={isSubmitting || isLoading || totalEmails === 0}
                          className={classNames(
                            'inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all',
                            'bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600',
                            'shadow-lg shadow-blue-500/25 hover:shadow-xl hover:shadow-blue-500/30',
                            isSubmitting || totalEmails === 0
                              ? 'opacity-50 cursor-not-allowed'
                              : 'hover:-translate-y-0.5'
                          )}
                        >
                          {isSubmitting ? (
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
                              Sending...
                            </>
                          ) : (
                            <>
                              <EnvelopeIcon className="w-4 h-4" />
                              Send {totalEmails > 1 ? 'Invitations' : 'Invitation'}
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  </form>
                )}
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}

export default BulkInviteModal;
