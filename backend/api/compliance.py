"""
Compliance Scanner API Endpoints
Endpoints for running compliance scans and managing compliance rules.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import and_, select

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.api.utils.auth import verify_card_ownership
from backend.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from backend.models.compliance import ComplianceRule, ComplianceScan
import backend.models as models_module
from backend.schemas.compliance import (
    AsyncScanResponse,
    ComplianceRuleCreate,
    ComplianceRuleList,
    ComplianceRuleResponse,
    ComplianceRuleUpdate,
    ComplianceScanList,
    ComplianceScanRequest,
    ComplianceScanResponse,
    ComplianceScanStatusResponse,
    ComplianceSummary,
    DocumentType,
    FunderRulesInfo,
    ScanStatus,
)
from backend.schemas.common import PaginationInfo
from backend.services.compliance_scanner import ComplianceScannerService

router = APIRouter(prefix="/api", tags=["Compliance"])


# =============================================================================
# Rate Limiting
# =============================================================================

# Simple in-memory rate limiter (for production, use Redis)
scan_timestamps: Dict[str, List[datetime]] = {}


def check_rate_limit(user_id: str, max_requests: int = 10, window_minutes: int = 5) -> bool:
    """
    Check if user has exceeded rate limit.

    Args:
        user_id: The user's unique identifier.
        max_requests: Maximum number of requests allowed in the window.
        window_minutes: Time window in minutes.

    Returns:
        True if request is allowed, False if rate limit exceeded.
    """
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=window_minutes)

    if user_id not in scan_timestamps:
        scan_timestamps[user_id] = []

    # Clean old timestamps
    scan_timestamps[user_id] = [t for t in scan_timestamps[user_id] if t > window_start]

    if len(scan_timestamps[user_id]) >= max_requests:
        return False

    scan_timestamps[user_id].append(now)
    return True


# =============================================================================
# Compliance Scan Endpoints
# =============================================================================


@router.post(
    "/kanban/{card_id}/compliance/scan",
    response_model=ComplianceScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run compliance scan (sync)",
    description="Run a compliance scan on a document for a grant application (synchronous).",
)
async def run_compliance_scan(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    card_id: UUID,
    request: ComplianceScanRequest,
) -> ComplianceScanResponse:
    """
    Run a compliance scan on a document for a grant application (synchronous).

    The scan checks the document against funder-specific rules for:
    - Page limits
    - Word count limits
    - Required sections
    - Budget arithmetic (if applicable)
    - Font and margin requirements (basic check)

    If no rule set is specified, the system will try to find appropriate rules
    based on the grant's funder and mechanism.

    Rate limited to 10 requests per 5 minutes per user.
    """
    # Check rate limit
    if not check_rate_limit(str(current_user.id)):
        raise ValidationError("Rate limit exceeded. Maximum 10 scans per 5 minutes.")

    # Verify the kanban card exists and belongs to user
    await verify_card_ownership(db, card_id, current_user.id)

    # Fetch the application for additional context
    result = await db.execute(
        select(models_module.GrantApplication).where(
            models_module.GrantApplication.id == card_id,
        )
    )
    application = result.scalar_one_or_none()

    # Initialize scanner service
    scanner = ComplianceScannerService()

    # Find or determine the rule set to use
    rule_set = None
    if request.rule_set_id:
        result = await db.execute(
            select(ComplianceRule).where(
                and_(
                    ComplianceRule.id == request.rule_set_id,
                    ComplianceRule.is_active,
                )
            )
        )
        rule_set = result.scalar_one_or_none()
        if not rule_set:
            raise NotFoundError("Rule set")
    else:
        # Try to find rules based on funder/mechanism
        funder = request.funder
        mechanism = request.mechanism

        # If not provided, try to get from the grant
        if not funder and application.grant:
            grant = await db.get(models_module.Grant, application.grant_id)
            if grant:
                funder = grant.agency

        if funder:
            # First try to find mechanism-specific rules
            if mechanism:
                result = await db.execute(
                    select(ComplianceRule).where(
                        and_(
                            ComplianceRule.funder.ilike(f"%{funder}%"),
                            ComplianceRule.mechanism == mechanism,
                            ComplianceRule.is_active,
                        )
                    )
                )
                rule_set = result.scalar_one_or_none()

            # Fall back to general funder rules
            if not rule_set:
                result = await db.execute(
                    select(ComplianceRule).where(
                        and_(
                            ComplianceRule.funder.ilike(f"%{funder}%"),
                            ComplianceRule.mechanism.is_(None),
                            ComplianceRule.is_active,
                        )
                    )
                )
                rule_set = result.scalar_one_or_none()

    if not rule_set:
        raise ValidationError(
            "No compliance rules found for the specified funder/mechanism. Please specify a rule_set_id or create rules for this funder."
        )

    # Validate document content before scanning
    scanner.validate_document_content(
        content=request.content,
        document_type=request.document_type,
    )

    # Run the compliance scan
    scan_results = scanner.run_scan(
        rules=rule_set.rules,
        document_type=request.document_type,
        content=request.content,
        page_count=request.page_count,
        word_count=request.word_count,
        font_info=request.font_info,
        margin_info=request.margin_info,
        line_spacing=request.line_spacing,
        budget_data=request.budget_data,
        sections_found=request.sections_found,
    )

    # Count results
    passed_count = sum(1 for r in scan_results if r["passed"])
    failed_count = sum(1 for r in scan_results if not r["passed"] and r["severity"] == "error")
    warning_count = sum(1 for r in scan_results if not r["passed"] and r["severity"] == "warning")

    # Determine overall status
    if failed_count > 0:
        overall_status = ScanStatus.FAILED.value
    elif warning_count > 0:
        overall_status = ScanStatus.WARNING.value
    else:
        overall_status = ScanStatus.PASSED.value

    # Calculate content hash for duplicate detection
    file_content_hash = None
    if request.content:
        file_content_hash = scanner.calculate_content_hash(request.content)

    # Create scan record and persist to database
    scan = ComplianceScan(
        kanban_card_id=card_id,
        rule_set_id=rule_set.id,
        document_type=request.document_type.value,
        file_name=request.file_name,
        file_content_hash=file_content_hash,
        results=scan_results,
        passed_count=passed_count,
        failed_count=failed_count,
        warning_count=warning_count,
        overall_status=overall_status,
        scanned_by=current_user.id,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    return scan


@router.post(
    "/kanban/{card_id}/compliance/scan/async",
    response_model=AsyncScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Run compliance scan (async)",
    description="Queue a compliance scan to run asynchronously in the background.",
)
async def run_compliance_scan_async_endpoint(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    card_id: UUID,
    request: ComplianceScanRequest,
) -> AsyncScanResponse:
    """
    Queue a compliance scan to run asynchronously.

    This endpoint is useful for large documents or when you want to avoid
    blocking the request. Use the /compliance/scans/{scan_id}/status endpoint
    to check the scan progress.

    Rate limited to 10 requests per 5 minutes per user.
    """
    # Import Celery task here to avoid circular imports
    from backend.tasks.compliance_tasks import run_compliance_scan_async

    # Check rate limit
    if not check_rate_limit(str(current_user.id)):
        raise ValidationError("Rate limit exceeded. Maximum 10 scans per 5 minutes.")

    # Verify the kanban card exists and belongs to user
    await verify_card_ownership(db, card_id, current_user.id)

    # Fetch the application for additional context
    result = await db.execute(
        select(models_module.GrantApplication).where(
            models_module.GrantApplication.id == card_id,
        )
    )
    application = result.scalar_one_or_none()

    # Find the rule set ID to use
    rule_set_id = None
    rule_set = None
    if request.rule_set_id:
        result = await db.execute(
            select(ComplianceRule).where(
                and_(
                    ComplianceRule.id == request.rule_set_id,
                    ComplianceRule.is_active,
                )
            )
        )
        rule_set = result.scalar_one_or_none()
        if not rule_set:
            raise NotFoundError("Rule set")
        rule_set_id = str(rule_set.id)
    else:
        # Try to find rules based on funder/mechanism
        funder = request.funder
        mechanism = request.mechanism

        if not funder and application and application.grant:
            grant = await db.get(models_module.Grant, application.grant_id)
            if grant:
                funder = grant.agency

        if funder:
            if mechanism:
                result = await db.execute(
                    select(ComplianceRule).where(
                        and_(
                            ComplianceRule.funder.ilike(f"%{funder}%"),
                            ComplianceRule.mechanism == mechanism,
                            ComplianceRule.is_active,
                        )
                    )
                )
                rule_set = result.scalar_one_or_none()
                if rule_set:
                    rule_set_id = str(rule_set.id)

            if not rule_set_id:
                result = await db.execute(
                    select(ComplianceRule).where(
                        and_(
                            ComplianceRule.funder.ilike(f"%{funder}%"),
                            ComplianceRule.mechanism.is_(None),
                            ComplianceRule.is_active,
                        )
                    )
                )
                rule_set = result.scalar_one_or_none()
                if rule_set:
                    rule_set_id = str(rule_set.id)

    if not rule_set_id:
        raise ValidationError("No compliance rules found for the specified funder/mechanism.")

    # Create a pending scan record
    scan = ComplianceScan(
        kanban_card_id=card_id,
        rule_set_id=UUID(rule_set_id),
        document_type=request.document_type.value,
        file_name=request.file_name,
        results=[],
        passed_count=0,
        failed_count=0,
        warning_count=0,
        overall_status=ScanStatus.PENDING.value,
        scanned_by=current_user.id,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    # Queue the scan task
    task = run_compliance_scan_async.delay(
        scan_id=str(scan.id),
        card_id=str(card_id),
        document_type=request.document_type.value,
        file_content=request.content or "",
        user_id=str(current_user.id),
        rule_set_id=rule_set_id,
        file_name=request.file_name,
        page_count=request.page_count,
        word_count=request.word_count,
        font_info=request.font_info,
        margin_info=request.margin_info,
        line_spacing=request.line_spacing,
        budget_data=request.budget_data,
        sections_found=request.sections_found,
    )

    return AsyncScanResponse(
        scan_id=scan.id,
        task_id=task.id,
        status=ScanStatus.PENDING,
        message="Scan queued for processing. Use the status endpoint to check progress.",
    )


@router.get(
    "/compliance/scans/{scan_id}/status",
    response_model=ComplianceScanStatusResponse,
    summary="Get scan status",
    description="Get the status of a compliance scan (useful for async scans).",
)
async def get_scan_status(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    scan_id: UUID,
) -> ComplianceScanStatusResponse:
    """
    Get the status of a compliance scan.

    This is particularly useful for checking the progress of async scans.
    """
    # Get the scan record
    result = await db.execute(select(ComplianceScan).where(ComplianceScan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise NotFoundError("Scan")

    # Verify user has access to this scan (owns the associated application)
    result = await db.execute(
        select(models_module.GrantApplication).where(
            and_(
                models_module.GrantApplication.id == scan.kanban_card_id,
                models_module.GrantApplication.user_id == current_user.id,
            )
        )
    )
    application = result.scalar_one_or_none()
    if not application:
        raise AuthorizationError("Access denied to this scan")

    return ComplianceScanStatusResponse(
        scan_id=scan.id,
        status=ScanStatus(scan.overall_status),
        passed_count=scan.passed_count,
        failed_count=scan.failed_count,
        warning_count=scan.warning_count,
        scanned_at=scan.scanned_at,
        results=scan.results if scan.overall_status != ScanStatus.PENDING.value else None,
    )


@router.get(
    "/kanban/{card_id}/compliance/results",
    response_model=ComplianceScanList,
    summary="Get compliance scan results",
    description="Get all compliance scan results for a grant application.",
)
async def get_compliance_results(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    card_id: UUID,
    document_type: Optional[DocumentType] = Query(None, description="Filter by document type"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results to return"),
) -> ComplianceScanList:
    """
    Get all compliance scan results for a grant application.

    Results are ordered by scan date (most recent first).
    """
    # Verify the kanban card exists and belongs to user
    await verify_card_ownership(db, card_id, current_user.id)

    # Build query
    query = select(ComplianceScan).where(ComplianceScan.kanban_card_id == card_id)

    if document_type:
        query = query.where(ComplianceScan.document_type == document_type.value)

    query = query.order_by(ComplianceScan.scanned_at.desc()).limit(limit)

    result = await db.execute(query)
    scans = result.scalars().all()

    return ComplianceScanList(
        data=list(scans),
        pagination=PaginationInfo(
            total=len(scans),
            offset=0,
            limit=limit,
            has_more=False,
        ),
    )


@router.get(
    "/kanban/{card_id}/compliance/summary",
    response_model=ComplianceSummary,
    summary="Get compliance summary",
    description="Get a summary of compliance status for a grant application.",
)
async def get_compliance_summary(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    card_id: UUID,
) -> ComplianceSummary:
    """
    Get a summary of compliance status for a grant application.

    Returns an overview of all compliance scans including:
    - Total number of scans
    - Documents scanned
    - Overall compliance status
    - Issue and warning counts
    """
    # Verify the kanban card exists and belongs to user
    await verify_card_ownership(db, card_id, current_user.id)

    # Get all scans for this card
    result = await db.execute(
        select(ComplianceScan)
        .where(ComplianceScan.kanban_card_id == card_id)
        .order_by(ComplianceScan.scanned_at.desc())
    )
    scans = result.scalars().all()

    if not scans:
        return ComplianceSummary(
            kanban_card_id=card_id,
            total_scans=0,
            latest_scan_at=None,
            documents_scanned=[],
            overall_compliance=ScanStatus.PENDING,
            issues_count=0,
            warnings_count=0,
        )

    # Get unique document types (most recent scan per type)
    documents_scanned = list(set(s.document_type for s in scans))

    # Get the most recent scan per document type for status calculation
    latest_by_type = {}
    for scan in scans:
        if scan.document_type not in latest_by_type:
            latest_by_type[scan.document_type] = scan

    # Calculate totals from latest scans
    total_issues = sum(s.failed_count for s in latest_by_type.values())
    total_warnings = sum(s.warning_count for s in latest_by_type.values())

    # Determine overall status
    if total_issues > 0:
        overall_compliance = ScanStatus.FAILED
    elif total_warnings > 0:
        overall_compliance = ScanStatus.WARNING
    else:
        overall_compliance = ScanStatus.PASSED

    return ComplianceSummary(
        kanban_card_id=card_id,
        total_scans=len(scans),
        latest_scan_at=scans[0].scanned_at if scans else None,
        documents_scanned=documents_scanned,
        overall_compliance=overall_compliance,
        issues_count=total_issues,
        warnings_count=total_warnings,
    )


# =============================================================================
# Compliance Rules Endpoints
# =============================================================================


@router.get(
    "/compliance/rules/{funder}",
    response_model=FunderRulesInfo,
    summary="Get funder compliance rules",
    description="Get all compliance rules for a specific funder.",
)
async def get_funder_rules(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    funder: str,
) -> FunderRulesInfo:
    """
    Get all compliance rules for a specific funder.

    Returns:
    - General rules that apply to all mechanisms
    - Mechanism-specific rules
    - List of available mechanisms
    """
    # Get all active rules for this funder
    result = await db.execute(
        select(ComplianceRule).where(
            and_(
                ComplianceRule.funder.ilike(f"%{funder}%"),
                ComplianceRule.is_active,
            )
        )
    )
    rules = result.scalars().all()

    if not rules:
        raise NotFoundError("Compliance rules", funder)

    # Separate general and mechanism-specific rules
    general_rule = None
    mechanism_rules = []
    mechanisms = set()

    for rule in rules:
        if rule.mechanism is None:
            general_rule = rule
        else:
            mechanism_rules.append(rule)
            mechanisms.add(rule.mechanism)

    return FunderRulesInfo(
        funder=funder,
        mechanisms=sorted(list(mechanisms)),
        general_rule_set=general_rule,
        mechanism_rule_sets=mechanism_rules,
    )


@router.get(
    "/compliance/rules",
    response_model=ComplianceRuleList,
    summary="List all compliance rules",
    description="List all available compliance rule sets.",
)
async def list_compliance_rules(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    funder: Optional[str] = Query(None, description="Filter by funder"),
    mechanism: Optional[str] = Query(None, description="Filter by mechanism"),
    include_inactive: bool = Query(False, description="Include inactive rule sets"),
) -> ComplianceRuleList:
    """
    List all available compliance rule sets.

    Filters:
    - funder: Filter by funding organization
    - mechanism: Filter by grant mechanism
    - include_inactive: Include inactive rule sets
    """
    query = select(ComplianceRule)

    if not include_inactive:
        query = query.where(ComplianceRule.is_active)

    if funder:
        query = query.where(ComplianceRule.funder.ilike(f"%{funder}%"))

    if mechanism:
        query = query.where(ComplianceRule.mechanism == mechanism)

    query = query.order_by(ComplianceRule.funder, ComplianceRule.mechanism)

    result = await db.execute(query)
    rules = result.scalars().all()

    return ComplianceRuleList(
        data=list(rules),
        pagination=PaginationInfo(
            total=len(rules),
            offset=0,
            limit=len(rules),
            has_more=False,
        ),
    )


@router.post(
    "/compliance/rules",
    response_model=ComplianceRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create compliance rule set",
    description="Create a new compliance rule set (admin only).",
)
async def create_compliance_rules(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    data: ComplianceRuleCreate,
) -> ComplianceRuleResponse:
    """
    Create a new compliance rule set.

    This allows administrators to define custom compliance rules for
    specific funders and mechanisms.

    Note: In a production environment, this endpoint should be restricted
    to admin users only.
    """
    # Check for existing rule set with same funder/mechanism
    result = await db.execute(
        select(ComplianceRule).where(
            and_(
                ComplianceRule.funder == data.funder,
                ComplianceRule.mechanism == data.mechanism,
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise ValidationError(f"Rule set already exists for {data.funder} / {data.mechanism or 'general'}")

    # Convert rules to dict format for storage
    rules_data = [rule.model_dump() for rule in data.rules]

    rule_set = ComplianceRule(
        funder=data.funder,
        mechanism=data.mechanism,
        name=data.name,
        description=data.description,
        rules=rules_data,
        is_active=True,
        is_system=False,
        created_by=current_user.id,
    )
    db.add(rule_set)
    await db.commit()
    await db.refresh(rule_set)

    return rule_set


@router.get(
    "/compliance/rules/id/{rule_id}",
    response_model=ComplianceRuleResponse,
    summary="Get compliance rule set by ID",
    description="Get a specific compliance rule set.",
)
async def get_compliance_rule(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    rule_id: UUID,
) -> ComplianceRuleResponse:
    """Get a specific compliance rule set by ID."""
    result = await db.execute(select(ComplianceRule).where(ComplianceRule.id == rule_id))
    rule_set = result.scalar_one_or_none()
    if not rule_set:
        raise NotFoundError("Compliance rule set")
    return rule_set


@router.patch(
    "/compliance/rules/id/{rule_id}",
    response_model=ComplianceRuleResponse,
    summary="Update compliance rule set",
    description="Update a compliance rule set.",
)
async def update_compliance_rule(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    rule_id: UUID,
    data: ComplianceRuleUpdate,
) -> ComplianceRuleResponse:
    """
    Update a compliance rule set.

    System rule sets cannot be modified.
    """
    result = await db.execute(select(ComplianceRule).where(ComplianceRule.id == rule_id))
    rule_set = result.scalar_one_or_none()
    if not rule_set:
        raise NotFoundError("Compliance rule set")

    if rule_set.is_system:
        raise AuthorizationError("System rule sets cannot be modified")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            if field == "rules":
                value = [rule.model_dump() if hasattr(rule, "model_dump") else rule for rule in value]
            setattr(rule_set, field, value)

    rule_set.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(rule_set)

    return rule_set


@router.delete(
    "/compliance/rules/id/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete compliance rule set",
    description="Delete a compliance rule set.",
)
async def delete_compliance_rule(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    rule_id: UUID,
) -> None:
    """
    Delete a compliance rule set.

    System rule sets cannot be deleted.
    """
    result = await db.execute(select(ComplianceRule).where(ComplianceRule.id == rule_id))
    rule_set = result.scalar_one_or_none()
    if not rule_set:
        raise NotFoundError("Compliance rule set")

    if rule_set.is_system:
        raise AuthorizationError("System rule sets cannot be deleted")

    await db.delete(rule_set)
    await db.commit()


# =============================================================================
# Utility Endpoints
# =============================================================================


@router.get(
    "/compliance/funders",
    response_model=List[str],
    summary="List available funders",
    description="Get list of funders with compliance rules.",
)
async def list_funders(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> List[str]:
    """Get list of all funders that have compliance rules defined."""
    result = await db.execute(
        select(ComplianceRule.funder).where(ComplianceRule.is_active).distinct().order_by(ComplianceRule.funder)
    )
    funders = result.scalars().all()
    return list(funders)


@router.get(
    "/compliance/document-types",
    response_model=List[dict],
    summary="List document types",
    description="Get list of supported document types for compliance scanning.",
)
async def list_document_types() -> List[dict]:
    """Get list of supported document types for compliance scanning."""
    return [{"value": dt.value, "label": dt.value.replace("_", " ").title()} for dt in DocumentType]
