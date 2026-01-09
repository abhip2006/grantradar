/**
 * Skeleton Loading Components
 *
 * A consistent loading skeleton system for GrandRadar frontend.
 * Uses smooth shimmer animations that respect reduced-motion preferences.
 *
 * Usage:
 * - Base components for building custom skeletons
 * - Page-specific skeletons for common loading states
 * - All components support className prop for customization
 */

import type { HTMLAttributes, ReactNode } from 'react';

/* ═══════════════════════════════════════════════════════════════════════════
   BASE SKELETON COMPONENTS
   ═══════════════════════════════════════════════════════════════════════════ */

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  /** Width of the skeleton. Can be any CSS width value */
  width?: string | number;
  /** Height of the skeleton. Can be any CSS height value */
  height?: string | number;
  /** Border radius. Defaults to 'sm' */
  rounded?: 'none' | 'sm' | 'md' | 'lg' | 'xl' | 'full';
  /** Whether to show the shimmer animation */
  animate?: boolean;
}

const roundedClasses = {
  none: 'rounded-none',
  sm: 'rounded',
  md: 'rounded-md',
  lg: 'rounded-lg',
  xl: 'rounded-xl',
  full: 'rounded-full',
};

/**
 * Base Skeleton component with shimmer animation.
 * Use this to create custom skeleton layouts.
 */
export function Skeleton({
  width,
  height,
  rounded = 'sm',
  animate = true,
  className = '',
  style,
  ...props
}: SkeletonProps) {
  return (
    <div
      className={`skeleton ${roundedClasses[rounded]} ${animate ? '' : 'skeleton-static'} ${className}`}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
        ...style,
      }}
      aria-hidden="true"
      role="presentation"
      {...props}
    />
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   TEXT SKELETON COMPONENTS
   ═══════════════════════════════════════════════════════════════════════════ */

interface SkeletonTextProps extends HTMLAttributes<HTMLDivElement> {
  /** Width of the text line. Defaults to '100%' */
  width?: string | number;
  /** Size variant affecting height */
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
}

const textSizeClasses = {
  xs: 'h-3',
  sm: 'h-4',
  md: 'h-5',
  lg: 'h-6',
  xl: 'h-8',
};

/**
 * Single line text skeleton.
 * Perfect for titles, labels, or single-line content.
 */
export function SkeletonText({
  width = '100%',
  size = 'md',
  className = '',
  style,
  ...props
}: SkeletonTextProps) {
  return (
    <div
      className={`skeleton ${textSizeClasses[size]} rounded ${className}`}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        ...style,
      }}
      aria-hidden="true"
      {...props}
    />
  );
}

interface SkeletonParagraphProps extends HTMLAttributes<HTMLDivElement> {
  /** Number of lines to show. Defaults to 3 */
  lines?: number;
  /** Gap between lines. Defaults to 2 (0.5rem) */
  gap?: number;
  /** Width of the last line. Defaults to '60%' */
  lastLineWidth?: string | number;
  /** Size variant for all lines */
  size?: 'xs' | 'sm' | 'md' | 'lg';
}

/**
 * Multi-line paragraph skeleton.
 * Shows multiple lines with the last line shorter for a natural look.
 */
export function SkeletonParagraph({
  lines = 3,
  gap = 2,
  lastLineWidth = '60%',
  size = 'sm',
  className = '',
  ...props
}: SkeletonParagraphProps) {
  return (
    <div className={`flex flex-col gap-${gap} ${className}`} aria-hidden="true" {...props}>
      {Array.from({ length: lines }).map((_, index) => (
        <SkeletonText
          key={index}
          size={size}
          width={index === lines - 1 ? lastLineWidth : '100%'}
        />
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   AVATAR SKELETON
   ═══════════════════════════════════════════════════════════════════════════ */

interface SkeletonAvatarProps extends HTMLAttributes<HTMLDivElement> {
  /** Size of the avatar. Defaults to 'md' */
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
}

const avatarSizeClasses = {
  xs: 'w-6 h-6',
  sm: 'w-8 h-8',
  md: 'w-10 h-10',
  lg: 'w-12 h-12',
  xl: 'w-16 h-16',
};

/**
 * Circular avatar skeleton.
 * Use for user avatars or circular icons.
 */
export function SkeletonAvatar({
  size = 'md',
  className = '',
  ...props
}: SkeletonAvatarProps) {
  return (
    <div
      className={`skeleton rounded-full ${avatarSizeClasses[size]} ${className}`}
      aria-hidden="true"
      {...props}
    />
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   CARD SKELETON
   ═══════════════════════════════════════════════════════════════════════════ */

interface SkeletonCardProps extends HTMLAttributes<HTMLDivElement> {
  /** Height of the card. Defaults to 'auto' */
  height?: string | number;
  /** Whether to show a header section */
  header?: boolean;
  /** Number of content lines */
  contentLines?: number;
  /** Whether to show action buttons at bottom */
  actions?: boolean;
  /** Children to render instead of default content */
  children?: ReactNode;
}

/**
 * Card skeleton with optional header, content lines, and actions.
 * Matches the app's card styling.
 */
export function SkeletonCard({
  height,
  header = true,
  contentLines = 2,
  actions = false,
  children,
  className = '',
  style,
  ...props
}: SkeletonCardProps) {
  return (
    <div
      className={`bg-[var(--gr-bg-card)] border border-[var(--gr-border-default)] rounded-xl p-6 ${className}`}
      style={{
        height: typeof height === 'number' ? `${height}px` : height,
        ...style,
      }}
      aria-hidden="true"
      {...props}
    >
      {children || (
        <>
          {header && (
            <div className="flex items-center gap-3 mb-4">
              <SkeletonAvatar size="lg" />
              <div className="flex-1">
                <SkeletonText width="75%" size="lg" className="mb-2" />
                <SkeletonText width="50%" size="sm" />
              </div>
            </div>
          )}
          {contentLines > 0 && (
            <SkeletonParagraph lines={contentLines} className="mb-4" />
          )}
          {actions && (
            <div className="flex gap-2 pt-4 border-t border-[var(--gr-border-subtle)]">
              <Skeleton width={80} height={32} rounded="md" />
              <Skeleton width={80} height={32} rounded="md" />
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   TABLE SKELETON
   ═══════════════════════════════════════════════════════════════════════════ */

interface SkeletonTableProps extends HTMLAttributes<HTMLDivElement> {
  /** Number of rows to show. Defaults to 5 */
  rows?: number;
  /** Number of columns. Defaults to 4 */
  columns?: number;
  /** Whether to show a header row */
  header?: boolean;
}

/**
 * Table skeleton with header and data rows.
 * Shows a structured table loading state.
 */
export function SkeletonTable({
  rows = 5,
  columns = 4,
  header = true,
  className = '',
  ...props
}: SkeletonTableProps) {
  const columnWidths = ['40%', '25%', '20%', '15%'];

  return (
    <div
      className={`bg-[var(--gr-bg-card)] border border-[var(--gr-border-default)] rounded-xl overflow-hidden ${className}`}
      aria-hidden="true"
      {...props}
    >
      {header && (
        <div className="flex items-center gap-4 px-6 py-4 bg-[var(--gr-bg-secondary)] border-b border-[var(--gr-border-subtle)]">
          {Array.from({ length: columns }).map((_, i) => (
            <SkeletonText
              key={i}
              width={columnWidths[i % columnWidths.length]}
              size="sm"
            />
          ))}
        </div>
      )}
      <div className="divide-y divide-[var(--gr-border-subtle)]">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div
            key={rowIndex}
            className="flex items-center gap-4 px-6 py-4"
            style={{ animationDelay: `${rowIndex * 0.05}s` }}
          >
            {Array.from({ length: columns }).map((_, colIndex) => (
              <SkeletonText
                key={colIndex}
                width={columnWidths[colIndex % columnWidths.length]}
                size="md"
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   CHART SKELETON
   ═══════════════════════════════════════════════════════════════════════════ */

interface SkeletonChartProps extends HTMLAttributes<HTMLDivElement> {
  /** Type of chart to simulate */
  type?: 'bar' | 'line' | 'pie' | 'area';
  /** Height of the chart. Defaults to 200 */
  height?: number;
}

/**
 * Chart skeleton with visual representation based on chart type.
 * Provides a realistic loading state for data visualizations.
 */
export function SkeletonChart({
  type = 'bar',
  height = 200,
  className = '',
  ...props
}: SkeletonChartProps) {
  return (
    <div
      className={`bg-[var(--gr-bg-card)] border border-[var(--gr-border-default)] rounded-xl p-6 ${className}`}
      aria-hidden="true"
      {...props}
    >
      {/* Chart title */}
      <SkeletonText width="40%" size="lg" className="mb-6" />

      {/* Chart area */}
      <div
        className="relative flex items-end gap-2"
        style={{ height: `${height}px` }}
      >
        {type === 'bar' && (
          <>
            {[65, 45, 80, 55, 90, 40, 70, 60].map((h, i) => (
              <div
                key={i}
                className="flex-1 skeleton rounded-t"
                style={{
                  height: `${h}%`,
                  animationDelay: `${i * 0.1}s`,
                }}
              />
            ))}
          </>
        )}

        {type === 'line' && (
          <div className="absolute inset-0 flex flex-col justify-between py-4">
            {/* Grid lines */}
            {[...Array(4)].map((_, i) => (
              <div key={i} className="w-full h-px bg-[var(--gr-border-subtle)]" />
            ))}
            {/* Line placeholder */}
            <div className="absolute inset-0 flex items-center justify-center">
              <Skeleton width="90%" height={4} rounded="full" />
            </div>
          </div>
        )}

        {type === 'pie' && (
          <div className="w-full flex items-center justify-center">
            <Skeleton
              width={height * 0.8}
              height={height * 0.8}
              rounded="full"
            />
          </div>
        )}

        {type === 'area' && (
          <div className="w-full h-full skeleton rounded-lg" />
        )}
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 mt-6">
        {['30%', '25%', '20%'].map((w, i) => (
          <div key={i} className="flex items-center gap-2">
            <Skeleton width={12} height={12} rounded="sm" />
            <SkeletonText width={w} size="xs" />
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   PAGE-SPECIFIC SKELETONS
   ═══════════════════════════════════════════════════════════════════════════ */

/**
 * Dashboard page loading skeleton.
 * Includes stats bar and grant card grid.
 */
export function DashboardSkeleton() {
  return (
    <div className="space-y-8" aria-label="Loading dashboard" role="status">
      {/* Stats Bar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="stat-card"
            style={{ animationDelay: `${i * 0.1}s` }}
          >
            <div className="flex items-start justify-between">
              <Skeleton width={40} height={40} rounded="xl" />
              <SkeletonText width={40} size="xs" />
            </div>
            <div className="mt-4">
              <SkeletonText width={60} size="xl" className="mb-2" />
              <SkeletonText width={100} size="sm" />
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <SkeletonCard className="!p-4" header={false}>
        <div className="flex flex-col lg:flex-row lg:items-center gap-4">
          <Skeleton height={44} className="flex-1 max-w-md" rounded="lg" />
          <div className="flex gap-2">
            {[80, 80, 80, 100].map((w, i) => (
              <Skeleton key={i} width={w} height={40} rounded="lg" />
            ))}
          </div>
        </div>
      </SkeletonCard>

      {/* Grant Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <GrantCardSkeleton key={i} delay={i} />
        ))}
      </div>
    </div>
  );
}

interface GrantCardSkeletonProps {
  delay?: number;
}

/**
 * Grant card loading skeleton.
 * Matches the GrantCard component layout.
 */
export function GrantCardSkeleton({ delay = 0 }: GrantCardSkeletonProps) {
  return (
    <div
      className="grant-card animate-fade-in-up"
      style={{ animationDelay: `${delay * 0.05}s` }}
      aria-hidden="true"
    >
      {/* Header with badges */}
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-3">
            <Skeleton width={70} height={24} rounded="full" />
            <Skeleton width={50} height={24} rounded="full" />
          </div>
          <SkeletonText width="90%" size="lg" className="mb-2" />
          <SkeletonText width="60%" size="md" />
        </div>
      </div>

      {/* Funder */}
      <div className="flex items-center gap-2 mb-3">
        <Skeleton width={16} height={16} rounded="sm" />
        <SkeletonText width="45%" size="sm" />
      </div>

      {/* Description */}
      <SkeletonParagraph lines={2} size="sm" className="mb-4" />

      {/* Meta info */}
      <div className="flex flex-wrap items-center gap-4 mb-4">
        <div className="flex items-center gap-1.5">
          <Skeleton width={16} height={16} rounded="sm" />
          <SkeletonText width={100} size="sm" />
        </div>
        <div className="flex items-center gap-1.5">
          <Skeleton width={16} height={16} rounded="sm" />
          <SkeletonText width={80} size="sm" />
        </div>
      </div>

      {/* Focus areas */}
      <div className="flex flex-wrap gap-1.5">
        {[60, 80, 50].map((w, i) => (
          <Skeleton key={i} width={w} height={24} rounded="md" />
        ))}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-2 mt-4 pt-4 border-t border-[var(--gr-border-subtle)]">
        <Skeleton width={70} height={32} rounded="md" />
        <Skeleton width={60} height={32} rounded="md" />
      </div>
    </div>
  );
}

/**
 * Kanban card loading skeleton.
 * Matches the KanbanCard component layout.
 */
export function KanbanCardSkeleton() {
  return (
    <div className="kanban-card" aria-hidden="true">
      {/* Title */}
      <div className="mb-3">
        <SkeletonText width="85%" size="sm" className="mb-1" />
        <SkeletonText width="60%" size="sm" />
      </div>

      {/* Agency badge */}
      <div className="mb-3">
        <Skeleton width={100} height={26} rounded="lg" />
      </div>

      {/* Progress bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1.5">
          <SkeletonText width={50} size="xs" />
          <SkeletonText width={30} size="xs" />
        </div>
        <Skeleton height={6} rounded="full" />
      </div>

      {/* Metadata row */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <Skeleton width={16} height={16} rounded="sm" />
          <SkeletonText width={30} size="xs" />
        </div>
        <div className="flex items-center gap-1.5">
          <Skeleton width={16} height={16} rounded="sm" />
          <SkeletonText width={45} size="xs" />
        </div>
      </div>

      {/* Assignees */}
      <div className="flex items-center gap-1 mt-3 pt-3 border-t border-gray-50">
        <div className="flex -space-x-2">
          {[1, 2].map((i) => (
            <SkeletonAvatar key={i} size="sm" className="border-2 border-white" />
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Analytics page loading skeleton.
 * Shows stats cards, charts, and metrics.
 */
export function AnalyticsSkeleton() {
  return (
    <div className="space-y-8" aria-label="Loading analytics" role="status">
      {/* Header */}
      <div className="analytics-header">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <SkeletonText width={256} size="xl" className="mb-3" />
          <SkeletonText width={384} size="md" />
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Tab bar */}
        <Skeleton height={56} className="mb-8" rounded="xl" />

        {/* Stats cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-8">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="stat-card-animated p-6"
              style={{ animationDelay: `${i * 0.1}s` }}
            >
              <div className="flex items-start justify-between mb-4">
                <Skeleton width={48} height={48} rounded="xl" />
                <SkeletonText width={60} size="sm" />
              </div>
              <SkeletonText width={80} size="xl" className="mb-2" />
              <SkeletonText width={120} size="sm" />
            </div>
          ))}
        </div>

        {/* Charts grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonChart type="bar" height={300} />
          <SkeletonChart type="line" height={300} />
        </div>
      </div>
    </div>
  );
}

/**
 * Grant detail page loading skeleton.
 * Shows hero section, content cards, and sidebar.
 */
export function GrantDetailSkeleton() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-8" aria-label="Loading grant details" role="status">
      {/* Back button */}
      <Skeleton width={96} height={40} rounded="xl" className="mb-8" />

      {/* Hero section */}
      <div className="bg-white rounded-2xl border border-[var(--gr-border-default)] p-8 mb-6">
        {/* Gradient accent bar */}
        <div className="h-1.5 skeleton rounded-full mb-6" />

        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-6 mb-6">
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-4">
              <Skeleton width={100} height={28} rounded="full" />
              <Skeleton width={70} height={28} rounded="full" />
            </div>
            <SkeletonText size="xl" width="75%" className="mb-4" />
            <div className="flex items-center gap-3">
              <Skeleton width={40} height={40} rounded="xl" />
              <div>
                <SkeletonText width={60} size="xs" className="mb-1" />
                <SkeletonText width={180} size="lg" />
              </div>
            </div>
          </div>
          {/* Match score placeholder */}
          <Skeleton width={80} height={80} rounded="xl" />
        </div>

        {/* Key metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="rounded-xl p-4 border border-[var(--gr-border-subtle)]">
              <div className="flex items-start gap-3">
                <Skeleton width={36} height={36} rounded="lg" />
                <div className="flex-1">
                  <SkeletonText width="60%" size="xs" className="mb-2" />
                  <SkeletonText width="80%" size="lg" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          <SkeletonCard header={false}>
            <div className="flex items-center gap-3 mb-4">
              <Skeleton width={36} height={36} rounded="lg" />
              <SkeletonText width={150} size="lg" />
            </div>
            <SkeletonParagraph lines={5} gap={3} />
          </SkeletonCard>

          {/* Eligibility */}
          <SkeletonCard header={false}>
            <div className="flex items-center gap-3 mb-4">
              <Skeleton width={36} height={36} rounded="lg" />
              <SkeletonText width={200} size="lg" />
            </div>
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-[var(--gr-gray-50)]">
                  <Skeleton width={20} height={20} rounded="full" />
                  <SkeletonText width="80%" size="md" />
                </div>
              ))}
            </div>
          </SkeletonCard>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quick actions */}
          <SkeletonCard header={false}>
            <SkeletonText width={120} size="lg" className="mb-4" />
            <div className="space-y-3">
              <Skeleton height={48} rounded="xl" />
              <Skeleton height={48} rounded="xl" />
              <Skeleton height={48} rounded="xl" />
            </div>
          </SkeletonCard>

          {/* Match score card */}
          <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-2xl border border-slate-200 p-6 text-center">
            <div className="flex justify-center mb-3">
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Skeleton key={i} width={20} height={20} rounded="sm" />
                ))}
              </div>
            </div>
            <SkeletonText width={60} size="xl" className="mx-auto mb-2" />
            <SkeletonText width={80} size="sm" className="mx-auto" />
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * List skeleton for simple list loading states.
 */
export function SkeletonList({
  items = 5,
  className = '',
}: {
  items?: number;
  className?: string;
}) {
  return (
    <div className={`space-y-3 ${className}`} aria-hidden="true">
      {Array.from({ length: items }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3"
          style={{ animationDelay: `${i * 0.05}s` }}
        >
          <SkeletonAvatar size="sm" />
          <div className="flex-1">
            <SkeletonText width="60%" size="md" className="mb-1" />
            <SkeletonText width="40%" size="sm" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Button skeleton for loading button states.
 */
export function SkeletonButton({
  size = 'md',
  width,
}: {
  size?: 'sm' | 'md' | 'lg';
  width?: string | number;
}) {
  const sizeClasses = {
    sm: 'h-8',
    md: 'h-10',
    lg: 'h-12',
  };

  return (
    <Skeleton
      width={width || (size === 'sm' ? 80 : size === 'lg' ? 140 : 100)}
      className={sizeClasses[size]}
      rounded="lg"
    />
  );
}

export default Skeleton;
