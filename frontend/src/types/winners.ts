/**
 * Types for the Grant Winners Intelligence feature.
 * Provides access to 2.6M+ funded NIH/NSF projects.
 */

// =============================================================================
// Core Data Models
// =============================================================================

export interface FundedProjectPI {
  name?: string;
  email?: string;
  profile_id?: number;
}

export interface FundedProjectOrg {
  name?: string;
  city?: string;
  state?: string;
  country?: string;
}

export interface FundedProject {
  project_num: string;
  title: string;
  abstract?: string;
  award_amount?: number;
  activity_code?: string;
  mechanism?: string;
  agency: string;
  institute?: string;
  institute_name?: string;
  fiscal_year?: number;
  start_date?: string;
  end_date?: string;
  award_date?: string;
  principal_investigator?: FundedProjectPI;
  organization?: FundedProjectOrg;
  program_officer?: string;
  terms?: string;
  source_url?: string;
}

// =============================================================================
// Search Types
// =============================================================================

export interface WinnersSearchParams {
  query?: string;
  activity_codes?: string;
  institute?: string;
  fiscal_years?: string;
  institution?: string;
  pi_name?: string;
  state?: string;
  min_amount?: number;
  max_amount?: number;
  page?: number;
  limit?: number;
}

export interface YearAggregation {
  year: number;
  count: number;
  total_funding: number;
}

export interface MechanismAggregation {
  code: string;
  count: number;
  avg_award?: number;
}

export interface InstituteAggregation {
  abbreviation: string;
  name?: string;
  count: number;
}

export interface SearchAggregations {
  by_year: YearAggregation[];
  by_mechanism: MechanismAggregation[];
  by_institute: InstituteAggregation[];
}

export interface WinnersSearchResponse {
  results: FundedProject[];
  total: number;
  page: number;
  pages: number;
  aggregations: SearchAggregations;
}

// =============================================================================
// Program Officer Types
// =============================================================================

export interface ProgramOfficerProject {
  project_num: string;
  title: string;
  award_amount?: number;
  fiscal_year?: number;
  activity_code?: string;
}

export interface ProgramOfficer {
  name: string;
  email?: string;
  institute: string;
  institute_name?: string;
  total_projects: number;
  total_funding: number;
  avg_award_size?: number;
  top_mechanisms: string[];
  research_themes: string[];
  recent_projects: ProgramOfficerProject[];
}

export interface ProgramOfficersResponse {
  officers: ProgramOfficer[];
  total: number;
}

// =============================================================================
// Institution Types
// =============================================================================

export interface InstitutionStats {
  name: string;
  city?: string;
  state?: string;
  total_awards: number;
  total_funding: number;
  avg_award_size?: number;
  top_mechanisms: string[];
  top_pis: string[];
  rank?: number;
}

export interface InstitutionsResponse {
  institutions: InstitutionStats[];
  total: number;
}

// =============================================================================
// Keyword Analysis Types
// =============================================================================

export interface KeywordItem {
  keyword: string;
  frequency: number;
  percentage: number;
  trending?: string;
}

export interface KeywordCluster {
  theme: string;
  keywords: string[];
  project_count: number;
}

export interface ProfileKeywordComparison {
  matching_keywords: string[];
  missing_keywords: string[];
  match_score: number;
}

export interface KeywordAnalysisRequest {
  mechanism?: string;
  institute?: string;
  fiscal_years?: number[];
  compare_to_profile?: boolean;
  top_n?: number;
}

export interface KeywordAnalysisResponse {
  top_keywords: KeywordItem[];
  keyword_clusters: KeywordCluster[];
  profile_comparison?: ProfileKeywordComparison;
  projects_analyzed: number;
}

// =============================================================================
// Abstract Analysis Types
// =============================================================================

export interface AbstractPattern {
  pattern_type: string;
  description: string;
  examples: string[];
  frequency: number;
}

export interface LanguageInsights {
  avg_length: number;
  avg_sentences: number;
  key_phrases: string[];
  action_verbs: string[];
  avoided_phrases: string[];
}

export interface UserAbstractComparison {
  strengths: string[];
  gaps: string[];
  similarity_score: number;
  suggestions: string[];
}

export interface AbstractAnalysisRequest {
  mechanism: string;
  institute?: string;
  fiscal_years?: number[];
  user_abstract?: string;
}

export interface AbstractAnalysisResponse {
  common_patterns: AbstractPattern[];
  language_insights: LanguageInsights;
  recommendations: string[];
  user_comparison?: UserAbstractComparison;
  abstracts_analyzed: number;
}

// =============================================================================
// Success Prediction Types
// =============================================================================

export interface PredictionFactor {
  factor: string;
  impact: 'positive' | 'negative' | 'neutral';
  weight: number;
  explanation: string;
}

export interface SuccessPredictionRequest {
  mechanism: string;
  institute: string;
  research_area: string;
  keywords?: string[];
  institution?: string;
  draft_abstract?: string;
  pi_previous_awards?: number;
}

export interface SuccessPredictionResponse {
  probability: number;
  confidence: 'low' | 'medium' | 'high';
  factors: PredictionFactor[];
  similar_funded: FundedProject[];
  recommendations: string[];
  historical_rate?: number;
}

// =============================================================================
// Filter State Types (for UI)
// =============================================================================

export interface WinnersFilters {
  query: string;
  activityCodes: string[];
  institute: string;
  fiscalYears: number[];
  institution: string;
  piName: string;
  state: string;
  minAmount: number | null;
  maxAmount: number | null;
}

export const defaultWinnersFilters: WinnersFilters = {
  query: '',
  activityCodes: [],
  institute: '',
  fiscalYears: [],
  institution: '',
  piName: '',
  state: '',
  minAmount: null,
  maxAmount: null,
};

// NIH Institute options for filters
export const NIH_INSTITUTES = [
  { value: 'NCI', label: 'National Cancer Institute (NCI)' },
  { value: 'NHLBI', label: 'National Heart, Lung, and Blood Institute (NHLBI)' },
  { value: 'NINDS', label: 'National Institute of Neurological Disorders and Stroke (NINDS)' },
  { value: 'NIAID', label: 'National Institute of Allergy and Infectious Diseases (NIAID)' },
  { value: 'NIA', label: 'National Institute on Aging (NIA)' },
  { value: 'NIMH', label: 'National Institute of Mental Health (NIMH)' },
  { value: 'NIDDK', label: 'National Institute of Diabetes and Digestive and Kidney Diseases (NIDDK)' },
  { value: 'NIGMS', label: 'National Institute of General Medical Sciences (NIGMS)' },
  { value: 'NICHD', label: 'Eunice Kennedy Shriver NICHD' },
  { value: 'NEI', label: 'National Eye Institute (NEI)' },
  { value: 'NIEHS', label: 'National Institute of Environmental Health Sciences (NIEHS)' },
  { value: 'NIDCR', label: 'National Institute of Dental and Craniofacial Research (NIDCR)' },
  { value: 'NIAMS', label: 'National Institute of Arthritis and Musculoskeletal and Skin Diseases (NIAMS)' },
  { value: 'NIDA', label: 'National Institute on Drug Abuse (NIDA)' },
  { value: 'NIAAA', label: 'National Institute on Alcohol Abuse and Alcoholism (NIAAA)' },
  { value: 'NIBIB', label: 'National Institute of Biomedical Imaging and Bioengineering (NIBIB)' },
  { value: 'NHGRI', label: 'National Human Genome Research Institute (NHGRI)' },
  { value: 'NLM', label: 'National Library of Medicine (NLM)' },
  { value: 'NCATS', label: 'National Center for Advancing Translational Sciences (NCATS)' },
];

// Common activity codes
export const ACTIVITY_CODES = [
  { value: 'R01', label: 'R01 - Research Project' },
  { value: 'R21', label: 'R21 - Exploratory/Developmental' },
  { value: 'R03', label: 'R03 - Small Research Grant' },
  { value: 'R15', label: 'R15 - AREA Grant' },
  { value: 'K08', label: 'K08 - Mentored Clinical Scientist' },
  { value: 'K23', label: 'K23 - Mentored Patient-Oriented Research' },
  { value: 'K01', label: 'K01 - Mentored Research Scientist' },
  { value: 'K99', label: 'K99/R00 - Pathway to Independence' },
  { value: 'F31', label: 'F31 - Predoctoral Fellowship' },
  { value: 'F32', label: 'F32 - Postdoctoral Fellowship' },
  { value: 'T32', label: 'T32 - Training Grant' },
  { value: 'P01', label: 'P01 - Program Project' },
  { value: 'U01', label: 'U01 - Cooperative Agreement' },
];
