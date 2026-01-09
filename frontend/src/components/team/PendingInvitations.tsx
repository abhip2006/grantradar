import { useState } from 'react';
import {
  ClockIcon,
  ArrowPathIcon,
  XMarkIcon,
  EnvelopeIcon,
} from '@heroicons/react/24/outline';
import type { TeamMember } from '../../types/team';
import { ROLE_CONFIGS } from '../../types/team';

interface PendingInvitationsProps {
  invitations: TeamMember[];
  onResend: (memberId: string) => Promise<void>;
  onCancel: (memberId: string) => Promise<void>;
  isResending?: string; // ID of invitation being resent
  isCancelling?: string; // ID of invitation being cancelled
}

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

// Calculate days since invitation
function getDaysAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffTime = Math.abs(now.getTime() - date.getTime());
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 14) return '1 week ago';
  return `${Math.floor(diffDays / 7)} weeks ago`;
}

// Calculate expiry (assuming 7 days from invitation)
function getExpiresIn(dateString: string): { text: string; isExpired: boolean; isWarning: boolean } {
  const invitedDate = new Date(dateString);
  const expiryDate = new Date(invitedDate.getTime() + 7 * 24 * 60 * 60 * 1000);
  const now = new Date();
  const diffTime = expiryDate.getTime() - now.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  if (diffDays <= 0) {
    return { text: 'Expired', isExpired: true, isWarning: false };
  }
  if (diffDays === 1) {
    return { text: 'Expires tomorrow', isExpired: false, isWarning: true };
  }
  if (diffDays <= 2) {
    return { text: `Expires in ${diffDays} days`, isExpired: false, isWarning: true };
  }
  return { text: `Expires in ${diffDays} days`, isExpired: false, isWarning: false };
}

export function PendingInvitations({
  invitations,
  onResend,
  onCancel,
  isResending,
  isCancelling,
}: PendingInvitationsProps) {
  const [confirmCancel, setConfirmCancel] = useState<string | null>(null);

  if (invitations.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="w-16 h-16 mx-auto mb-4 rounded-xl bg-gray-100 flex items-center justify-center">
          <EnvelopeIcon className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-1">No pending invitations</h3>
        <p className="text-sm text-gray-500 max-w-sm mx-auto">
          All your team invitations have been accepted or expired. Invite new members to grow your team.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {invitations.map((invitation) => {
        const roleConfig = ROLE_CONFIGS[invitation.role];
        const expiry = getExpiresIn(invitation.invited_at);
        const isResendingThis = isResending === invitation.id;
        const isCancellingThis = isCancelling === invitation.id;
        const showCancelConfirm = confirmCancel === invitation.id;

        return (
          <div
            key={invitation.id}
            className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-sm transition-shadow"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4 flex-1 min-w-0">
                {/* Icon */}
                <div className="w-10 h-10 rounded-xl bg-yellow-50 flex items-center justify-center flex-shrink-0">
                  <ClockIcon className="w-5 h-5 text-yellow-600" />
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {invitation.member_email}
                  </p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className={classNames(
                      'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
                      roleConfig.bgColor,
                      roleConfig.color
                    )}>
                      {roleConfig.label}
                    </span>
                    <span className="text-xs text-gray-500">
                      Invited {getDaysAgo(invitation.invited_at)}
                    </span>
                    <span className={classNames(
                      'text-xs font-medium',
                      expiry.isExpired ? 'text-red-600' : expiry.isWarning ? 'text-amber-600' : 'text-gray-500'
                    )}>
                      {expiry.text}
                    </span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 ml-4">
                {/* Resend button */}
                <button
                  onClick={() => onResend(invitation.id)}
                  disabled={isResendingThis || isCancellingThis}
                  className={classNames(
                    'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                    isResendingThis
                      ? 'bg-blue-100 text-blue-600 cursor-not-allowed'
                      : 'text-blue-600 hover:bg-blue-50'
                  )}
                >
                  <ArrowPathIcon className={classNames('w-4 h-4', isResendingThis ? 'animate-spin' : '')} />
                  {isResendingThis ? 'Sending...' : 'Resend'}
                </button>

                {/* Cancel button */}
                {showCancelConfirm ? (
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => {
                        onCancel(invitation.id);
                        setConfirmCancel(null);
                      }}
                      disabled={isCancellingThis}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 transition-colors"
                    >
                      {isCancellingThis ? (
                        <>
                          <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          Cancelling...
                        </>
                      ) : (
                        'Confirm'
                      )}
                    </button>
                    <button
                      onClick={() => setConfirmCancel(null)}
                      disabled={isCancellingThis}
                      className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
                    >
                      <XMarkIcon className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setConfirmCancel(invitation.id)}
                    disabled={isResendingThis || isCancellingThis}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100 transition-colors"
                  >
                    <XMarkIcon className="w-4 h-4" />
                    Cancel
                  </button>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default PendingInvitations;
