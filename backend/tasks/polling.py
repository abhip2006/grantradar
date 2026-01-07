"""
GrantRadar Polling Tasks

Celery tasks for polling external grant data sources (Grants.gov, NSF, NIH).
These tasks are scheduled via Celery Beat to run at regular intervals.

Scheduled Tasks:
    - poll_grants_gov: Every 5 minutes (Grants.gov RSS and XML)
    - poll_nsf: Every 15 minutes (NSF Award Search API)
    - scrape_nih: Every 30 minutes (NIH funding page scraper)

Each task:
    - Instantiates the appropriate discovery agent
    - Executes the discovery process
    - Publishes results to Redis stream "grants:discovered"
    - Returns stats (grants found, errors, etc.)
    - Includes circuit breaker protection and retry logic
"""

import asyncio
import logging
from typing import Any

from backend.celery_app import (
    celery_app,
    grants_gov_circuit,
    nsf_circuit,
    nih_circuit,
    CircuitBreakerOpenError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Grants.gov Polling Tasks
# =============================================================================


@celery_app.task(
    name="backend.tasks.polling.poll_grants_gov",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # 10 minutes max delay
    retry_kwargs={"max_retries": 3},
    acks_late=True,
    time_limit=1800,  # 30 minute hard limit (for XML processing)
    soft_time_limit=1500,  # 25 minute soft limit
)
def poll_grants_gov(self) -> dict[str, Any]:
    """
    Poll Grants.gov for new funding opportunities.

    Uses both RSS feed and XML extract agents to discover grants.
    Scheduled to run every 5 minutes via Celery Beat.

    Returns:
        Dict with polling results including:
            - status: "success" or "error"
            - grants_discovered: Total count of new grants
            - sources: Dict with results per source (rss, xml)
            - errors: List of any errors encountered

    Raises:
        Exception: On critical failures after retries
    """
    logger.info(
        "Starting Grants.gov polling task",
        extra={"task_id": self.request.id},
    )

    results = {
        "status": "success",
        "grants_discovered": 0,
        "sources": {},
        "errors": [],
    }

    # Check circuit breaker
    if not grants_gov_circuit.can_execute():
        logger.warning(
            "Grants.gov circuit breaker is open, skipping poll",
            extra={"task_id": self.request.id},
        )
        raise CircuitBreakerOpenError("Grants.gov circuit breaker is open")

    try:
        # Import agents (lazy import to avoid circular dependencies)
        from agents.discovery.grants_gov_rss import GrantsGovRSSAgent
        from agents.discovery.grants_gov_xml import GrantsGovXMLAgent

        # Poll RSS feed
        logger.info("Polling Grants.gov RSS feed")
        try:
            rss_agent = GrantsGovRSSAgent()
            rss_result = asyncio.run(_run_rss_agent(rss_agent))
            results["sources"]["rss"] = rss_result
            results["grants_discovered"] += rss_result.get("grants_discovered", 0)
        except Exception as e:
            logger.error(
                f"Grants.gov RSS polling failed: {e}",
                exc_info=True,
                extra={"task_id": self.request.id},
            )
            results["errors"].append(f"RSS: {str(e)}")

        # Poll XML extract (less frequently - every other call)
        # To reduce load, we can check call count or time
        # For now, we'll try XML on every call but with shorter timeout
        logger.info("Polling Grants.gov XML extract")
        try:
            xml_agent = GrantsGovXMLAgent()
            xml_result = asyncio.run(_run_xml_agent(xml_agent))
            results["sources"]["xml"] = xml_result
            results["grants_discovered"] += xml_result.get("grants_discovered", 0)
        except Exception as e:
            logger.error(
                f"Grants.gov XML polling failed: {e}",
                exc_info=True,
                extra={"task_id": self.request.id},
            )
            results["errors"].append(f"XML: {str(e)}")

        # Record success with circuit breaker
        grants_gov_circuit.record_success()

        # Set overall status
        if results["errors"]:
            results["status"] = "partial_success"

        logger.info(
            f"Grants.gov polling completed: {results['grants_discovered']} grants discovered",
            extra={
                "task_id": self.request.id,
                "grants_discovered": results["grants_discovered"],
                "errors_count": len(results["errors"]),
            },
        )

        return results

    except Exception as e:
        # Record failure with circuit breaker
        grants_gov_circuit.record_failure()

        results["status"] = "error"
        results["errors"].append(str(e))

        logger.error(
            f"Grants.gov polling task failed: {e}",
            exc_info=True,
            extra={"task_id": self.request.id},
        )

        raise


async def _run_rss_agent(agent) -> dict[str, Any]:
    """Helper to run RSS agent and return results."""
    try:
        grants = await agent.discover_new_grants()
        return {
            "status": "success",
            "grants_discovered": len(grants),
            "grant_ids": [g.external_id for g in grants[:10]],  # Sample IDs
        }
    finally:
        await agent.close()


async def _run_xml_agent(agent) -> dict[str, Any]:
    """Helper to run XML agent and return results."""
    try:
        grants = await agent.discover_new_grants()
        return {
            "status": "success",
            "grants_discovered": len(grants),
            "sample_ids": [g.external_id for g in grants[:10]],  # Sample IDs
        }
    finally:
        await agent.close()


# =============================================================================
# NSF Polling Task
# =============================================================================


@celery_app.task(
    name="backend.tasks.polling.poll_nsf",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # 10 minutes max delay
    retry_kwargs={"max_retries": 3},
    acks_late=True,
    time_limit=600,  # 10 minute hard limit
    soft_time_limit=540,  # 9 minute soft limit
)
def poll_nsf(self) -> dict[str, Any]:
    """
    Poll NSF Award Search API for new grants.

    Scheduled to run every 15 minutes via Celery Beat.

    Returns:
        Dict with polling results:
            - status: "success" or "error"
            - grants_discovered: Number of new grants found
            - source: "nsf"

    Raises:
        Exception: On critical failures after retries
    """
    logger.info(
        "Starting NSF polling task",
        extra={"task_id": self.request.id},
    )

    # Check circuit breaker
    if not nsf_circuit.can_execute():
        logger.warning(
            "NSF circuit breaker is open, skipping poll",
            extra={"task_id": self.request.id},
        )
        raise CircuitBreakerOpenError("NSF circuit breaker is open")

    try:
        # Import agent (lazy import)
        from agents.discovery.nsf_api import NSFDiscoveryAgent

        # Instantiate agent
        agent = NSFDiscoveryAgent()

        # Run discovery in async context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            count = loop.run_until_complete(agent.run())
        finally:
            loop.close()

        # Record success with circuit breaker
        nsf_circuit.record_success()

        logger.info(
            f"NSF polling completed: {count} grants discovered",
            extra={
                "task_id": self.request.id,
                "grants_discovered": count,
            },
        )

        return {
            "status": "success",
            "grants_discovered": count,
            "source": "nsf",
        }

    except Exception as e:
        # Record failure with circuit breaker
        nsf_circuit.record_failure()

        logger.error(
            f"NSF polling task failed: {e}",
            exc_info=True,
            extra={"task_id": self.request.id},
        )

        raise


# =============================================================================
# NIH Scraping Task
# =============================================================================


@celery_app.task(
    name="backend.tasks.polling.scrape_nih",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # 10 minutes max delay
    retry_kwargs={"max_retries": 3},
    acks_late=True,
    time_limit=600,  # 10 minute hard limit
    soft_time_limit=540,  # 9 minute soft limit
)
def scrape_nih(self) -> dict[str, Any]:
    """
    Scrape NIH funding opportunities page using Playwright.

    Uses intelligent change detection to only extract when content changes.
    Falls back from Claude API to BeautifulSoup if needed.
    Scheduled to run every 30 minutes via Celery Beat.

    Returns:
        Dict with scraping results:
            - status: "success" or "error"
            - success: Boolean
            - change_detected: Whether page content changed
            - opportunities_found: Number of opportunities extracted
            - error: Error message if failed

    Raises:
        Exception: On critical failures after retries
    """
    logger.info(
        "Starting NIH scraping task",
        extra={"task_id": self.request.id},
    )

    # Check circuit breaker
    if not nih_circuit.can_execute():
        logger.warning(
            "NIH circuit breaker is open, skipping scrape",
            extra={"task_id": self.request.id},
        )
        raise CircuitBreakerOpenError("NIH circuit breaker is open")

    try:
        # Import scraper function (lazy import)
        from agents.discovery.nih_scraper import run_nih_scraper

        # Run the scraper in async context
        result = asyncio.run(run_nih_scraper())

        # Record success with circuit breaker
        nih_circuit.record_success()

        logger.info(
            f"NIH scraping completed: {result.get('opportunities_found', 0)} opportunities found",
            extra={
                "task_id": self.request.id,
                "change_detected": result.get("change_detected", False),
                "opportunities_found": result.get("opportunities_found", 0),
            },
        )

        # Add status field for consistency
        result["status"] = "success" if result.get("success") else "error"

        return result

    except Exception as e:
        # Record failure with circuit breaker
        nih_circuit.record_failure()

        logger.error(
            f"NIH scraping task failed: {e}",
            exc_info=True,
            extra={"task_id": self.request.id},
        )

        raise


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "poll_grants_gov",
    "poll_nsf",
    "scrape_nih",
]
