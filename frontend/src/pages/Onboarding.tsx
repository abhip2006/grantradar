import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import {
  AcademicCapIcon,
  BeakerIcon,
  UserGroupIcon,
  BuildingLibraryIcon,
  CheckCircleIcon,
  ArrowRightIcon,
  ArrowLeftIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { onboardingApi } from '../services/api';
import type { OnboardingData, CareerStage, CitizenshipStatus, InstitutionType } from '../types';

// Research area suggestions
const researchAreaSuggestions = [
  'Cancer Biology',
  'Immunology',
  'Neuroscience',
  'Cardiovascular Research',
  'Infectious Diseases',
  'Genetics & Genomics',
  'Cell Biology',
  'Molecular Biology',
  'Biochemistry',
  'Biomedical Engineering',
  'Public Health',
  'Epidemiology',
  'Clinical Research',
  'Drug Discovery',
  'Bioinformatics',
  'Stem Cell Research',
  'Regenerative Medicine',
  'Microbiology',
  'Virology',
  'Structural Biology',
];

// Method suggestions
const methodSuggestions = [
  'CRISPR/Gene Editing',
  'RNA Sequencing',
  'Mass Spectrometry',
  'Flow Cytometry',
  'Microscopy',
  'Clinical Trials',
  'Animal Models',
  'Cell Culture',
  'Computational Modeling',
  'Machine Learning',
  'Statistical Analysis',
  'Proteomics',
  'Single-Cell Analysis',
  'High-Throughput Screening',
  'X-ray Crystallography',
];

const careerStages: { value: CareerStage; label: string; description: string }[] = [
  { value: 'early_career', label: 'Early Career', description: 'Postdoc or early faculty (0-5 years)' },
  { value: 'mid_career', label: 'Mid Career', description: 'Established faculty (5-15 years)' },
  { value: 'established', label: 'Established', description: 'Senior faculty (15+ years)' },
  { value: 'senior', label: 'Senior/Emeritus', description: 'Department head or emeritus' },
];

const citizenshipStatuses: { value: CitizenshipStatus; label: string }[] = [
  { value: 'us_citizen', label: 'US Citizen' },
  { value: 'permanent_resident', label: 'Permanent Resident' },
  { value: 'visa_holder', label: 'Visa Holder' },
  { value: 'international', label: 'International' },
];

const institutionTypes: { value: InstitutionType; label: string }[] = [
  { value: 'r1_university', label: 'R1 University' },
  { value: 'r2_university', label: 'R2 University' },
  { value: 'liberal_arts', label: 'Liberal Arts College' },
  { value: 'community_college', label: 'Community College' },
  { value: 'hbcu', label: 'HBCU' },
  { value: 'msi', label: 'Minority-Serving Institution' },
  { value: 'nonprofit', label: 'Research Nonprofit' },
  { value: 'industry', label: 'Industry/Pharma' },
  { value: 'government', label: 'Government Lab' },
  { value: 'other', label: 'Other' },
];

type Step = 'research' | 'methods' | 'career' | 'eligibility';

export function Onboarding() {
  const { user, refreshUser } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [currentStep, setCurrentStep] = useState<Step>('research');
  const [formData, setFormData] = useState<OnboardingData>({
    name: user?.name || '',
    institution: user?.institution || '',
    research_areas: [],
    methods: [],
    career_stage: undefined,
    citizenship_status: undefined,
    institution_type: undefined,
    is_pi_eligible: false,
  });
  const [customResearchArea, setCustomResearchArea] = useState('');
  const [customMethod, setCustomMethod] = useState('');

  const onboardingMutation = useMutation({
    mutationFn: onboardingApi.completeOnboarding,
    onSuccess: async () => {
      showToast('Profile created! Grant matching will begin shortly.', 'success');
      await refreshUser();
      navigate('/dashboard');
    },
    onError: (error: Error) => {
      showToast(error.message || 'Failed to create profile', 'error');
    },
  });

  const steps: { key: Step; label: string; icon: React.ElementType }[] = [
    { key: 'research', label: 'Research Areas', icon: AcademicCapIcon },
    { key: 'methods', label: 'Methods', icon: BeakerIcon },
    { key: 'career', label: 'Career Stage', icon: UserGroupIcon },
    { key: 'eligibility', label: 'Eligibility', icon: BuildingLibraryIcon },
  ];

  const currentStepIndex = steps.findIndex((s) => s.key === currentStep);

  const canProceed = () => {
    switch (currentStep) {
      case 'research':
        return formData.research_areas.length > 0;
      case 'methods':
        return true; // Methods are optional
      case 'career':
        return formData.career_stage !== undefined;
      case 'eligibility':
        return true; // All optional on this step
      default:
        return false;
    }
  };

  const nextStep = () => {
    const idx = currentStepIndex;
    if (idx < steps.length - 1) {
      setCurrentStep(steps[idx + 1].key);
    }
  };

  const prevStep = () => {
    const idx = currentStepIndex;
    if (idx > 0) {
      setCurrentStep(steps[idx - 1].key);
    }
  };

  const handleSubmit = () => {
    if (formData.research_areas.length === 0) {
      showToast('Please select at least one research area', 'error');
      setCurrentStep('research');
      return;
    }
    onboardingMutation.mutate(formData);
  };

  const toggleResearchArea = (area: string) => {
    setFormData((prev) => ({
      ...prev,
      research_areas: prev.research_areas.includes(area)
        ? prev.research_areas.filter((a) => a !== area)
        : [...prev.research_areas, area],
    }));
  };

  const addCustomResearchArea = () => {
    if (customResearchArea.trim() && !formData.research_areas.includes(customResearchArea.trim())) {
      setFormData((prev) => ({
        ...prev,
        research_areas: [...prev.research_areas, customResearchArea.trim()],
      }));
      setCustomResearchArea('');
    }
  };

  const toggleMethod = (method: string) => {
    setFormData((prev) => ({
      ...prev,
      methods: (prev.methods || []).includes(method)
        ? (prev.methods || []).filter((m) => m !== method)
        : [...(prev.methods || []), method],
    }));
  };

  const addCustomMethod = () => {
    if (customMethod.trim() && !(formData.methods || []).includes(customMethod.trim())) {
      setFormData((prev) => ({
        ...prev,
        methods: [...(prev.methods || []), customMethod.trim()],
      }));
      setCustomMethod('');
    }
  };

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)] flex flex-col">
      {/* Header */}
      <header className="border-b border-[var(--gr-border-subtle)] bg-[var(--gr-bg-elevated)]">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-[var(--gr-amber-500)] to-[var(--gr-amber-600)]">
              <SparklesIcon className="h-6 w-6 text-[var(--gr-slate-950)]" />
            </div>
            <div>
              <h1 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
                Complete Your Profile
              </h1>
              <p className="text-sm text-[var(--gr-text-tertiary)]">
                Help us find the best grants for your research
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Progress bar */}
      <div className="bg-[var(--gr-bg-elevated)] border-b border-[var(--gr-border-subtle)]">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            {steps.map((step, idx) => (
              <div key={step.key} className="flex items-center">
                <button
                  onClick={() => setCurrentStep(step.key)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all ${
                    currentStep === step.key
                      ? 'bg-[var(--gr-amber-500)]/10 text-[var(--gr-amber-400)]'
                      : idx < currentStepIndex
                      ? 'text-[var(--gr-emerald-400)]'
                      : 'text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)]'
                  }`}
                >
                  {idx < currentStepIndex ? (
                    <CheckCircleIcon className="h-5 w-5" />
                  ) : (
                    <step.icon className="h-5 w-5" />
                  )}
                  <span className="text-sm font-medium hidden sm:inline">{step.label}</span>
                </button>
                {idx < steps.length - 1 && (
                  <div
                    className={`w-8 h-0.5 mx-2 ${
                      idx < currentStepIndex ? 'bg-[var(--gr-emerald-400)]' : 'bg-[var(--gr-border-default)]'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto px-6 py-8">
          {/* Research Areas Step */}
          {currentStep === 'research' && (
            <div className="space-y-6 animate-fade-in-up">
              <div>
                <h2 className="text-2xl font-display font-medium text-[var(--gr-text-primary)]">
                  What are your research areas?
                </h2>
                <p className="mt-2 text-[var(--gr-text-secondary)]">
                  Select all that apply. This helps us match you with relevant grants.
                </p>
              </div>

              <div className="card p-6 space-y-4">
                <div className="flex flex-wrap gap-2">
                  {researchAreaSuggestions.map((area) => (
                    <button
                      key={area}
                      onClick={() => toggleResearchArea(area)}
                      className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                        formData.research_areas.includes(area)
                          ? 'bg-[var(--gr-amber-500)] text-[var(--gr-slate-950)]'
                          : 'bg-[var(--gr-bg-card)] text-[var(--gr-text-secondary)] border border-[var(--gr-border-default)] hover:border-[var(--gr-amber-500)]/50'
                      }`}
                    >
                      {area}
                    </button>
                  ))}
                </div>

                {/* Custom input */}
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={customResearchArea}
                    onChange={(e) => setCustomResearchArea(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addCustomResearchArea())}
                    placeholder="Add custom research area..."
                    className="input flex-1"
                  />
                  <button onClick={addCustomResearchArea} className="btn-secondary">
                    Add
                  </button>
                </div>

                {/* Selected areas */}
                {formData.research_areas.length > 0 && (
                  <div className="pt-4 border-t border-[var(--gr-border-subtle)]">
                    <p className="text-sm text-[var(--gr-text-tertiary)] mb-2">
                      Selected ({formData.research_areas.length}):
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {formData.research_areas.map((area) => (
                        <span
                          key={area}
                          className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-[var(--gr-amber-500)]/20 text-[var(--gr-amber-400)] text-sm"
                        >
                          {area}
                          <button
                            onClick={() => toggleResearchArea(area)}
                            className="ml-1 hover:text-[var(--gr-text-primary)]"
                          >
                            &times;
                          </button>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Methods Step */}
          {currentStep === 'methods' && (
            <div className="space-y-6 animate-fade-in-up">
              <div>
                <h2 className="text-2xl font-display font-medium text-[var(--gr-text-primary)]">
                  What methods do you use?
                </h2>
                <p className="mt-2 text-[var(--gr-text-secondary)]">
                  Optional: Select your primary research methods and techniques.
                </p>
              </div>

              <div className="card p-6 space-y-4">
                <div className="flex flex-wrap gap-2">
                  {methodSuggestions.map((method) => (
                    <button
                      key={method}
                      onClick={() => toggleMethod(method)}
                      className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                        (formData.methods || []).includes(method)
                          ? 'bg-[var(--gr-cyan-500)] text-[var(--gr-slate-950)]'
                          : 'bg-[var(--gr-bg-card)] text-[var(--gr-text-secondary)] border border-[var(--gr-border-default)] hover:border-[var(--gr-cyan-500)]/50'
                      }`}
                    >
                      {method}
                    </button>
                  ))}
                </div>

                {/* Custom input */}
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={customMethod}
                    onChange={(e) => setCustomMethod(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addCustomMethod())}
                    placeholder="Add custom method..."
                    className="input flex-1"
                  />
                  <button onClick={addCustomMethod} className="btn-secondary">
                    Add
                  </button>
                </div>

                {/* Selected methods */}
                {(formData.methods || []).length > 0 && (
                  <div className="pt-4 border-t border-[var(--gr-border-subtle)]">
                    <p className="text-sm text-[var(--gr-text-tertiary)] mb-2">
                      Selected ({(formData.methods || []).length}):
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {(formData.methods || []).map((method) => (
                        <span
                          key={method}
                          className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-[var(--gr-cyan-500)]/20 text-[var(--gr-cyan-400)] text-sm"
                        >
                          {method}
                          <button
                            onClick={() => toggleMethod(method)}
                            className="ml-1 hover:text-[var(--gr-text-primary)]"
                          >
                            &times;
                          </button>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Career Stage Step */}
          {currentStep === 'career' && (
            <div className="space-y-6 animate-fade-in-up">
              <div>
                <h2 className="text-2xl font-display font-medium text-[var(--gr-text-primary)]">
                  What is your career stage?
                </h2>
                <p className="mt-2 text-[var(--gr-text-secondary)]">
                  This helps us filter grants by eligibility requirements.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {careerStages.map((stage) => (
                  <button
                    key={stage.value}
                    onClick={() => setFormData((prev) => ({ ...prev, career_stage: stage.value }))}
                    className={`p-6 rounded-2xl border-2 text-left transition-all ${
                      formData.career_stage === stage.value
                        ? 'border-[var(--gr-amber-500)] bg-[var(--gr-amber-500)]/10'
                        : 'border-[var(--gr-border-default)] hover:border-[var(--gr-border-strong)] bg-[var(--gr-bg-card)]'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-medium text-[var(--gr-text-primary)]">{stage.label}</h3>
                      {formData.career_stage === stage.value && (
                        <CheckCircleIcon className="h-5 w-5 text-[var(--gr-amber-400)]" />
                      )}
                    </div>
                    <p className="text-sm text-[var(--gr-text-tertiary)]">{stage.description}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Eligibility Step */}
          {currentStep === 'eligibility' && (
            <div className="space-y-6 animate-fade-in-up">
              <div>
                <h2 className="text-2xl font-display font-medium text-[var(--gr-text-primary)]">
                  Eligibility Information
                </h2>
                <p className="mt-2 text-[var(--gr-text-secondary)]">
                  Optional: Help us filter grants based on eligibility requirements.
                </p>
              </div>

              <div className="card p-6 space-y-6">
                {/* Citizenship Status */}
                <div>
                  <label className="label">Citizenship Status</label>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {citizenshipStatuses.map((status) => (
                      <button
                        key={status.value}
                        onClick={() =>
                          setFormData((prev) => ({ ...prev, citizenship_status: status.value }))
                        }
                        className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                          formData.citizenship_status === status.value
                            ? 'bg-[var(--gr-amber-500)] text-[var(--gr-slate-950)]'
                            : 'bg-[var(--gr-bg-card)] text-[var(--gr-text-secondary)] border border-[var(--gr-border-default)] hover:border-[var(--gr-amber-500)]/50'
                        }`}
                      >
                        {status.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Institution Type */}
                <div>
                  <label className="label">Institution Type</label>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {institutionTypes.map((type) => (
                      <button
                        key={type.value}
                        onClick={() => setFormData((prev) => ({ ...prev, institution_type: type.value }))}
                        className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                          formData.institution_type === type.value
                            ? 'bg-[var(--gr-amber-500)] text-[var(--gr-slate-950)]'
                            : 'bg-[var(--gr-bg-card)] text-[var(--gr-text-secondary)] border border-[var(--gr-border-default)] hover:border-[var(--gr-amber-500)]/50'
                        }`}
                      >
                        {type.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* PI Eligibility */}
                <div className="flex items-center justify-between p-4 bg-[var(--gr-bg-card)] rounded-xl border border-[var(--gr-border-subtle)]">
                  <div>
                    <h3 className="text-sm font-medium text-[var(--gr-text-primary)]">
                      PI Eligible
                    </h3>
                    <p className="text-sm text-[var(--gr-text-tertiary)]">
                      Are you eligible to serve as a Principal Investigator?
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setFormData((prev) => ({ ...prev, is_pi_eligible: !prev.is_pi_eligible }))}
                    className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full transition-colors ${
                      formData.is_pi_eligible ? 'bg-[var(--gr-amber-500)]' : 'bg-[var(--gr-slate-600)]'
                    }`}
                  >
                    <span
                      className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ${
                        formData.is_pi_eligible ? 'translate-x-5' : 'translate-x-0.5'
                      } mt-0.5`}
                    />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer navigation */}
      <div className="border-t border-[var(--gr-border-subtle)] bg-[var(--gr-bg-elevated)]">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={prevStep}
            disabled={currentStepIndex === 0}
            className="btn-ghost disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ArrowLeftIcon className="h-4 w-4" />
            Back
          </button>

          <div className="text-sm text-[var(--gr-text-tertiary)]">
            Step {currentStepIndex + 1} of {steps.length}
          </div>

          {currentStepIndex === steps.length - 1 ? (
            <button
              onClick={handleSubmit}
              disabled={!canProceed() || onboardingMutation.isPending}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {onboardingMutation.isPending ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-[var(--gr-slate-950)] border-t-transparent" />
                  Creating Profile...
                </>
              ) : (
                <>
                  Complete Setup
                  <CheckCircleIcon className="h-4 w-4" />
                </>
              )}
            </button>
          ) : (
            <button
              onClick={nextStep}
              disabled={!canProceed()}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continue
              <ArrowRightIcon className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default Onboarding;
