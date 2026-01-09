import React, { Component, type ReactNode, type ErrorInfo } from 'react';
import {
  ExclamationTriangleIcon,
  ArrowPathIcon,
  HomeIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  DocumentMagnifyingGlassIcon,
} from '@heroicons/react/24/outline';

// ============================================================================
// Types
// ============================================================================

export interface FallbackProps {
  error: Error;
  errorInfo?: ErrorInfo;
  resetErrorBoundary: () => void;
}

export type FallbackRender = (props: FallbackProps) => ReactNode;

export interface ErrorBoundaryProps {
  children: ReactNode;
  /** Custom fallback component to render when an error occurs */
  fallback?: ReactNode;
  /** Render prop for custom fallback with access to error and reset function */
  fallbackRender?: FallbackRender;
  /** Callback fired when an error is caught */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Callback fired when the error boundary resets */
  onReset?: () => void;
  /** Key to force reset when changed */
  resetKeys?: unknown[];
  /** Feature/component name for logging purposes */
  name?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

// ============================================================================
// ErrorBoundary Component
// ============================================================================

/**
 * A flexible error boundary component that catches JavaScript errors
 * in its child component tree and displays a fallback UI.
 *
 * @example Basic usage
 * ```tsx
 * <ErrorBoundary fallback={<ErrorFallback />}>
 *   <RiskyComponent />
 * </ErrorBoundary>
 * ```
 *
 * @example With render prop
 * ```tsx
 * <ErrorBoundary
 *   onError={(error) => logToService(error)}
 *   fallbackRender={({ error, resetErrorBoundary }) => (
 *     <div>
 *       <p>Something went wrong</p>
 *       <button onClick={resetErrorBoundary}>Try again</button>
 *     </div>
 *   )}
 * >
 *   <RiskyComponent />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });

    // Log to console
    const name = this.props.name || 'ErrorBoundary';
    console.error(`[${name}] Caught error:`, error);
    console.error(`[${name}] Component stack:`, errorInfo.componentStack);

    // Call onError callback if provided
    this.props.onError?.(error, errorInfo);

    // In production, this would be where you'd send to an error tracking service
    // e.g., Sentry.captureException(error, { extra: { componentStack: errorInfo.componentStack } });
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps): void {
    // Reset on resetKeys change
    if (
      this.state.hasError &&
      this.props.resetKeys &&
      prevProps.resetKeys &&
      !arraysEqual(prevProps.resetKeys, this.props.resetKeys)
    ) {
      this.resetErrorBoundary();
    }
  }

  resetErrorBoundary = (): void => {
    this.props.onReset?.();
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render(): ReactNode {
    const { hasError, error, errorInfo } = this.state;
    const { children, fallback, fallbackRender } = this.props;

    if (hasError && error) {
      // Render prop takes precedence
      if (fallbackRender) {
        return fallbackRender({
          error,
          errorInfo: errorInfo ?? undefined,
          resetErrorBoundary: this.resetErrorBoundary,
        });
      }

      // Custom fallback component
      if (fallback) {
        return fallback;
      }

      // Default fallback (component-level)
      return (
        <DefaultErrorFallback
          error={error}
          errorInfo={errorInfo ?? undefined}
          resetErrorBoundary={this.resetErrorBoundary}
        />
      );
    }

    return children;
  }
}

// ============================================================================
// Default Error Fallback Component
// ============================================================================

interface DefaultErrorFallbackProps extends FallbackProps {
  variant?: 'page' | 'component' | 'inline';
}

export function DefaultErrorFallback({
  error,
  errorInfo,
  resetErrorBoundary,
  variant = 'component',
}: DefaultErrorFallbackProps) {
  const [showDetails, setShowDetails] = React.useState(false);
  const isDev = import.meta.env.DEV;

  if (variant === 'inline') {
    return (
      <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
        <ExclamationTriangleIcon className="w-4 h-4 text-red-500 flex-shrink-0" />
        <span className="text-sm text-red-700">Something went wrong</span>
        <button
          onClick={resetErrorBoundary}
          className="ml-auto text-xs font-medium text-red-600 hover:text-red-700 underline"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div
      className={`
        bg-[var(--gr-bg-card)] rounded-xl border border-[var(--gr-border-default)]
        ${variant === 'page' ? 'max-w-lg mx-auto shadow-lg' : ''}
      `}
    >
      <div className="flex flex-col items-center justify-center p-8 text-center">
        {/* Icon */}
        <div className="w-14 h-14 rounded-full bg-red-50 flex items-center justify-center mb-5">
          <ExclamationTriangleIcon className="w-7 h-7 text-red-500" />
        </div>

        {/* Title */}
        <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-2">
          {variant === 'page' ? 'Page Error' : 'Something went wrong'}
        </h3>

        {/* Description */}
        <p className="text-sm text-[var(--gr-text-secondary)] max-w-sm mb-6">
          {variant === 'page'
            ? "We're sorry, but this page encountered an unexpected error. Please try refreshing or return to the home page."
            : 'This section encountered an error. You can try again or refresh the page if the problem persists.'}
        </p>

        {/* Error details (dev only) */}
        {isDev && error && (
          <div className="w-full max-w-md mb-6">
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="flex items-center gap-1 text-xs text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)] transition-colors mx-auto"
            >
              <DocumentMagnifyingGlassIcon className="w-3.5 h-3.5" />
              <span>Error details</span>
              {showDetails ? (
                <ChevronUpIcon className="w-3 h-3" />
              ) : (
                <ChevronDownIcon className="w-3 h-3" />
              )}
            </button>
            {showDetails && (
              <div className="mt-3 text-left">
                <div className="p-3 bg-[var(--gr-bg-secondary)] border border-[var(--gr-border-subtle)] rounded-lg">
                  <p className="text-xs font-medium text-red-600 mb-1">{error.name}</p>
                  <p className="text-xs text-red-500 break-words">{error.message}</p>
                  {errorInfo?.componentStack && (
                    <pre className="mt-2 text-[10px] text-[var(--gr-text-tertiary)] overflow-auto max-h-32 whitespace-pre-wrap">
                      {errorInfo.componentStack}
                    </pre>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={resetErrorBoundary}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-[var(--gr-bg-primary)] border border-[var(--gr-border-default)] rounded-lg text-sm font-medium text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-hover)] hover:border-[var(--gr-border-strong)] transition-all"
          >
            <ArrowPathIcon className="w-4 h-4" />
            Try again
          </button>
          {variant === 'page' && (
            <a
              href="/"
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-[var(--gr-blue-600)] text-white rounded-lg text-sm font-medium hover:bg-[var(--gr-blue-700)] transition-colors"
            >
              <HomeIcon className="w-4 h-4" />
              Go Home
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Page Error Boundary
// ============================================================================

interface PageErrorBoundaryProps {
  children: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

/**
 * Error boundary wrapper for page-level errors.
 * Displays a full-page error state while maintaining navigation.
 *
 * @example
 * ```tsx
 * <PageErrorBoundary>
 *   <Dashboard />
 * </PageErrorBoundary>
 * ```
 */
export function PageErrorBoundary({ children, onError }: PageErrorBoundaryProps) {
  return (
    <ErrorBoundary
      name="PageErrorBoundary"
      onError={onError}
      fallbackRender={({ error, errorInfo, resetErrorBoundary }) => (
        <div className="min-h-screen bg-[var(--gr-bg-primary)] flex items-center justify-center px-4 py-12">
          <DefaultErrorFallback
            error={error}
            errorInfo={errorInfo}
            resetErrorBoundary={resetErrorBoundary}
            variant="page"
          />
        </div>
      )}
    >
      {children}
    </ErrorBoundary>
  );
}

// ============================================================================
// Component Error Boundary
// ============================================================================

interface ComponentErrorBoundaryProps {
  children: ReactNode;
  /** Name of the component/feature for logging */
  name?: string;
  /** Custom fallback UI */
  fallback?: ReactNode;
  /** Use inline variant (smaller, more subtle) */
  inline?: boolean;
  /** Callback fired when error occurs */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Callback fired when reset */
  onReset?: () => void;
}

/**
 * Error boundary wrapper for component-level errors.
 * Displays an inline error state that doesn't break the whole page.
 *
 * @example
 * ```tsx
 * <ComponentErrorBoundary name="UserStats" inline>
 *   <UserStatsWidget />
 * </ComponentErrorBoundary>
 * ```
 */
export function ComponentErrorBoundary({
  children,
  name,
  fallback,
  inline = false,
  onError,
  onReset,
}: ComponentErrorBoundaryProps) {
  return (
    <ErrorBoundary
      name={name || 'ComponentErrorBoundary'}
      onError={onError}
      onReset={onReset}
      fallback={fallback}
      fallbackRender={
        fallback
          ? undefined
          : ({ error, errorInfo, resetErrorBoundary }) => (
              <DefaultErrorFallback
                error={error}
                errorInfo={errorInfo}
                resetErrorBoundary={resetErrorBoundary}
                variant={inline ? 'inline' : 'component'}
              />
            )
      }
    >
      {children}
    </ErrorBoundary>
  );
}

// ============================================================================
// Higher-Order Component
// ============================================================================

/**
 * HOC to wrap a component with an error boundary.
 *
 * @example
 * ```tsx
 * const SafeChart = withErrorBoundary(Chart, {
 *   name: 'Chart',
 *   inline: true
 * });
 * ```
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  options: Omit<ComponentErrorBoundaryProps, 'children'> = {}
): React.FC<P> {
  const displayName = Component.displayName || Component.name || 'Component';

  const WrappedComponent: React.FC<P> = (props) => (
    <ComponentErrorBoundary name={options.name || displayName} {...options}>
      <Component {...props} />
    </ComponentErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${displayName})`;

  return WrappedComponent;
}

// ============================================================================
// Utilities
// ============================================================================

function arraysEqual(a: unknown[], b: unknown[]): boolean {
  if (a.length !== b.length) return false;
  return a.every((item, index) => item === b[index]);
}

export default ErrorBoundary;
