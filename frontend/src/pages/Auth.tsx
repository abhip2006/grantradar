import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { AxiosError } from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import type { LoginCredentials, SignupData } from '../types';

// Helper to extract error message from API response
function getErrorMessage(error: unknown): string {
  if (error instanceof AxiosError && error.response?.data) {
    const data = error.response.data;
    // Handle FastAPI/Pydantic validation errors (422)
    if (data.detail) {
      if (Array.isArray(data.detail)) {
        // Pydantic validation errors: [{loc: [...], msg: "...", type: "..."}]
        return data.detail.map((err: { msg: string }) => err.msg).join('. ');
      }
      // Simple string detail
      return data.detail;
    }
    // Handle generic error message
    if (data.message) {
      return data.message;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred';
}

const organizationTypes = [
  '501(c)(3) Nonprofit',
  'Educational Institution',
  'Government Agency',
  'Healthcare Organization',
  'Research Institution',
  'Community Organization',
  'Other',
];

const focusAreaOptions = [
  'Education',
  'Healthcare',
  'Environment',
  'Arts & Culture',
  'Social Services',
  'Economic Development',
  'Housing',
  'Youth Development',
  'Senior Services',
  'Disability Services',
  'Food Security',
  'Technology',
  'Research',
  'International',
];

export function Auth() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login, signup, isAuthenticated, isLoading } = useAuth();
  const { showToast } = useToast();

  const [isSignup, setIsSignup] = useState(searchParams.get('mode') === 'signup');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Login form state
  const [loginForm, setLoginForm] = useState<LoginCredentials>({
    email: '',
    password: '',
  });

  // Signup form state
  const [signupForm, setSignupForm] = useState<SignupData>({
    email: '',
    password: '',
    name: '',
    organization_name: '',
    organization_type: '',
    lab_name: '',
    focus_areas: [],
  });

  const [confirmPassword, setConfirmPassword] = useState('');
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [isUploadingCv, setIsUploadingCv] = useState(false);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, isLoading, navigate]);

  // Update mode from URL params
  useEffect(() => {
    setIsSignup(searchParams.get('mode') === 'signup');
  }, [searchParams]);

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      await login(loginForm);
      showToast('Welcome back!', 'success');
      navigate('/dashboard');
    } catch (error: unknown) {
      showToast(getErrorMessage(error), 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (signupForm.password !== confirmPassword) {
      showToast('Passwords do not match', 'error');
      return;
    }

    // Password validation matching backend requirements
    const password = signupForm.password;
    if (password.length < 12) {
      showToast('Password must be at least 12 characters', 'error');
      return;
    }
    if (!/[A-Z]/.test(password)) {
      showToast('Password must contain at least one uppercase letter', 'error');
      return;
    }
    if (!/[a-z]/.test(password)) {
      showToast('Password must contain at least one lowercase letter', 'error');
      return;
    }
    if (!/\d/.test(password)) {
      showToast('Password must contain at least one number', 'error');
      return;
    }
    if (!/[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;'/`~]/.test(password)) {
      showToast('Password must contain at least one special character', 'error');
      return;
    }

    if (!signupForm.focus_areas || signupForm.focus_areas.length === 0) {
      showToast('Please select at least one focus area', 'error');
      return;
    }

    setIsSubmitting(true);

    try {
      await signup(signupForm);
      showToast('Account created successfully!', 'success');

      // Upload CV if provided (non-blocking)
      if (cvFile) {
        setIsUploadingCv(true);
        try {
          const formData = new FormData();
          formData.append('file', cvFile);

          const token = localStorage.getItem('access_token');
          await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/profile/import/cv?save_file=true&trigger_analysis=true`, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${token}`,
            },
            body: formData,
          });
          showToast('CV uploaded! We\'re analyzing your profile...', 'success');
        } catch (cvError) {
          console.error('CV upload failed:', cvError);
          // Don't block signup on CV upload failure
        } finally {
          setIsUploadingCv(false);
        }
      }

      // Redirect to onboarding to complete profile setup
      navigate('/onboarding');
    } catch (error: unknown) {
      showToast(getErrorMessage(error), 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleFocusArea = (area: string) => {
    setSignupForm((prev) => {
      const currentAreas = prev.focus_areas || [];
      return {
        ...prev,
        focus_areas: currentAreas.includes(area)
          ? currentAreas.filter((a) => a !== area)
          : [...currentAreas, area],
      };
    });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--gr-bg-primary)]">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-[var(--gr-blue-600)] border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      {/* Background gradient - Editorial forest green */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(26, 58, 47, 0.08) 0%, transparent 50%)',
        }}
      />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <Link to="/" className="flex justify-center items-center gap-3">
          <div className="w-10 h-10 bg-[var(--gr-blue-600)] rounded-lg flex items-center justify-center shadow-md">
            <span className="text-white font-bold text-xl font-display">G</span>
          </div>
          <span className="text-2xl font-display font-semibold text-[var(--gr-text-primary)]">GrantRadar</span>
        </Link>
        <h2 className="mt-8 text-center text-3xl font-display font-medium text-[var(--gr-text-primary)]">
          {isSignup ? 'Create your account' : 'Welcome back'}
        </h2>
        {isSignup && (
          <p className="mt-2 text-center text-xs text-[var(--gr-text-tertiary)]">
            Takes about 2 minutes • Start matching grants immediately
          </p>
        )}
        <p className="mt-2 text-center text-sm text-[var(--gr-text-secondary)]">
          {isSignup ? (
            <>
              Already have an account?{' '}
              <button
                onClick={() => setIsSignup(false)}
                className="font-medium text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-500)] transition-colors"
              >
                Sign in
              </button>
            </>
          ) : (
            <>
              Don't have an account?{' '}
              <button
                onClick={() => setIsSignup(true)}
                className="font-medium text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-500)] transition-colors"
              >
                Sign up
              </button>
            </>
          )}
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="card-elevated sm:rounded-2xl sm:px-10 py-8 px-4">
          {isSignup ? (
            <form onSubmit={handleSignupSubmit} className="space-y-5">
              <div>
                <label htmlFor="full-name" className="label">
                  Full Name
                </label>
                <input
                  id="full-name"
                  type="text"
                  required
                  value={signupForm.name}
                  onChange={(e) =>
                    setSignupForm((prev) => ({
                      ...prev,
                      name: e.target.value,
                    }))
                  }
                  className="input"
                  placeholder="Dr. Jane Smith"
                />
                <p className="mt-1 text-xs text-[var(--gr-text-tertiary)]">
                  Your name as it appears on publications
                </p>
              </div>

              <div>
                <label htmlFor="org-name" className="label">
                  Institution / Organization
                </label>
                <input
                  id="org-name"
                  type="text"
                  required
                  value={signupForm.organization_name}
                  onChange={(e) =>
                    setSignupForm((prev) => ({
                      ...prev,
                      organization_name: e.target.value,
                    }))
                  }
                  className="input"
                  placeholder="Stanford University"
                />
                <p className="mt-1 text-xs text-[var(--gr-text-tertiary)]">
                  Your research institution, university, or organization
                </p>
              </div>

              <div>
                <label htmlFor="lab-name" className="label">
                  Lab / Research Group Name
                </label>
                <input
                  id="lab-name"
                  type="text"
                  value={signupForm.lab_name}
                  onChange={(e) =>
                    setSignupForm((prev) => ({
                      ...prev,
                      lab_name: e.target.value,
                    }))
                  }
                  className="input"
                  placeholder="Smith Computational Biology Lab"
                />
                <p className="mt-1 text-xs text-[var(--gr-text-tertiary)]">
                  The specific lab or research group you work in (optional)
                </p>
              </div>

              <div>
                <label htmlFor="org-type" className="label">
                  Organization Type
                </label>
                <select
                  id="org-type"
                  required
                  value={signupForm.organization_type}
                  onChange={(e) =>
                    setSignupForm((prev) => ({
                      ...prev,
                      organization_type: e.target.value,
                    }))
                  }
                  className="input"
                >
                  <option value="">Select type...</option>
                  {organizationTypes.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-[var(--gr-text-tertiary)]">
                  This helps us find grants you're eligible for
                </p>
              </div>

              <div>
                <label className="label">Focus Areas</label>
                <p className="text-xs text-[var(--gr-text-tertiary)] mb-3">
                  Select all that apply • You can change these later in Settings
                </p>
                <div className="flex flex-wrap gap-2">
                  {focusAreaOptions.map((area) => (
                    <button
                      key={area}
                      type="button"
                      onClick={() => toggleFocusArea(area)}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                        signupForm.focus_areas?.includes(area)
                          ? 'bg-[var(--gr-blue-600)] text-white'
                          : 'bg-[var(--gr-bg-card)] text-[var(--gr-text-secondary)] border border-[var(--gr-border-default)] hover:border-[var(--gr-border-strong)]'
                      }`}
                    >
                      {area}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label htmlFor="cv-upload" className="label">
                  Upload CV (Optional)
                </label>
                <div className="mt-1">
                  <label
                    htmlFor="cv-upload"
                    className={`flex items-center justify-center w-full px-4 py-3 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
                      cvFile
                        ? 'border-[var(--gr-blue-500)] bg-[var(--gr-blue-50)]'
                        : 'border-[var(--gr-border-default)] hover:border-[var(--gr-border-strong)] bg-[var(--gr-bg-secondary)]'
                    }`}
                  >
                    <div className="text-center">
                      {cvFile ? (
                        <div className="flex items-center gap-2">
                          <svg className="w-5 h-5 text-[var(--gr-blue-600)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span className="text-sm text-[var(--gr-text-primary)]">{cvFile.name}</span>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault();
                              setCvFile(null);
                            }}
                            className="text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-primary)]"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      ) : (
                        <>
                          <svg className="mx-auto h-8 w-8 text-[var(--gr-text-tertiary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                          </svg>
                          <p className="mt-1 text-sm text-[var(--gr-text-secondary)]">
                            Click to upload PDF (max 10MB)
                          </p>
                        </>
                      )}
                    </div>
                    <input
                      id="cv-upload"
                      type="file"
                      accept=".pdf"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          if (file.size > 10 * 1024 * 1024) {
                            showToast('File too large. Maximum size is 10MB.', 'error');
                            return;
                          }
                          setCvFile(file);
                        }
                      }}
                    />
                  </label>
                </div>
                <p className="mt-1 text-xs text-[var(--gr-text-tertiary)]">
                  We'll analyze your CV to auto-populate your profile and find relevant grants
                </p>
              </div>

              <div>
                <label htmlFor="signup-email" className="label">
                  Email Address
                </label>
                <input
                  id="signup-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={signupForm.email}
                  onChange={(e) =>
                    setSignupForm((prev) => ({ ...prev, email: e.target.value }))
                  }
                  className="input"
                  placeholder="you@organization.org"
                />
              </div>

              <div>
                <label htmlFor="signup-password" className="label">
                  Password
                </label>
                <input
                  id="signup-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={12}
                  value={signupForm.password}
                  onChange={(e) =>
                    setSignupForm((prev) => ({
                      ...prev,
                      password: e.target.value,
                    }))
                  }
                  className="input"
                  placeholder="At least 12 characters"
                />
                <p className="mt-1 text-xs text-[var(--gr-text-tertiary)]">
                  Must include uppercase, lowercase, number, and special character
                </p>
              </div>

              <div>
                <label htmlFor="confirm-password" className="label">
                  Confirm Password
                </label>
                <input
                  id="confirm-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="input"
                  placeholder="Confirm your password"
                />
              </div>

              {/* What happens next */}
              <div className="mt-6 p-4 bg-[var(--gr-blue-50)] rounded-xl border border-[var(--gr-blue-100)]">
                <p className="text-sm text-[var(--gr-text-secondary)]">
                  <strong className="text-[var(--gr-text-primary)]">What happens next:</strong>{' '}
                  We'll analyze 86,000+ grants against your profile. You'll see your first matches within 5 minutes.
                </p>
              </div>

              <button
                type="submit"
                disabled={isSubmitting || isUploadingCv}
                className="btn-primary w-full justify-center mt-6"
              >
                {isSubmitting || isUploadingCv ? (
                  <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-5 w-5 border-2 border-[var(--gr-slate-950)] border-t-transparent"></div>
                    <span>{isUploadingCv ? 'Uploading CV...' : 'Creating account...'}</span>
                  </div>
                ) : (
                  'Create Account & Start Matching'
                )}
              </button>
            </form>
          ) : (
            <form onSubmit={handleLoginSubmit} className="space-y-6">
              <div>
                <label htmlFor="login-email" className="label">
                  Email Address
                </label>
                <input
                  id="login-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={loginForm.email}
                  onChange={(e) =>
                    setLoginForm((prev) => ({ ...prev, email: e.target.value }))
                  }
                  className="input"
                  placeholder="you@organization.org"
                />
              </div>

              <div>
                <label htmlFor="login-password" className="label">
                  Password
                </label>
                <input
                  id="login-password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={loginForm.password}
                  onChange={(e) =>
                    setLoginForm((prev) => ({
                      ...prev,
                      password: e.target.value,
                    }))
                  }
                  className="input"
                  placeholder="Your password"
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <input
                    id="remember-me"
                    type="checkbox"
                    className="h-4 w-4 rounded border-[var(--gr-border-default)] bg-[var(--gr-bg-card)] text-[var(--gr-blue-600)] focus:ring-[var(--gr-blue-600)]"
                  />
                  <label
                    htmlFor="remember-me"
                    className="ml-2 block text-sm text-[var(--gr-text-secondary)]"
                  >
                    Remember me
                  </label>
                </div>

                <Link
                  to="/contact"
                  className="text-sm font-medium text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-500)] transition-colors"
                >
                  Forgot password?
                </Link>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="btn-primary w-full justify-center"
              >
                {isSubmitting ? (
                  <div className="animate-spin rounded-full h-5 w-5 border-2 border-[var(--gr-slate-950)] border-t-transparent"></div>
                ) : (
                  'Sign in'
                )}
              </button>
            </form>
          )}
        </div>

        <p className="mt-6 text-center text-xs text-[var(--gr-text-tertiary)]">
          By signing up, you agree to our{' '}
          <Link to="/terms" className="text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-500)]">
            Terms of Service
          </Link>{' '}
          and{' '}
          <Link to="/privacy" className="text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-500)]">
            Privacy Policy
          </Link>
          .
        </p>
      </div>
    </div>
  );
}

export default Auth;
