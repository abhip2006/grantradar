import { Fragment, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, ClipboardDocumentIcon, CheckIcon } from '@heroicons/react/24/outline';
import { useRenderTemplate } from '../../hooks/useTemplates';
import type { Template } from '../../types';

interface TemplatePreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  template: Template | null;
}

export function TemplatePreviewModal({ isOpen, onClose, template }: TemplatePreviewModalProps) {
  const [variables, setVariables] = useState<Record<string, string>>({});
  const [showRendered, setShowRendered] = useState(false);
  const [copied, setCopied] = useState(false);
  const renderTemplate = useRenderTemplate();

  if (!template) return null;

  const handleRender = async () => {
    try {
      await renderTemplate.mutateAsync({ id: template.id, variables });
      setShowRendered(true);
    } catch (error) {
      console.error('Failed to render template:', error);
    }
  };

  const handleCopy = () => {
    const content = showRendered && renderTemplate.data
      ? renderTemplate.data.rendered_content
      : template.content;
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClose = () => {
    setVariables({});
    setShowRendered(false);
    renderTemplate.reset();
    onClose();
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
              <Dialog.Panel className="w-full max-w-4xl transform overflow-hidden rounded-2xl bg-[var(--gr-bg-elevated)] shadow-[var(--gr-shadow-xl)] transition-all">
                <div className="flex items-center justify-between p-6 border-b border-[var(--gr-border-subtle)]">
                  <div>
                    <Dialog.Title className="text-lg font-semibold text-[var(--gr-text-primary)]">
                      {template.title}
                    </Dialog.Title>
                    {template.description && (
                      <p className="mt-1 text-sm text-[var(--gr-text-secondary)]">{template.description}</p>
                    )}
                  </div>
                  <button
                    onClick={handleClose}
                    className="text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-primary)] transition-colors"
                  >
                    <XMarkIcon className="h-6 w-6" />
                  </button>
                </div>

                <div className="flex max-h-[calc(100vh-200px)]">
                  {/* Variables Panel */}
                  {template.variables && template.variables.length > 0 && (
                    <div className="w-80 border-r border-[var(--gr-border-subtle)] p-6 bg-[var(--gr-bg-secondary)] overflow-y-auto">
                      <h4 className="text-sm font-medium text-[var(--gr-text-primary)] mb-4">
                        Fill in Variables
                      </h4>
                      <div className="space-y-4">
                        {template.variables.map((variable) => (
                          <div key={variable.name}>
                            <label className="block text-sm font-medium text-[var(--gr-text-primary)] mb-1">
                              {variable.name}
                              {variable.required && <span className="text-red-500 ml-1">*</span>}
                            </label>
                            {variable.description && (
                              <p className="text-xs text-[var(--gr-text-tertiary)] mb-1">{variable.description}</p>
                            )}
                            {variable.type === 'select' && variable.options ? (
                              <select
                                value={variables[variable.name] || ''}
                                onChange={(e) => setVariables({ ...variables, [variable.name]: e.target.value })}
                                className="w-full px-3 py-2 border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] text-sm focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]"
                              >
                                <option value="">Select...</option>
                                {variable.options.map((opt) => (
                                  <option key={opt} value={opt}>{opt}</option>
                                ))}
                              </select>
                            ) : (
                              <input
                                type={variable.type === 'number' ? 'number' : 'text'}
                                value={variables[variable.name] || ''}
                                onChange={(e) => setVariables({ ...variables, [variable.name]: e.target.value })}
                                placeholder={variable.default || ''}
                                className="w-full px-3 py-2 border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] placeholder:text-[var(--gr-text-tertiary)] text-sm focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]"
                              />
                            )}
                          </div>
                        ))}
                      </div>
                      <button
                        onClick={handleRender}
                        disabled={renderTemplate.isPending}
                        className="mt-6 w-full btn-primary"
                      >
                        {renderTemplate.isPending ? 'Rendering...' : 'Preview with Values'}
                      </button>
                    </div>
                  )}

                  {/* Content Panel */}
                  <div className="flex-1 p-6 overflow-y-auto">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex gap-2">
                        <button
                          onClick={() => setShowRendered(false)}
                          className={`px-3 py-1 text-sm font-medium rounded-lg transition-colors ${
                            !showRendered
                              ? 'bg-[var(--gr-blue-100)] text-[var(--gr-blue-700)]'
                              : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)]'
                          }`}
                        >
                          Template
                        </button>
                        {renderTemplate.data && (
                          <button
                            onClick={() => setShowRendered(true)}
                            className={`px-3 py-1 text-sm font-medium rounded-lg transition-colors ${
                              showRendered
                                ? 'bg-[var(--gr-blue-100)] text-[var(--gr-blue-700)]'
                                : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)]'
                            }`}
                          >
                            Rendered
                          </button>
                        )}
                      </div>
                      <button
                        onClick={handleCopy}
                        className="inline-flex items-center gap-1 px-3 py-1 text-sm text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] transition-colors"
                      >
                        {copied ? (
                          <>
                            <CheckIcon className="h-4 w-4 text-green-500" />
                            Copied!
                          </>
                        ) : (
                          <>
                            <ClipboardDocumentIcon className="h-4 w-4" />
                            Copy
                          </>
                        )}
                      </button>
                    </div>
                    <div className="bg-[var(--gr-bg-secondary)] rounded-lg p-4 max-h-96 overflow-y-auto border border-[var(--gr-border-subtle)]">
                      <pre className="whitespace-pre-wrap text-sm text-[var(--gr-text-primary)] font-mono">
                        {showRendered && renderTemplate.data
                          ? renderTemplate.data.rendered_content
                          : template.content}
                      </pre>
                    </div>
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

export default TemplatePreviewModal;
