import { useState, useRef } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  DocumentArrowUpIcon,
  GlobeAltIcon,
  CheckCircleIcon,
  XMarkIcon,
  ArrowPathIcon,
  AcademicCapIcon,
  BeakerIcon,
  DocumentTextIcon,
  CurrencyDollarIcon,
} from '@heroicons/react/24/outline';
import { profileImportApi } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import type { ImportPreview } from '../types';

interface ProfileImportProps {
  onImportComplete?: (data: ImportPreview) => void;
}

export function ProfileImport({ onImportComplete }: ProfileImportProps) {
  const [importMethod, setImportMethod] = useState<'orcid' | 'cv' | null>(null);
  const [orcidInput, setOrcidInput] = useState('');
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useToast();

  // ORCID import mutation
  const orcidMutation = useMutation({
    mutationFn: (orcid: string) => profileImportApi.importFromOrcid(orcid),
    onSuccess: (data) => {
      setPreview(data);
      showToast('ORCID profile imported successfully', 'success');
    },
    onError: () => {
      showToast('Failed to import ORCID profile. Check the ORCID ID and ensure the profile is public.', 'error');
    },
  });

  // CV import mutation
  const cvMutation = useMutation({
    mutationFn: (file: File) => profileImportApi.importFromCv(file),
    onSuccess: (data) => {
      setPreview(data);
      showToast('CV parsed successfully', 'success');
    },
    onError: () => {
      showToast('Failed to parse CV. Ensure the PDF contains extractable text.', 'error');
    },
  });

  const handleOrcidSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (orcidInput.trim()) {
      orcidMutation.mutate(orcidInput.trim());
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type !== 'application/pdf') {
        showToast('Please upload a PDF file', 'error');
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        showToast('File too large. Maximum size is 10MB.', 'error');
        return;
      }
      cvMutation.mutate(file);
    }
  };

  const handleUseImport = () => {
    if (preview && onImportComplete) {
      onImportComplete(preview);
      setPreview(null);
      setImportMethod(null);
      showToast('Profile data applied', 'success');
    }
  };

  const resetImport = () => {
    setPreview(null);
    setOrcidInput('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const isLoading = orcidMutation.isPending || cvMutation.isPending;

  // Preview display
  if (preview) {
    return (
      <div className="space-y-6 animate-fade-in-up">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
            Import Preview
          </h3>
          <div className="flex items-center gap-2">
            <button onClick={resetImport} className="btn-ghost text-sm">
              <XMarkIcon className="h-4 w-4" />
              Cancel
            </button>
            <button onClick={handleUseImport} className="btn-primary text-sm">
              <CheckCircleIcon className="h-4 w-4" />
              Use This Data
            </button>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[var(--gr-bg-card)] border border-[var(--gr-border-subtle)]">
          <div className="flex items-center gap-2 mb-4">
            <span className="badge badge-cyan">
              {preview.source === 'orcid' ? 'ORCID' : 'CV'}
            </span>
            {preview.orcid && (
              <span className="text-xs text-[var(--gr-text-tertiary)]">
                {preview.orcid}
              </span>
            )}
          </div>

          <div className="grid gap-4">
            {preview.name && (
              <div>
                <p className="text-xs text-[var(--gr-text-tertiary)] uppercase tracking-wider mb-1">Name</p>
                <p className="text-sm text-[var(--gr-text-primary)]">{preview.name}</p>
              </div>
            )}

            {preview.institution && (
              <div>
                <p className="text-xs text-[var(--gr-text-tertiary)] uppercase tracking-wider mb-1">Institution</p>
                <p className="text-sm text-[var(--gr-text-primary)]">{preview.institution}</p>
              </div>
            )}

            {preview.career_stage && (
              <div>
                <p className="text-xs text-[var(--gr-text-tertiary)] uppercase tracking-wider mb-1">Career Stage</p>
                <p className="text-sm text-[var(--gr-text-primary)] capitalize">{preview.career_stage.replace('_', ' ')}</p>
              </div>
            )}

            {preview.research_areas.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <AcademicCapIcon className="h-4 w-4 text-[var(--gr-amber-400)]" />
                  <p className="text-xs text-[var(--gr-text-tertiary)] uppercase tracking-wider">Research Areas</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {preview.research_areas.slice(0, 10).map((area, i) => (
                    <span key={i} className="badge badge-amber text-xs">{area}</span>
                  ))}
                  {preview.research_areas.length > 10 && (
                    <span className="text-xs text-[var(--gr-text-tertiary)]">
                      +{preview.research_areas.length - 10} more
                    </span>
                  )}
                </div>
              </div>
            )}

            {preview.methods.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <BeakerIcon className="h-4 w-4 text-[var(--gr-cyan-400)]" />
                  <p className="text-xs text-[var(--gr-text-tertiary)] uppercase tracking-wider">Methods</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {preview.methods.slice(0, 8).map((method, i) => (
                    <span key={i} className="badge badge-cyan text-xs">{method}</span>
                  ))}
                  {preview.methods.length > 8 && (
                    <span className="text-xs text-[var(--gr-text-tertiary)]">
                      +{preview.methods.length - 8} more
                    </span>
                  )}
                </div>
              </div>
            )}

            {preview.publications.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <DocumentTextIcon className="h-4 w-4 text-[var(--gr-emerald-400)]" />
                  <p className="text-xs text-[var(--gr-text-tertiary)] uppercase tracking-wider">
                    Publications ({preview.publications.length})
                  </p>
                </div>
                <ul className="space-y-1">
                  {preview.publications.slice(0, 3).map((pub, i) => (
                    <li key={i} className="text-sm text-[var(--gr-text-secondary)] truncate">
                      {pub.title}
                      {pub.year && <span className="text-[var(--gr-text-tertiary)]"> ({pub.year})</span>}
                    </li>
                  ))}
                  {preview.publications.length > 3 && (
                    <li className="text-xs text-[var(--gr-text-tertiary)]">
                      +{preview.publications.length - 3} more publications
                    </li>
                  )}
                </ul>
              </div>
            )}

            {preview.past_grants.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <CurrencyDollarIcon className="h-4 w-4 text-[var(--gr-amber-400)]" />
                  <p className="text-xs text-[var(--gr-text-tertiary)] uppercase tracking-wider">
                    Past Grants ({preview.past_grants.length})
                  </p>
                </div>
                <ul className="space-y-1">
                  {preview.past_grants.slice(0, 3).map((grant, i) => (
                    <li key={i} className="text-sm text-[var(--gr-text-secondary)] truncate">
                      {grant.title}
                      {grant.funder && <span className="text-[var(--gr-text-tertiary)]"> - {grant.funder}</span>}
                    </li>
                  ))}
                  {preview.past_grants.length > 3 && (
                    <li className="text-xs text-[var(--gr-text-tertiary)]">
                      +{preview.past_grants.length - 3} more grants
                    </li>
                  )}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-2">
          Import Profile Data
        </h3>
        <p className="text-sm text-[var(--gr-text-secondary)]">
          Quickly populate your profile by importing from ORCID or uploading your CV
        </p>
      </div>

      {/* Import method selection */}
      {!importMethod && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <button
            onClick={() => setImportMethod('orcid')}
            className="p-6 rounded-xl border border-[var(--gr-border-default)] hover:border-[var(--gr-amber-500)]/50 hover:bg-[var(--gr-amber-500)]/5 transition-all text-left group"
          >
            <div className="p-3 rounded-xl bg-[var(--gr-emerald-500)]/10 w-fit mb-4">
              <GlobeAltIcon className="h-6 w-6 text-[var(--gr-emerald-400)]" />
            </div>
            <h4 className="font-medium text-[var(--gr-text-primary)] mb-1">Import from ORCID</h4>
            <p className="text-sm text-[var(--gr-text-tertiary)]">
              Fetch your publications, grants, and research areas from your ORCID profile
            </p>
          </button>

          <button
            onClick={() => setImportMethod('cv')}
            className="p-6 rounded-xl border border-[var(--gr-border-default)] hover:border-[var(--gr-amber-500)]/50 hover:bg-[var(--gr-amber-500)]/5 transition-all text-left group"
          >
            <div className="p-3 rounded-xl bg-[var(--gr-cyan-500)]/10 w-fit mb-4">
              <DocumentArrowUpIcon className="h-6 w-6 text-[var(--gr-cyan-400)]" />
            </div>
            <h4 className="font-medium text-[var(--gr-text-primary)] mb-1">Upload CV</h4>
            <p className="text-sm text-[var(--gr-text-tertiary)]">
              Parse your CV/resume to extract research areas, methods, and experience
            </p>
          </button>
        </div>
      )}

      {/* ORCID import form */}
      {importMethod === 'orcid' && (
        <div className="animate-fade-in-up">
          <button
            onClick={() => setImportMethod(null)}
            className="btn-ghost text-sm mb-4"
          >
            <XMarkIcon className="h-4 w-4" />
            Back
          </button>

          <form onSubmit={handleOrcidSubmit} className="space-y-4">
            <div>
              <label htmlFor="orcid" className="label">ORCID ID</label>
              <input
                id="orcid"
                type="text"
                value={orcidInput}
                onChange={(e) => setOrcidInput(e.target.value)}
                placeholder="0000-0002-1825-0097 or https://orcid.org/..."
                className="input"
                disabled={isLoading}
              />
              <p className="mt-1 text-xs text-[var(--gr-text-tertiary)]">
                Enter your ORCID ID or full ORCID URL. Your profile must be public.
              </p>
            </div>

            <button
              type="submit"
              disabled={!orcidInput.trim() || isLoading}
              className="btn-primary"
            >
              {isLoading ? (
                <>
                  <ArrowPathIcon className="h-4 w-4 animate-spin" />
                  Importing...
                </>
              ) : (
                <>
                  <GlobeAltIcon className="h-4 w-4" />
                  Import from ORCID
                </>
              )}
            </button>
          </form>
        </div>
      )}

      {/* CV upload form */}
      {importMethod === 'cv' && (
        <div className="animate-fade-in-up">
          <button
            onClick={() => setImportMethod(null)}
            className="btn-ghost text-sm mb-4"
          >
            <XMarkIcon className="h-4 w-4" />
            Back
          </button>

          <div className="space-y-4">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="hidden"
              disabled={isLoading}
            />

            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading}
              className="w-full p-8 border-2 border-dashed border-[var(--gr-border-default)] rounded-xl hover:border-[var(--gr-amber-500)]/50 hover:bg-[var(--gr-amber-500)]/5 transition-all flex flex-col items-center gap-3"
            >
              {isLoading ? (
                <>
                  <ArrowPathIcon className="h-8 w-8 text-[var(--gr-amber-400)] animate-spin" />
                  <span className="text-sm text-[var(--gr-text-secondary)]">Parsing CV...</span>
                </>
              ) : (
                <>
                  <DocumentArrowUpIcon className="h-8 w-8 text-[var(--gr-text-tertiary)]" />
                  <span className="text-sm text-[var(--gr-text-secondary)]">
                    Click to upload or drag and drop
                  </span>
                  <span className="text-xs text-[var(--gr-text-tertiary)]">
                    PDF only, max 10MB
                  </span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProfileImport;
