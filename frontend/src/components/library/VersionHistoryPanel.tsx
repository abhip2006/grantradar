import { Fragment, useState } from 'react';
import { Dialog, Transition, Menu } from '@headlessui/react';
import {
  XMarkIcon,
  ClockIcon,
  EllipsisVerticalIcon,
  ArrowPathIcon,
  EyeIcon,
  TagIcon,
  ArrowsRightLeftIcon,
  TrashIcon,
  BookmarkIcon,
  PencilIcon,
  CheckIcon,
} from '@heroicons/react/24/outline';
import {
  useDocumentVersions,
  useRestoreDocumentVersion,
  useDeleteVersion,
  useRenameSnapshot,
  useCreateSnapshot,
} from '../../hooks/useComponents';
import type { DocumentVersion } from '../../types/components';

interface VersionHistoryPanelProps {
  isOpen: boolean;
  onClose: () => void;
  kanbanCardId: string;
  section: string;
  onCompare?: (versionA: DocumentVersion, versionB: DocumentVersion) => void;
  onPreview?: (version: DocumentVersion) => void;
}

export function VersionHistoryPanel({
  isOpen,
  onClose,
  kanbanCardId,
  section,
  onCompare,
  onPreview,
}: VersionHistoryPanelProps) {
  const [selectedVersions, setSelectedVersions] = useState<string[]>([]);
  const [editingSnapshot, setEditingSnapshot] = useState<string | null>(null);
  const [snapshotName, setSnapshotName] = useState('');
  const [createSnapshotMode, setCreateSnapshotMode] = useState(false);
  const [newSnapshotName, setNewSnapshotName] = useState('');

  const { data: versionsData, isLoading } = useDocumentVersions(kanbanCardId, section);
  const restoreVersion = useRestoreDocumentVersion();
  const deleteVersion = useDeleteVersion();
  const renameSnapshot = useRenameSnapshot();
  const createSnapshot = useCreateSnapshot();

  const versions = versionsData?.items || [];

  const handleVersionSelect = (versionId: string) => {
    if (selectedVersions.includes(versionId)) {
      setSelectedVersions(selectedVersions.filter((id) => id !== versionId));
    } else if (selectedVersions.length < 2) {
      setSelectedVersions([...selectedVersions, versionId]);
    } else {
      // Replace oldest selection
      setSelectedVersions([selectedVersions[1], versionId]);
    }
  };

  const handleCompare = () => {
    if (selectedVersions.length !== 2 || !onCompare) return;

    const versionA = versions.find((v) => v.id === selectedVersions[0]);
    const versionB = versions.find((v) => v.id === selectedVersions[1]);

    if (versionA && versionB) {
      onCompare(versionA, versionB);
    }
  };

  const handleRestore = async (version: DocumentVersion) => {
    if (!confirm(`Restore to version ${version.version_number}? This will create a new version.`)) {
      return;
    }

    try {
      await restoreVersion.mutateAsync({
        kanbanCardId,
        versionId: version.id,
      });
    } catch (error) {
      console.error('Failed to restore version:', error);
    }
  };

  const handleDelete = async (version: DocumentVersion) => {
    if (!confirm(`Delete version ${version.version_number}? This cannot be undone.`)) {
      return;
    }

    try {
      await deleteVersion.mutateAsync({
        versionId: version.id,
        kanbanCardId,
      });
    } catch (error) {
      console.error('Failed to delete version:', error);
    }
  };

  const handleStartRename = (version: DocumentVersion) => {
    setEditingSnapshot(version.id);
    setSnapshotName(version.snapshot_name || '');
  };

  const handleSaveRename = async (version: DocumentVersion) => {
    if (!snapshotName.trim()) {
      setEditingSnapshot(null);
      return;
    }

    try {
      await renameSnapshot.mutateAsync({
        versionId: version.id,
        snapshotName: snapshotName.trim(),
        kanbanCardId,
      });
      setEditingSnapshot(null);
    } catch (error) {
      console.error('Failed to rename snapshot:', error);
    }
  };

  const handleCreateSnapshot = async () => {
    if (!newSnapshotName.trim()) return;

    try {
      await createSnapshot.mutateAsync({
        kanbanCardId,
        section,
        snapshotName: newSnapshotName.trim(),
      });
      setNewSnapshotName('');
      setCreateSnapshotMode(false);
    } catch (error) {
      console.error('Failed to create snapshot:', error);
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

  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(dateString);
  };

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
              enterFrom="opacity-0 translate-x-full"
              enterTo="opacity-100 translate-x-0"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-x-0"
              leaveTo="opacity-0 translate-x-full"
            >
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-[var(--gr-bg-elevated)] shadow-[var(--gr-shadow-xl)] transition-all flex flex-col max-h-[90vh]">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-[var(--gr-border-subtle)]">
                  <div>
                    <Dialog.Title className="text-lg font-semibold text-[var(--gr-text-primary)]">
                      Version History
                    </Dialog.Title>
                    <p className="mt-1 text-sm text-[var(--gr-text-secondary)]">
                      {section} section
                    </p>
                  </div>
                  <button
                    onClick={onClose}
                    className="text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-primary)] transition-colors"
                  >
                    <XMarkIcon className="h-6 w-6" />
                  </button>
                </div>

                {/* Create Snapshot */}
                <div className="p-4 border-b border-[var(--gr-border-subtle)] bg-[var(--gr-bg-secondary)]">
                  {createSnapshotMode ? (
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={newSnapshotName}
                        onChange={(e) => setNewSnapshotName(e.target.value)}
                        placeholder="Snapshot name..."
                        autoFocus
                        className="flex-1 px-3 py-2 text-sm border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] placeholder:text-[var(--gr-text-tertiary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleCreateSnapshot();
                          if (e.key === 'Escape') setCreateSnapshotMode(false);
                        }}
                      />
                      <button
                        onClick={handleCreateSnapshot}
                        disabled={!newSnapshotName.trim() || createSnapshot.isPending}
                        className="btn-primary text-sm px-3"
                      >
                        {createSnapshot.isPending ? '...' : 'Save'}
                      </button>
                      <button
                        onClick={() => setCreateSnapshotMode(false)}
                        className="btn-secondary text-sm px-3"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setCreateSnapshotMode(true)}
                      className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-[var(--gr-blue-600)] hover:bg-[var(--gr-blue-50)] rounded-lg transition-colors"
                    >
                      <BookmarkIcon className="h-4 w-4" />
                      Create Named Snapshot
                    </button>
                  )}
                </div>

                {/* Compare Button */}
                {selectedVersions.length === 2 && onCompare && (
                  <div className="p-4 border-b border-[var(--gr-border-subtle)] bg-[var(--gr-blue-50)]">
                    <button
                      onClick={handleCompare}
                      className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-[var(--gr-blue-700)] bg-[var(--gr-blue-100)] hover:bg-[var(--gr-blue-200)] rounded-lg transition-colors"
                    >
                      <ArrowsRightLeftIcon className="h-4 w-4" />
                      Compare Selected Versions
                    </button>
                  </div>
                )}

                {/* Version List */}
                <div className="flex-1 overflow-y-auto p-4">
                  {isLoading ? (
                    <div className="flex items-center justify-center py-12">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--gr-blue-600)]"></div>
                    </div>
                  ) : versions.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                      <ClockIcon className="h-12 w-12 text-[var(--gr-text-tertiary)] mb-4" />
                      <h3 className="text-sm font-medium text-[var(--gr-text-primary)]">
                        No versions yet
                      </h3>
                      <p className="mt-1 text-sm text-[var(--gr-text-secondary)]">
                        Versions will appear here as you make changes
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {versions.map((version, index) => {
                        const isSelected = selectedVersions.includes(version.id);
                        const isLatest = index === 0;

                        return (
                          <div
                            key={version.id}
                            className={`
                              relative p-4 rounded-xl border-2 transition-all
                              ${
                                isSelected
                                  ? 'border-[var(--gr-blue-500)] bg-[var(--gr-blue-50)]'
                                  : 'border-[var(--gr-border-subtle)] hover:border-[var(--gr-border-default)] bg-[var(--gr-bg-elevated)]'
                              }
                            `}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  {/* Selection Checkbox */}
                                  {onCompare && (
                                    <button
                                      onClick={() => handleVersionSelect(version.id)}
                                      className={`
                                        w-5 h-5 rounded border-2 flex items-center justify-center transition-colors
                                        ${
                                          isSelected
                                            ? 'border-[var(--gr-blue-500)] bg-[var(--gr-blue-500)]'
                                            : 'border-[var(--gr-border-default)] hover:border-[var(--gr-blue-400)]'
                                        }
                                      `}
                                    >
                                      {isSelected && <CheckIcon className="h-3 w-3 text-white" />}
                                    </button>
                                  )}

                                  <span className="text-sm font-medium text-[var(--gr-text-primary)]">
                                    Version {version.version_number}
                                  </span>
                                  {isLatest && (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                                      Current
                                    </span>
                                  )}
                                </div>

                                {/* Snapshot Name */}
                                {editingSnapshot === version.id ? (
                                  <div className="flex gap-2 mb-2">
                                    <input
                                      type="text"
                                      value={snapshotName}
                                      onChange={(e) => setSnapshotName(e.target.value)}
                                      className="flex-1 px-2 py-1 text-sm border border-[var(--gr-border-default)] rounded bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)]"
                                      autoFocus
                                      onKeyDown={(e) => {
                                        if (e.key === 'Enter') handleSaveRename(version);
                                        if (e.key === 'Escape') setEditingSnapshot(null);
                                      }}
                                    />
                                    <button
                                      onClick={() => handleSaveRename(version)}
                                      className="text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-700)]"
                                    >
                                      <CheckIcon className="h-4 w-4" />
                                    </button>
                                  </div>
                                ) : version.snapshot_name ? (
                                  <div className="flex items-center gap-1 mb-2">
                                    <TagIcon className="h-3.5 w-3.5 text-[var(--gr-text-tertiary)]" />
                                    <span className="text-xs text-[var(--gr-text-secondary)]">
                                      {version.snapshot_name}
                                    </span>
                                  </div>
                                ) : null}

                                <div className="flex items-center gap-3 text-xs text-[var(--gr-text-tertiary)]">
                                  <span title={formatDate(version.created_at)}>
                                    {formatRelativeTime(version.created_at)}
                                  </span>
                                  {version.created_by_name && (
                                    <span>by {version.created_by_name}</span>
                                  )}
                                </div>
                              </div>

                              {/* Actions Menu */}
                              <Menu as="div" className="relative">
                                <Menu.Button className="p-1 text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-tertiary)] rounded-lg transition-colors">
                                  <EllipsisVerticalIcon className="h-5 w-5" />
                                </Menu.Button>
                                <Transition
                                  as={Fragment}
                                  enter="transition ease-out duration-100"
                                  enterFrom="transform opacity-0 scale-95"
                                  enterTo="transform opacity-100 scale-100"
                                  leave="transition ease-in duration-75"
                                  leaveFrom="transform opacity-100 scale-100"
                                  leaveTo="transform opacity-0 scale-95"
                                >
                                  <Menu.Items className="absolute right-0 mt-1 w-40 origin-top-right bg-[var(--gr-bg-elevated)] border border-[var(--gr-border-default)] rounded-lg shadow-[var(--gr-shadow-lg)] py-1 z-10">
                                    {onPreview && (
                                      <Menu.Item>
                                        {({ active }) => (
                                          <button
                                            onClick={() => onPreview(version)}
                                            className={`${
                                              active ? 'bg-[var(--gr-bg-tertiary)]' : ''
                                            } flex w-full items-center gap-2 px-3 py-2 text-sm text-[var(--gr-text-primary)]`}
                                          >
                                            <EyeIcon className="h-4 w-4" />
                                            Preview
                                          </button>
                                        )}
                                      </Menu.Item>
                                    )}
                                    {!isLatest && (
                                      <Menu.Item>
                                        {({ active }) => (
                                          <button
                                            onClick={() => handleRestore(version)}
                                            className={`${
                                              active ? 'bg-[var(--gr-bg-tertiary)]' : ''
                                            } flex w-full items-center gap-2 px-3 py-2 text-sm text-[var(--gr-text-primary)]`}
                                          >
                                            <ArrowPathIcon className="h-4 w-4" />
                                            Restore
                                          </button>
                                        )}
                                      </Menu.Item>
                                    )}
                                    <Menu.Item>
                                      {({ active }) => (
                                        <button
                                          onClick={() => handleStartRename(version)}
                                          className={`${
                                            active ? 'bg-[var(--gr-bg-tertiary)]' : ''
                                          } flex w-full items-center gap-2 px-3 py-2 text-sm text-[var(--gr-text-primary)]`}
                                        >
                                          <PencilIcon className="h-4 w-4" />
                                          {version.snapshot_name ? 'Rename' : 'Add Name'}
                                        </button>
                                      )}
                                    </Menu.Item>
                                    {!isLatest && (
                                      <>
                                        <div className="my-1 border-t border-[var(--gr-border-subtle)]" />
                                        <Menu.Item>
                                          {({ active }) => (
                                            <button
                                              onClick={() => handleDelete(version)}
                                              className={`${
                                                active ? 'bg-red-50' : ''
                                              } flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600`}
                                            >
                                              <TrashIcon className="h-4 w-4" />
                                              Delete
                                            </button>
                                          )}
                                        </Menu.Item>
                                      </>
                                    )}
                                  </Menu.Items>
                                </Transition>
                              </Menu>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-[var(--gr-border-subtle)] bg-[var(--gr-bg-secondary)]">
                  <div className="flex items-center justify-between text-xs text-[var(--gr-text-tertiary)]">
                    <span>{versions.length} version{versions.length !== 1 ? 's' : ''}</span>
                    {selectedVersions.length > 0 && onCompare && (
                      <span>{selectedVersions.length}/2 selected for comparison</span>
                    )}
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

export default VersionHistoryPanel;
