import { Fragment, useState } from 'react';
import { Dialog, Transition, RadioGroup } from '@headlessui/react';
import {
  XMarkIcon,
  EnvelopeIcon,
  UserPlusIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import type { MemberRole, TeamInviteRequest } from '../../types/team';
import { ROLE_CONFIGS } from '../../types/team';

interface InviteMemberModalProps {
  isOpen: boolean;
  onClose: () => void;
  onInvite: (data: TeamInviteRequest) => Promise<void>;
  isLoading?: boolean;
}

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

const ROLES: MemberRole[] = ['admin', 'member', 'viewer'];

export function InviteMemberModal({
  isOpen,
  onClose,
  onInvite,
  isLoading = false,
}: InviteMemberModalProps) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<MemberRole>('member');
  const [message, setMessage] = useState('');
  const [emailError, setEmailError] = useState('');

  const validateEmail = (email: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate email
    if (!email.trim()) {
      setEmailError('Email is required');
      return;
    }
    if (!validateEmail(email)) {
      setEmailError('Please enter a valid email address');
      return;
    }

    setEmailError('');

    try {
      await onInvite({
        email: email.trim(),
        role,
        message: message.trim() || undefined,
      });
      // Reset form on success
      setEmail('');
      setRole('member');
      setMessage('');
      onClose();
    } catch (error) {
      // Error handling done in parent component
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      setEmail('');
      setRole('member');
      setMessage('');
      setEmailError('');
      onClose();
    }
  };

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
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white shadow-xl transition-all">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
                      <UserPlusIcon className="w-5 h-5 text-blue-600" />
                    </div>
                    <Dialog.Title className="text-lg font-semibold text-gray-900">
                      Invite Team Member
                    </Dialog.Title>
                  </div>
                  <button
                    onClick={handleClose}
                    className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
                  >
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6 space-y-5">
                  {/* Email input */}
                  <div>
                    <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1.5">
                      Email address
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <EnvelopeIcon className="h-5 w-5 text-gray-400" />
                      </div>
                      <input
                        type="email"
                        id="email"
                        value={email}
                        onChange={(e) => {
                          setEmail(e.target.value);
                          if (emailError) setEmailError('');
                        }}
                        placeholder="colleague@university.edu"
                        className={classNames(
                          'block w-full pl-10 pr-4 py-2.5 rounded-xl border text-sm transition-colors',
                          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                          emailError
                            ? 'border-red-300 bg-red-50'
                            : 'border-gray-300 bg-white hover:border-gray-400'
                        )}
                        disabled={isLoading}
                      />
                    </div>
                    {emailError && (
                      <p className="mt-1.5 text-sm text-red-600">{emailError}</p>
                    )}
                  </div>

                  {/* Role selector */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Role
                    </label>
                    <RadioGroup value={role} onChange={setRole} disabled={isLoading}>
                      <div className="space-y-2">
                        {ROLES.map((r) => {
                          const config = ROLE_CONFIGS[r];
                          return (
                            <RadioGroup.Option
                              key={r}
                              value={r}
                              className={({ checked, active }) =>
                                classNames(
                                  'relative flex cursor-pointer rounded-xl border p-4 transition-all',
                                  checked
                                    ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-500'
                                    : 'border-gray-200 hover:border-gray-300 bg-white',
                                  active ? 'ring-2 ring-blue-500' : '',
                                  isLoading ? 'opacity-50 cursor-not-allowed' : ''
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

                  {/* Optional message */}
                  <div>
                    <label htmlFor="message" className="block text-sm font-medium text-gray-700 mb-1.5">
                      Personal message <span className="text-gray-400 font-normal">(optional)</span>
                    </label>
                    <textarea
                      id="message"
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      placeholder="Add a personal note to the invitation email..."
                      rows={3}
                      className="block w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 hover:border-gray-400 resize-none"
                      disabled={isLoading}
                    />
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-end gap-3 pt-2">
                    <button
                      type="button"
                      onClick={handleClose}
                      className="px-4 py-2.5 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
                      disabled={isLoading}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isLoading}
                      className={classNames(
                        'inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all',
                        'bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600',
                        'shadow-lg shadow-blue-500/25 hover:shadow-xl hover:shadow-blue-500/30',
                        isLoading ? 'opacity-50 cursor-not-allowed' : 'hover:-translate-y-0.5'
                      )}
                    >
                      {isLoading ? (
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
                          Send Invitation
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}

export default InviteMemberModal;
