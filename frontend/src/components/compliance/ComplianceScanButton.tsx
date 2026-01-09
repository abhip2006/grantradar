import { useState } from 'react';
import {
  ShieldCheckIcon,
  ArrowPathIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline';
import { useRunComplianceScan } from '../../hooks/useCompliance';
import type { ComplianceScanRequest } from '../../types/compliance';

interface ComplianceScanButtonProps {
  cardId: string;
  funder?: string;
  mechanism?: string;
  variant?: 'primary' | 'secondary' | 'minimal';
  size?: 'sm' | 'md' | 'lg';
  showDropdown?: boolean;
  onScanComplete?: () => void;
}

const DOCUMENT_TYPES = [
  { value: 'all', label: 'All Documents' },
  { value: 'narrative', label: 'Research Narrative' },
  { value: 'budget', label: 'Budget' },
  { value: 'biosketch', label: 'Biosketch' },
  { value: 'facilities', label: 'Facilities & Equipment' },
];

export function ComplianceScanButton({
  cardId,
  funder,
  mechanism,
  variant = 'primary',
  size = 'md',
  showDropdown = false,
  onScanComplete,
}: ComplianceScanButtonProps) {
  const [showMenu, setShowMenu] = useState(false);
  const scanMutation = useRunComplianceScan();

  const handleScan = (documentType?: string) => {
    const request: ComplianceScanRequest = {
      funder,
      mechanism,
      document_type: documentType === 'all' ? undefined : documentType,
    };

    scanMutation.mutate(
      { cardId, request },
      {
        onSuccess: () => {
          setShowMenu(false);
          onScanComplete?.();
        },
      }
    );
  };

  // Size classes
  const sizeClasses = {
    sm: 'px-2.5 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-5 py-2.5 text-base',
  };

  // Variant classes
  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm',
    secondary: 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50',
    minimal: 'text-blue-600 hover:bg-blue-50',
  };

  const iconSize = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-5 h-5',
  };

  if (showDropdown) {
    return (
      <div className="relative inline-block">
        <button
          type="button"
          onClick={() => setShowMenu(!showMenu)}
          disabled={scanMutation.isPending}
          className={`
            inline-flex items-center gap-2 rounded-lg font-medium
            transition-colors disabled:opacity-50 disabled:cursor-not-allowed
            ${sizeClasses[size]}
            ${variantClasses[variant]}
          `}
        >
          {scanMutation.isPending ? (
            <ArrowPathIcon className={`${iconSize[size]} animate-spin`} />
          ) : (
            <ShieldCheckIcon className={iconSize[size]} />
          )}
          {scanMutation.isPending ? 'Scanning...' : 'Run Compliance Scan'}
          <ChevronDownIcon className="w-4 h-4" />
        </button>

        {showMenu && (
          <div className="absolute right-0 mt-2 w-56 rounded-lg bg-white shadow-lg ring-1 ring-black ring-opacity-5 z-10">
            <div className="py-1">
              {DOCUMENT_TYPES.map((docType) => (
                <button
                  key={docType.value}
                  onClick={() => handleScan(docType.value)}
                  disabled={scanMutation.isPending}
                  className="block w-full px-4 py-2 text-sm text-left text-gray-700 hover:bg-gray-100 disabled:opacity-50"
                >
                  {docType.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => handleScan()}
      disabled={scanMutation.isPending}
      className={`
        inline-flex items-center gap-2 rounded-lg font-medium
        transition-colors disabled:opacity-50 disabled:cursor-not-allowed
        ${sizeClasses[size]}
        ${variantClasses[variant]}
      `}
    >
      {scanMutation.isPending ? (
        <ArrowPathIcon className={`${iconSize[size]} animate-spin`} />
      ) : (
        <ShieldCheckIcon className={iconSize[size]} />
      )}
      {scanMutation.isPending ? 'Scanning...' : 'Run Compliance Scan'}
    </button>
  );
}

export default ComplianceScanButton;
