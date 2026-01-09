import React, { Fragment, useState, useMemo } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import {
  XMarkIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  FolderIcon,
  ClipboardDocumentIcon,
  CheckIcon,
} from '@heroicons/react/24/outline';
import {
  useDocumentComponents,
  useDeleteComponent,
  useDuplicateComponent,
} from '../../hooks/useComponents';
import { ComponentCard } from './ComponentCard';
import { ComponentEditor } from './ComponentEditor';
import { ComponentCategoryList } from './ComponentCategoryTabs';
import type { DocumentComponent, ComponentCategory } from '../../types/components';
import { COMPONENT_CATEGORY_CONFIG } from '../../types/components';

interface ComponentLibraryPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ComponentLibraryPanel = React.memo(function ComponentLibraryPanel({ isOpen, onClose }: ComponentLibraryPanelProps) {
  const [selectedCategory, setSelectedCategory] = useState<ComponentCategory | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingComponent, setEditingComponent] = useState<DocumentComponent | null>(null);
  const [previewComponent, setPreviewComponent] = useState<DocumentComponent | null>(null);
  const [copied, setCopied] = useState(false);

  // Fetch all components first, then filter
  const { data: allComponentsData, isLoading } = useDocumentComponents();

  const deleteComponent = useDeleteComponent();
  const duplicateComponent = useDuplicateComponent();

  // Filter components based on category and search
  const filteredComponents = useMemo(() => {
    if (!allComponentsData?.items) return [];

    let filtered = allComponentsData.items;

    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter((c) => c.category === selectedCategory);
    }

    // Filter by search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.name.toLowerCase().includes(query) ||
          c.content.toLowerCase().includes(query) ||
          c.metadata?.tags?.some((tag) => tag.toLowerCase().includes(query)) ||
          c.metadata?.funder?.toLowerCase().includes(query) ||
          c.metadata?.mechanism?.toLowerCase().includes(query)
      );
    }

    return filtered;
  }, [allComponentsData?.items, selectedCategory, searchQuery]);

  // Calculate category counts
  const categoryCounts = useMemo(() => {
    if (!allComponentsData?.items) return undefined;

    const counts: Record<ComponentCategory | 'all', number> = {
      all: allComponentsData.items.length,
      facilities: 0,
      equipment: 0,
      biosketch: 0,
      boilerplate: 0,
      human_subjects: 0,
      vertebrate_animals: 0,
      institution: 0,
      other: 0,
    };

    allComponentsData.items.forEach((component) => {
      if (component.category in counts) {
        counts[component.category as ComponentCategory]++;
      }
    });

    return counts;
  }, [allComponentsData?.items]);

  const handleCreateNew = () => {
    setEditingComponent(null);
    setEditorOpen(true);
  };

  const handleEdit = (component: DocumentComponent) => {
    setEditingComponent(component);
    setEditorOpen(true);
  };

  const handleDelete = async (component: DocumentComponent) => {
    if (!confirm(`Delete "${component.name}"? This cannot be undone.`)) {
      return;
    }

    try {
      await deleteComponent.mutateAsync(component.id);
    } catch (error) {
      console.error('Failed to delete component:', error);
    }
  };

  const handleDuplicate = async (component: DocumentComponent) => {
    try {
      await duplicateComponent.mutateAsync({
        id: component.id,
        newName: `${component.name} (Copy)`,
      });
    } catch (error) {
      console.error('Failed to duplicate component:', error);
    }
  };

  const handlePreview = (component: DocumentComponent) => {
    setPreviewComponent(component);
  };

  const handleCopyContent = (content: string) => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClosePreview = () => {
    setPreviewComponent(null);
    setCopied(false);
  };

  return (
    <>
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
                        Component Library
                      </Dialog.Title>
                      <p className="mt-1 text-sm text-[var(--gr-text-secondary)]">
                        Manage reusable document components for your grant applications
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <button onClick={handleCreateNew} className="btn-primary flex items-center gap-2">
                        <PlusIcon className="h-4 w-4" />
                        New Component
                      </button>
                      <button
                        onClick={onClose}
                        className="text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-primary)] transition-colors"
                      >
                        <XMarkIcon className="h-6 w-6" />
                      </button>
                    </div>
                  </div>

                  {/* Content */}
                  <div className="flex flex-1 overflow-hidden">
                    {/* Sidebar */}
                    <div className="w-64 border-r border-[var(--gr-border-subtle)] bg-[var(--gr-bg-secondary)] p-4 overflow-y-auto">
                      <ComponentCategoryList
                        selectedCategory={selectedCategory}
                        onCategoryChange={setSelectedCategory}
                        categoryCounts={categoryCounts}
                      />
                    </div>

                    {/* Main Content */}
                    <div className="flex-1 flex flex-col overflow-hidden">
                      {/* Search Bar */}
                      <div className="p-4 border-b border-[var(--gr-border-subtle)]">
                        <div className="relative">
                          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-[var(--gr-text-tertiary)]" />
                          <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Search components by name, content, tags, funder..."
                            className="w-full pl-10 pr-4 py-2 border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] placeholder:text-[var(--gr-text-tertiary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]"
                          />
                        </div>
                      </div>

                      {/* Components Grid */}
                      <div className="flex-1 overflow-y-auto p-4">
                        {isLoading ? (
                          <div className="flex items-center justify-center py-12">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--gr-blue-600)]"></div>
                          </div>
                        ) : filteredComponents.length === 0 ? (
                          <div className="flex flex-col items-center justify-center py-12 text-center">
                            <FolderIcon className="h-12 w-12 text-[var(--gr-text-tertiary)] mb-4" />
                            <h3 className="text-sm font-medium text-[var(--gr-text-primary)]">
                              {searchQuery
                                ? 'No components found'
                                : selectedCategory === 'all'
                                ? 'No components yet'
                                : `No ${COMPONENT_CATEGORY_CONFIG[selectedCategory]?.label.toLowerCase()} components`}
                            </h3>
                            <p className="mt-1 text-sm text-[var(--gr-text-secondary)] max-w-sm">
                              {searchQuery
                                ? 'Try adjusting your search or category filter'
                                : 'Create your first reusable component to get started'}
                            </p>
                            {!searchQuery && (
                              <button
                                onClick={handleCreateNew}
                                className="mt-4 btn-primary flex items-center gap-2"
                              >
                                <PlusIcon className="h-4 w-4" />
                                Create Component
                              </button>
                            )}
                          </div>
                        ) : (
                          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {filteredComponents.map((component) => (
                              <ComponentCard
                                key={component.id}
                                component={component}
                                onEdit={handleEdit}
                                onDelete={handleDelete}
                                onDuplicate={handleDuplicate}
                                onPreview={handlePreview}
                              />
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Footer Stats */}
                      <div className="px-4 py-3 border-t border-[var(--gr-border-subtle)] bg-[var(--gr-bg-secondary)]">
                        <div className="flex items-center justify-between text-xs text-[var(--gr-text-tertiary)]">
                          <span>
                            {filteredComponents.length} component
                            {filteredComponents.length !== 1 ? 's' : ''}
                            {selectedCategory !== 'all' &&
                              ` in ${COMPONENT_CATEGORY_CONFIG[selectedCategory]?.label}`}
                            {searchQuery && ` matching "${searchQuery}"`}
                          </span>
                          <span>{allComponentsData?.total || 0} total</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </Dialog>
      </Transition>

      {/* Component Editor Modal */}
      <ComponentEditor
        isOpen={editorOpen}
        onClose={() => {
          setEditorOpen(false);
          setEditingComponent(null);
        }}
        component={editingComponent}
        defaultCategory={selectedCategory === 'all' ? undefined : selectedCategory}
      />

      {/* Preview Modal */}
      <Transition appear show={!!previewComponent} as={Fragment}>
        <Dialog as="div" className="relative z-50" onClose={handleClosePreview}>
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
                <Dialog.Panel className="w-full max-w-3xl transform overflow-hidden rounded-2xl bg-[var(--gr-bg-elevated)] shadow-[var(--gr-shadow-xl)] transition-all">
                  {previewComponent && (
                    <>
                      {/* Header */}
                      <div className="flex items-center justify-between p-6 border-b border-[var(--gr-border-subtle)]">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[var(--gr-bg-tertiary)] text-[var(--gr-text-secondary)]">
                              {COMPONENT_CATEGORY_CONFIG[previewComponent.category as ComponentCategory]?.label}
                            </span>
                            <span className="text-xs text-[var(--gr-text-tertiary)]">
                              v{previewComponent.version}
                            </span>
                          </div>
                          <Dialog.Title className="text-lg font-semibold text-[var(--gr-text-primary)]">
                            {previewComponent.name}
                          </Dialog.Title>
                        </div>
                        <button
                          onClick={handleClosePreview}
                          className="text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-primary)] transition-colors"
                        >
                          <XMarkIcon className="h-6 w-6" />
                        </button>
                      </div>

                      {/* Content */}
                      <div className="p-6 max-h-[60vh] overflow-y-auto">
                        <div className="bg-[var(--gr-bg-secondary)] rounded-lg p-4 border border-[var(--gr-border-subtle)]">
                          <pre className="whitespace-pre-wrap text-sm text-[var(--gr-text-primary)] font-sans">
                            {previewComponent.content}
                          </pre>
                        </div>

                        {/* Metadata */}
                        {(previewComponent.metadata?.funder ||
                          previewComponent.metadata?.mechanism ||
                          previewComponent.metadata?.tags?.length) && (
                          <div className="mt-4 pt-4 border-t border-[var(--gr-border-subtle)]">
                            <h4 className="text-xs font-medium text-[var(--gr-text-secondary)] uppercase tracking-wider mb-2">
                              Metadata
                            </h4>
                            <div className="flex flex-wrap gap-4 text-sm">
                              {previewComponent.metadata.funder && (
                                <div>
                                  <span className="text-[var(--gr-text-tertiary)]">Funder:</span>{' '}
                                  <span className="text-[var(--gr-text-primary)]">
                                    {previewComponent.metadata.funder}
                                  </span>
                                </div>
                              )}
                              {previewComponent.metadata.mechanism && (
                                <div>
                                  <span className="text-[var(--gr-text-tertiary)]">Mechanism:</span>{' '}
                                  <span className="text-[var(--gr-text-primary)]">
                                    {previewComponent.metadata.mechanism}
                                  </span>
                                </div>
                              )}
                              {previewComponent.metadata.word_limit && (
                                <div>
                                  <span className="text-[var(--gr-text-tertiary)]">Word Limit:</span>{' '}
                                  <span className="text-[var(--gr-text-primary)]">
                                    {previewComponent.metadata.word_limit}
                                  </span>
                                </div>
                              )}
                            </div>
                            {previewComponent.metadata.tags && previewComponent.metadata.tags.length > 0 && (
                              <div className="mt-2 flex flex-wrap gap-1">
                                {previewComponent.metadata.tags.map((tag, index) => (
                                  <span
                                    key={index}
                                    className="inline-flex px-2 py-0.5 rounded text-xs bg-[var(--gr-bg-tertiary)] text-[var(--gr-text-secondary)]"
                                  >
                                    {tag}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Footer */}
                      <div className="flex items-center justify-between p-6 border-t border-[var(--gr-border-subtle)] bg-[var(--gr-bg-secondary)]">
                        <div className="text-xs text-[var(--gr-text-tertiary)]">
                          {previewComponent.content.split(/\s+/).filter(Boolean).length} words |
                          Last updated {new Date(previewComponent.updated_at).toLocaleDateString()}
                        </div>
                        <div className="flex gap-3">
                          <button
                            onClick={() => handleCopyContent(previewComponent.content)}
                            className="btn-secondary flex items-center gap-2"
                          >
                            {copied ? (
                              <>
                                <CheckIcon className="h-4 w-4 text-green-500" />
                                Copied!
                              </>
                            ) : (
                              <>
                                <ClipboardDocumentIcon className="h-4 w-4" />
                                Copy Content
                              </>
                            )}
                          </button>
                          <button
                            onClick={() => {
                              handleClosePreview();
                              handleEdit(previewComponent);
                            }}
                            className="btn-primary"
                          >
                            Edit Component
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </Dialog>
      </Transition>
    </>
  );
});

export default ComponentLibraryPanel;
