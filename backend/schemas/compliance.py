"""
Compliance Scanner Schemas
Pydantic models for compliance scanning API requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, computed_field, field_validator

from backend.schemas.common import PaginationInfo


# =============================================================================
# Enums
# =============================================================================


class RuleSeverity(str, Enum):
    """Severity levels for compliance rules."""

    ERROR = "error"  # Must be fixed before submission
    WARNING = "warning"  # Should be reviewed but may be acceptable
    INFO = "info"  # Informational, no action required


class RuleType(str, Enum):
    """Types of compliance rules."""

    PAGE_LIMIT = "page_limit"
    WORD_COUNT = "word_count"
    REQUIRED_SECTION = "required_section"
    BUDGET_ARITHMETIC = "budget_arithmetic"
    FONT_SIZE = "font_size"
    MARGIN = "margin"
    LINE_SPACING = "line_spacing"
    CITATION_FORMAT = "citation_format"
    FILE_FORMAT = "file_format"
    CUSTOM = "custom"


class ScanStatus(str, Enum):
    """Overall status of a compliance scan."""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


class DocumentType(str, Enum):
    """Types of documents that can be scanned."""

    SPECIFIC_AIMS = "specific_aims"
    RESEARCH_STRATEGY = "research_strategy"
    BUDGET = "budget"
    BUDGET_JUSTIFICATION = "budget_justification"
    BIOSKETCH = "biosketch"
    FACILITIES = "facilities"
    EQUIPMENT = "equipment"
    BIBLIOGRAPHY = "bibliography"
    ABSTRACT = "abstract"
    PROJECT_NARRATIVE = "project_narrative"
    DATA_MANAGEMENT = "data_management"
    OTHER = "other"


# =============================================================================
# Rule Definition Schemas
# =============================================================================


class RuleDefinition(BaseModel):
    """Definition of a single compliance rule."""

    type: RuleType = Field(..., description="Type of the rule")
    name: str = Field(..., min_length=1, max_length=100, description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")
    params: Dict[str, Any] = Field(default_factory=dict, description="Rule parameters (e.g., max_pages, min_font_size)")
    severity: RuleSeverity = Field(RuleSeverity.ERROR, description="Severity level when rule fails")
    message: Optional[str] = Field(None, description="Custom message to display when rule fails")
    document_types: Optional[List[DocumentType]] = Field(
        None, description="Document types this rule applies to (null = all)"
    )


class ComplianceRuleCreate(BaseModel):
    """Schema for creating a new compliance rule set."""

    funder: str = Field(..., min_length=1, max_length=100, description="Funding organization (e.g., 'NIH', 'NSF')")
    mechanism: Optional[str] = Field(None, max_length=50, description="Grant mechanism type (e.g., 'R01', 'R21')")
    name: str = Field(..., min_length=1, max_length=255, description="Name of the rule set")
    description: Optional[str] = Field(None, description="Description of what this rule set validates")
    rules: List[RuleDefinition] = Field(..., min_length=1, description="List of compliance rules")

    @field_validator("rules")
    @classmethod
    def validate_rules_structure(cls, v: List[RuleDefinition]) -> List[RuleDefinition]:
        """Validate that rules conform to ComplianceRuleItemDict structure."""
        if not v:
            raise ValueError("At least one rule is required")

        # Validate rule names are unique
        names = [rule.name for rule in v]
        if len(names) != len(set(names)):
            raise ValueError("Rule names must be unique within a rule set")

        # Validate severity values
        valid_severities = {"error", "warning", "info"}
        for rule in v:
            if rule.severity.value not in valid_severities:
                raise ValueError(
                    f"Invalid severity '{rule.severity}' for rule '{rule.name}'. Must be one of: {valid_severities}"
                )

        return v


class ComplianceRuleUpdate(BaseModel):
    """Schema for updating a compliance rule set."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Name of the rule set")
    description: Optional[str] = Field(None, description="Description of what this rule set validates")
    rules: Optional[List[RuleDefinition]] = Field(None, description="List of compliance rules")
    is_active: Optional[bool] = Field(None, description="Whether this rule set is active")


class ComplianceRuleResponse(BaseModel):
    """Schema for compliance rule set response."""

    id: UUID = Field(..., description="Rule set ID")
    funder: str = Field(..., description="Funding organization")
    mechanism: Optional[str] = Field(None, description="Grant mechanism type")
    name: str = Field(..., description="Rule set name")
    description: Optional[str] = Field(None, description="Rule set description")
    rules: List[Dict[str, Any]] = Field(..., description="List of rules")
    is_active: bool = Field(..., description="Whether rule set is active")
    is_system: bool = Field(..., description="Whether this is a system rule set")
    created_by: Optional[UUID] = Field(None, description="Creator user ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @computed_field
    @property
    def rule_count(self) -> int:
        """Total number of rules in this set."""
        return len(self.rules)

    class Config:
        from_attributes = True


class ComplianceRuleList(BaseModel):
    """Schema for list of compliance rule sets (standard paginated format)."""

    data: List[ComplianceRuleResponse] = Field(..., description="List of rule sets")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")

    # Backward compatibility aliases
    @property
    def items(self) -> List[ComplianceRuleResponse]:
        """Backward compatibility: alias for 'data'."""
        return self.data

    @property
    def total(self) -> int:
        """Backward compatibility: alias for 'pagination.total'."""
        return self.pagination.total


# =============================================================================
# Scan Result Schemas
# =============================================================================


class ScanResultItem(BaseModel):
    """Result of a single rule check."""

    rule_id: str = Field(..., description="Identifier for the rule")
    rule_name: str = Field(..., description="Name of the rule")
    rule_type: RuleType = Field(..., description="Type of the rule")
    passed: bool = Field(..., description="Whether the rule passed")
    severity: RuleSeverity = Field(..., description="Severity level")
    message: str = Field(..., description="Result message")
    location: Optional[str] = Field(None, description="Location in document where issue was found")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details (e.g., actual value vs expected)")


class ComplianceScanRequest(BaseModel):
    """Schema for requesting a compliance scan."""

    document_type: DocumentType = Field(..., description="Type of document being scanned")
    funder: Optional[str] = Field(None, description="Funder to use for rules (auto-detected if not provided)")
    mechanism: Optional[str] = Field(None, description="Mechanism to use for rules")
    rule_set_id: Optional[UUID] = Field(None, description="Specific rule set to use (overrides funder/mechanism)")
    file_name: Optional[str] = Field(None, max_length=255, description="Name of the file being scanned")
    content: Optional[str] = Field(None, description="Text content to scan (alternative to file upload)")
    # Document metadata for scanning
    page_count: Optional[int] = Field(None, ge=0, description="Number of pages in the document")
    word_count: Optional[int] = Field(None, ge=0, description="Word count of the document")
    font_info: Optional[Dict[str, Any]] = Field(None, description="Font information (size, family)")
    margin_info: Optional[Dict[str, Any]] = Field(
        None, description="Margin information (top, bottom, left, right in inches)"
    )
    line_spacing: Optional[float] = Field(None, description="Line spacing (e.g., 1.0, 1.5, 2.0)")
    budget_data: Optional[Dict[str, Any]] = Field(None, description="Budget data for arithmetic validation")
    sections_found: Optional[List[str]] = Field(None, description="List of section headings found in document")


class ComplianceScanResponse(BaseModel):
    """Schema for compliance scan response."""

    id: UUID = Field(..., description="Scan ID")
    kanban_card_id: UUID = Field(..., description="Associated grant application ID")
    rule_set_id: Optional[UUID] = Field(None, description="Rule set used")
    document_type: str = Field(..., description="Type of document scanned")
    file_name: Optional[str] = Field(None, description="Filename")
    results: List[ScanResultItem] = Field(..., description="Individual rule results")
    passed_count: int = Field(..., description="Rules passed")
    failed_count: int = Field(..., description="Rules failed")
    warning_count: int = Field(..., description="Rules with warnings")
    overall_status: ScanStatus = Field(..., description="Overall scan status")
    scanned_by: Optional[UUID] = Field(None, description="User who ran the scan")
    scanned_at: datetime = Field(..., description="When scan was performed")

    @computed_field
    @property
    def total_rules(self) -> int:
        """Total number of rules checked."""
        return self.passed_count + self.failed_count + self.warning_count

    @computed_field
    @property
    def compliance_score(self) -> float:
        """Compliance score as percentage (0-100)."""
        total = self.total_rules
        if total == 0:
            return 100.0
        return round((self.passed_count / total) * 100, 1)

    class Config:
        from_attributes = True


class ComplianceScanList(BaseModel):
    """Schema for list of compliance scans (standard paginated format)."""

    data: List[ComplianceScanResponse] = Field(..., description="List of scans")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")

    # Backward compatibility aliases
    @property
    def items(self) -> List[ComplianceScanResponse]:
        """Backward compatibility: alias for 'data'."""
        return self.data

    @property
    def total(self) -> int:
        """Backward compatibility: alias for 'pagination.total'."""
        return self.pagination.total


# =============================================================================
# Summary Schemas
# =============================================================================


class ComplianceSummary(BaseModel):
    """Summary of compliance status for a grant application."""

    kanban_card_id: UUID = Field(..., description="Grant application ID")
    total_scans: int = Field(..., description="Total number of scans")
    latest_scan_at: Optional[datetime] = Field(None, description="When last scan was performed")
    documents_scanned: List[str] = Field(..., description="Types of documents that have been scanned")
    overall_compliance: ScanStatus = Field(..., description="Overall compliance status across all documents")
    issues_count: int = Field(..., description="Total number of issues found")
    warnings_count: int = Field(..., description="Total number of warnings")


class FunderRulesInfo(BaseModel):
    """Information about available rules for a funder."""

    funder: str = Field(..., description="Funder name")
    mechanisms: List[str] = Field(..., description="Available mechanisms with specific rules")
    general_rule_set: Optional[ComplianceRuleResponse] = Field(
        None, description="General rule set for this funder (no specific mechanism)"
    )
    mechanism_rule_sets: List[ComplianceRuleResponse] = Field(..., description="Mechanism-specific rule sets")


# =============================================================================
# Async Scan Schemas
# =============================================================================


class AsyncScanResponse(BaseModel):
    """Response for async scan request."""

    scan_id: UUID = Field(..., description="ID of the created scan record")
    task_id: str = Field(..., description="Celery task ID for tracking")
    status: ScanStatus = Field(..., description="Initial scan status (pending)")
    message: str = Field(..., description="Status message")


class ComplianceScanStatusResponse(BaseModel):
    """Response for scan status check."""

    scan_id: UUID = Field(..., description="Scan ID")
    status: ScanStatus = Field(..., description="Current scan status")
    passed_count: int = Field(..., description="Rules passed (0 if pending)")
    failed_count: int = Field(..., description="Rules failed (0 if pending)")
    warning_count: int = Field(..., description="Rules with warnings (0 if pending)")
    scanned_at: datetime = Field(..., description="When scan was created/completed")
    results: Optional[List[Dict[str, Any]]] = Field(
        None, description="Scan results (only populated when scan is complete)"
    )

    @computed_field
    @property
    def is_complete(self) -> bool:
        """Whether the scan has completed processing."""
        return self.status != ScanStatus.PENDING
