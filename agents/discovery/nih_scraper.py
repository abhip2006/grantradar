"""
NIH Grant Discovery Agent
Scrapes NIH funding opportunities with intelligent change detection.
"""

import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import anthropic
import redis
import structlog
from bs4 import BeautifulSoup
from celery import Celery
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field, field_validator
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from backend.core.config import settings

# ===== Logging Setup =====
logger = structlog.get_logger(__name__)

# ===== Celery Setup =====
celery_app = Celery(
    "nih_scraper",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minute hard limit
    task_soft_time_limit=540,  # 9 minute soft limit
)

# ===== Redis Keys =====
REDIS_HASH_KEY = "nih:scraper:content_hash"
REDIS_STATE_KEY = "nih:scraper:state"
REDIS_STREAM_KEY = "grants:discovered"

# ===== Constants =====
NIH_FUNDING_URL = "https://grants.nih.gov/funding/searchguide/"
SCREENSHOT_DIR = Path("/tmp/nih_scraper_screenshots")
MAX_TOKENS_FOR_EXTRACTION = 100000  # Claude's context limit safety margin
CHARS_PER_TOKEN_ESTIMATE = 4  # Conservative estimate


# ===== Pydantic Models =====
class NIHFundingOpportunity(BaseModel):
    """Extracted NIH funding opportunity from scraped HTML."""

    foa_number: str = Field(..., description="Funding Opportunity Announcement number")
    title: str = Field(..., description="Grant title")
    deadline: Optional[str] = Field(None, description="Application deadline")
    url: Optional[str] = Field(None, description="Direct URL to the opportunity")
    description: Optional[str] = Field(None, description="Brief description")
    eligibility: Optional[str] = Field(None, description="Eligibility requirements")

    @field_validator("foa_number")
    @classmethod
    def validate_foa_number(cls, v: str) -> str:
        """Validate FOA number format."""
        v = v.strip()
        if not v:
            raise ValueError("FOA number cannot be empty")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title is not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        return v


class ScraperState(BaseModel):
    """Tracks scraper state for monitoring and debugging."""

    content_hash: Optional[str] = Field(None, description="SHA-256 hash of filtered content")
    last_run: Optional[datetime] = Field(None, description="Last successful run timestamp")
    last_change_detected: Optional[datetime] = Field(None, description="When content last changed")
    error_count: int = Field(0, description="Consecutive error count")
    last_error: Optional[str] = Field(None, description="Last error message")
    opportunities_found: int = Field(0, description="Opportunities found in last run")


class DiscoveredGrant(BaseModel):
    """Normalized grant output for the Redis stream."""

    source: str = Field("nih", description="Grant source identifier")
    source_id: str = Field(..., description="Unique ID from source (FOA number)")
    title: str = Field(..., description="Grant title")
    deadline: Optional[str] = Field(None, description="Application deadline")
    url: Optional[str] = Field(None, description="Direct URL")
    description: Optional[str] = Field(None, description="Description")
    eligibility: Optional[str] = Field(None, description="Eligibility info")
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_data: dict = Field(default_factory=dict, description="Original extracted data")

    def to_stream_dict(self) -> dict[str, str]:
        """Convert to Redis stream-compatible dict (all string values)."""
        return {
            "source": self.source,
            "source_id": self.source_id,
            "title": self.title,
            "deadline": self.deadline or "",
            "url": self.url or "",
            "description": self.description or "",
            "eligibility": self.eligibility or "",
            "discovered_at": self.discovered_at.isoformat(),
            "raw_data": json.dumps(self.raw_data),
        }


# ===== Helper Functions =====
def get_redis_client() -> redis.Redis:
    """Get Redis client instance."""
    return redis.from_url(settings.redis_url, decode_responses=True)


def filter_dynamic_content(html: str) -> str:
    """
    Remove dynamic elements from HTML before hashing.
    Filters out timestamps, session IDs, CSRF tokens, etc.
    """
    # Remove script tags entirely
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Remove style tags
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Remove comments
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)

    # Remove common dynamic attributes
    patterns_to_remove = [
        r'data-timestamp="[^"]*"',
        r'data-session="[^"]*"',
        r'csrf[_-]?token="[^"]*"',
        r'nonce="[^"]*"',
        r'data-random="[^"]*"',
        r'__RequestVerificationToken[^"]*"[^"]*"',
        r'data-request-id="[^"]*"',
    ]

    for pattern in patterns_to_remove:
        html = re.sub(pattern, "", html, flags=re.IGNORECASE)

    # Remove common timestamp patterns in text
    html = re.sub(r"\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s*(?:AM|PM)?", "", html, flags=re.IGNORECASE)
    html = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", "", html)

    # Normalize whitespace
    html = re.sub(r"\s+", " ", html)

    return html.strip()


def compute_content_hash(html: str) -> str:
    """Compute SHA-256 hash of filtered HTML content."""
    filtered = filter_dynamic_content(html)
    return hashlib.sha256(filtered.encode("utf-8")).hexdigest()


def estimate_tokens(text: str) -> int:
    """Estimate token count for text (conservative)."""
    return len(text) // CHARS_PER_TOKEN_ESTIMATE


def truncate_for_claude(html: str, max_tokens: int = MAX_TOKENS_FOR_EXTRACTION) -> str:
    """Truncate HTML to fit within Claude's context window."""
    estimated_tokens = estimate_tokens(html)

    if estimated_tokens <= max_tokens:
        return html

    # Calculate safe character limit
    max_chars = max_tokens * CHARS_PER_TOKEN_ESTIMATE

    logger.warning(
        "truncating_html_for_claude",
        original_chars=len(html),
        max_chars=max_chars,
        estimated_tokens=estimated_tokens,
    )

    return html[:max_chars]


# ===== Claude API Integration =====
EXTRACTION_PROMPT = """Extract grant funding opportunities from this NIH funding page HTML.

Return a JSON array of opportunities. Each opportunity should have:
- foa_number: The Funding Opportunity Announcement number (e.g., "PAR-24-001", "RFA-CA-24-001")
- title: The grant title
- deadline: Application deadline if mentioned (any format)
- url: Direct URL to the opportunity if available
- description: Brief description of the funding opportunity
- eligibility: Who is eligible to apply

Important:
- Only include actual funding opportunities, not navigation or informational content
- If a field is not available, use null
- Return an empty array [] if no opportunities are found
- Return ONLY the JSON array, no other text

HTML Content:
"""


class ClaudeExtractionError(Exception):
    """Raised when Claude API extraction fails."""

    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((anthropic.APIConnectionError, anthropic.RateLimitError)),
)
async def extract_opportunities_with_claude(html: str) -> list[NIHFundingOpportunity]:
    """
    Use Claude API to extract grant opportunities from HTML.
    Includes retry logic for API failures.
    """
    if not settings.anthropic_api_key:
        raise ClaudeExtractionError("Anthropic API key not configured")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # Truncate HTML if needed
    truncated_html = truncate_for_claude(html)

    prompt = EXTRACTION_PROMPT + truncated_html

    logger.info(
        "calling_claude_api",
        html_length=len(truncated_html),
        estimated_tokens=estimate_tokens(prompt),
    )

    try:
        message = client.messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text.strip()

        # Parse JSON response
        # Handle potential markdown code blocks
        if response_text.startswith("```"):
            # Extract JSON from code block
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
            if json_match:
                response_text = json_match.group(1)

        opportunities_data = json.loads(response_text)

        if not isinstance(opportunities_data, list):
            raise ClaudeExtractionError(f"Expected JSON array, got {type(opportunities_data)}")

        # Validate and parse opportunities
        opportunities = []
        for item in opportunities_data:
            try:
                opp = NIHFundingOpportunity(**item)
                opportunities.append(opp)
            except Exception as e:
                logger.warning(
                    "invalid_opportunity_data",
                    data=item,
                    error=str(e),
                )

        logger.info(
            "claude_extraction_complete",
            total_extracted=len(opportunities_data),
            valid_opportunities=len(opportunities),
        )

        return opportunities

    except anthropic.APIError as e:
        logger.error("claude_api_error", error=str(e))
        raise ClaudeExtractionError(f"Claude API error: {e}")
    except json.JSONDecodeError as e:
        logger.error("claude_json_parse_error", error=str(e), response=response_text[:500])
        raise ClaudeExtractionError(f"Failed to parse Claude response as JSON: {e}")


def extract_opportunities_with_beautifulsoup(html: str) -> list[NIHFundingOpportunity]:
    """
    Fallback extraction using BeautifulSoup when Claude API fails.
    Uses heuristics to find grant opportunities.
    """
    logger.info("falling_back_to_beautifulsoup")

    soup = BeautifulSoup(html, "lxml")
    opportunities = []

    # Common patterns for NIH grant listings
    # Look for tables with grant information
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            text = " ".join(cell.get_text(strip=True) for cell in cells)

            # Look for FOA number patterns
            foa_match = re.search(r"((?:PAR|RFA|PA|NOT|OTA)-\d{2}-\d{3,4})", text, re.IGNORECASE)

            if foa_match:
                foa_number = foa_match.group(1).upper()

                # Try to extract title (usually nearby text)
                title = text.replace(foa_number, "").strip()[:200] or f"NIH Opportunity {foa_number}"

                # Look for links
                link = row.find("a", href=True)
                url = link["href"] if link else None
                if url and not url.startswith("http"):
                    url = f"https://grants.nih.gov{url}"

                try:
                    opp = NIHFundingOpportunity(
                        foa_number=foa_number,
                        title=title,
                        url=url,
                    )
                    opportunities.append(opp)
                except Exception:
                    pass

    # Also search in links and list items
    for link in soup.find_all("a", href=True):
        text = link.get_text(strip=True)
        href = link["href"]

        foa_match = re.search(r"((?:PAR|RFA|PA|NOT|OTA)-\d{2}-\d{3,4})", text + " " + href, re.IGNORECASE)

        if foa_match:
            foa_number = foa_match.group(1).upper()

            # Check if we already have this FOA
            if any(o.foa_number == foa_number for o in opportunities):
                continue

            url = href if href.startswith("http") else f"https://grants.nih.gov{href}"

            try:
                opp = NIHFundingOpportunity(
                    foa_number=foa_number,
                    title=text[:200] or f"NIH Opportunity {foa_number}",
                    url=url,
                )
                opportunities.append(opp)
            except Exception:
                pass

    logger.info(
        "beautifulsoup_extraction_complete",
        opportunities_found=len(opportunities),
    )

    return opportunities


# ===== Main Scraper Logic =====
async def scrape_nih_page() -> tuple[str, bytes]:
    """
    Scrape NIH funding page using Playwright.
    Returns (html_content, screenshot_bytes).
    """
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        try:
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )

            page = await context.new_page()

            logger.info("navigating_to_nih_page", url=NIH_FUNDING_URL)

            # Navigate with timeout
            await page.goto(
                NIH_FUNDING_URL,
                wait_until="networkidle",
                timeout=60000,  # 60 second timeout
            )

            # Wait for content to load
            await page.wait_for_load_state("domcontentloaded")

            # Additional wait for dynamic content
            await asyncio.sleep(2)

            # Get page content
            html_content = await page.content()

            # Take screenshot
            screenshot = await page.screenshot(full_page=True)

            logger.info(
                "page_scraped_successfully",
                content_length=len(html_content),
            )

            return html_content, screenshot

        except PlaywrightTimeoutError as e:
            # Take error screenshot
            try:
                error_screenshot = await page.screenshot(full_page=True)
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                screenshot_path = SCREENSHOT_DIR / f"error_{timestamp}.png"
                screenshot_path.write_bytes(error_screenshot)
                logger.error(
                    "playwright_timeout",
                    error=str(e),
                    screenshot_path=str(screenshot_path),
                )
            except Exception:
                logger.error("playwright_timeout", error=str(e))
            raise

        finally:
            await browser.close()


async def run_nih_scraper() -> dict[str, Any]:
    """
    Main scraper execution logic.
    Returns status dict with results.
    """
    redis_client = get_redis_client()
    result = {
        "success": False,
        "change_detected": False,
        "opportunities_found": 0,
        "error": None,
    }

    # Load current state
    state_json = redis_client.get(REDIS_STATE_KEY)
    state = ScraperState(**json.loads(state_json)) if state_json else ScraperState()

    try:
        # Scrape the page
        html_content, screenshot = await scrape_nih_page()

        # Compute hash
        new_hash = compute_content_hash(html_content)
        stored_hash = redis_client.get(REDIS_HASH_KEY)

        logger.info(
            "content_hash_comparison",
            new_hash=new_hash[:16] + "...",
            stored_hash=(stored_hash[:16] + "..." if stored_hash else None),
        )

        # Check if content changed
        if stored_hash and new_hash == stored_hash:
            logger.info("no_content_change_detected")
            result["success"] = True
            result["change_detected"] = False

            # Update state
            state.last_run = datetime.now(timezone.utc)
            state.error_count = 0
            state.last_error = None
            redis_client.set(REDIS_STATE_KEY, state.model_dump_json())

            return result

        # Content changed - extract opportunities
        logger.info("content_change_detected")
        result["change_detected"] = True

        # Try Claude first, fall back to BeautifulSoup
        try:
            opportunities = await extract_opportunities_with_claude(html_content)
        except ClaudeExtractionError as e:
            logger.warning("claude_extraction_failed_using_fallback", error=str(e))
            opportunities = extract_opportunities_with_beautifulsoup(html_content)

        result["opportunities_found"] = len(opportunities)

        # Publish to Redis stream
        for opp in opportunities:
            discovered_grant = DiscoveredGrant(
                source="nih",
                source_id=opp.foa_number,
                title=opp.title,
                deadline=opp.deadline,
                url=opp.url,
                description=opp.description,
                eligibility=opp.eligibility,
                raw_data=opp.model_dump(),
            )

            # Wrap in "data" key as JSON string - format expected by validator
            import json as json_lib

            redis_client.xadd(
                REDIS_STREAM_KEY,
                {"data": json_lib.dumps(discovered_grant.to_stream_dict())},
            )

            logger.info(
                "published_to_stream",
                foa_number=opp.foa_number,
                title=opp.title[:50] + "..." if len(opp.title) > 50 else opp.title,
            )

        # Update hash
        redis_client.set(REDIS_HASH_KEY, new_hash)

        # Update state
        state.content_hash = new_hash
        state.last_run = datetime.now(timezone.utc)
        state.last_change_detected = datetime.now(timezone.utc)
        state.error_count = 0
        state.last_error = None
        state.opportunities_found = len(opportunities)
        redis_client.set(REDIS_STATE_KEY, state.model_dump_json())

        # Save success screenshot
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        screenshot_path = SCREENSHOT_DIR / f"success_{timestamp}.png"
        screenshot_path.write_bytes(screenshot)

        result["success"] = True

        logger.info(
            "scraper_completed_successfully",
            opportunities_found=len(opportunities),
            screenshot_path=str(screenshot_path),
        )

        return result

    except Exception as e:
        # Update error state
        state.error_count += 1
        state.last_error = str(e)
        state.last_run = datetime.now(timezone.utc)
        redis_client.set(REDIS_STATE_KEY, state.model_dump_json())

        result["error"] = str(e)

        logger.error(
            "scraper_failed",
            error=str(e),
            error_count=state.error_count,
        )

        raise


# ===== Celery Task =====
@celery_app.task(
    bind=True,
    name="agents.discovery.nih_scraper.scrape_nih_funding",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 3},
)
def scrape_nih_funding(self) -> dict[str, Any]:
    """
    Celery task to scrape NIH funding opportunities.
    Runs every 30 minutes via Celery Beat.
    """
    logger.info(
        "starting_nih_scraper_task",
        task_id=self.request.id,
    )

    try:
        # Run async scraper in event loop
        result = asyncio.run(run_nih_scraper())

        logger.info(
            "nih_scraper_task_completed",
            task_id=self.request.id,
            result=result,
        )

        return result

    except Exception as e:
        logger.error(
            "nih_scraper_task_failed",
            task_id=self.request.id,
            error=str(e),
        )
        raise


# ===== Celery Beat Schedule =====
celery_app.conf.beat_schedule = {
    "scrape-nih-funding-every-30-minutes": {
        "task": "agents.discovery.nih_scraper.scrape_nih_funding",
        "schedule": 1800.0,  # 30 minutes in seconds
    },
}


# ===== CLI Entry Point =====
if __name__ == "__main__":
    """Run scraper directly for testing."""
    import sys

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    try:
        result = asyncio.run(run_nih_scraper())
        print(f"\nResult: {json.dumps(result, indent=2, default=str)}")
        sys.exit(0 if result["success"] else 1)
    except Exception as e:
        print(f"\nFailed: {e}")
        sys.exit(1)
