import React from 'react';
import { CheckIcon } from '@heroicons/react/24/solid';
import { ROLE_CONFIGS } from '../../types/reviews';
import type { ReviewWorkflow, ReviewStatus } from '../../types/reviews';

interface ReviewStageIndicatorProps {
  workflow: ReviewWorkflow;
  currentStage: number;
  status: ReviewStatus;
}

export const ReviewStageIndicator = React.memo(function ReviewStageIndicator({
  workflow,
  currentStage,
  status,
}: ReviewStageIndicatorProps) {
  const stages = workflow.stages;
  const isCompleted = status === 'approved';
  const isRejected = status === 'rejected';

  return (
    <div className="w-full">
      {/* Progress bar */}
      <div className="relative">
        {/* Background line */}
        <div className="absolute top-4 left-4 right-4 h-0.5 bg-gray-200" />

        {/* Progress line */}
        <div
          className={`absolute top-4 left-4 h-0.5 transition-all duration-500 ${
            isRejected ? 'bg-red-500' : isCompleted ? 'bg-green-500' : 'bg-blue-500'
          }`}
          style={{
            width: `calc(${Math.min(
              ((currentStage) / (stages.length - 1)) * 100,
              100
            )}% - 2rem)`,
          }}
        />

        {/* Stage dots */}
        <div className="relative flex justify-between">
          {stages.map((stage, index) => {
            const isActive = index === currentStage;
            const isPast = index < currentStage;
            const roleConfig = ROLE_CONFIGS[stage.required_role];

            return (
              <div
                key={stage.order}
                className="flex flex-col items-center"
                style={{ width: `${100 / stages.length}%` }}
              >
                {/* Stage dot */}
                <div
                  className={`
                    w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                    transition-all duration-300 relative z-10
                    ${
                      isPast || (isCompleted && index === stages.length - 1)
                        ? isRejected && index === currentStage
                          ? 'bg-red-500 text-white'
                          : 'bg-green-500 text-white'
                        : isActive
                        ? isRejected
                          ? 'bg-red-500 text-white ring-4 ring-red-100'
                          : 'bg-blue-500 text-white ring-4 ring-blue-100'
                        : 'bg-gray-200 text-gray-500'
                    }
                  `}
                >
                  {isPast || (isCompleted && index === stages.length - 1) ? (
                    <CheckIcon className="w-4 h-4" />
                  ) : (
                    index + 1
                  )}
                </div>

                {/* Stage label */}
                <div className="mt-2 text-center">
                  <p
                    className={`text-xs font-medium ${
                      isActive
                        ? 'text-gray-900'
                        : isPast
                        ? 'text-green-600'
                        : 'text-gray-500'
                    }`}
                  >
                    {stage.name}
                  </p>
                  <p className={`text-xs mt-0.5 ${roleConfig?.bgColor} ${roleConfig?.color} px-1.5 py-0.5 rounded-full inline-block`}>
                    {roleConfig?.label || stage.required_role}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Current stage info */}
      {!isCompleted && !isRejected && stages[currentStage] && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-100 rounded-lg">
          <div className="flex items-start gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5" />
            <div>
              <p className="text-sm font-medium text-blue-900">
                Current Stage: {stages[currentStage].name}
              </p>
              {stages[currentStage].sla_hours > 0 && (
                <p className="text-xs text-blue-700 mt-0.5">
                  Expected completion within {stages[currentStage].sla_hours} hours
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Completed state */}
      {isCompleted && (
        <div className="mt-4 p-3 bg-green-50 border border-green-100 rounded-lg">
          <div className="flex items-center gap-2">
            <CheckIcon className="w-5 h-5 text-green-600" />
            <p className="text-sm font-medium text-green-900">
              Review completed and approved
            </p>
          </div>
        </div>
      )}

      {/* Rejected state */}
      {isRejected && (
        <div className="mt-4 p-3 bg-red-50 border border-red-100 rounded-lg">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-full bg-red-100 flex items-center justify-center">
              <span className="text-red-600 text-xs font-bold">!</span>
            </div>
            <p className="text-sm font-medium text-red-900">
              Review rejected at stage: {stages[currentStage]?.name || 'Unknown'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
});

export default ReviewStageIndicator;
