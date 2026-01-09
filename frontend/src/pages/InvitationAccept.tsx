import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import {
  CheckCircleIcon,
  XCircleIcon,
  ArrowRightIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline';
import { useAcceptInvitation } from '../hooks/useTeam';
import { useAuth } from '../contexts/AuthContext';

type AcceptStatus = 'loading' | 'success' | 'error' | 'login_required';

export function InvitationAccept() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const acceptInvitation = useAcceptInvitation();

  const [status, setStatus] = useState<AcceptStatus>('loading');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const token = searchParams.get('token');

  useEffect(() => {
    // Wait for auth to finish loading
    if (authLoading) return;

    // If no token, show error
    if (!token) {
      setStatus('error');
      setErrorMessage('Invalid invitation link. Please check the link and try again.');
      return;
    }

    // If user is not logged in, show login required
    if (!isAuthenticated) {
      setStatus('login_required');
      return;
    }

    // User is logged in, accept the invitation
    const acceptInvite = async () => {
      try {
        await acceptInvitation.mutateAsync(token);
        setStatus('success');
        // Redirect to team page after a short delay
        setTimeout(() => {
          navigate('/team');
        }, 2000);
      } catch (error: any) {
        setStatus('error');
        setErrorMessage(
          error.response?.data?.detail ||
          'Failed to accept invitation. The invitation may have expired or already been used.'
        );
      }
    };

    acceptInvite();
  }, [token, isAuthenticated, authLoading]);

  // Loading state
  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-xl bg-blue-50 flex items-center justify-center">
            <svg className="animate-spin w-8 h-8 text-blue-600" viewBox="0 0 24 24">
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
            Accepting Invitation...
          </h2>
          <p className="text-gray-500">
            Please wait while we process your invitation.
          </p>
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
            Welcome to the Team!
          </h2>
          <p className="text-gray-500 mb-6">
            You've successfully joined the team. You'll be redirected to the team page shortly.
          </p>
          <Link
            to="/team"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-xl text-sm font-semibold hover:from-blue-700 hover:to-blue-600 transition-all shadow-lg shadow-blue-500/25"
          >
            Go to Team
            <ArrowRightIcon className="w-4 h-4" />
          </Link>
        </div>
      </div>
    );
  }

  // Login required state
  if (status === 'login_required') {
    const returnUrl = encodeURIComponent(`/team/invite/accept?token=${token}`);

    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-xl bg-blue-50 flex items-center justify-center">
            <UserGroupIcon className="w-8 h-8 text-blue-600" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            You've Been Invited!
          </h2>
          <p className="text-gray-500 mb-6">
            Sign in or create an account to join the team and start collaborating on grant applications.
          </p>
          <div className="space-y-3">
            <Link
              to={`/auth?returnUrl=${returnUrl}`}
              className="block w-full px-5 py-2.5 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-xl text-sm font-semibold hover:from-blue-700 hover:to-blue-600 transition-all shadow-lg shadow-blue-500/25"
            >
              Sign In to Accept
            </Link>
            <Link
              to={`/auth?mode=signup&returnUrl=${returnUrl}`}
              className="block w-full px-5 py-2.5 border border-gray-200 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors"
            >
              Create Account
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  return (
    <div className="min-h-screen bg-mesh flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
        <div className="w-16 h-16 mx-auto mb-6 rounded-xl bg-red-50 flex items-center justify-center">
          <XCircleIcon className="w-8 h-8 text-red-600" />
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Unable to Accept Invitation
        </h2>
        <p className="text-gray-500 mb-6">
          {errorMessage}
        </p>
        <div className="space-y-3">
          <Link
            to="/dashboard"
            className="block w-full px-5 py-2.5 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-xl text-sm font-semibold hover:from-blue-700 hover:to-blue-600 transition-all shadow-lg shadow-blue-500/25"
          >
            Go to Dashboard
          </Link>
          <Link
            to="/"
            className="block w-full px-5 py-2.5 border border-gray-200 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors"
          >
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}

export default InvitationAccept;
