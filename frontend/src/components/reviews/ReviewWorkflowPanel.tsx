import React, { useState } from 'react';
import {
  PlayIcon,
  XMarkIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useApplicationReview, useStartReview, useCancelReview, useReviewWorkflows } from '../../hooks/useReviews';
import { ReviewStageIndicator } from './ReviewStageIndicator';
import { ReviewActionModal } from './ReviewActionModal';
import { ReviewHistory } from './ReviewHistory';
import { REVIEW_STATUS_CONFIGS } from '../../types/reviews';
import type { ReviewWorkflow } from '../../types/reviews';

interface ReviewWorkflowPanelProps {
  cardId: string;
  onClose?: () => void;
}

export const ReviewWorkflowPanel = React.memo(function ReviewWorkflowPanel({ cardId, onClose }: ReviewWorkflowPanelProps) {
  const [showActionModal, setShowActionModal] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string>('');

  const { data: review, isLoading: reviewLoading } = useApplicationReview(cardId);
  const { data: workflowsData, isLoading: workflowsLoading } = useReviewWorkflows();
  const startReviewMutation = useStartReview();
  const cancelReviewMutation = useCancelReview();

  const workflows = workflowsData?.workflows || [];
  const defaultWorkflow = workflows.find((w) => w.is_default);

  const handleStartReview = () => {
    const workflowId = selectedWorkflowId || defaultWorkflow?.id;
    startReviewMutation.mutate({
      cardId,
      data: workflowId ? { workflow_id: workflowId } : undefined,
    });
  };

  const handleCancelReview = () => {
    if (window.confirm('Are you sure you want to cancel this review process?')) {
      cancelReviewMutation.mutate(cardId);
    }
  };

  if (reviewLoading || workflowsLoading) {
    return (
      <div className="p-4 space-y-4">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-200 rounded w-1/3"></div>
          <div className="h-20 bg-gray-200 rounded"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  // No active review - show start review UI
  if (!review) {
    return (
      <div className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">Internal Review</h3>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <XMarkIcon className="w-5 h-5 text-gray-500" />
            </button>
          )}
        </div>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
              <PlayIcon className="w-5 h-5 text-blue-600" />
            </div>
            <div className="flex-1">
              <h4 className="font-medium text-gray-900">Start Review Process</h4>
              <p className="text-sm text-gray-500 mt-1">
                Begin the internal review workflow for this application. Reviews help ensure
                quality and compliance before submission.
              </p>
            </div>
          </div>

          {workflows.length > 1 && (
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Select Workflow
              </label>
              <select
                value={selectedWorkflowId}
                onChange={(e) => setSelectedWorkflowId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Default Workflow</option>
                {workflows.map((workflow) => (
                  <option key={workflow.id} value={workflow.id}>
                    {workflow.name} {workflow.is_default && '(Default)'}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="mt-4">
            <button
              onClick={handleStartReview}
              disabled={startReviewMutation.isPending}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {startReviewMutation.isPending ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <PlayIcon className="w-4 h-4" />
                  Start Review
                </>
              )}
            </button>
          </div>
        </div>

        {/* Preview workflow stages */}
        {(selectedWorkflowId || defaultWorkflow) && (
          <WorkflowPreview
            workflow={
              workflows.find((w) => w.id === selectedWorkflowId) || defaultWorkflow!
            }
          />
        )}
      </div>
    );
  }

  // Active review - show status and controls
  const statusConfig = REVIEW_STATUS_CONFIGS[review.status];
  const currentWorkflow = review.workflow || workflows.find((w) => w.id === review.workflow_id);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Internal Review</h3>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <XMarkIcon className="w-5 h-5 text-gray-500" />
          </button>
        )}
      </div>

      {/* Status Badge */}
      <div className="flex items-center justify-between">
        <div
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium ${statusConfig.bgColor} ${statusConfig.color}`}
        >
          <StatusIcon status={review.status} />
          {statusConfig.label}
        </div>
        {review.is_overdue && (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
            <ExclamationTriangleIcon className="w-3.5 h-3.5" />
            Overdue
          </span>
        )}
      </div>

      {/* Progress Indicator */}
      {currentWorkflow && (
        <ReviewStageIndicator
          workflow={currentWorkflow}
          currentStage={review.current_stage}
          status={review.status}
        />
      )}

      {/* SLA Info */}
      {review.sla_deadline && review.status === 'in_review' && (
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <ClockIcon className="w-4 h-4" />
          <span>
            Due by {new Date(review.sla_deadline).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              hour: 'numeric',
              minute: '2-digit',
            })}
          </span>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        {(review.status === 'pending' || review.status === 'in_review') && (
          <button
            onClick={() => setShowActionModal(true)}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Take Action
          </button>
        )}
        <button
          onClick={() => setShowHistory(!showHistory)}
          className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          {showHistory ? 'Hide History' : 'View History'}
        </button>
        {(review.status === 'pending' || review.status === 'in_review') && (
          <button
            onClick={handleCancelReview}
            disabled={cancelReviewMutation.isPending}
            className="px-4 py-2 border border-red-300 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Review History */}
      {showHistory && <ReviewHistory cardId={cardId} />}

      {/* Action Modal */}
      {showActionModal && (
        <ReviewActionModal
          cardId={cardId}
          currentStage={review.current_stage}
          workflow={currentWorkflow}
          onClose={() => setShowActionModal(false)}
        />
      )}
    </div>
  );
});

// Helper component to show workflow stages preview
const WorkflowPreview = React.memo(function WorkflowPreview({ workflow }: { workflow: ReviewWorkflow }) {
  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <h4 className="text-sm font-medium text-gray-900 mb-3">Workflow Stages</h4>
      <div className="space-y-2">
        {workflow.stages.map((stage, index) => (
          <div
            key={stage.order}
            className="flex items-center gap-3 text-sm"
          >
            <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs font-medium text-gray-600">
              {index + 1}
            </div>
            <div className="flex-1">
              <span className="text-gray-900">{stage.name}</span>
              {stage.sla_hours > 0 && (
                <span className="ml-2 text-gray-500">
                  ({stage.sla_hours}h SLA)
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});

// Helper component for status icons
function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'approved':
      return <CheckCircleIcon className="w-4 h-4" />;
    case 'escalated':
      return <ExclamationTriangleIcon className="w-4 h-4" />;
    default:
      return <ClockIcon className="w-4 h-4" />;
  }
}

export default ReviewWorkflowPanel;
