import { useEffect, useState, useCallback, useRef } from 'react';
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { useToast, type Toast as ToastType, type ToastType as ToastVariant } from '../../contexts/ToastContext';

interface ToastStyleConfig {
  bg: string;
  border: string;
  icon: typeof CheckCircleIcon;
  iconColor: string;
  progressColor: string;
}

const toastStyles: Record<ToastVariant, ToastStyleConfig> = {
  success: {
    bg: 'bg-white',
    border: 'border-green-200',
    icon: CheckCircleIcon,
    iconColor: 'text-green-500',
    progressColor: 'bg-green-500',
  },
  error: {
    bg: 'bg-white',
    border: 'border-red-200',
    icon: ExclamationCircleIcon,
    iconColor: 'text-red-500',
    progressColor: 'bg-red-500',
  },
  warning: {
    bg: 'bg-white',
    border: 'border-amber-200',
    icon: ExclamationTriangleIcon,
    iconColor: 'text-amber-500',
    progressColor: 'bg-amber-500',
  },
  info: {
    bg: 'bg-white',
    border: 'border-blue-200',
    icon: InformationCircleIcon,
    iconColor: 'text-blue-500',
    progressColor: 'bg-blue-500',
  },
};

interface ToastItemProps {
  toast: ToastType;
  onRemove: () => void;
  index: number;
}

function ToastItem({ toast, onRemove, index }: ToastItemProps) {
  const style = toastStyles[toast.type];
  const Icon = style.icon;
  const [isExiting, setIsExiting] = useState(false);
  const [progress, setProgress] = useState(100);
  const [isPaused, setIsPaused] = useState(false);
  const startTimeRef = useRef(Date.now());
  const remainingTimeRef = useRef(toast.duration);
  const animationFrameRef = useRef<number | undefined>(undefined);

  const handleDismiss = useCallback(() => {
    setIsExiting(true);
    // Wait for exit animation to complete
    setTimeout(onRemove, 300);
  }, [onRemove]);

  // Progress bar animation
  useEffect(() => {
    if (toast.persist || toast.duration <= 0) return;

    const updateProgress = () => {
      if (isPaused) {
        animationFrameRef.current = requestAnimationFrame(updateProgress);
        return;
      }

      const elapsed = Date.now() - startTimeRef.current;
      const remaining = remainingTimeRef.current - elapsed;
      const newProgress = (remaining / toast.duration) * 100;

      if (newProgress <= 0) {
        handleDismiss();
        return;
      }

      setProgress(newProgress);
      animationFrameRef.current = requestAnimationFrame(updateProgress);
    };

    animationFrameRef.current = requestAnimationFrame(updateProgress);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [toast.duration, toast.persist, isPaused, handleDismiss]);

  // Handle pause on hover
  const handleMouseEnter = useCallback(() => {
    if (toast.persist || toast.duration <= 0) return;
    setIsPaused(true);
    // Store remaining time
    const elapsed = Date.now() - startTimeRef.current;
    remainingTimeRef.current = remainingTimeRef.current - elapsed;
  }, [toast.persist, toast.duration]);

  const handleMouseLeave = useCallback(() => {
    if (toast.persist || toast.duration <= 0) return;
    setIsPaused(false);
    // Reset start time
    startTimeRef.current = Date.now();
  }, [toast.persist, toast.duration]);

  // Handle action button click
  const handleActionClick = useCallback(() => {
    if (toast.action?.onClick) {
      toast.action.onClick();
    }
    handleDismiss();
  }, [toast.action, handleDismiss]);

  // Custom render support
  if (toast.customRender) {
    return (
      <div
        className={`
          transform transition-all duration-300 ease-out
          ${isExiting ? 'translate-x-full opacity-0' : 'translate-x-0 opacity-100'}
        `}
        style={{
          animationDelay: `${index * 50}ms`,
        }}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {toast.customRender(toast, handleDismiss)}
      </div>
    );
  }

  return (
    <div
      className={`
        relative overflow-hidden
        flex flex-col
        w-full max-w-sm
        rounded-xl border ${style.border} ${style.bg}
        shadow-lg
        transform transition-all duration-300 ease-out
        ${isExiting ? 'translate-x-full opacity-0 scale-95' : 'translate-x-0 opacity-100 scale-100'}
      `}
      style={{
        animationDelay: `${index * 50}ms`,
      }}
      role="alert"
      aria-live="polite"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* Main content */}
      <div className="flex items-start gap-3 p-4">
        {/* Icon */}
        <div className={`flex-shrink-0 ${style.iconColor}`}>
          <Icon className="h-5 w-5" />
        </div>

        {/* Message and action */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-[var(--gr-text-primary)] break-words">
            {toast.message}
          </p>

          {/* Action button */}
          {toast.action && (
            <button
              onClick={handleActionClick}
              className="mt-2 text-sm font-semibold text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-700)] transition-colors"
            >
              {toast.action.label}
            </button>
          )}
        </div>

        {/* Close button */}
        <button
          onClick={handleDismiss}
          className="flex-shrink-0 p-1 rounded-lg text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)] hover:bg-[var(--gr-gray-100)] transition-all"
          aria-label="Dismiss notification"
        >
          <XMarkIcon className="h-4 w-4" />
        </button>
      </div>

      {/* Progress bar */}
      {!toast.persist && toast.duration > 0 && (
        <div className="h-1 w-full bg-[var(--gr-gray-100)]">
          <div
            className={`h-full ${style.progressColor} transition-none`}
            style={{
              width: `${progress}%`,
            }}
          />
        </div>
      )}
    </div>
  );
}

export function ToastContainer() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed top-4 right-4 z-50 flex flex-col gap-3 w-full max-w-sm pointer-events-none"
      aria-label="Notifications"
    >
      {toasts.map((toast, index) => (
        <div key={toast.id} className="pointer-events-auto animate-slide-in-right">
          <ToastItem
            toast={toast}
            onRemove={() => removeToast(toast.id)}
            index={index}
          />
        </div>
      ))}
    </div>
  );
}

export default ToastContainer;
