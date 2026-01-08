import { useMemo } from 'react';
import { useFieldDefinitions, useUpdateCardFields, useKanbanBoard } from '../../hooks/useKanban';
import type { ApplicationStage, KanbanCard, CustomFieldDefinition } from '../../types/kanban';

interface CustomFieldsEditorProps {
  applicationId: string;
}

const STAGES: ApplicationStage[] = ['researching', 'writing', 'submitted', 'awarded', 'rejected'];

export function CustomFieldsEditor({ applicationId }: CustomFieldsEditorProps) {
  const { data: fieldDefs = [] } = useFieldDefinitions();
  const { data: board } = useKanbanBoard();
  const updateFieldsMutation = useUpdateCardFields();

  // Find current card to get existing values
  const card = useMemo(() => {
    if (!board) return null;
    for (const stage of STAGES) {
      const found = board.columns[stage]?.find((c: KanbanCard) => c.id === applicationId);
      if (found) return found;
    }
    return null;
  }, [board, applicationId]);

  const handleFieldChange = (fieldId: string, value: string | number | boolean) => {
    updateFieldsMutation.mutate({
      appId: applicationId,
      fields: { [fieldId]: value },
    });
  };

  if (fieldDefs.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500 text-sm">No custom fields defined</p>
        <p className="text-gray-400 text-xs mt-1">
          Add custom fields from board settings
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {fieldDefs.map((field: CustomFieldDefinition) => {
        const currentValue = card?.custom_fields?.[field.id];

        return (
          <div key={field.id}>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {field.name}
              {field.is_required && <span className="text-red-500 ml-1">*</span>}
            </label>

            {field.field_type === 'text' && (
              <input
                type="text"
                value={currentValue || ''}
                onChange={(e) => handleFieldChange(field.id, e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            )}

            {field.field_type === 'number' && (
              <input
                type="number"
                value={currentValue || ''}
                onChange={(e) => handleFieldChange(field.id, e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            )}

            {field.field_type === 'date' && (
              <input
                type="date"
                value={currentValue || ''}
                onChange={(e) => handleFieldChange(field.id, e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            )}

            {(field.field_type === 'select' || field.field_type === 'multiselect') && (
              <select
                value={currentValue || ''}
                onChange={(e) => handleFieldChange(field.id, e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select...</option>
                {field.options?.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            )}

            {field.field_type === 'checkbox' && (
              <input
                type="checkbox"
                checked={currentValue || false}
                onChange={(e) => handleFieldChange(field.id, e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
            )}

            {field.field_type === 'url' && (
              <input
                type="url"
                value={currentValue || ''}
                onChange={(e) => handleFieldChange(field.id, e.target.value)}
                placeholder="https://..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default CustomFieldsEditor;
