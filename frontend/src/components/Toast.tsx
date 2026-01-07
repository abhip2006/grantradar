import { useEffect } from 'react';
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  InformationCircleIcon,
  XCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { useToast, type Toast as ToastType, type ToastType as ToastVariant } from '../contexts/ToastContext';

const toastStyles: Record<ToastVariant, { bg: string; border: string; icon: typeof CheckCircleIcon; iconColor: string }> = {
  success: {
    bg: 'bg-[var(--gr-bg-elevated)]',
    border: 'border-[var(--gr-emerald-500)]/30',
    icon: CheckCircleIcon,
    iconColor: 'text-[var(--gr-emerald-400)]',
  },
  error: {
    bg: 'bg-[var(--gr-bg-elevated)]',
    border: 'border-[var(--gr-danger)]/30',
    icon: XCircleIcon,
    iconColor: 'text-[var(--gr-danger)]',
  },
  warning: {
    bg: 'bg-[var(--gr-bg-elevated)]',
    border: 'border-[var(--gr-amber-500)]/30',
    icon: ExclamationCircleIcon,
    iconColor: 'text-[var(--gr-amber-400)]',
  },
  info: {
    bg: 'bg-[var(--gr-bg-elevated)]',
    border: 'border-[var(--gr-cyan-500)]/30',
    icon: InformationCircleIcon,
    iconColor: 'text-[var(--gr-cyan-400)]',
  },
};

function ToastItem({ toast, onRemove }: { toast: ToastType; onRemove: () => void }) {
  const style = toastStyles[toast.type];
  const Icon = style.icon;

  useEffect(() => {
    if (toast.duration && toast.duration > 0) {
      const timer = setTimeout(onRemove, toast.duration);
      return () => clearTimeout(timer);
    }
  }, [toast.duration, onRemove]);

  return (
    <div
      className={`flex items-start gap-3 p-4 rounded-xl border ${style.bg} ${style.border} shadow-[var(--gr-shadow-lg)] animate-fade-in-up`}
      role="alert"
    >
      <Icon className={`h-5 w-5 flex-shrink-0 ${style.iconColor}`} />
      <p className="flex-1 text-sm text-[var(--gr-text-primary)]">{toast.message}</p>
      <button
        onClick={onRemove}
        className="flex-shrink-0 text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)] transition-colors"
        aria-label="Close notification"
      >
        <XMarkIcon className="h-5 w-5" />
      </button>
    </div>
  );
}

export function ToastContainer() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full">
      {toasts.map((toast) => (
        <ToastItem
          key={toast.id}
          toast={toast}
          onRemove={() => removeToast(toast.id)}
        />
      ))}
    </div>
  );
}

export default ToastContainer;
