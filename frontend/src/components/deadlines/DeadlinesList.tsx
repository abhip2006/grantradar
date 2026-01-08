import {
  CalendarIcon,
  PencilIcon,
  TrashIcon,
  CheckCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline';
import type { Deadline, DeadlineStatus } from '../../types';
import { format } from 'date-fns';

interface DeadlinesListProps {
  deadlines: Deadline[];
  onEdit: (deadline: Deadline) => void;
  onDelete: (id: string) => void;
  onStatusChange: (id: string, status: DeadlineStatus) => void;
}

const priorityColors = {
  low: 'bg-gray-100 text-gray-700',
  medium: 'bg-blue-100 text-blue-700',
  high: 'bg-orange-100 text-orange-700',
  critical: 'bg-red-100 text-red-700',
};

const statusColors = {
  active: 'bg-green-100 text-green-700',
  completed: 'bg-gray-100 text-gray-700',
  archived: 'bg-gray-50 text-gray-500',
};

export function DeadlinesList({ deadlines, onEdit, onDelete, onStatusChange }: DeadlinesListProps) {
  if (deadlines.length === 0) {
    return (
      <div className="text-center py-12">
        <CalendarIcon className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">No deadlines</h3>
        <p className="mt-1 text-sm text-gray-500">
          Get started by creating a new deadline.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white shadow rounded-lg overflow-hidden">
      <ul className="divide-y divide-gray-200">
        {deadlines.map((deadline) => (
          <li key={deadline.id} className={`p-4 hover:bg-gray-50 ${deadline.is_overdue ? 'bg-red-50' : ''}`}>
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  <div
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: deadline.color }}
                  />
                  <h3 className="text-sm font-medium text-gray-900 truncate">
                    {deadline.title}
                  </h3>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${priorityColors[deadline.priority]}`}>
                    {deadline.priority}
                  </span>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusColors[deadline.status]}`}>
                    {deadline.status}
                  </span>
                </div>
                <div className="mt-1 flex items-center gap-4 text-sm text-gray-500">
                  {deadline.funder && (
                    <span>{deadline.funder}</span>
                  )}
                  {deadline.mechanism && (
                    <span>{deadline.mechanism}</span>
                  )}
                  <span className="flex items-center">
                    <CalendarIcon className="h-4 w-4 mr-1" />
                    {format(new Date(deadline.sponsor_deadline), 'MMM d, yyyy')}
                  </span>
                  <span className={`flex items-center ${deadline.is_overdue ? 'text-red-600 font-medium' : ''}`}>
                    <ClockIcon className="h-4 w-4 mr-1" />
                    {deadline.is_overdue
                      ? `${Math.abs(deadline.days_until_deadline)} days overdue`
                      : deadline.days_until_deadline === 0
                        ? 'Due today'
                        : `${deadline.days_until_deadline} days left`
                    }
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {deadline.status === 'active' && (
                  <button
                    onClick={() => onStatusChange(deadline.id, 'completed')}
                    className="p-2 text-gray-400 hover:text-green-600 rounded-full hover:bg-green-50"
                    title="Mark complete"
                  >
                    <CheckCircleIcon className="h-5 w-5" />
                  </button>
                )}
                <button
                  onClick={() => onEdit(deadline)}
                  className="p-2 text-gray-400 hover:text-blue-600 rounded-full hover:bg-blue-50"
                  title="Edit"
                >
                  <PencilIcon className="h-5 w-5" />
                </button>
                <button
                  onClick={() => onDelete(deadline.id)}
                  className="p-2 text-gray-400 hover:text-red-600 rounded-full hover:bg-red-50"
                  title="Delete"
                >
                  <TrashIcon className="h-5 w-5" />
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
