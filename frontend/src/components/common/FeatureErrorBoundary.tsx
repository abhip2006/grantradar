import React from 'react';
import { ExclamationTriangleIcon, ArrowPathIcon } from '@heroicons/react/24/outline';

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  featureName: string;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error?: Error;
}

/**
 * Error boundary component for wrapping feature panels.
 * Catches JavaScript errors in child components and displays a fallback UI.
 */
export class FeatureErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log error to console in development
    console.error(`[${this.props.featureName}] Error caught by boundary:`, error, errorInfo);

    // In production, you might want to send this to an error tracking service
    // e.g., Sentry, LogRocket, etc.
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: undefined });
    this.props.onReset?.();
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      // Custom fallback UI provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
      return (
        <div className="bg-white rounded-xl border border-red-200 p-6">
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center mb-4">
              <ExclamationTriangleIcon className="w-6 h-6 text-red-600" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {this.props.featureName} encountered an error
            </h3>
            <p className="text-sm text-gray-500 max-w-md mb-4">
              Something went wrong while loading this feature. Please try refreshing or contact
              support if the problem persists.
            </p>
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mb-4 w-full max-w-md text-left">
                <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">
                  Error details (dev only)
                </summary>
                <pre className="mt-2 p-3 bg-gray-50 rounded-lg text-xs text-red-600 overflow-auto max-h-32">
                  {this.state.error.message}
                  {'\n'}
                  {this.state.error.stack}
                </pre>
              </details>
            )}
            <div className="flex gap-3">
              <button
                onClick={this.handleReset}
                className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                <ArrowPathIcon className="w-4 h-4" />
                Try again
              </button>
              <button
                onClick={() => window.location.reload()}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                Refresh page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Functional component wrapper for use with hooks
 */
export function withFeatureErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  featureName: string
): React.FC<P> {
  return function WrappedComponent(props: P) {
    return (
      <FeatureErrorBoundary featureName={featureName}>
        <Component {...props} />
      </FeatureErrorBoundary>
    );
  };
}

export default FeatureErrorBoundary;
