import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  XCircleIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useDeclineInvitation } from '../hooks/useTeam';

type DeclineStatus = 'confirm' | 'loading' | 'success' | 'error';

export function InvitationDecline() {
  const [searchParams] = useSearchParams();
  const declineInvitation = useDeclineInvitation();

  const [status, setStatus] = useState<DeclineStatus>('confirm');
  const [reason, setReason] = useState('');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const token = searchParams.get('token');

  // If no token, show error immediately
  useEffect(() => {
    if (!token) {
      setStatus('error');
      setErrorMessage('Invalid invitation link. Please check the link and try again.');
    }
  }, [token]);

  const handleDecline = async () => {
    if (!token) return;

    setStatus('loading');
    try {
      await declineInvitation.mutateAsync({
        token,
        reason: reason.trim() || undefined,
      });
      setStatus('success');
    } catch (error: any) {
      setStatus('error');
      setErrorMessage(
        error.response?.data?.detail ||
        'Failed to decline invitation. The invitation may have expired or already been processed.'
      );
    }
  };

  // Error state (no token or API error)
  if (status === 'error') {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-xl bg-red-50 flex items-center justify-center">
            <XCircleIcon className="w-8 h-8 text-red-600" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Unable to Process Request
          </h2>
          <p className="text-gray-500 mb-6">
            {errorMessage}
          </p>
          <Link
            to="/"
            className="inline-flex items-center justify-center w-full px-5 py-2.5 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-xl text-sm font-semibold hover:from-blue-700 hover:to-blue-600 transition-all shadow-lg shadow-blue-500/25"
          >
            Back to Home
          </Link>
        </div>
      </div>
    );
  }

  // Success state
  if (status === 'success') {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-xl bg-green-50 flex items-center justify-center">
            <CheckCircleIcon className="w-8 h-8 text-green-600" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Invitation Declined
          </h2>
          <p className="text-gray-500 mb-6">
            You've declined the team invitation. You can close this page now.
          </p>
          <Link
            to="/"
            className="inline-flex items-center justify-center w-full px-5 py-2.5 border border-gray-200 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors"
          >
            Go to Home
          </Link>
        </div>
      </div>
    );
  }

  // Loading state
  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-xl bg-gray-100 flex items-center justify-center">
            <svg className="animate-spin w-8 h-8 text-gray-600" viewBox="0 0 24 24">
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
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Processing...
          </h2>
          <p className="text-gray-500">
            Please wait while we process your response.
          </p>
        </div>
      </div>
    );
  }

  // Confirmation state
  return (
    <div className="min-h-screen bg-mesh flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full">
        <div className="text-center mb-6">
          <div className="w-16 h-16 mx-auto mb-6 rounded-xl bg-amber-50 flex items-center justify-center">
            <ExclamationTriangleIcon className="w-8 h-8 text-amber-600" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Decline Invitation?
          </h2>
          <p className="text-gray-500">
            Are you sure you want to decline this team invitation? You won't be able to join unless invited again.
          </p>
        </div>

        {/* Optional reason */}
        <div className="mb-6">
          <label htmlFor="reason" className="block text-sm font-medium text-gray-700 mb-1.5">
            Reason <span className="text-gray-400 font-normal">(optional)</span>
          </label>
          <textarea
            id="reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Let them know why you're declining..."
            rows={3}
            className="block w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 hover:border-gray-400 resize-none"
          />
        </div>

        {/* Actions */}
        <div className="space-y-3">
          <button
            onClick={handleDecline}
            className="w-full px-5 py-2.5 bg-red-600 text-white rounded-xl text-sm font-semibold hover:bg-red-700 transition-colors"
          >
            Yes, Decline Invitation
          </button>
          <Link
            to={`/team/invite/accept?token=${token}`}
            className="block w-full text-center px-5 py-2.5 border border-gray-200 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors"
          >
            Accept Instead
          </Link>
        </div>
      </div>
    </div>
  );
}

export default InvitationDecline;
