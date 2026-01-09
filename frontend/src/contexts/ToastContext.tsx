import {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  type ReactNode,
} from 'react';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface ToastAction {
  label: string;
  onClick: () => void;
}

export interface ToastOptions {
  duration?: number;
  persist?: boolean;
  action?: ToastAction;
  customRender?: (toast: Toast, onDismiss: () => void) => ReactNode;
}

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
  duration: number;
  persist: boolean;
  action?: ToastAction;
  customRender?: (toast: Toast, onDismiss: () => void) => ReactNode;
  createdAt: number;
}

interface ToastHelpers {
  success: (message: string, options?: Omit<ToastOptions, 'type'>) => string;
  error: (message: string, options?: Omit<ToastOptions, 'type'>) => string;
  warning: (message: string, options?: Omit<ToastOptions, 'type'>) => string;
  info: (message: string, options?: Omit<ToastOptions, 'type'>) => string;
}

interface ToastContextType {
  toasts: Toast[];
  showToast: (message: string, type?: ToastType, options?: ToastOptions) => string;
  removeToast: (id: string) => void;
  clearAllToasts: () => void;
  toast: ToastHelpers;
  maxVisible: number;
}

const DEFAULT_DURATION = 5000;
const MAX_VISIBLE_TOASTS = 5;

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({
  children,
  maxVisible = MAX_VISIBLE_TOASTS
}: {
  children: ReactNode;
  maxVisible?: number;
}) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const clearAllToasts = useCallback(() => {
    setToasts([]);
  }, []);

  const showToast = useCallback(
    (message: string, type: ToastType = 'info', options: ToastOptions = {}): string => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
      const duration = options.persist ? 0 : (options.duration ?? DEFAULT_DURATION);

      const toast: Toast = {
        id,
        message,
        type,
        duration,
        persist: options.persist ?? false,
        action: options.action,
        customRender: options.customRender,
        createdAt: Date.now(),
      };

      setToasts((prev) => {
        // Add new toast and limit to max visible
        const newToasts = [...prev, toast];
        if (newToasts.length > maxVisible) {
          // Remove oldest non-persistent toasts first
          const sortedByPersistence = newToasts.sort((a, b) => {
            if (a.persist && !b.persist) return 1;
            if (!a.persist && b.persist) return -1;
            return a.createdAt - b.createdAt;
          });
          return sortedByPersistence.slice(-maxVisible);
        }
        return newToasts;
      });

      return id;
    },
    [maxVisible]
  );

  // Helper methods for convenience
  const toast = useMemo<ToastHelpers>(() => ({
    success: (message: string, options?: Omit<ToastOptions, 'type'>) =>
      showToast(message, 'success', options),
    error: (message: string, options?: Omit<ToastOptions, 'type'>) =>
      showToast(message, 'error', options),
    warning: (message: string, options?: Omit<ToastOptions, 'type'>) =>
      showToast(message, 'warning', options),
    info: (message: string, options?: Omit<ToastOptions, 'type'>) =>
      showToast(message, 'info', options),
  }), [showToast]);

  const value = useMemo(() => ({
    toasts,
    showToast,
    removeToast,
    clearAllToasts,
    toast,
    maxVisible,
  }), [toasts, showToast, removeToast, clearAllToasts, toast, maxVisible]);

  return (
    <ToastContext.Provider value={value}>
      {children}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextType {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

export default ToastContext;
