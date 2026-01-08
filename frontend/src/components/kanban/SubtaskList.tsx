import { useState } from 'react';
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline';
import { useCreateSubtask, useUpdateSubtask, useDeleteSubtask } from '../../hooks/useKanban';
import type { Subtask } from '../../types/kanban';

interface SubtaskListProps {
  applicationId: string;
  subtasks: Subtask[];
}

export function SubtaskList({ applicationId, subtasks }: SubtaskListProps) {
  const [newTitle, setNewTitle] = useState('');

  const createMutation = useCreateSubtask();
  const updateMutation = useUpdateSubtask();
  const deleteMutation = useDeleteSubtask();

  const handleAdd = () => {
    if (!newTitle.trim()) return;
    createMutation.mutate(
      { appId: applicationId, data: { title: newTitle } },
      { onSuccess: () => setNewTitle('') }
    );
  };

  const handleToggle = (subtask: Subtask) => {
    updateMutation.mutate({
      subtaskId: subtask.id,
      data: { is_completed: !subtask.is_completed },
    });
  };

  const handleDelete = (subtaskId: string) => {
    deleteMutation.mutate(subtaskId);
  };

  const completedCount = subtasks.filter(s => s.is_completed).length;

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      {subtasks.length > 0 && (
        <div className="flex items-center gap-3">
          <div className="flex-1 bg-gray-200 rounded-full h-2">
            <div
              className="bg-green-500 h-2 rounded-full transition-all"
              style={{ width: `${(completedCount / subtasks.length) * 100}%` }}
            />
          </div>
          <span className="text-sm text-gray-500">
            {completedCount}/{subtasks.length}
          </span>
        </div>
      )}

      {/* Subtask list */}
      <div className="space-y-2">
        {subtasks.map(subtask => (
          <div
            key={subtask.id}
            className="flex items-center gap-3 p-2 rounded hover:bg-gray-50 group"
          >
            <input
              type="checkbox"
              checked={subtask.is_completed}
              onChange={() => handleToggle(subtask)}
              className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className={`flex-1 text-sm ${subtask.is_completed ? 'line-through text-gray-400' : 'text-gray-700'}`}>
              {subtask.title}
            </span>
            <button
              onClick={() => handleDelete(subtask.id)}
              className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-opacity"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>

      {/* Add new subtask */}
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          placeholder="Add a subtask..."
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleAdd}
          disabled={!newTitle.trim() || createMutation.isPending}
          className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          <PlusIcon className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

export default SubtaskList;
