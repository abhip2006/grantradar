import { useState, Fragment } from 'react';
import { Dialog, Transition, RadioGroup } from '@headlessui/react';
import {
  XMarkIcon,
  CheckIcon,
  XCircleIcon,
  ArrowUturnLeftIcon,
  ChatBubbleLeftIcon,
} from '@heroicons/react/24/outline';
import { useSubmitReviewAction, useCanUserReview } from '../../hooks/useReviews';
import { REVIEW_ACTION_CONFIGS, ROLE_CONFIGS } from '../../types/reviews';
import type { ReviewWorkflow, ReviewAction } from '../../types/reviews';

interface ReviewActionModalProps {
  cardId: string;
  currentStage: number;
  workflow?: ReviewWorkflow;
  onClose: () => void;
}

const ACTION_OPTIONS: ReviewAction[] = ['approved', 'rejected', 'returned', 'commented'];

const ACTION_ICONS: Record<ReviewAction, React.ComponentType<React.SVGProps<SVGSVGElement>>> = {
  approved: CheckIcon,
  rejected: XCircleIcon,
  returned: ArrowUturnLeftIcon,
  commented: ChatBubbleLeftIcon,
};

export function ReviewActionModal({
  cardId,
  currentStage,
  workflow,
  onClose,
}: ReviewActionModalProps) {
  const [selectedAction, setSelectedAction] = useState<ReviewAction | null>(null);
  const [comments, setComments] = useState('');

  const { data: canReviewData, isLoading: checkingPermission } = useCanUserReview(cardId);
  const submitActionMutation = useSubmitReviewAction();

  const currentStageName = workflow?.stages[currentStage]?.name || `Stage ${currentStage + 1}`;
  const requiredRole = workflow?.stages[currentStage]?.required_role;
  const roleConfig = requiredRole ? ROLE_CONFIGS[requiredRole] : null;

  const handleSubmit = () => {
    if (!selectedAction) return;

    submitActionMutation.mutate(
      {
        cardId,
        data: {
          action: selectedAction,
          comments: comments.trim() || undefined,
        },
      },
      {
        onSuccess: () => {
          onClose();
        },
      }
    );
  };

  const isCommentsRequired =
    selectedAction === 'rejected' || selectedAction === 'returned' || selectedAction === 'commented';

  const canSubmit =
    selectedAction !== null &&
    (!isCommentsRequired || comments.trim().length > 0) &&
    canReviewData?.can_review;

  return (
    <Transition appear show as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/25" />
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
              <Dialog.Panel className="w-full max-w-md bg-white rounded-xl shadow-xl">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b">
                  <Dialog.Title className="text-lg font-semibold text-gray-900">
                    Review Action
                  </Dialog.Title>
                  <button
                    onClick={onClose}
                    className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <XMarkIcon className="w-5 h-5 text-gray-500" />
                  </button>
                </div>

                <div className="p-4 space-y-4">
                  {/* Current stage info */}
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-sm text-gray-600">Current Stage</p>
                    <p className="font-medium text-gray-900">{currentStageName}</p>
                    {roleConfig && (
                      <span
                        className={`inline-flex items-center mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${roleConfig.bgColor} ${roleConfig.color}`}
                      >
                        Requires: {roleConfig.label}
                      </span>
                    )}
                  </div>

                  {/* Permission check */}
                  {checkingPermission ? (
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
                      Checking permissions...
                    </div>
                  ) : !canReviewData?.can_review ? (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                      <p className="text-sm font-medium text-amber-800">Cannot take action</p>
                      <p className="text-sm text-amber-700 mt-1">
                        {canReviewData?.reason || 'You do not have permission to review at this stage.'}
                      </p>
                    </div>
                  ) : null}

                  {/* Action selection */}
                  {canReviewData?.can_review && (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Select Action
                        </label>
                        <RadioGroup value={selectedAction} onChange={setSelectedAction}>
                          <div className="space-y-2">
                            {ACTION_OPTIONS.map((action) => {
                              const config = REVIEW_ACTION_CONFIGS[action];
                              const Icon = ACTION_ICONS[action];

                              return (
                                <RadioGroup.Option
                                  key={action}
                                  value={action}
                                  className={({ checked }) =>
                                    `relative flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                                      checked
                                        ? 'border-blue-500 bg-blue-50'
                                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                                    }`
                                  }
                                >
                                  {({ checked }) => (
                                    <>
                                      <div
                                        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${config.bgColor}`}
                                      >
                                        <Icon className={`w-4 h-4 ${config.color}`} />
                                      </div>
                                      <div className="flex-1">
                                        <RadioGroup.Label
                                          as="p"
                                          className="text-sm font-medium text-gray-900"
                                        >
                                          {config.label}
                                        </RadioGroup.Label>
                                        <RadioGroup.Description
                                          as="p"
                                          className="text-xs text-gray-500 mt-0.5"
                                        >
                                          {config.description}
                                        </RadioGroup.Description>
                                      </div>
                                      {checked && (
                                        <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
                                          <CheckIcon className="w-3 h-3 text-white" />
                                        </div>
                                      )}
                                    </>
                                  )}
                                </RadioGroup.Option>
                              );
                            })}
                          </div>
                        </RadioGroup>
                      </div>

                      {/* Comments */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Comments
                          {isCommentsRequired && (
                            <span className="text-red-500 ml-1">*</span>
                          )}
                        </label>
                        <textarea
                          value={comments}
                          onChange={(e) => setComments(e.target.value)}
                          placeholder={
                            isCommentsRequired
                              ? 'Please provide feedback or reason...'
                              : 'Optional comments or feedback...'
                          }
                          rows={4}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                        />
                        {isCommentsRequired && comments.trim().length === 0 && (
                          <p className="text-xs text-red-500 mt-1">
                            Comments are required for this action
                          </p>
                        )}
                      </div>
                    </>
                  )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-2 p-4 border-t bg-gray-50">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSubmit}
                    disabled={!canSubmit || submitActionMutation.isPending}
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 ${
                      selectedAction === 'rejected'
                        ? 'bg-red-600 text-white hover:bg-red-700'
                        : selectedAction === 'approved'
                        ? 'bg-green-600 text-white hover:bg-green-700'
                        : 'bg-blue-600 text-white hover:bg-blue-700'
                    }`}
                  >
                    {submitActionMutation.isPending ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Submitting...
                      </>
                    ) : (
                      'Submit'
                    )}
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}

export default ReviewActionModal;
