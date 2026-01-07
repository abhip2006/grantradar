import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  CalendarDaysIcon,
  ArrowDownTrayIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline';
import { calendarApi } from '../services/api';
import { useToast } from '../contexts/ToastContext';

interface CalendarSyncProps {
  grantId: string;
  grantTitle: string;
  hasDeadline: boolean;
}

export function CalendarSync({ grantId, grantTitle, hasDeadline }: CalendarSyncProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { showToast } = useToast();

  // Fetch calendar links
  const { data: calendarLinks, isLoading } = useQuery({
    queryKey: ['calendar-links', grantId],
    queryFn: () => calendarApi.getCalendarLinks(grantId),
    enabled: hasDeadline && isOpen,
    retry: false,
  });

  const handleDownloadIcs = async () => {
    try {
      const blob = await calendarApi.getGrantIcs(grantId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${grantTitle.slice(0, 50).replace(/[^a-zA-Z0-9]/g, '_')}_deadline.ics`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showToast('Calendar file downloaded', 'success');
    } catch {
      showToast('Failed to download calendar file', 'error');
    }
  };

  if (!hasDeadline) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="btn-secondary text-sm"
      >
        <CalendarDaysIcon className="h-4 w-4" />
        Add to Calendar
        <ChevronDownIcon className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown */}
          <div className="absolute top-full mt-2 right-0 z-20 w-56 rounded-xl bg-[var(--gr-bg-elevated)] border border-[var(--gr-border-default)] shadow-xl animate-fade-in-up">
            {isLoading ? (
              <div className="p-4 flex items-center justify-center">
                <div className="animate-spin rounded-full h-5 w-5 border-2 border-[var(--gr-amber-500)] border-t-transparent" />
              </div>
            ) : calendarLinks ? (
              <div className="py-2">
                <a
                  href={calendarLinks.google_calendar_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 px-4 py-2.5 hover:bg-[var(--gr-bg-hover)] transition-colors"
                  onClick={() => setIsOpen(false)}
                >
                  <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12.545 10.239v3.821h5.445c-.712 2.315-2.647 3.972-5.445 3.972-3.332 0-6.033-2.701-6.033-6.032s2.701-6.032 6.033-6.032c1.498 0 2.866.549 3.921 1.453l2.814-2.814C17.503 2.988 15.139 2 12.545 2 7.021 2 2.543 6.477 2.543 12s4.478 10 10.002 10c8.396 0 10.249-7.85 9.426-11.748l-9.426-.013z" fill="currentColor"/>
                  </svg>
                  <span className="text-sm text-[var(--gr-text-primary)]">Google Calendar</span>
                </a>

                <a
                  href={calendarLinks.outlook_calendar_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 px-4 py-2.5 hover:bg-[var(--gr-bg-hover)] transition-colors"
                  onClick={() => setIsOpen(false)}
                >
                  <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M7.88 12.04q0 .45-.11.87-.1.41-.33.74-.22.33-.58.52-.37.2-.87.2t-.85-.2q-.35-.21-.57-.55-.22-.33-.33-.75-.1-.42-.1-.86t.1-.87q.1-.43.34-.76.22-.34.59-.54.36-.2.87-.2t.86.2q.35.21.57.55.22.34.31.77.1.43.1.88zM24 12v9.38q0 .46-.33.8-.33.32-.8.32H7.13q-.46 0-.8-.33-.32-.33-.32-.8V18H1q-.41 0-.7-.3-.3-.29-.3-.7V7q0-.41.3-.7Q.58 6 1 6h6.5V2.55q0-.44.3-.75.3-.3.75-.3h12.9q.44 0 .75.3.3.3.3.75V12zm-6-8.25v3h3v-3h-3zm0 4.5v3h3v-3h-3zm0 4.5v1.83l3.05-1.83h-3.05zm-5.25-9v3h3.75v-3h-3.75zm0 4.5v3h3.75v-3h-3.75zm0 4.5v2.03l2.41 1.5 1.34-.8v-2.73h-3.75zM9 3.75V6h2l.13.01.12.04v-2.3H9zM3.38 7H1.63v10h5.25V7h-1.5q-.47 0-.8-.33-.33-.34-.33-.8V5.87zM7 17.75H1.63v.6q0 .13.08.22.08.1.22.1H7v-.92z" fill="currentColor"/>
                  </svg>
                  <span className="text-sm text-[var(--gr-text-primary)]">Outlook Calendar</span>
                </a>

                <div className="my-1 border-t border-[var(--gr-border-subtle)]" />

                <button
                  onClick={() => {
                    handleDownloadIcs();
                    setIsOpen(false);
                  }}
                  className="flex items-center gap-3 px-4 py-2.5 w-full hover:bg-[var(--gr-bg-hover)] transition-colors"
                >
                  <ArrowDownTrayIcon className="h-5 w-5 text-[var(--gr-text-secondary)]" />
                  <span className="text-sm text-[var(--gr-text-primary)]">Download .ics file</span>
                </button>
              </div>
            ) : (
              <div className="p-4 text-center text-sm text-[var(--gr-text-tertiary)]">
                Calendar links unavailable
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default CalendarSync;
