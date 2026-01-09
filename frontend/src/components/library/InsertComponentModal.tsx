import { Fragment, useState, useMemo } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import {
  XMarkIcon,
  MagnifyingGlassIcon,
  DocumentTextIcon,
  ClipboardDocumentCheckIcon,
  CheckIcon,
} from '@heroicons/react/24/outline';
import { useDocumentComponents, useInsertComponent } from '../../hooks/useComponents';
import { ComponentCategoryTabs } from './ComponentCategoryTabs';
import type { DocumentComponent, ComponentCategory } from '../../types/components';
import { COMPONENT_CATEGORY_CONFIG } from '../../types/components';

interface InsertComponentModalProps {
  isOpen: boolean;
  onClose: () => void;
  kanbanCardId: string;
  section: string;
  onInsert?: (component: DocumentComponent, content: string) => void;
}

export function InsertComponentModal({
  isOpen,
  onClose,
  kanbanCardId,
  section,
  onInsert,
}: InsertComponentModalProps) {
  const [selectedCategory, setSelectedCategory] = useState<ComponentCategory | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedComponent, setSelectedComponent] = useState<DocumentComponent | null>(null);
  const [insertPosition, setInsertPosition] = useState<'start' | 'end' | 'cursor'>('end');
  const [copied, setCopied] = useState(false);

  const { data: componentsData, isLoading } = useDocumentComponents(
    selectedCategory === 'all' ? undefined : selectedCategory
  );
  const insertComponent = useInsertComponent();

  const filteredComponents = useMemo(() => {
    if (!componentsData?.items) return [];

    let filtered = componentsData.items;

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.name.toLowerCase().includes(query) ||
          c.content.toLowerCase().includes(query) ||
          c.metadata?.tags?.some((tag) => tag.toLowerCase().includes(query))
      );
    }

    return filtered;
  }, [componentsData?.items, searchQuery]);

  const categoryCounts = useMemo(() => {
    if (!componentsData?.items) return undefined;

    const counts: Record<ComponentCategory | 'all', number> = {
      all: componentsData.items.length,
      facilities: 0,
      equipment: 0,
      biosketch: 0,
      boilerplate: 0,
      human_subjects: 0,
      vertebrate_animals: 0,
      institution: 0,
      other: 0,
    };

    componentsData.items.forEach((component) => {
      if (component.category in counts) {
        counts[component.category as ComponentCategory]++;
      }
    });

    return counts;
  }, [componentsData?.items]);

  const handleInsert = async () => {
    if (!selectedComponent) return;

    try {
      // If onInsert callback is provided, use it (for direct insertion into editor)
      if (onInsert) {
        onInsert(selectedComponent, selectedComponent.content);
        handleClose();
        return;
      }

      // Otherwise, use the API to record the insertion
      await insertComponent.mutateAsync({
        component_id: selectedComponent.id,
        kanban_card_id: kanbanCardId,
        section,
        position: insertPosition,
      });

      handleClose();
    } catch (error) {
      console.error('Failed to insert component:', error);
    }
  };

  const handleCopyContent = () => {
    if (!selectedComponent) return;

    navigator.clipboard.writeText(selectedComponent.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClose = () => {
    setSelectedComponent(null);
    setSearchQuery('');
    setSelectedCategory('all');
    setCopied(false);
    onClose();
  };

  const truncateContent = (content: string, maxLength: number = 200) => {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength).trim() + '...';
  };

  const getWordCount = (content: string) => {
    return content.split(/\s+/).filter(Boolean).length;
  };

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={handleClose}>
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
              <Dialog.Panel className="w-full max-w-5xl transform overflow-hidden rounded-2xl bg-[var(--gr-bg-elevated)] shadow-[var(--gr-shadow-xl)] transition-all">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-[var(--gr-border-subtle)]">
                  <div>
                    <Dialog.Title className="text-lg font-semibold text-[var(--gr-text-primary)]">
                      Insert Component
                    </Dialog.Title>
                    <p className="mt-1 text-sm text-[var(--gr-text-secondary)]">
                      Select a reusable component to insert into your document
                    </p>
                  </div>
                  <button
                    onClick={handleClose}
                    className="text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-primary)] transition-colors"
                  >
                    <XMarkIcon className="h-6 w-6" />
                  </button>
                </div>

                {/* Search and Filters */}
                <div className="p-4 border-b border-[var(--gr-border-subtle)] bg-[var(--gr-bg-secondary)]">
                  <div className="relative mb-4">
                    <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-[var(--gr-text-tertiary)]" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search components by name, content, or tags..."
                      className="w-full pl-10 pr-4 py-2 border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] placeholder:text-[var(--gr-text-tertiary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]"
                    />
                  </div>
                  <ComponentCategoryTabs
                    selectedCategory={selectedCategory}
                    onCategoryChange={setSelectedCategory}
                    categoryCounts={categoryCounts}
                  />
                </div>

                {/* Content */}
                <div className="flex max-h-[calc(100vh-350px)]">
                  {/* Component List */}
                  <div className="flex-1 overflow-y-auto p-4">
                    {isLoading ? (
                      <div className="flex items-center justify-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--gr-blue-600)]"></div>
                      </div>
                    ) : filteredComponents.length === 0 ? (
                      <div className="flex flex-col items-center justify-center py-12 text-center">
                        <DocumentTextIcon className="h-12 w-12 text-[var(--gr-text-tertiary)] mb-4" />
                        <h3 className="text-sm font-medium text-[var(--gr-text-primary)]">
                          No components found
                        </h3>
                        <p className="mt-1 text-sm text-[var(--gr-text-secondary)]">
                          {searchQuery
                            ? 'Try adjusting your search or category filter'
                            : 'Create components in the Library to reuse them here'}
                        </p>
                      </div>
                    ) : (
                      <div className="grid grid-cols-2 gap-3">
                        {filteredComponents.map((component) => {
                          const isSelected = selectedComponent?.id === component.id;
                          const categoryConfig = COMPONENT_CATEGORY_CONFIG[component.category as ComponentCategory] ||
                            COMPONENT_CATEGORY_CONFIG.other;

                          return (
                            <button
                              key={component.id}
                              onClick={() => setSelectedComponent(component)}
                              className={`
                                relative text-left p-4 rounded-xl border-2 transition-all
                                ${
                                  isSelected
                                    ? 'border-[var(--gr-blue-500)] bg-[var(--gr-blue-50)] ring-2 ring-[var(--gr-blue-500)]/20'
                                    : 'border-[var(--gr-border-subtle)] hover:border-[var(--gr-border-default)] bg-[var(--gr-bg-elevated)]'
                                }
                              `}
                            >
                              {isSelected && (
                                <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-[var(--gr-blue-500)] flex items-center justify-center">
                                  <CheckIcon className="h-3 w-3 text-white" />
                                </div>
                              )}
                              <div className="flex items-center gap-2 mb-2">
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[var(--gr-bg-tertiary)] text-[var(--gr-text-secondary)]">
                                  {categoryConfig.label}
                                </span>
                                <span className="text-xs text-[var(--gr-text-tertiary)]">
                                  {getWordCount(component.content)} words
                                </span>
                              </div>
                              <h4 className="text-sm font-medium text-[var(--gr-text-primary)] mb-1 pr-6">
                                {component.name}
                              </h4>
                              <p className="text-xs text-[var(--gr-text-secondary)] line-clamp-2">
                                {truncateContent(component.content, 100)}
                              </p>
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* Preview Panel */}
                  {selectedComponent && (
                    <div className="w-96 border-l border-[var(--gr-border-subtle)] bg-[var(--gr-bg-secondary)] flex flex-col">
                      <div className="p-4 border-b border-[var(--gr-border-subtle)]">
                        <h4 className="text-sm font-semibold text-[var(--gr-text-primary)]">
                          {selectedComponent.name}
                        </h4>
                        <div className="flex items-center gap-2 mt-2">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[var(--gr-bg-tertiary)] text-[var(--gr-text-secondary)]">
                            {COMPONENT_CATEGORY_CONFIG[selectedComponent.category as ComponentCategory]?.label}
                          </span>
                          <span className="text-xs text-[var(--gr-text-tertiary)]">
                            v{selectedComponent.version}
                          </span>
                          <span className="text-xs text-[var(--gr-text-tertiary)]">
                            {getWordCount(selectedComponent.content)} words
                          </span>
                        </div>
                      </div>
                      <div className="flex-1 overflow-y-auto p-4">
                        <pre className="whitespace-pre-wrap text-sm text-[var(--gr-text-primary)] font-sans">
                          {selectedComponent.content}
                        </pre>
                      </div>
                      <div className="p-4 border-t border-[var(--gr-border-subtle)]">
                        <button
                          onClick={handleCopyContent}
                          className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-tertiary)] rounded-lg transition-colors"
                        >
                          {copied ? (
                            <>
                              <CheckIcon className="h-4 w-4 text-green-500" />
                              Copied to clipboard
                            </>
                          ) : (
                            <>
                              <ClipboardDocumentCheckIcon className="h-4 w-4" />
                              Copy content
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between p-6 border-t border-[var(--gr-border-subtle)] bg-[var(--gr-bg-secondary)]">
                  <div className="flex items-center gap-4">
                    <span className="text-sm text-[var(--gr-text-secondary)]">Insert at:</span>
                    <div className="flex gap-2">
                      {(['end', 'start', 'cursor'] as const).map((position) => (
                        <button
                          key={position}
                          onClick={() => setInsertPosition(position)}
                          className={`
                            px-3 py-1.5 text-sm rounded-lg transition-colors
                            ${
                              insertPosition === position
                                ? 'bg-[var(--gr-blue-100)] text-[var(--gr-blue-700)]'
                                : 'text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-tertiary)]'
                            }
                          `}
                        >
                          {position === 'end' ? 'End' : position === 'start' ? 'Beginning' : 'Cursor'}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <button onClick={handleClose} className="btn-secondary">
                      Cancel
                    </button>
                    <button
                      onClick={handleInsert}
                      disabled={!selectedComponent || insertComponent.isPending}
                      className="btn-primary"
                    >
                      {insertComponent.isPending ? 'Inserting...' : 'Insert Component'}
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

export default InsertComponentModal;
