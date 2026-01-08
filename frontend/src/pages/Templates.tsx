import { useState } from 'react';
import {
  PlusIcon,
  MagnifyingGlassIcon,
  DocumentDuplicateIcon,
  PencilIcon,
  TrashIcon,
  EyeIcon,
} from '@heroicons/react/24/outline';
import {
  useTemplates,
  useTemplateCategories,
  useDeleteTemplate,
  useDuplicateTemplate,
} from '../hooks/useTemplates';
import type { Template, TemplateFilters } from '../types';
import { TemplateModal } from '../components/templates/TemplateModal';
import { TemplatePreviewModal } from '../components/templates/TemplatePreviewModal';

export function Templates() {
  const [filters, setFilters] = useState<TemplateFilters>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isPreviewModalOpen, setIsPreviewModalOpen] = useState(false);
  const [previewTemplate, setPreviewTemplate] = useState<Template | null>(null);

  const { data: templatesData, isLoading } = useTemplates({
    ...filters,
    search: searchQuery || undefined,
  });
  const { data: categories } = useTemplateCategories();
  const deleteTemplate = useDeleteTemplate();
  const duplicateTemplate = useDuplicateTemplate();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // Search is already reactive through the query
  };

  const handleDelete = async (template: Template) => {
    if (confirm(`Are you sure you want to delete "${template.title}"?`)) {
      await deleteTemplate.mutateAsync(template.id);
    }
  };

  const handleDuplicate = async (template: Template) => {
    await duplicateTemplate.mutateAsync(template.id);
  };

  const handlePreview = (template: Template) => {
    setPreviewTemplate(template);
    setIsPreviewModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      {/* Header */}
      <div className="bg-[var(--gr-bg-secondary)] border-b border-[var(--gr-border-subtle)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-display font-semibold text-[var(--gr-text-primary)]">
                Document Templates
              </h1>
              <p className="mt-1 text-sm text-[var(--gr-text-secondary)]">
                Reusable templates for grant proposal sections
              </p>
            </div>
            <button
              onClick={() => {
                setSelectedTemplate(null);
                setIsCreateModalOpen(true);
              }}
              className="btn-primary flex items-center gap-2"
            >
              <PlusIcon className="h-5 w-5" />
              New Template
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filters */}
        <div className="bg-[var(--gr-bg-secondary)] rounded-xl border border-[var(--gr-border-default)] p-4 mb-6">
          <div className="flex flex-wrap gap-4 items-center">
            {/* Search */}
            <form onSubmit={handleSearch} className="flex-1 min-w-64">
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-[var(--gr-text-tertiary)]" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search templates..."
                  className="w-full pl-10 pr-4 py-2 border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] placeholder:text-[var(--gr-text-tertiary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]"
                />
              </div>
            </form>

            {/* Category Filter */}
            <select
              value={filters.category_id || ''}
              onChange={(e) => setFilters({ ...filters, category_id: e.target.value || undefined })}
              className="px-3 py-2 border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]"
            >
              <option value="">All Categories</option>
              {categories?.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name} ({cat.template_count})
                </option>
              ))}
            </select>

            {/* Type Filter */}
            <select
              value={
                filters.is_system === true ? 'system' :
                filters.is_public === true ? 'public' :
                filters.is_public === false ? 'mine' :
                ''
              }
              onChange={(e) => {
                const val = e.target.value;
                if (val === 'system') {
                  setFilters({ ...filters, is_system: true, is_public: undefined });
                } else if (val === 'public') {
                  setFilters({ ...filters, is_system: false, is_public: true });
                } else if (val === 'mine') {
                  setFilters({ ...filters, is_system: false, is_public: false });
                } else {
                  setFilters({ ...filters, is_system: undefined, is_public: undefined });
                }
              }}
              className="px-3 py-2 border border-[var(--gr-border-default)] rounded-lg bg-[var(--gr-bg-primary)] text-[var(--gr-text-primary)] focus:ring-2 focus:ring-[var(--gr-blue-600)] focus:border-[var(--gr-blue-600)]"
            >
              <option value="">All Types</option>
              <option value="mine">My Templates</option>
              <option value="public">Public Templates</option>
              <option value="system">System Templates</option>
            </select>
          </div>
        </div>

        {/* Templates Grid */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="bg-[var(--gr-bg-secondary)] rounded-xl border border-[var(--gr-border-default)] p-6 animate-pulse">
                <div className="h-4 bg-[var(--gr-bg-tertiary)] rounded w-3/4 mb-4"></div>
                <div className="h-3 bg-[var(--gr-bg-tertiary)] rounded w-full mb-2"></div>
                <div className="h-3 bg-[var(--gr-bg-tertiary)] rounded w-2/3"></div>
              </div>
            ))}
          </div>
        ) : templatesData?.items.length === 0 ? (
          <div className="text-center py-12">
            <DocumentDuplicateIcon className="mx-auto h-12 w-12 text-[var(--gr-text-tertiary)]" />
            <h3 className="mt-2 text-sm font-medium text-[var(--gr-text-primary)]">No templates found</h3>
            <p className="mt-1 text-sm text-[var(--gr-text-secondary)]">
              Get started by creating a new template.
            </p>
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="mt-4 btn-primary inline-flex items-center gap-2"
            >
              <PlusIcon className="h-5 w-5" />
              New Template
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {templatesData?.items.map((template) => (
              <div
                key={template.id}
                className="bg-[var(--gr-bg-secondary)] rounded-xl border border-[var(--gr-border-default)] overflow-hidden hover:shadow-[var(--gr-shadow-md)] transition-shadow"
              >
                <div className="p-6">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="text-lg font-semibold text-[var(--gr-text-primary)] line-clamp-1">
                      {template.title}
                    </h3>
                    <div className="flex gap-1 ml-2 flex-shrink-0">
                      {template.is_system && (
                        <span className="inline-flex items-center rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700">
                          System
                        </span>
                      )}
                      {template.is_public && !template.is_system && (
                        <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                          Public
                        </span>
                      )}
                    </div>
                  </div>

                  {template.description && (
                    <p className="text-sm text-[var(--gr-text-secondary)] line-clamp-2 mb-4">
                      {template.description}
                    </p>
                  )}

                  <div className="flex items-center gap-4 text-sm text-[var(--gr-text-tertiary)] mb-4">
                    <span>{template.variables?.length || 0} variables</span>
                    <span>Used {template.usage_count} times</span>
                  </div>

                  <div className="flex items-center gap-2 pt-4 border-t border-[var(--gr-border-subtle)]">
                    <button
                      onClick={() => handlePreview(template)}
                      className="flex-1 inline-flex items-center justify-center gap-1 px-3 py-2 text-sm font-medium text-[var(--gr-text-secondary)] bg-[var(--gr-bg-tertiary)] rounded-lg hover:bg-[var(--gr-bg-hover)] transition-colors"
                    >
                      <EyeIcon className="h-4 w-4" />
                      Preview
                    </button>
                    <button
                      onClick={() => handleDuplicate(template)}
                      className="inline-flex items-center justify-center p-2 text-[var(--gr-text-tertiary)] hover:text-[var(--gr-blue-600)] hover:bg-[var(--gr-blue-50)] rounded-lg transition-colors"
                      title="Duplicate"
                    >
                      <DocumentDuplicateIcon className="h-5 w-5" />
                    </button>
                    {!template.is_system && template.user_id && (
                      <>
                        <button
                          onClick={() => {
                            setSelectedTemplate(template);
                            setIsCreateModalOpen(true);
                          }}
                          className="inline-flex items-center justify-center p-2 text-[var(--gr-text-tertiary)] hover:text-[var(--gr-blue-600)] hover:bg-[var(--gr-blue-50)] rounded-lg transition-colors"
                          title="Edit"
                        >
                          <PencilIcon className="h-5 w-5" />
                        </button>
                        <button
                          onClick={() => handleDelete(template)}
                          className="inline-flex items-center justify-center p-2 text-[var(--gr-text-tertiary)] hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Delete"
                        >
                          <TrashIcon className="h-5 w-5" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modals */}
      <TemplateModal
        isOpen={isCreateModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false);
          setSelectedTemplate(null);
        }}
        template={selectedTemplate}
        categories={categories || []}
      />

      <TemplatePreviewModal
        isOpen={isPreviewModalOpen}
        onClose={() => {
          setIsPreviewModalOpen(false);
          setPreviewTemplate(null);
        }}
        template={previewTemplate}
      />
    </div>
  );
}

export default Templates;
