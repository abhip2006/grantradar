import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Tab, TabGroup, TabList, TabPanels, TabPanel } from '@headlessui/react';
import {
  UserCircleIcon,
  BellIcon,
  CreditCardIcon,
  CheckIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { userApi } from '../services/api';
import type { NotificationPreferences } from '../types';

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

const tabs = [
  { name: 'Profile', icon: UserCircleIcon },
  { name: 'Notifications', icon: BellIcon },
  { name: 'Billing', icon: CreditCardIcon },
];

export function Settings() {
  const { user, updateUser } = useAuth();
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  // Profile form state
  const [profileForm, setProfileForm] = useState({
    organization_name: user?.organization_name || '',
    organization_type: user?.organization_type || '',
    focus_areas: user?.focus_areas || [],
  });
  const [isProfileSubmitting, setIsProfileSubmitting] = useState(false);

  // Notification preferences query
  const { data: notifPrefs, isLoading: notifLoading } = useQuery({
    queryKey: ['notification-preferences'],
    queryFn: userApi.getNotificationPreferences,
  });

  // Notification form state
  const [notifForm, setNotifForm] = useState<Partial<NotificationPreferences>>({});

  // Update notif form when data loads
  useEffect(() => {
    if (notifPrefs && Object.keys(notifForm).length === 0) {
      setNotifForm(notifPrefs);
    }
  }, [notifPrefs, notifForm]);

  // Profile update mutation
  const profileMutation = useMutation({
    mutationFn: userApi.updateProfile,
    onSuccess: (updatedUser) => {
      updateUser(updatedUser);
      showToast('Profile updated successfully', 'success');
    },
    onError: () => {
      showToast('Failed to update profile', 'error');
    },
  });

  // Notification preferences mutation
  const notifMutation = useMutation({
    mutationFn: userApi.updateNotificationPreferences,
    onSuccess: (updatedPrefs) => {
      queryClient.setQueryData(['notification-preferences'], updatedPrefs);
      showToast('Notification preferences updated', 'success');
    },
    onError: () => {
      showToast('Failed to update preferences', 'error');
    },
  });

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsProfileSubmitting(true);
    try {
      await profileMutation.mutateAsync(profileForm);
    } finally {
      setIsProfileSubmitting(false);
    }
  };

  const handleNotifSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    notifMutation.mutate(notifForm);
  };

  const toggleFocusArea = (area: string) => {
    setProfileForm((prev) => ({
      ...prev,
      focus_areas: prev.focus_areas.includes(area)
        ? prev.focus_areas.filter((a) => a !== area)
        : [...prev.focus_areas, area],
    }));
  };

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="mb-8 animate-fade-in-up">
          <h1 className="text-3xl font-display font-medium text-[var(--gr-text-primary)]">Settings</h1>
          <p className="mt-2 text-[var(--gr-text-secondary)]">
            Manage your account settings and preferences
          </p>
        </div>

        <TabGroup>
          <div className="card-elevated overflow-hidden animate-fade-in-up stagger-1">
            <TabList className="flex border-b border-[var(--gr-border-subtle)]">
              {tabs.map((tab) => (
                <Tab
                  key={tab.name}
                  className={({ selected }) =>
                    `flex-1 flex items-center justify-center gap-2 px-4 py-4 text-sm font-medium transition-colors outline-none ${
                      selected
                        ? 'text-[var(--gr-amber-400)] border-b-2 border-[var(--gr-amber-400)] bg-[var(--gr-amber-500)]/5'
                        : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-hover)]'
                    }`
                  }
                >
                  <tab.icon className="h-5 w-5" />
                  {tab.name}
                </Tab>
              ))}
            </TabList>

            <TabPanels>
              {/* Profile Panel */}
              <TabPanel className="p-6">
                <form onSubmit={handleProfileSubmit} className="space-y-6">
                  <div>
                    <label htmlFor="org-name" className="label">
                      Organization Name
                    </label>
                    <input
                      id="org-name"
                      type="text"
                      value={profileForm.organization_name}
                      onChange={(e) =>
                        setProfileForm((prev) => ({
                          ...prev,
                          organization_name: e.target.value,
                        }))
                      }
                      className="input"
                    />
                  </div>

                  <div>
                    <label htmlFor="org-type" className="label">
                      Organization Type
                    </label>
                    <select
                      id="org-type"
                      value={profileForm.organization_type}
                      onChange={(e) =>
                        setProfileForm((prev) => ({
                          ...prev,
                          organization_type: e.target.value,
                        }))
                      }
                      className="input"
                    >
                      <option value="">Select type...</option>
                      <option value="501(c)(3) Nonprofit">501(c)(3) Nonprofit</option>
                      <option value="Educational Institution">Educational Institution</option>
                      <option value="Government Agency">Government Agency</option>
                      <option value="Healthcare Organization">Healthcare Organization</option>
                      <option value="Research Institution">Research Institution</option>
                      <option value="Community Organization">Community Organization</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>

                  <div>
                    <label className="label">Focus Areas</label>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {focusAreaOptions.map((area) => (
                        <button
                          key={area}
                          type="button"
                          onClick={() => toggleFocusArea(area)}
                          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                            profileForm.focus_areas.includes(area)
                              ? 'bg-[var(--gr-amber-500)] text-[var(--gr-slate-950)]'
                              : 'bg-[var(--gr-bg-card)] text-[var(--gr-text-secondary)] border border-[var(--gr-border-default)] hover:border-[var(--gr-border-strong)]'
                          }`}
                        >
                          {area}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="pt-4 border-t border-[var(--gr-border-subtle)]">
                    <div className="flex justify-end">
                      <button
                        type="submit"
                        disabled={isProfileSubmitting}
                        className="btn-primary"
                      >
                        {isProfileSubmitting ? (
                          <div className="animate-spin rounded-full h-4 w-4 border-2 border-[var(--gr-slate-950)] border-t-transparent" />
                        ) : (
                          <CheckIcon className="h-4 w-4" />
                        )}
                        Save Changes
                      </button>
                    </div>
                  </div>
                </form>
              </TabPanel>

              {/* Notifications Panel */}
              <TabPanel className="p-6">
                {notifLoading ? (
                  <div className="space-y-4">
                    <div className="skeleton h-12 w-full" />
                    <div className="skeleton h-12 w-full" />
                    <div className="skeleton h-12 w-full" />
                  </div>
                ) : (
                  <form onSubmit={handleNotifSubmit} className="space-y-6">
                    <div className="flex items-center justify-between p-4 bg-[var(--gr-bg-card)] rounded-xl border border-[var(--gr-border-subtle)]">
                      <div>
                        <h3 className="text-sm font-medium text-[var(--gr-text-primary)]">
                          Email Notifications
                        </h3>
                        <p className="text-sm text-[var(--gr-text-tertiary)]">
                          Receive grant matches and updates via email
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() =>
                          setNotifForm((prev) => ({
                            ...prev,
                            email_enabled: !prev.email_enabled,
                          }))
                        }
                        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full transition-colors ${
                          notifForm.email_enabled ? 'bg-[var(--gr-amber-500)]' : 'bg-[var(--gr-slate-600)]'
                        }`}
                      >
                        <span
                          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ${
                            notifForm.email_enabled ? 'translate-x-5' : 'translate-x-0.5'
                          } mt-0.5`}
                        />
                      </button>
                    </div>

                    {notifForm.email_enabled && (
                      <>
                        <div>
                          <label htmlFor="email-frequency" className="label">
                            Email Frequency
                          </label>
                          <select
                            id="email-frequency"
                            value={notifForm.email_frequency || 'daily'}
                            onChange={(e) =>
                              setNotifForm((prev) => ({
                                ...prev,
                                email_frequency: e.target.value as 'daily' | 'weekly' | 'realtime',
                              }))
                            }
                            className="input"
                          >
                            <option value="realtime">Real-time (as matches found)</option>
                            <option value="daily">Daily digest</option>
                            <option value="weekly">Weekly digest</option>
                          </select>
                        </div>

                        <div>
                          <label htmlFor="min-score" className="label">
                            Minimum Match Score for Notifications
                          </label>
                          <div className="mt-2 flex items-center gap-4">
                            <input
                              id="min-score"
                              type="range"
                              min="0"
                              max="100"
                              value={notifForm.min_match_score || 70}
                              onChange={(e) =>
                                setNotifForm((prev) => ({
                                  ...prev,
                                  min_match_score: parseInt(e.target.value),
                                }))
                              }
                              className="flex-1 h-2 bg-[var(--gr-slate-700)] rounded-lg appearance-none cursor-pointer accent-[var(--gr-amber-500)]"
                            />
                            <span className="text-sm font-semibold text-[var(--gr-amber-400)] w-12">
                              {notifForm.min_match_score || 70}%
                            </span>
                          </div>
                          <p className="mt-2 text-xs text-[var(--gr-text-tertiary)]">
                            Only notify me for grants scoring above this threshold
                          </p>
                        </div>
                      </>
                    )}

                    <div className="flex items-center justify-between p-4 bg-[var(--gr-bg-card)] rounded-xl border border-[var(--gr-border-subtle)]">
                      <div>
                        <h3 className="text-sm font-medium text-[var(--gr-text-primary)]">
                          Deadline Reminders
                        </h3>
                        <p className="text-sm text-[var(--gr-text-tertiary)]">
                          Get notified before grant deadlines
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() =>
                          setNotifForm((prev) => ({
                            ...prev,
                            notify_on_deadline: !prev.notify_on_deadline,
                          }))
                        }
                        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full transition-colors ${
                          notifForm.notify_on_deadline ? 'bg-[var(--gr-amber-500)]' : 'bg-[var(--gr-slate-600)]'
                        }`}
                      >
                        <span
                          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ${
                            notifForm.notify_on_deadline ? 'translate-x-5' : 'translate-x-0.5'
                          } mt-0.5`}
                        />
                      </button>
                    </div>

                    {notifForm.notify_on_deadline && (
                      <div>
                        <label htmlFor="deadline-days" className="label">
                          Days Before Deadline
                        </label>
                        <select
                          id="deadline-days"
                          value={notifForm.deadline_warning_days || 7}
                          onChange={(e) =>
                            setNotifForm((prev) => ({
                              ...prev,
                              deadline_warning_days: parseInt(e.target.value),
                            }))
                          }
                          className="input"
                        >
                          <option value="3">3 days</option>
                          <option value="7">7 days</option>
                          <option value="14">14 days</option>
                          <option value="30">30 days</option>
                        </select>
                      </div>
                    )}

                    <div className="pt-4 border-t border-[var(--gr-border-subtle)]">
                      <div className="flex justify-end">
                        <button
                          type="submit"
                          disabled={notifMutation.isPending}
                          className="btn-primary"
                        >
                          {notifMutation.isPending ? (
                            <div className="animate-spin rounded-full h-4 w-4 border-2 border-[var(--gr-slate-950)] border-t-transparent" />
                          ) : (
                            <CheckIcon className="h-4 w-4" />
                          )}
                          Save Preferences
                        </button>
                      </div>
                    </div>
                  </form>
                )}
              </TabPanel>

              {/* Billing Panel */}
              <TabPanel className="p-6">
                <div className="space-y-6">
                  {/* Current plan */}
                  <div className="p-6 rounded-2xl bg-gradient-to-br from-[var(--gr-amber-500)]/10 to-transparent border border-[var(--gr-amber-500)]/30">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="badge badge-amber mb-2">Current Plan</span>
                        <h3 className="text-xl font-display font-medium text-[var(--gr-text-primary)]">
                          Beta Access
                        </h3>
                        <p className="text-sm text-[var(--gr-text-secondary)]">
                          Early adopter pricing locked in forever
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-4xl font-display font-semibold text-[var(--gr-amber-400)]">$200</p>
                        <p className="text-sm text-[var(--gr-text-tertiary)]">/month</p>
                      </div>
                    </div>
                  </div>

                  {/* Features */}
                  <div>
                    <h4 className="label mb-3">Plan Features</h4>
                    <ul className="space-y-2">
                      {[
                        'Unlimited grant matches',
                        'Federal & foundation grants',
                        'Real-time notifications',
                        'Match score insights',
                        'Email alerts',
                        'Priority support',
                      ].map((feature) => (
                        <li key={feature} className="flex items-center gap-2 text-sm text-[var(--gr-text-secondary)]">
                          <CheckIcon className="h-4 w-4 text-[var(--gr-emerald-400)]" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Payment method placeholder */}
                  <div className="pt-6 border-t border-[var(--gr-border-subtle)]">
                    <h4 className="label mb-3">Payment Method</h4>
                    <div className="p-4 rounded-xl bg-[var(--gr-bg-card)] border border-[var(--gr-border-subtle)] flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-[var(--gr-slate-700)]">
                          <CreditCardIcon className="h-6 w-6 text-[var(--gr-text-secondary)]" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-[var(--gr-text-primary)]">
                            **** **** **** 4242
                          </p>
                          <p className="text-xs text-[var(--gr-text-tertiary)]">Expires 12/25</p>
                        </div>
                      </div>
                      <button className="btn-ghost text-[var(--gr-amber-400)]">
                        Update
                      </button>
                    </div>
                  </div>

                  {/* Billing history placeholder */}
                  <div className="pt-6 border-t border-[var(--gr-border-subtle)]">
                    <h4 className="label mb-3">Billing History</h4>
                    <div className="space-y-2">
                      {[
                        { date: 'Jan 1, 2026', amount: '$200.00', status: 'Paid' },
                        { date: 'Dec 1, 2025', amount: '$200.00', status: 'Paid' },
                        { date: 'Nov 1, 2025', amount: '$200.00', status: 'Paid' },
                      ].map((invoice) => (
                        <div
                          key={invoice.date}
                          className="flex items-center justify-between py-3 px-4 rounded-xl bg-[var(--gr-bg-card)] border border-[var(--gr-border-subtle)]"
                        >
                          <span className="text-sm text-[var(--gr-text-secondary)]">{invoice.date}</span>
                          <span className="text-sm font-medium text-[var(--gr-text-primary)]">{invoice.amount}</span>
                          <span className="badge badge-emerald">{invoice.status}</span>
                          <button className="btn-ghost text-[var(--gr-amber-400)]">Download</button>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Cancel */}
                  <div className="pt-6 border-t border-[var(--gr-border-subtle)]">
                    <button className="text-sm text-[var(--gr-danger)] hover:text-[var(--gr-danger)]/80 transition-colors">
                      Cancel Subscription
                    </button>
                  </div>
                </div>
              </TabPanel>
            </TabPanels>
          </div>
        </TabGroup>
      </div>
    </div>
  );
}

export default Settings;
