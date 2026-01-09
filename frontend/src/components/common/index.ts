// Error Boundaries
export {
  ErrorBoundary,
  DefaultErrorFallback,
  PageErrorBoundary,
  ComponentErrorBoundary,
  withErrorBoundary,
  type FallbackProps,
  type FallbackRender,
  type ErrorBoundaryProps,
} from './ErrorBoundary';

// Legacy Feature Error Boundary (for backwards compatibility)
export { FeatureErrorBoundary, withFeatureErrorBoundary } from './FeatureErrorBoundary';

// Toast
export { ToastContainer } from './Toast';

// Skeleton loading components
export {
  Skeleton,
  SkeletonText,
  SkeletonParagraph,
  SkeletonAvatar,
  SkeletonCard,
  SkeletonTable,
  SkeletonChart,
  // Page-specific skeletons
  DashboardSkeleton,
  GrantCardSkeleton,
  KanbanCardSkeleton,
  AnalyticsSkeleton,
  GrantDetailSkeleton,
  SkeletonList,
  SkeletonButton,
} from './Skeleton';
