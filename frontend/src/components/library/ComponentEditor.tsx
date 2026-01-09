import { Fragment, useEffect, useState } from 'react';
import { Dialog, Transition, Listbox } from '@headlessui/react';
import {
  XMarkIcon,
  ChevronUpDownIcon,
  CheckIcon,
  TagIcon,
  PlusIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { useCreateComponent, useUpdateComponent } from '../../hooks/useComponents';
import type {
  DocumentComponent,
  DocumentComponentCreate,
  DocumentComponentUpdate,
  ComponentCategory,
  ComponentMetadata,
} from '../../types/components';
import { COMPONENT_CATEGORY_CONFIG } from '../../types/components';

interface ComponentEditorProps {
  isOpen: boolean;
  onClose: () => void;
  component: DocumentComponent | null;
  defaultCategory?: ComponentCategory;
}

const categoryOptions: ComponentCategory[] = [
  'facilities',
  'equipment',
  'biosketch',
  'boilerplate',
  'human_subjects',
  'vertebrate_animals',
  'institution',
  'other',
];

export function ComponentEditor({
  isOpen,
  onClose,
  component,
  defaultCategory,
}: ComponentEditorProps) {
  const [formData, setFormData] = useState<DocumentComponentCreate>({
    category: defaultCategory || 'other',
    name: '',
    content: '',
    metadata: {},
  });
  const [tagInput, setTagInput] = useState('');
  const [tags, setTags] = useState<string[]>([]);

  const createComponent = useCreateComponent();
  const updateComponent = useUpdateComponent();

  const isEditing = !!component;
  const isPending = createComponent.isPending || updateComponent.isPending;

  useEffect(() => {
    if (component) {
      setFormData({
        category: component.category,
        name: component.name,
        content: component.content,
        metadata: component.metadata || {},
      });
      setTags(component.metadata?.tags || []);
    } else {
      setFormData({
        category: defaultCategory || 'other',
        name: '',
        content: '',
        metadata: {},
      });
      setTags([]);
    }
    setTagInput('');
  }, [component, isOpen, defaultCategory]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const dataToSubmit = {
      ...formData,
      metadata: {
        ...formData.metadata,
        tags: tags.length > 0 ? tags : undefined,
      },
    };

    try {
      if (isEditing && component) {
        await updateComponent.mutateAsync({
          id: component.id,
          data: dataToSubmit as DocumentComponentUpdate,
        });
      } else {
        await createComponent.mutateAsync(dataToSubmit);
      }
      onClose();
    } catch (error) {
      console.error('Failed to save component:', error);
    }
  };

  const handleAddTag = () => {
    const trimmedTag = tagInput.trim();
    if (trimmedTag && !tags.includes(trimmedTag)) {
      setTags([...tags, trimmedTag]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter((tag) => tag !== tagToRemove));
  };

  const handleTagKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  const updateMetadata = (key: keyof ComponentMetadata, value: unknown) => {
    setFormData({
      ...formData,
      metadata: {
        ...formData.metadata,
        [key]: value || undefined,
      },
    });
  };

  const getWordCount = (content: string) => {
    return content.split(/\s+/).filter(Boolean).length;
  };

  const getCharCount = (content: string) => {
    return content.length;
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
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-4xl transform overflow-hidden rounded-2xl bg-[var(--gr-bg-elevated)] shadow-[var(--gr-shadow-xl)] transition-all">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-[var(--gr-border-subtle)]">
                  <Dialog.Title className="text-lg font-semibold text-[var(--gr-text-primary)]">
                    {isEditing ? 'Edit Component' : 'Create Component'}
                  </Dialog.Title>
                  <button
                    onClick={onClose}
                    className="text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-primary)] transition-colors"
                  >
                    <XMarkIcon className="h-6 w-6" />
                  </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit}>
                  <div className="flex max-h-[calc(100vh-200px)]">
                    {/* Main Content */}
                    <div className="flex-1 p-6 overflow-y-auto">
                      <div className="space-y-6">
                        {/* Name */}
                        <div>
                          <label className="block text-sm font-medium text-[var(--gr-text-primary)] mb-1">
                            Component Name *
                          </label>
                          <input
                            type="text"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            required
                            className="w-full px-3 py-2 border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] placeholder:text-[var(--gr-text-tertiary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]"
                            placeholder="e.g., Core Facilities Description - NIH"
                          />
                        </div>

                        {/* Category */}
                        <div>
                          <label className="block text-sm font-medium text-[var(--gr-text-primary)] mb-1">
                            Category *
                          </label>
                          <Listbox
                            value={formData.category}
                            onChange={(value) => setFormData({ ...formData, category: value })}
                          >
                            <div className="relative">
                              <Listbox.Button className="relative w-full cursor-pointer rounded-lg border border-[var(--gr-border-default)] bg-[var(--gr-bg-primary)] py-2 pl-3 pr-10 text-left text-[var(--gr-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]">
                                <span className="block truncate">
                                  {COMPONENT_CATEGORY_CONFIG[formData.category]?.label || formData.category}
                                </span>
                                <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                                  <ChevronUpDownIcon className="h-5 w-5 text-[var(--gr-text-tertiary)]" />
                                </span>
                              </Listbox.Button>
                              <Transition
                                as={Fragment}
                                leave="transition ease-in duration-100"
                                leaveFrom="opacity-100"
                                leaveTo="opacity-0"
                              >
                                <Listbox.Options className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-lg bg-[var(--gr-bg-elevated)] border border-[var(--gr-border-default)] py-1 shadow-[var(--gr-shadow-lg)] focus:outline-none">
                                  {categoryOptions.map((category) => (
                                    <Listbox.Option
                                      key={category}
                                      value={category}
                                      className={({ active }) =>
                                        `relative cursor-pointer select-none py-2 pl-10 pr-4 ${
                                          active
                                            ? 'bg-[var(--gr-bg-tertiary)] text-[var(--gr-text-primary)]'
                                            : 'text-[var(--gr-text-secondary)]'
                                        }`
                                      }
                                    >
                                      {({ selected }) => (
                                        <>
                                          <span className={`block truncate ${selected ? 'font-medium' : 'font-normal'}`}>
                                            {COMPONENT_CATEGORY_CONFIG[category]?.label || category}
                                          </span>
                                          <span className="block text-xs text-[var(--gr-text-tertiary)]">
                                            {COMPONENT_CATEGORY_CONFIG[category]?.description}
                                          </span>
                                          {selected && (
                                            <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-[var(--gr-blue-600)]">
                                              <CheckIcon className="h-5 w-5" />
                                            </span>
                                          )}
                                        </>
                                      )}
                                    </Listbox.Option>
                                  ))}
                                </Listbox.Options>
                              </Transition>
                            </div>
                          </Listbox>
                        </div>

                        {/* Content */}
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <label className="block text-sm font-medium text-[var(--gr-text-primary)]">
                              Content *
                            </label>
                            <span className="text-xs text-[var(--gr-text-tertiary)]">
                              {getWordCount(formData.content)} words / {getCharCount(formData.content)} characters
                            </span>
                          </div>
                          <textarea
                            value={formData.content}
                            onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                            required
                            rows={15}
                            className="w-full px-3 py-2 border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] placeholder:text-[var(--gr-text-tertiary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)] font-mono text-sm resize-y"
                            placeholder="Enter your component content here..."
                          />
                        </div>
                      </div>
                    </div>

                    {/* Sidebar - Metadata */}
                    <div className="w-80 border-l border-[var(--gr-border-subtle)] p-6 bg-[var(--gr-bg-secondary)] overflow-y-auto">
                      <h4 className="text-sm font-medium text-[var(--gr-text-primary)] mb-4">
                        Metadata (Optional)
                      </h4>
                      <div className="space-y-4">
                        {/* Funder */}
                        <div>
                          <label className="block text-xs font-medium text-[var(--gr-text-secondary)] mb-1">
                            Funder
                          </label>
                          <input
                            type="text"
                            value={formData.metadata?.funder || ''}
                            onChange={(e) => updateMetadata('funder', e.target.value)}
                            className="w-full px-3 py-2 text-sm border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] placeholder:text-[var(--gr-text-tertiary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]"
                            placeholder="e.g., NIH, NSF"
                          />
                        </div>

                        {/* Mechanism */}
                        <div>
                          <label className="block text-xs font-medium text-[var(--gr-text-secondary)] mb-1">
                            Grant Mechanism
                          </label>
                          <input
                            type="text"
                            value={formData.metadata?.mechanism || ''}
                            onChange={(e) => updateMetadata('mechanism', e.target.value)}
                            className="w-full px-3 py-2 text-sm border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] placeholder:text-[var(--gr-text-tertiary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]"
                            placeholder="e.g., R01, R21, K99"
                          />
                        </div>

                        {/* Word Limit */}
                        <div>
                          <label className="block text-xs font-medium text-[var(--gr-text-secondary)] mb-1">
                            Word Limit
                          </label>
                          <input
                            type="number"
                            value={formData.metadata?.word_limit || ''}
                            onChange={(e) => updateMetadata('word_limit', e.target.value ? parseInt(e.target.value) : undefined)}
                            className="w-full px-3 py-2 text-sm border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] placeholder:text-[var(--gr-text-tertiary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]"
                            placeholder="e.g., 500"
                          />
                        </div>

                        {/* Page Limit */}
                        <div>
                          <label className="block text-xs font-medium text-[var(--gr-text-secondary)] mb-1">
                            Page Limit
                          </label>
                          <input
                            type="number"
                            value={formData.metadata?.page_limit || ''}
                            onChange={(e) => updateMetadata('page_limit', e.target.value ? parseInt(e.target.value) : undefined)}
                            className="w-full px-3 py-2 text-sm border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] placeholder:text-[var(--gr-text-tertiary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]"
                            placeholder="e.g., 1"
                          />
                        </div>

                        {/* Notes */}
                        <div>
                          <label className="block text-xs font-medium text-[var(--gr-text-secondary)] mb-1">
                            Notes
                          </label>
                          <textarea
                            value={formData.metadata?.notes || ''}
                            onChange={(e) => updateMetadata('notes', e.target.value)}
                            rows={3}
                            className="w-full px-3 py-2 text-sm border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] placeholder:text-[var(--gr-text-tertiary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)] resize-none"
                            placeholder="Any additional notes..."
                          />
                        </div>

                        {/* Tags */}
                        <div>
                          <label className="block text-xs font-medium text-[var(--gr-text-secondary)] mb-1">
                            Tags
                          </label>
                          <div className="flex gap-2 mb-2">
                            <div className="relative flex-1">
                              <TagIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--gr-text-tertiary)]" />
                              <input
                                type="text"
                                value={tagInput}
                                onChange={(e) => setTagInput(e.target.value)}
                                onKeyDown={handleTagKeyDown}
                                className="w-full pl-9 pr-3 py-2 text-sm border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] placeholder:text-[var(--gr-text-tertiary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]"
                                placeholder="Add tag..."
                              />
                            </div>
                            <button
                              type="button"
                              onClick={handleAddTag}
                              className="p-2 text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-tertiary)] rounded-lg transition-colors"
                            >
                              <PlusIcon className="h-5 w-5" />
                            </button>
                          </div>
                          {tags.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {tags.map((tag, index) => (
                                <span
                                  key={index}
                                  className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-[var(--gr-bg-tertiary)] text-[var(--gr-text-secondary)]"
                                >
                                  {tag}
                                  <button
                                    type="button"
                                    onClick={() => handleRemoveTag(tag)}
                                    className="hover:text-red-500 transition-colors"
                                  >
                                    <XCircleIcon className="h-3.5 w-3.5" />
                                  </button>
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="flex items-center justify-between p-6 border-t border-[var(--gr-border-subtle)] bg-[var(--gr-bg-secondary)]">
                    {isEditing && component && (
                      <div className="text-xs text-[var(--gr-text-tertiary)]">
                        Version {component.version} | Last updated {new Date(component.updated_at).toLocaleDateString()}
                      </div>
                    )}
                    {!isEditing && <div />}
                    <div className="flex gap-3">
                      <button type="button" onClick={onClose} className="btn-secondary">
                        Cancel
                      </button>
                      <button type="submit" disabled={isPending} className="btn-primary">
                        {isPending ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Component'}
                      </button>
                    </div>
                  </div>
                </form>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}

export default ComponentEditor;
