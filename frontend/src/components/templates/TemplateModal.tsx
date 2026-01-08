import { Fragment, useEffect, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { useCreateTemplate, useUpdateTemplate } from '../../hooks/useTemplates';
import type { Template, TemplateCategory, TemplateCreate, TemplateUpdate } from '../../types';

interface TemplateModalProps {
  isOpen: boolean;
  onClose: () => void;
  template: Template | null;
  categories: TemplateCategory[];
}

export function TemplateModal({ isOpen, onClose, template, categories }: TemplateModalProps) {
  const [formData, setFormData] = useState<TemplateCreate>({
    title: '',
    description: '',
    content: '',
    category_id: undefined,
    is_public: false,
  });

  const createTemplate = useCreateTemplate();
  const updateTemplate = useUpdateTemplate();

  useEffect(() => {
    if (template) {
      setFormData({
        title: template.title,
        description: template.description || '',
        content: template.content,
        category_id: template.category_id || undefined,
        is_public: template.is_public,
      });
    } else {
      setFormData({
        title: '',
        description: '',
        content: '',
        category_id: undefined,
        is_public: false,
      });
    }
  }, [template, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      if (template) {
        await updateTemplate.mutateAsync({
          id: template.id,
          data: formData as TemplateUpdate,
        });
      } else {
        await createTemplate.mutateAsync(formData);
      }
      onClose();
    } catch (error) {
      console.error('Failed to save template:', error);
    }
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
              <Dialog.Panel className="w-full max-w-3xl transform overflow-hidden rounded-2xl bg-[var(--gr-bg-elevated)] p-6 shadow-[var(--gr-shadow-xl)] transition-all">
                <div className="flex items-center justify-between mb-6">
                  <Dialog.Title className="text-lg font-semibold text-[var(--gr-text-primary)]">
                    {template ? 'Edit Template' : 'Create Template'}
                  </Dialog.Title>
                  <button
                    onClick={onClose}
                    className="text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-primary)] transition-colors"
                  >
                    <XMarkIcon className="h-6 w-6" />
                  </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-[var(--gr-text-primary)] mb-1">
                      Title *
                    </label>
                    <input
                      type="text"
                      value={formData.title}
                      onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                      required
                      className="w-full px-3 py-2 border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] placeholder:text-[var(--gr-text-tertiary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]"
                      placeholder="e.g., NIH R01 Specific Aims"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-[var(--gr-text-primary)] mb-1">
                      Category
                    </label>
                    <select
                      value={formData.category_id || ''}
                      onChange={(e) => setFormData({ ...formData, category_id: e.target.value || undefined })}
                      className="w-full px-3 py-2 border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]"
                    >
                      <option value="">Select a category</option>
                      {categories.map((cat) => (
                        <option key={cat.id} value={cat.id}>
                          {cat.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-[var(--gr-text-primary)] mb-1">
                      Description
                    </label>
                    <input
                      type="text"
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      className="w-full px-3 py-2 border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] placeholder:text-[var(--gr-text-tertiary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]"
                      placeholder="Brief description of this template"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-[var(--gr-text-primary)] mb-1">
                      Content *
                    </label>
                    <p className="text-xs text-[var(--gr-text-tertiary)] mb-2">
                      Use {"{{variable_name}}"} for placeholders. Example: {"{{project_title}}"}
                    </p>
                    <textarea
                      value={formData.content}
                      onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                      required
                      rows={12}
                      className="w-full px-3 py-2 border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] placeholder:text-[var(--gr-text-tertiary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)] font-mono text-sm"
                      placeholder="Enter your template content here..."
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="is_public"
                      checked={formData.is_public}
                      onChange={(e) => setFormData({ ...formData, is_public: e.target.checked })}
                      className="h-4 w-4 rounded border-[var(--gr-border-default)] text-[var(--gr-blue-600)] focus:ring-[var(--gr-blue-600)]"
                    />
                    <label htmlFor="is_public" className="text-sm text-[var(--gr-text-secondary)]">
                      Make this template public (visible to all users)
                    </label>
                  </div>

                  <div className="flex justify-end gap-3 pt-4 border-t border-[var(--gr-border-subtle)]">
                    <button
                      type="button"
                      onClick={onClose}
                      className="btn-secondary"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={createTemplate.isPending || updateTemplate.isPending}
                      className="btn-primary"
                    >
                      {createTemplate.isPending || updateTemplate.isPending ? 'Saving...' : 'Save Template'}
                    </button>
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

export default TemplateModal;
