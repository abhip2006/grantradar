import { Fragment, useEffect, useMemo, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import {
  XMarkIcon,
  ArrowsRightLeftIcon,
  PlusIcon,
  MinusIcon,
  DocumentTextIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { useCompareVersions, useRestoreDocumentVersion } from '../../hooks/useComponents';
import type { DocumentVersion, DiffChange } from '../../types/components';

interface VersionDiffProps {
  isOpen: boolean;
  onClose: () => void;
  versionA: DocumentVersion | null;
  versionB: DocumentVersion | null;
  kanbanCardId?: string;
}

type DiffViewMode = 'unified' | 'split';

/**
 * Simple diff algorithm to compute line-by-line differences
 */
function computeSimpleDiff(textA: string, textB: string): DiffChange[] {
  const linesA = textA.split('\n');
  const linesB = textB.split('\n');
  const changes: DiffChange[] = [];

  // Use a simple LCS-based approach for visualization
  let indexA = 0;
  let indexB = 0;

  while (indexA < linesA.length || indexB < linesB.length) {
    const lineA = linesA[indexA];
    const lineB = linesB[indexB];

    if (indexA >= linesA.length) {
      // All remaining lines in B are additions
      changes.push({
        type: 'add',
        content: lineB,
        line_number_b: indexB + 1,
      });
      indexB++;
    } else if (indexB >= linesB.length) {
      // All remaining lines in A are removals
      changes.push({
        type: 'remove',
        content: lineA,
        line_number_a: indexA + 1,
      });
      indexA++;
    } else if (lineA === lineB) {
      // Lines match
      changes.push({
        type: 'unchanged',
        content: lineA,
        line_number_a: indexA + 1,
        line_number_b: indexB + 1,
      });
      indexA++;
      indexB++;
    } else {
      // Check if lineA appears later in B (removal)
      const lineAInB = linesB.slice(indexB + 1).findIndex((l) => l === lineA);
      // Check if lineB appears later in A (addition)
      const lineBInA = linesA.slice(indexA + 1).findIndex((l) => l === lineB);

      if (lineBInA !== -1 && (lineAInB === -1 || lineBInA < lineAInB)) {
        // lineA was removed
        changes.push({
          type: 'remove',
          content: lineA,
          line_number_a: indexA + 1,
        });
        indexA++;
      } else if (lineAInB !== -1) {
        // lineB was added
        changes.push({
          type: 'add',
          content: lineB,
          line_number_b: indexB + 1,
        });
        indexB++;
      } else {
        // Both lines changed - show as removal then addition
        changes.push({
          type: 'remove',
          content: lineA,
          line_number_a: indexA + 1,
        });
        changes.push({
          type: 'add',
          content: lineB,
          line_number_b: indexB + 1,
        });
        indexA++;
        indexB++;
      }
    }
  }

  return changes;
}

export function VersionDiff({
  isOpen,
  onClose,
  versionA,
  versionB,
  kanbanCardId,
}: VersionDiffProps) {
  const [viewMode, setViewMode] = useState<DiffViewMode>('unified');
  const compareVersions = useCompareVersions();
  const restoreVersion = useRestoreDocumentVersion();

  // Compute diff locally for immediate display
  const localDiff = useMemo(() => {
    if (!versionA || !versionB) return null;
    return computeSimpleDiff(versionA.content, versionB.content);
  }, [versionA, versionB]);

  // Also fetch from API for potentially better results
  useEffect(() => {
    if (isOpen && versionA && versionB) {
      compareVersions.mutate({
        versionAId: versionA.id,
        versionBId: versionB.id,
      });
    }
  }, [isOpen, versionA?.id, versionB?.id]);

  // Use API diff if available, otherwise local
  const diff = compareVersions.data?.changes || localDiff || [];
  const additions = diff.filter((c) => c.type === 'add').length;
  const deletions = diff.filter((c) => c.type === 'remove').length;

  const handleRestore = async (version: DocumentVersion) => {
    if (!kanbanCardId) return;
    if (!confirm(`Restore to version ${version.version_number}? This will create a new version.`)) {
      return;
    }

    try {
      await restoreVersion.mutateAsync({
        kanbanCardId,
        versionId: version.id,
      });
      onClose();
    } catch (error) {
      console.error('Failed to restore version:', error);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  if (!versionA || !versionB) return null;

  // Ensure versionA is older
  const [older, newer] =
    versionA.version_number < versionB.version_number
      ? [versionA, versionB]
      : [versionB, versionA];

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/25 backdrop-blur-sm" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-6xl transform overflow-hidden rounded-2xl bg-[var(--gr-bg-elevated)] shadow-[var(--gr-shadow-xl)] transition-all flex flex-col max-h-[90vh]">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-[var(--gr-border-subtle)]">
                  <div>
                    <Dialog.Title className="text-lg font-semibold text-[var(--gr-text-primary)]">
                      Compare Versions
                    </Dialog.Title>
                    <p className="mt-1 text-sm text-[var(--gr-text-secondary)]">
                      Version {older.version_number} vs Version {newer.version_number}
                    </p>
                  </div>
                  <button
                    onClick={onClose}
                    className="text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-primary)] transition-colors"
                  >
                    <XMarkIcon className="h-6 w-6" />
                  </button>
                </div>

                {/* Version Info Bar */}
                <div className="flex items-stretch border-b border-[var(--gr-border-subtle)] bg-[var(--gr-bg-secondary)]">
                  <div className="flex-1 p-4 border-r border-[var(--gr-border-subtle)]">
                    <div className="flex items-center gap-2 mb-1">
                      <DocumentTextIcon className="h-4 w-4 text-red-500" />
                      <span className="text-sm font-medium text-[var(--gr-text-primary)]">
                        Version {older.version_number}
                      </span>
                      {older.snapshot_name && (
                        <span className="text-xs text-[var(--gr-text-tertiary)]">
                          ({older.snapshot_name})
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[var(--gr-text-tertiary)]">
                      {formatDate(older.created_at)}
                      {older.created_by_name && ` by ${older.created_by_name}`}
                    </p>
                  </div>
                  <div className="flex items-center px-4">
                    <ArrowsRightLeftIcon className="h-5 w-5 text-[var(--gr-text-tertiary)]" />
                  </div>
                  <div className="flex-1 p-4 border-l border-[var(--gr-border-subtle)]">
                    <div className="flex items-center gap-2 mb-1">
                      <DocumentTextIcon className="h-4 w-4 text-green-500" />
                      <span className="text-sm font-medium text-[var(--gr-text-primary)]">
                        Version {newer.version_number}
                      </span>
                      {newer.snapshot_name && (
                        <span className="text-xs text-[var(--gr-text-tertiary)]">
                          ({newer.snapshot_name})
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[var(--gr-text-tertiary)]">
                      {formatDate(newer.created_at)}
                      {newer.created_by_name && ` by ${newer.created_by_name}`}
                    </p>
                  </div>
                </div>

                {/* Stats and View Toggle */}
                <div className="flex items-center justify-between px-6 py-3 border-b border-[var(--gr-border-subtle)]">
                  <div className="flex items-center gap-4 text-sm">
                    <span className="flex items-center gap-1 text-green-600">
                      <PlusIcon className="h-4 w-4" />
                      {additions} additions
                    </span>
                    <span className="flex items-center gap-1 text-red-600">
                      <MinusIcon className="h-4 w-4" />
                      {deletions} deletions
                    </span>
                  </div>
                  <div className="flex gap-1 p-1 bg-[var(--gr-bg-tertiary)] rounded-lg">
                    <button
                      onClick={() => setViewMode('unified')}
                      className={`px-3 py-1 text-sm rounded-md transition-colors ${
                        viewMode === 'unified'
                          ? 'bg-[var(--gr-bg-elevated)] text-[var(--gr-text-primary)] shadow-sm'
                          : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)]'
                      }`}
                    >
                      Unified
                    </button>
                    <button
                      onClick={() => setViewMode('split')}
                      className={`px-3 py-1 text-sm rounded-md transition-colors ${
                        viewMode === 'split'
                          ? 'bg-[var(--gr-bg-elevated)] text-[var(--gr-text-primary)] shadow-sm'
                          : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)]'
                      }`}
                    >
                      Split
                    </button>
                  </div>
                </div>

                {/* Diff Content */}
                <div className="flex-1 overflow-auto">
                  {viewMode === 'unified' ? (
                    <UnifiedDiffView diff={diff} />
                  ) : (
                    <SplitDiffView older={older} newer={newer} diff={diff} />
                  )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between p-6 border-t border-[var(--gr-border-subtle)] bg-[var(--gr-bg-secondary)]">
                  <div className="text-xs text-[var(--gr-text-tertiary)]">
                    {diff.length} line{diff.length !== 1 ? 's' : ''} changed
                  </div>
                  <div className="flex gap-3">
                    {kanbanCardId && (
                      <button
                        onClick={() => handleRestore(older)}
                        disabled={restoreVersion.isPending}
                        className="flex items-center gap-2 btn-secondary"
                      >
                        <ArrowPathIcon className="h-4 w-4" />
                        Restore v{older.version_number}
                      </button>
                    )}
                    <button onClick={onClose} className="btn-primary">
                      Close
                    </button>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}

/**
 * Unified diff view - shows all changes in a single column
 */
function UnifiedDiffView({ diff }: { diff: DiffChange[] }) {
  return (
    <div className="font-mono text-sm">
      {diff.map((change, index) => {
        let bgColor = '';
        let textColor = 'text-[var(--gr-text-primary)]';
        let prefix = ' ';
        let lineNumber = '';

        if (change.type === 'add') {
          bgColor = 'bg-green-50';
          textColor = 'text-green-800';
          prefix = '+';
          lineNumber = String(change.line_number_b || '');
        } else if (change.type === 'remove') {
          bgColor = 'bg-red-50';
          textColor = 'text-red-800';
          prefix = '-';
          lineNumber = String(change.line_number_a || '');
        } else {
          lineNumber = String(change.line_number_a || change.line_number_b || '');
        }

        return (
          <div key={index} className={`flex ${bgColor}`}>
            <div className="w-12 flex-shrink-0 px-2 py-0.5 text-right text-[var(--gr-text-tertiary)] border-r border-[var(--gr-border-subtle)] select-none">
              {lineNumber}
            </div>
            <div className={`w-6 flex-shrink-0 px-1 py-0.5 text-center ${textColor} select-none`}>
              {prefix}
            </div>
            <div className={`flex-1 px-2 py-0.5 ${textColor} whitespace-pre-wrap break-words`}>
              {change.content || '\u00A0'}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/**
 * Split diff view - shows old and new content side by side
 */
function SplitDiffView({
  older: _older,
  newer: _newer,
  diff,
}: {
  older: DocumentVersion;
  newer: DocumentVersion;
  diff: DiffChange[];
}) {
  // Build parallel arrays for split view
  const leftLines: Array<{ type: 'remove' | 'unchanged' | 'empty'; content: string; lineNum?: number }> = [];
  const rightLines: Array<{ type: 'add' | 'unchanged' | 'empty'; content: string; lineNum?: number }> = [];

  let leftLineNum = 1;
  let rightLineNum = 1;

  for (const change of diff) {
    if (change.type === 'unchanged') {
      leftLines.push({ type: 'unchanged', content: change.content, lineNum: leftLineNum++ });
      rightLines.push({ type: 'unchanged', content: change.content, lineNum: rightLineNum++ });
    } else if (change.type === 'remove') {
      leftLines.push({ type: 'remove', content: change.content, lineNum: leftLineNum++ });
      rightLines.push({ type: 'empty', content: '' });
    } else if (change.type === 'add') {
      leftLines.push({ type: 'empty', content: '' });
      rightLines.push({ type: 'add', content: change.content, lineNum: rightLineNum++ });
    }
  }

  const maxLines = Math.max(leftLines.length, rightLines.length);

  return (
    <div className="flex font-mono text-sm">
      {/* Left Side (Older) */}
      <div className="flex-1 border-r border-[var(--gr-border-default)]">
        {Array.from({ length: maxLines }, (_, i) => {
          const line = leftLines[i] || { type: 'empty', content: '' };
          let bgColor = '';
          let textColor = 'text-[var(--gr-text-primary)]';

          if (line.type === 'remove') {
            bgColor = 'bg-red-50';
            textColor = 'text-red-800';
          } else if (line.type === 'empty') {
            bgColor = 'bg-[var(--gr-bg-tertiary)]';
          }

          return (
            <div key={i} className={`flex ${bgColor}`}>
              <div className="w-10 flex-shrink-0 px-2 py-0.5 text-right text-[var(--gr-text-tertiary)] border-r border-[var(--gr-border-subtle)] select-none">
                {line.lineNum || ''}
              </div>
              <div className={`flex-1 px-2 py-0.5 ${textColor} whitespace-pre-wrap break-words`}>
                {line.content || '\u00A0'}
              </div>
            </div>
          );
        })}
      </div>

      {/* Right Side (Newer) */}
      <div className="flex-1">
        {Array.from({ length: maxLines }, (_, i) => {
          const line = rightLines[i] || { type: 'empty', content: '' };
          let bgColor = '';
          let textColor = 'text-[var(--gr-text-primary)]';

          if (line.type === 'add') {
            bgColor = 'bg-green-50';
            textColor = 'text-green-800';
          } else if (line.type === 'empty') {
            bgColor = 'bg-[var(--gr-bg-tertiary)]';
          }

          return (
            <div key={i} className={`flex ${bgColor}`}>
              <div className="w-10 flex-shrink-0 px-2 py-0.5 text-right text-[var(--gr-text-tertiary)] border-r border-[var(--gr-border-subtle)] select-none">
                {line.lineNum || ''}
              </div>
              <div className={`flex-1 px-2 py-0.5 ${textColor} whitespace-pre-wrap break-words`}>
                {line.content || '\u00A0'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default VersionDiff;
