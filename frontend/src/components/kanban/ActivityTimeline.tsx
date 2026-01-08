import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { useAddComment } from '../../hooks/useKanban';
import type { Activity } from '../../types/kanban';
import {
  ArrowRightIcon,
  CheckCircleIcon,
  PaperClipIcon,
  ChatBubbleLeftIcon,
  UserPlusIcon,
} from '@heroicons/react/24/outline';

interface ActivityTimelineProps {
  applicationId: string;
  activities: Activity[];
}

type ActionConfig = {
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  color: string;
  label: string;
};

const ACTION_CONFIG: Record<string, ActionConfig> = {
  created: { icon: CheckCircleIcon, color: 'bg-green-100 text-green-600', label: 'created' },
  stage_changed: { icon: ArrowRightIcon, color: 'bg-blue-100 text-blue-600', label: 'moved' },
  subtask_completed: { icon: CheckCircleIcon, color: 'bg-green-100 text-green-600', label: 'completed subtask' },
  subtask_added: { icon: CheckCircleIcon, color: 'bg-gray-100 text-gray-600', label: 'added subtask' },
  subtask_deleted: { icon: CheckCircleIcon, color: 'bg-red-100 text-red-600', label: 'deleted subtask' },
  attachment_added: { icon: PaperClipIcon, color: 'bg-purple-100 text-purple-600', label: 'attached' },
  attachment_deleted: { icon: PaperClipIcon, color: 'bg-red-100 text-red-600', label: 'removed attachment' },
  comment_added: { icon: ChatBubbleLeftIcon, color: 'bg-yellow-100 text-yellow-600', label: 'commented' },
  assignee_added: { icon: UserPlusIcon, color: 'bg-indigo-100 text-indigo-600', label: 'assigned' },
  assignee_removed: { icon: UserPlusIcon, color: 'bg-red-100 text-red-600', label: 'unassigned' },
  field_updated: { icon: CheckCircleIcon, color: 'bg-gray-100 text-gray-600', label: 'updated field' },
  priority_changed: { icon: ArrowRightIcon, color: 'bg-amber-100 text-amber-600', label: 'changed priority' },
};

export function ActivityTimeline({ applicationId, activities }: ActivityTimelineProps) {
  const [comment, setComment] = useState('');
  const addCommentMutation = useAddComment();

  const handleAddComment = () => {
    if (!comment.trim()) return;
    addCommentMutation.mutate(
      { appId: applicationId, content: comment },
      { onSuccess: () => setComment('') }
    );
  };

  const getActionDetails = (activity: Activity): string => {
    const details = activity.details || {};
    switch (activity.action) {
      case 'stage_changed':
        return `from ${details.from_stage} to ${details.to_stage}`;
      case 'subtask_completed':
      case 'subtask_added':
      case 'subtask_deleted':
        return details.title || '';
      case 'attachment_added':
      case 'attachment_deleted':
        return details.filename || '';
      case 'comment_added':
        return details.content || '';
      case 'priority_changed':
        return `from ${details.from_priority} to ${details.to_priority}`;
      case 'field_updated':
        return details.field_name || '';
      default:
        return '';
    }
  };

  const getUserName = (activity: Activity): string => {
    return activity.user?.name || activity.user?.email || 'System';
  };

  return (
    <div className="space-y-4">
      {/* Add comment */}
      <div className="flex gap-2">
        <input
          type="text"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAddComment()}
          placeholder="Add a comment..."
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleAddComment}
          disabled={!comment.trim() || addCommentMutation.isPending}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          Post
        </button>
      </div>

      {/* Timeline */}
      <div className="space-y-3">
        {activities.map((activity) => {
          const config = ACTION_CONFIG[activity.action] || ACTION_CONFIG.created;
          const Icon = config.icon;

          return (
            <div key={activity.id} className="flex gap-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${config.color}`}>
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-900">
                  <span className="font-medium">{getUserName(activity)}</span>
                  {' '}{config.label}
                </p>
                {getActionDetails(activity) && (
                  <p className="text-sm text-gray-500 truncate">
                    {getActionDetails(activity)}
                  </p>
                )}
                <p className="text-xs text-gray-400 mt-1">
                  {formatDistanceToNow(new Date(activity.created_at), { addSuffix: true })}
                </p>
              </div>
            </div>
          );
        })}

        {activities.length === 0 && (
          <p className="text-center text-gray-400 py-8 text-sm">
            No activity yet
          </p>
        )}
      </div>
    </div>
  );
}

export default ActivityTimeline;
