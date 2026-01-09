"""
GrantRadar Compliance Tasks

Celery tasks for async compliance scanning and related maintenance.

Tasks:
    - run_compliance_scan_async: Run compliance scan as background task
    - cleanup_old_scans: Remove old scan results for maintenance

Queue: normal (all tasks run on normal priority queue)
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from backend.celery_app import celery_app
from backend.database import get_sync_db
from backend.models.compliance import ComplianceRule, ComplianceScan
from backend.services.compliance_scanner import ComplianceScannerService

logger = logging.getLogger(__name__)


# =============================================================================
# Async Compliance Scan Task
# =============================================================================


@celery_app.task(
    name="backend.tasks.compliance_tasks.run_compliance_scan_async",
    queue="normal",
    soft_time_limit=300,  # 5 minutes
    time_limit=600,  # 10 minutes
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def run_compliance_scan_async(
    self,
    scan_id: str,
    card_id: str,
    document_type: str,
    file_content: str,
    user_id: str,
    rule_set_id: str,
    file_name: Optional[str] = None,
    page_count: Optional[int] = None,
    word_count: Optional[int] = None,
    font_info: Optional[Dict[str, Any]] = None,
    margin_info: Optional[Dict[str, Any]] = None,
    line_spacing: Optional[float] = None,
    budget_data: Optional[Dict[str, Any]] = None,
    sections_found: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Run compliance scan as background task.

    This task processes a compliance scan asynchronously and updates the
    scan record in the database with results.

    Args:
        scan_id: ID of the pending scan record to update.
        card_id: Grant application (kanban card) ID.
        document_type: Type of document being scanned.
        file_content: Text content to scan.
        user_id: User who requested the scan.
        rule_set_id: Compliance rule set to use.
        file_name: Optional filename.
        page_count: Optional page count.
        word_count: Optional word count.
        font_info: Optional font information.
        margin_info: Optional margin information.
        line_spacing: Optional line spacing.
        budget_data: Optional budget data for validation.
        sections_found: Optional list of section headings found.

    Returns:
        dict: Scan results and statistics.

    Raises:
        SQLAlchemyError: On database errors (will trigger retry).
    """
    logger.info(f"Starting async compliance scan for scan_id={scan_id}")
    start_time = datetime.utcnow()

    db = get_sync_db()

    try:
        # Get the scan record
        scan_uuid = UUID(scan_id)
        result = db.execute(
            select(ComplianceScan).where(ComplianceScan.id == scan_uuid)
        )
        scan = result.scalar_one_or_none()

        if not scan:
            error_msg = f"Scan record not found: {scan_id}"
            logger.error(error_msg)
            return {"error": error_msg, "scan_id": scan_id}

        # Get the rule set
        rule_set_uuid = UUID(rule_set_id)
        result = db.execute(
            select(ComplianceRule).where(ComplianceRule.id == rule_set_uuid)
        )
        rule_set = result.scalar_one_or_none()

        if not rule_set:
            # Update scan to failed status
            scan.overall_status = "failed"
            scan.results = [{"error": "Rule set not found"}]
            db.commit()
            error_msg = f"Rule set not found: {rule_set_id}"
            logger.error(error_msg)
            return {"error": error_msg, "scan_id": scan_id}

        # Initialize scanner service
        scanner = ComplianceScannerService()

        # Validate document content
        try:
            from backend.schemas.compliance import DocumentType as DocType
            doc_type_enum = DocType(document_type)
            scanner.validate_document_content(
                content=file_content,
                document_type=doc_type_enum,
            )
        except ValueError as e:
            # Validation failed but continue with scan
            logger.warning(f"Document validation warning: {e}")

        # Run the compliance scan
        scan_results = scanner.run_scan(
            rules=rule_set.rules,
            document_type=doc_type_enum,
            content=file_content,
            page_count=page_count,
            word_count=word_count,
            font_info=font_info,
            margin_info=margin_info,
            line_spacing=line_spacing,
            budget_data=budget_data,
            sections_found=sections_found,
        )

        # Count results
        passed_count = sum(1 for r in scan_results if r["passed"])
        failed_count = sum(
            1 for r in scan_results
            if not r["passed"] and r.get("severity") == "error"
        )
        warning_count = sum(
            1 for r in scan_results
            if not r["passed"] and r.get("severity") == "warning"
        )

        # Determine overall status
        if failed_count > 0:
            overall_status = "failed"
        elif warning_count > 0:
            overall_status = "warning"
        else:
            overall_status = "passed"

        # Calculate content hash for duplicate detection
        file_content_hash = None
        if file_content:
            file_content_hash = scanner.calculate_content_hash(file_content)

        # Update scan record
        scan.results = scan_results
        scan.passed_count = passed_count
        scan.failed_count = failed_count
        scan.warning_count = warning_count
        scan.overall_status = overall_status
        scan.file_content_hash = file_content_hash
        scan.scanned_at = datetime.utcnow()

        db.commit()

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        logger.info(
            f"Completed async compliance scan for scan_id={scan_id}, "
            f"status={overall_status}, duration={duration:.2f}s"
        )

        return {
            "scan_id": scan_id,
            "status": overall_status,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "warning_count": warning_count,
            "duration_seconds": duration,
        }

    except SQLAlchemyError as e:
        db.rollback()
        error_msg = f"Database error during scan: {e}"
        logger.error(error_msg, exc_info=True)

        # Try to update scan to failed status
        try:
            result = db.execute(
                select(ComplianceScan).where(ComplianceScan.id == UUID(scan_id))
            )
            scan = result.scalar_one_or_none()
            if scan:
                scan.overall_status = "failed"
                scan.results = [{"error": str(e)}]
                db.commit()
        except Exception:
            pass

        # Retry the task
        raise self.retry(exc=e)

    except Exception as e:
        error_msg = f"Unexpected error during scan: {e}"
        logger.error(error_msg, exc_info=True)

        # Try to update scan to failed status
        try:
            result = db.execute(
                select(ComplianceScan).where(ComplianceScan.id == UUID(scan_id))
            )
            scan = result.scalar_one_or_none()
            if scan:
                scan.overall_status = "failed"
                scan.results = [{"error": str(e)}]
                db.commit()
        except Exception:
            pass

        return {
            "scan_id": scan_id,
            "error": error_msg,
            "status": "failed",
        }

    finally:
        db.close()


# =============================================================================
# Cleanup Task for Old Scans
# =============================================================================


@celery_app.task(
    name="backend.tasks.compliance_tasks.cleanup_old_scans",
    queue="normal",
    soft_time_limit=600,  # 10 minutes
    time_limit=900,  # 15 minutes
)
def cleanup_old_scans(days: int = 90) -> Dict[str, Any]:
    """
    Remove scan results older than specified days.

    This maintenance task cleans up old compliance scan records to manage
    database size. Old scans that haven't been referenced or updated are
    safe to delete.

    Args:
        days: Number of days to retain scans (default: 90).

    Returns:
        dict: Cleanup statistics.

    Raises:
        SQLAlchemyError: On database errors.
    """
    logger.info(f"Cleaning up compliance scans older than {days} days")
    start_time = datetime.utcnow()
    stats: Dict[str, Any] = {
        "started_at": start_time.isoformat(),
        "scans_deleted": 0,
        "by_status": {},
    }

    db = get_sync_db()

    try:
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get statistics before deletion
        from sqlalchemy import func

        status_counts = db.execute(
            select(
                ComplianceScan.overall_status,
                func.count(ComplianceScan.id).label("count"),
            )
            .where(ComplianceScan.scanned_at < cutoff_date)
            .group_by(ComplianceScan.overall_status)
        ).all()

        for status, count in status_counts:
            stats["by_status"][status] = count

        # Delete old scans
        delete_query = delete(ComplianceScan).where(
            ComplianceScan.scanned_at < cutoff_date
        )
        result = db.execute(delete_query)
        stats["scans_deleted"] = result.rowcount

        db.commit()

        end_time = datetime.utcnow()
        stats["completed_at"] = end_time.isoformat()
        stats["duration_seconds"] = (end_time - start_time).total_seconds()

        logger.info(
            f"Deleted {stats['scans_deleted']} old compliance scans",
            extra={"stats": stats},
        )

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to cleanup old scans: {e}", exc_info=True)
        raise
    finally:
        db.close()

    return stats


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "run_compliance_scan_async",
    "cleanup_old_scans",
]
