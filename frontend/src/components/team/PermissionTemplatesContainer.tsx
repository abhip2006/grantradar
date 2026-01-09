import { PermissionTemplatesManager } from './PermissionTemplatesManager';
import {
  usePermissionTemplates,
  useCreateTemplate,
  useUpdateTemplate,
  useDeleteTemplate,
} from '../../hooks/usePermissionTemplates';
import { useToast } from '../../contexts/ToastContext';
import type { PermissionTemplateCreate, PermissionTemplateUpdate } from '../../types/team';

/**
 * Container component that connects PermissionTemplatesManager to hooks.
 * This is the component that should be used in the Team page.
 */
export function PermissionTemplatesContainer() {
  const { showToast } = useToast();
  const { data: templates = [], isLoading } = usePermissionTemplates();
  const createTemplate = useCreateTemplate();
  const updateTemplate = useUpdateTemplate();
  const deleteTemplate = useDeleteTemplate();

  const handleCreateTemplate = async (data: PermissionTemplateCreate) => {
    try {
      await createTemplate.mutateAsync(data);
      showToast('Template created successfully', 'success');
    } catch (error: any) {
      showToast(error.response?.data?.detail || 'Failed to create template', 'error');
      throw error;
    }
  };

  const handleUpdateTemplate = async (id: string, data: PermissionTemplateUpdate) => {
    try {
      await updateTemplate.mutateAsync({ id, data });
      showToast('Template updated successfully', 'success');
    } catch (error: any) {
      showToast(error.response?.data?.detail || 'Failed to update template', 'error');
      throw error;
    }
  };

  const handleDeleteTemplate = async (id: string) => {
    try {
      await deleteTemplate.mutateAsync(id);
      showToast('Template deleted successfully', 'success');
    } catch (error: any) {
      showToast(error.response?.data?.detail || 'Failed to delete template', 'error');
      throw error;
    }
  };

  return (
    <PermissionTemplatesManager
      templates={templates}
      onCreateTemplate={handleCreateTemplate}
      onUpdateTemplate={handleUpdateTemplate}
      onDeleteTemplate={handleDeleteTemplate}
      isLoading={isLoading}
    />
  );
}

export default PermissionTemplatesContainer;
