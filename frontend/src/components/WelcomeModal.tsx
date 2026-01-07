import { useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import {
  SparklesIcon,
  MagnifyingGlassIcon,
  BellIcon,
  XMarkIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline';

interface WelcomeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const steps = [
  {
    icon: SparklesIcon,
    title: 'Welcome to GrantRadar!',
    description:
      "You're all set up. We're now matching grants from NIH, NSF, and Grants.gov against your organization profile.",
    color: 'blue',
  },
  {
    icon: MagnifyingGlassIcon,
    title: 'How Matching Works',
    description:
      'Each grant gets a match score (0-100) based on how well it aligns with your focus areas and eligibility. Higher scores mean better fits.',
    color: 'yellow',
  },
  {
    icon: BellIcon,
    title: "What's Next",
    description:
      "Your first matches will appear within 5 minutes. We'll also send you email alerts when new high-scoring grants are found.",
    color: 'green',
  },
];

export function WelcomeModal({ isOpen, onClose }: WelcomeModalProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [dontShowAgain, setDontShowAgain] = useState(false);

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleClose();
    }
  };

  const handleClose = () => {
    if (dontShowAgain) {
      localStorage.setItem('grantradar_welcome_dismissed', 'true');
    }
    onClose();
  };

  const step = steps[currentStep];
  const isLastStep = currentStep === steps.length - 1;

  const colorMap: Record<string, { bg: string; icon: string }> = {
    blue: { bg: 'bg-[var(--gr-blue-50)]', icon: 'text-[var(--gr-blue-600)]' },
    yellow: { bg: 'bg-[var(--gr-yellow-50)]', icon: 'text-[var(--gr-yellow-600)]' },
    green: { bg: 'bg-green-50', icon: 'text-[var(--gr-green-600)]' },
  };
  const colors = colorMap[step.color] || colorMap.blue;

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
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-8 text-left align-middle shadow-xl transition-all">
                {/* Close Button */}
                <button
                  onClick={handleClose}
                  className="absolute top-4 right-4 text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)] transition-colors"
                >
                  <XMarkIcon className="w-5 h-5" />
                </button>

                {/* Icon */}
                <div className={`w-16 h-16 ${colors.bg} rounded-2xl flex items-center justify-center mb-6 mx-auto`}>
                  <step.icon className={`w-8 h-8 ${colors.icon}`} />
                </div>

                {/* Content */}
                <Dialog.Title
                  as="h3"
                  className="text-2xl font-display font-medium text-[var(--gr-text-primary)] text-center mb-3"
                >
                  {step.title}
                </Dialog.Title>

                <p className="text-[var(--gr-text-secondary)] text-center leading-relaxed mb-8">
                  {step.description}
                </p>

                {/* Progress Dots */}
                <div className="flex justify-center gap-2 mb-6">
                  {steps.map((_, index) => (
                    <button
                      key={index}
                      onClick={() => setCurrentStep(index)}
                      className={`w-2 h-2 rounded-full transition-colors ${
                        index === currentStep
                          ? 'bg-[var(--gr-blue-600)]'
                          : 'bg-[var(--gr-gray-200)] hover:bg-[var(--gr-gray-300)]'
                      }`}
                    />
                  ))}
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-3">
                  <button
                    onClick={handleNext}
                    className="btn-primary w-full justify-center"
                  >
                    {isLastStep ? (
                      'Start Exploring'
                    ) : (
                      <>
                        Next
                        <ArrowRightIcon className="w-4 h-4" />
                      </>
                    )}
                  </button>

                  {isLastStep && (
                    <label className="flex items-center justify-center gap-2 text-sm text-[var(--gr-text-tertiary)] cursor-pointer">
                      <input
                        type="checkbox"
                        checked={dontShowAgain}
                        onChange={(e) => setDontShowAgain(e.target.checked)}
                        className="rounded border-[var(--gr-border-default)]"
                      />
                      Don't show this again
                    </label>
                  )}

                  {!isLastStep && (
                    <button
                      onClick={handleClose}
                      className="text-sm text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)] transition-colors"
                    >
                      Skip tour
                    </button>
                  )}
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}

export default WelcomeModal;
