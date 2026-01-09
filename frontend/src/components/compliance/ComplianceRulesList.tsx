import {
  DocumentTextIcon,
  CalculatorIcon,
  ClipboardDocumentCheckIcon,
  DocumentCheckIcon,
  AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline';
import { useComplianceRules } from '../../hooks/useCompliance';
import type { ComplianceRule, ComplianceRuleType } from '../../types/compliance';
import { SEVERITY_CONFIG } from '../../types/compliance';

interface ComplianceRulesListProps {
  funder: string;
  mechanism?: string;
  compact?: boolean;
}

// Icon mapping for rule types
const RULE_TYPE_ICONS: Record<ComplianceRuleType, React.ComponentType<React.SVGProps<SVGSVGElement>>> = {
  page_limit: DocumentTextIcon,
  word_limit: DocumentTextIcon,
  font_size: AdjustmentsHorizontalIcon,
  margin: AdjustmentsHorizontalIcon,
  required_section: ClipboardDocumentCheckIcon,
  budget_arithmetic: CalculatorIcon,
  citation_format: DocumentCheckIcon,
  biosketch: DocumentCheckIcon,
  file_format: DocumentTextIcon,
  custom: AdjustmentsHorizontalIcon,
};

// Human-readable labels for rule types
const RULE_TYPE_LABELS: Record<ComplianceRuleType, string> = {
  page_limit: 'Page Limit',
  word_limit: 'Word Limit',
  font_size: 'Font Size',
  margin: 'Margins',
  required_section: 'Required Section',
  budget_arithmetic: 'Budget Validation',
  citation_format: 'Citation Format',
  biosketch: 'Biosketch Check',
  file_format: 'File Format',
  custom: 'Custom Rule',
};

interface RuleCardProps {
  rule: ComplianceRule;
  compact?: boolean;
}

function RuleCard({ rule, compact }: RuleCardProps) {
  const Icon = RULE_TYPE_ICONS[rule.type] || AdjustmentsHorizontalIcon;
  const severityConfig = SEVERITY_CONFIG[rule.severity];

  if (compact) {
    return (
      <div className="flex items-center gap-2 py-1.5">
        <Icon className="w-4 h-4 text-gray-400 flex-shrink-0" />
        <span className="text-sm text-gray-700 truncate">{rule.name}</span>
        <span
          className={`
            ml-auto px-1.5 py-0.5 text-xs font-medium rounded
            ${rule.severity === 'error' ? 'bg-red-100 text-red-600' : ''}
            ${rule.severity === 'warning' ? 'bg-amber-100 text-amber-600' : ''}
            ${rule.severity === 'info' ? 'bg-blue-100 text-blue-600' : ''}
          `}
        >
          {severityConfig.label}
        </span>
      </div>
    );
  }

  return (
    <div
      className={`
        p-4 rounded-lg border bg-white
        ${severityConfig.borderColor}
      `}
    >
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg ${severityConfig.bgColor}`}>
          <Icon className={`w-5 h-5 ${severityConfig.iconColor}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="font-medium text-gray-900">{rule.name}</h4>
            <span
              className={`
                px-2 py-0.5 text-xs font-medium rounded-full
                ${rule.severity === 'error' ? 'bg-red-100 text-red-700' : ''}
                ${rule.severity === 'warning' ? 'bg-amber-100 text-amber-700' : ''}
                ${rule.severity === 'info' ? 'bg-blue-100 text-blue-700' : ''}
              `}
            >
              {severityConfig.label}
            </span>
          </div>
          {rule.description && (
            <p className="mt-1 text-sm text-gray-600">{rule.description}</p>
          )}
          <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
            <span className="inline-flex items-center gap-1">
              <span className="font-medium">Type:</span> {RULE_TYPE_LABELS[rule.type]}
            </span>
            {rule.mechanism && (
              <span className="inline-flex items-center gap-1">
                <span className="font-medium">Mechanism:</span> {rule.mechanism}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function ComplianceRulesList({ funder, mechanism, compact = false }: ComplianceRulesListProps) {
  const { data, isLoading, error } = useComplianceRules(funder, mechanism);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div
            key={i}
            className={`animate-pulse ${compact ? 'h-8' : 'h-24'} bg-gray-100 rounded-lg`}
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-6 text-gray-500">
        <p className="text-sm">Failed to load compliance rules</p>
      </div>
    );
  }

  if (!data || data.rules.length === 0) {
    return (
      <div className="text-center py-6 text-gray-500">
        <ClipboardDocumentCheckIcon className="w-12 h-12 mx-auto mb-2 text-gray-300" />
        <p className="text-sm">No compliance rules found for {funder}</p>
        {mechanism && (
          <p className="text-xs mt-1">Mechanism: {mechanism}</p>
        )}
      </div>
    );
  }

  // Group rules by type if not compact
  const rulesByType = data.rules.reduce((acc, rule) => {
    const type = rule.type;
    if (!acc[type]) {
      acc[type] = [];
    }
    acc[type].push(rule);
    return acc;
  }, {} as Record<ComplianceRuleType, ComplianceRule[]>);

  if (compact) {
    return (
      <div className="divide-y divide-gray-100">
        {data.rules.map((rule) => (
          <RuleCard key={rule.id} rule={rule} compact />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-gray-900">Compliance Rules for {funder}</h3>
          {mechanism && (
            <p className="text-sm text-gray-500 mt-0.5">Mechanism: {mechanism}</p>
          )}
        </div>
        <span className="text-sm text-gray-500">
          {data.total} rule{data.total !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Rules grouped by type */}
      {Object.entries(rulesByType).map(([type, rules]) => (
        <div key={type}>
          <h4 className="text-sm font-medium text-gray-700 mb-2">
            {RULE_TYPE_LABELS[type as ComplianceRuleType]}
          </h4>
          <div className="space-y-3">
            {rules.map((rule) => (
              <RuleCard key={rule.id} rule={rule} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default ComplianceRulesList;
