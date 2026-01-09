import { formatDistanceToNow } from 'date-fns';
import {
  CheckCircleIcon,
  XCircleIcon,
  ArrowUturnLeftIcon,
  ChatBubbleLeftIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { useReviewHistory } from '../../hooks/useReviews';
import { REVIEW_ACTION_CONFIGS } from '../../types/reviews';
import type { ReviewStageAction, ReviewAction } from '../../types/reviews';

interface ReviewHistoryProps {
  cardId: string;
}

const ACTION_ICONS: Record<ReviewAction, React.ComponentType<React.SVGProps<SVGSVGElement>>> = {
  approved: CheckCircleIcon,
  rejected: XCircleIcon,
  returned: ArrowUturnLeftIcon,
  commented: ChatBubbleLeftIcon,
};

export function ReviewHistory({ cardId }: ReviewHistoryProps) {
  const { data, isLoading, error } = useReviewHistory(cardId);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse flex gap-3">
            <div className="w-8 h-8 rounded-full bg-gray-200" />
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-gray-200 rounded w-1/3" />
              <div className="h-3 bg-gray-200 rounded w-2/3" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-6 text-sm text-red-500">
        Failed to load review history
      </div>
    );
  }

  const actions = data?.actions || [];

  if (actions.length === 0) {
    return (
      <div className="text-center py-8">
        <ClockIcon className="w-10 h-10 text-gray-300 mx-auto mb-2" />
        <p className="text-sm text-gray-500">No review actions yet</p>
        <p className="text-xs text-gray-400 mt-1">
          Actions will appear here as the review progresses
        </p>
      </div>
    );
  }

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
        <h4 className="text-sm font-medium text-gray-900">Review History</h4>
        <p className="text-xs text-gray-500 mt-0.5">{actions.length} action(s)</p>
      </div>

      <div className="divide-y divide-gray-100">
        {actions.map((action, index) => (
          <HistoryItem key={action.id} action={action} isFirst={index === 0} />
        ))}
      </div>
    </div>
  );
}

interface HistoryItemProps {
  action: ReviewStageAction;
  isFirst: boolean;
}

function HistoryItem({ action, isFirst }: HistoryItemProps) {
  const config = REVIEW_ACTION_CONFIGS[action.action];
  const Icon = ACTION_ICONS[action.action];
  const reviewerName = action.reviewer?.name || action.reviewer?.email || 'Unknown';

  return (
    <div className={`p-4 ${isFirst ? 'bg-blue-50/50' : ''}`}>
      <div className="flex gap-3">
        {/* Icon */}
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${config.bgColor}`}
        >
          <Icon className={`w-4 h-4 ${config.color}`} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <span className="text-sm font-medium text-gray-900">{reviewerName}</span>
            <span className={`text-sm ${config.color}`}>{config.label.toLowerCase()}</span>
            {action.stage_name && (
              <span className="text-sm text-gray-500">
                at <span className="font-medium">{action.stage_name}</span>
              </span>
            )}
          </div>

          {/* Timestamp */}
          <p className="text-xs text-gray-400 mt-0.5">
            {formatDistanceToNow(new Date(action.acted_at), { addSuffix: true })}
          </p>

          {/* Comments */}
          {action.comments && (
            <div className="mt-2 p-2 bg-gray-50 rounded-lg border border-gray-100">
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{action.comments}</p>
            </div>
          )}
        </div>

        {/* Badge for latest */}
        {isFirst && (
          <span className="flex-shrink-0 px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
            Latest
          </span>
        )}
      </div>
    </div>
  );
}

export default ReviewHistory;
