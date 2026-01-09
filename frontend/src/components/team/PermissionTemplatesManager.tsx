import { Fragment, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  XMarkIcon,
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import type {
  PermissionTemplate,
  PermissionTemplateCreate,
  PermissionTemplateUpdate,
  MemberPermissions,
} from '../../types/team';

interface PermissionTemplatesManagerProps {
  templates: PermissionTemplate[];
  onCreateTemplate: (data: PermissionTemplateCreate) => Promise<void>;
  onUpdateTemplate: (id: string, data: PermissionTemplateUpdate) => Promise<void>;
  onDeleteTemplate: (id: string) => Promise<void>;
  isLoading?: boolean;
}

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

// Permission definitions for display
const PERMISSION_DEFINITIONS: {
  key: keyof MemberPermissions;
  label: string;
  description: string;
}[] = [
  { key: 'can_view', label: 'View', description: 'View grants and applications' },
  { key: 'can_edit', label: 'Edit', description: 'Edit applications and content' },
  { key: 'can_create', label: 'Create', description: 'Create new applications' },
  { key: 'can_delete', label: 'Delete', description: 'Delete applications and content' },
  { key: 'can_invite', label: 'Invite', description: 'Invite new team members' },
  { key: 'can_manage_grants', label: 'Manage Grants', description: 'Manage grant tracking' },
  { key: 'can_export', label: 'Export', description: 'Export data and reports' },
];

// Default permissions for new templates
const DEFAULT_PERMISSIONS: MemberPermissions = {
  can_view: true,
  can_edit: false,
  can_create: false,
  can_delete: false,
  can_invite: false,
  can_manage_grants: false,
  can_export: false,
};

interface TemplateFormData {
  name: string;
  description: string;
  permissions: MemberPermissions;
}

// Template Card Component
function TemplateCard({
  template,
  onEdit,
  onDelete,
}: {
  template: PermissionTemplate;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const enabledPermissions = PERMISSION_DEFINITIONS.filter(
    (p) => template.permissions[p.key]
  );

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-all duration-200">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div
            className={classNames(
              'w-10 h-10 rounded-xl flex items-center justify-center',
              template.is_default ? 'bg-purple-50' : 'bg-blue-50'
            )}
          >
            <ShieldCheckIcon
              className={classNames(
                'w-5 h-5',
                template.is_default ? 'text-purple-600' : 'text-blue-600'
              )}
            />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-gray-900">{template.name}</h3>
              {template.is_default && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700">
                  <SparklesIcon className="w-3 h-3" />
                  Default
                </span>
              )}
            </div>
            {template.description && (
              <p className="text-xs text-gray-500 mt-0.5">{template.description}</p>
            )}
          </div>
        </div>

        {/* Actions - only show for non-default templates */}
        {!template.is_default && (
          <div className="flex items-center gap-1">
            <button
              onClick={onEdit}
              className="p-2 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
              title="Edit template"
            >
              <PencilIcon className="w-4 h-4" />
            </button>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="p-2 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
              title="Delete template"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Permission Badges */}
      <div className="flex flex-wrap gap-1.5">
        {enabledPermissions.length > 0 ? (
          enabledPermissions.map((perm) => (
            <span
              key={perm.key}
              className="inline-flex items-center px-2 py-1 rounded-lg text-xs font-medium bg-gray-100 text-gray-700"
              title={perm.description}
            >
              {perm.label}
            </span>
          ))
        ) : (
          <span className="text-xs text-gray-400">No permissions</span>
        )}
      </div>

      {/* Delete Confirmation */}
      {showDeleteConfirm && (
        <div className="mt-4 p-3 bg-red-50 rounded-lg border border-red-100">
          <div className="flex items-start gap-2">
            <ExclamationTriangleIcon className="w-5 h-5 text-red-500 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-red-800">Delete this template?</p>
              <p className="text-xs text-red-600 mt-0.5">This action cannot be undone.</p>
              <div className="flex items-center gap-2 mt-2">
                <button
                  onClick={() => {
                    onDelete();
                    setShowDeleteConfirm(false);
                  }}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium text-white bg-red-600 hover:bg-red-700 transition-colors"
                >
                  Delete
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium text-red-700 hover:bg-red-100 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Template Edit Modal Component
function TemplateEditModal({
  isOpen,
  onClose,
  onSave,
  template,
  isLoading,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: TemplateFormData) => Promise<void>;
  template?: PermissionTemplate | null;
  isLoading?: boolean;
}) {
  const [formData, setFormData] = useState<TemplateFormData>({
    name: template?.name || '',
    description: template?.description || '',
    permissions: template?.permissions || { ...DEFAULT_PERMISSIONS },
  });
  const [isSaving, setIsSaving] = useState(false);

  const isEditing = !!template;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      return;
    }

    setIsSaving(true);
    try {
      await onSave(formData);
      onClose();
    } catch (error) {
      console.error('Failed to save template:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handlePermissionChange = (key: keyof MemberPermissions, checked: boolean) => {
    setFormData((prev) => ({
      ...prev,
      permissions: {
        ...prev.permissions,
        [key]: checked,
      },
    }));
  };

  const handleClose = () => {
    if (!isSaving && !isLoading) {
      setFormData({
        name: '',
        description: '',
        permissions: { ...DEFAULT_PERMISSIONS },
      });
      onClose();
    }
  };

  // Reset form when template changes
  useState(() => {
    if (isOpen) {
      setFormData({
        name: template?.name || '',
        description: template?.description || '',
        permissions: template?.permissions || { ...DEFAULT_PERMISSIONS },
      });
    }
  });

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
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white shadow-xl transition-all">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
                      <ShieldCheckIcon className="w-5 h-5 text-blue-600" />
                    </div>
                    <Dialog.Title className="text-lg font-semibold text-gray-900">
                      {isEditing ? 'Edit Template' : 'Create Template'}
                    </Dialog.Title>
                  </div>
                  <button
                    onClick={handleClose}
                    className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
                  >
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6 space-y-5">
                  {/* Name */}
                  <div>
                    <label htmlFor="template-name" className="block text-sm font-medium text-gray-700 mb-1.5">
                      Template Name *
                    </label>
                    <input
                      id="template-name"
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                      placeholder="e.g., Grant Writer"
                      className="block w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 hover:border-gray-400"
                      disabled={isSaving}
                      required
                    />
                  </div>

                  {/* Description */}
                  <div>
                    <label htmlFor="template-description" className="block text-sm font-medium text-gray-700 mb-1.5">
                      Description
                    </label>
                    <input
                      id="template-description"
                      type="text"
                      value={formData.description}
                      onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
                      placeholder="Brief description of this template"
                      className="block w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 hover:border-gray-400"
                      disabled={isSaving}
                    />
                  </div>

                  {/* Permissions */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-3">
                      Permissions
                    </label>
                    <div className="space-y-2">
                      {PERMISSION_DEFINITIONS.map((perm) => (
                        <label
                          key={perm.key}
                          className={classNames(
                            'flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all',
                            formData.permissions[perm.key]
                              ? 'border-blue-200 bg-blue-50'
                              : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                          )}
                        >
                          <input
                            type="checkbox"
                            checked={formData.permissions[perm.key] || false}
                            onChange={(e) => handlePermissionChange(perm.key, e.target.checked)}
                            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            disabled={isSaving}
                          />
                          <div className="flex-1">
                            <span className="text-sm font-medium text-gray-900">{perm.label}</span>
                            <p className="text-xs text-gray-500">{perm.description}</p>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-end gap-3 pt-2">
                    <button
                      type="button"
                      onClick={handleClose}
                      className="px-4 py-2.5 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
                      disabled={isSaving}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSaving || isLoading || !formData.name.trim()}
                      className={classNames(
                        'inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all',
                        'bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600',
                        'shadow-lg shadow-blue-500/25 hover:shadow-xl hover:shadow-blue-500/30',
                        isSaving || !formData.name.trim() ? 'opacity-50 cursor-not-allowed' : 'hover:-translate-y-0.5'
                      )}
                    >
                      {isSaving ? (
                        <>
                          <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24">
                            <circle
                              className="opacity-25"
                              cx="12"
                              cy="12"
                              r="10"
                              stroke="currentColor"
                              strokeWidth="4"
                              fill="none"
                            />
                            <path
                              className="opacity-75"
                              fill="currentColor"
                              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                            />
                          </svg>
                          Saving...
                        </>
                      ) : isEditing ? (
                        'Update Template'
                      ) : (
                        'Create Template'
                      )}
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

export function PermissionTemplatesManager({
  templates,
  onCreateTemplate,
  onUpdateTemplate,
  onDeleteTemplate,
  isLoading = false,
}: PermissionTemplatesManagerProps) {
  const [showModal, setShowModal] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<PermissionTemplate | null>(null);

  const handleOpenCreate = () => {
    setEditingTemplate(null);
    setShowModal(true);
  };

  const handleOpenEdit = (template: PermissionTemplate) => {
    setEditingTemplate(template);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingTemplate(null);
  };

  const handleSave = async (data: TemplateFormData) => {
    if (editingTemplate) {
      await onUpdateTemplate(editingTemplate.id, {
        name: data.name,
        description: data.description || undefined,
        permissions: data.permissions,
      });
    } else {
      await onCreateTemplate({
        name: data.name,
        description: data.description || undefined,
        permissions: data.permissions,
      });
    }
  };

  // Separate default and custom templates
  const defaultTemplates = templates.filter((t) => t.is_default);
  const customTemplates = templates.filter((t) => !t.is_default);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Permission Templates</h2>
          <p className="text-sm text-gray-500 mt-1">
            Create reusable permission sets for team members
          </p>
        </div>
        <button
          onClick={handleOpenCreate}
          className={classNames(
            'inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-all',
            'bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600',
            'shadow-lg shadow-blue-500/25 hover:shadow-xl hover:shadow-blue-500/30 hover:-translate-y-0.5'
          )}
        >
          <PlusIcon className="w-4 h-4" />
          New Template
        </button>
      </div>

      {/* Default Templates */}
      {defaultTemplates.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-3">
            Default Templates
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {defaultTemplates.map((template) => (
              <TemplateCard
                key={template.id}
                template={template}
                onEdit={() => handleOpenEdit(template)}
                onDelete={() => onDeleteTemplate(template.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Custom Templates */}
      <div>
        {customTemplates.length > 0 ? (
          <>
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-3">
              Custom Templates
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {customTemplates.map((template) => (
                <TemplateCard
                  key={template.id}
                  template={template}
                  onEdit={() => handleOpenEdit(template)}
                  onDelete={() => onDeleteTemplate(template.id)}
                />
              ))}
            </div>
          </>
        ) : (
          <div className="text-center py-12 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200">
            <ShieldCheckIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <h3 className="text-sm font-medium text-gray-900 mb-1">No custom templates</h3>
            <p className="text-sm text-gray-500 mb-4">
              Create a template to quickly assign permissions to team members
            </p>
            <button
              onClick={handleOpenCreate}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-blue-600 hover:bg-blue-50 transition-colors"
            >
              <PlusIcon className="w-4 h-4" />
              Create Template
            </button>
          </div>
        )}
      </div>

      {/* Edit/Create Modal */}
      <TemplateEditModal
        isOpen={showModal}
        onClose={handleCloseModal}
        onSave={handleSave}
        template={editingTemplate}
        isLoading={isLoading}
      />
    </div>
  );
}

export default PermissionTemplatesManager;
