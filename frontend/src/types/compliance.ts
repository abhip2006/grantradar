// Compliance Scanner Types

// Severity level for compliance results
export type ComplianceSeverity = 'error' | 'warning' | 'info';

// Rule types for categorizing compliance checks
export type ComplianceRuleType =
  | 'page_limit'
  | 'word_limit'
  | 'font_size'
  | 'margin'
  | 'required_section'
  | 'budget_arithmetic'
  | 'citation_format'
  | 'biosketch'
  | 'file_format'
  | 'custom';

// Individual compliance rule definition
export interface ComplianceRule {
  id: string;
  funder: string;
  mechanism?: string;
  type: ComplianceRuleType;
  name: string;
  description?: string;
  params: Record<string, unknown>;
  severity: ComplianceSeverity;
  created_at: string;
}

// Compliance rules set for a funder
export interface ComplianceRuleSet {
  funder: string;
  mechanism?: string;
  rules: ComplianceRule[];
  total: number;
}

// Individual scan result for a rule
export interface ScanResultItem {
  rule_id: string;
  rule_name: string;
  rule_type: ComplianceRuleType;
  passed: boolean;
  severity: ComplianceSeverity;
  message: string;
  location?: string;
  details?: Record<string, unknown>;
}

// Full compliance scan result
export interface ComplianceScan {
  id: string;
  kanban_card_id: string;
  document_type?: string;
  file_name?: string;
  results: ScanResultItem[];
  passed_count: number;
  failed_count: number;
  warning_count: number;
  info_count: number;
  overall_status: 'passed' | 'failed' | 'warnings';
  scanned_at: string;
}

// Summary of scan results for display
export interface ComplianceSummary {
  passed: number;
  failed: number;
  warnings: number;
  info: number;
  total: number;
  overall_status: 'passed' | 'failed' | 'warnings';
}

// Request to run a compliance scan
export interface ComplianceScanRequest {
  document_type?: string;
  file_name?: string;
  funder?: string;
  mechanism?: string;
}

// Compliance scan list response
export interface ComplianceScanListResponse {
  scans: ComplianceScan[];
  total: number;
}

// Severity configuration for UI display
export interface SeverityConfig {
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  iconColor: string;
}

export const SEVERITY_CONFIG: Record<ComplianceSeverity, SeverityConfig> = {
  error: {
    label: 'Error',
    color: 'text-red-700',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    iconColor: 'text-red-500',
  },
  warning: {
    label: 'Warning',
    color: 'text-amber-700',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    iconColor: 'text-amber-500',
  },
  info: {
    label: 'Info',
    color: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    iconColor: 'text-blue-500',
  },
};

// Status configuration for overall scan status
export interface StatusConfig {
  label: string;
  color: string;
  bgColor: string;
  iconColor: string;
}

export const STATUS_CONFIG: Record<ComplianceScan['overall_status'], StatusConfig> = {
  passed: {
    label: 'Passed',
    color: 'text-green-700',
    bgColor: 'bg-green-50',
    iconColor: 'text-green-500',
  },
  failed: {
    label: 'Failed',
    color: 'text-red-700',
    bgColor: 'bg-red-50',
    iconColor: 'text-red-500',
  },
  warnings: {
    label: 'Passed with Warnings',
    color: 'text-amber-700',
    bgColor: 'bg-amber-50',
    iconColor: 'text-amber-500',
  },
};
