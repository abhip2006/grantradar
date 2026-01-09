"""
Compliance Scanner Service
Core logic for validating documents against funder-specific compliance rules.
"""
import hashlib
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

import structlog

from backend.schemas.compliance import DocumentType, RuleSeverity, RuleType

logger = structlog.get_logger(__name__)


class ComplianceScannerService:
    """
    Service for running compliance scans on grant application documents.

    Validates documents against configurable rules including:
    - Page limits
    - Word count limits
    - Required sections detection
    - Budget arithmetic validation
    - Font and margin compliance (basic checks)
    - Line spacing validation
    """

    def __init__(self):
        """Initialize the compliance scanner service."""
        self.rule_handlers = {
            RuleType.PAGE_LIMIT.value: self._check_page_limit,
            RuleType.WORD_COUNT.value: self._check_word_count,
            RuleType.REQUIRED_SECTION.value: self._check_required_section,
            RuleType.BUDGET_ARITHMETIC.value: self._check_budget_arithmetic,
            RuleType.FONT_SIZE.value: self._check_font_size,
            RuleType.MARGIN.value: self._check_margin,
            RuleType.LINE_SPACING.value: self._check_line_spacing,
            RuleType.FILE_FORMAT.value: self._check_file_format,
            RuleType.CITATION_FORMAT.value: self._check_citation_format,
            RuleType.CUSTOM.value: self._check_custom_rule,
        }

    def run_scan(
        self,
        rules: List[Dict[str, Any]],
        document_type: DocumentType,
        content: Optional[str] = None,
        page_count: Optional[int] = None,
        word_count: Optional[int] = None,
        font_info: Optional[Dict[str, Any]] = None,
        margin_info: Optional[Dict[str, Any]] = None,
        line_spacing: Optional[float] = None,
        budget_data: Optional[Dict[str, Any]] = None,
        sections_found: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Run compliance scan using the provided rules.

        Args:
            rules: List of rule definitions to check
            document_type: Type of document being scanned
            content: Text content of the document
            page_count: Number of pages in the document
            word_count: Word count of the document
            font_info: Font information (size, family)
            margin_info: Margin information (top, bottom, left, right in inches)
            line_spacing: Line spacing value
            budget_data: Budget data for arithmetic validation
            sections_found: List of section headings found in document

        Returns:
            List of scan result dictionaries
        """
        results = []

        # Build context for rule checking
        context = {
            "document_type": document_type.value if isinstance(document_type, DocumentType) else document_type,
            "content": content,
            "page_count": page_count,
            "word_count": word_count,
            "font_info": font_info or {},
            "margin_info": margin_info or {},
            "line_spacing": line_spacing,
            "budget_data": budget_data or {},
            "sections_found": sections_found or [],
        }

        # If content provided but word count not, calculate it
        if content and not word_count:
            context["word_count"] = len(content.split())

        # Process each rule
        for rule in rules:
            rule_type = rule.get("type", "")

            # Check if rule applies to this document type
            applicable_doc_types = rule.get("document_types")
            if applicable_doc_types and context["document_type"] not in applicable_doc_types:
                continue

            # Get the handler for this rule type
            handler = self.rule_handlers.get(rule_type)
            if not handler:
                logger.warning(f"Unknown rule type: {rule_type}")
                continue

            try:
                result = handler(rule, context)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing rule {rule.get('name')}: {str(e)}")
                results.append({
                    "rule_id": rule.get("id", str(uuid4())),
                    "rule_name": rule.get("name", "Unknown"),
                    "rule_type": rule_type,
                    "passed": False,
                    "severity": rule.get("severity", RuleSeverity.ERROR.value),
                    "message": f"Error checking rule: {str(e)}",
                    "location": None,
                    "details": {"error": str(e)},
                })

        return results

    def _check_page_limit(
        self,
        rule: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check if document is within page limit."""
        params = rule.get("params", {})
        max_pages = params.get("max_pages")
        page_count = context.get("page_count")

        if page_count is None:
            return self._create_result(
                rule,
                passed=False,
                message="Page count not provided - cannot verify page limit",
                severity=RuleSeverity.WARNING.value,
                details={"max_pages": max_pages, "actual_pages": None},
            )

        if max_pages is None:
            return self._create_result(
                rule,
                passed=True,
                message="No page limit defined",
                details={},
            )

        passed = page_count <= max_pages
        message = (
            f"Page count ({page_count}) is within limit ({max_pages})"
            if passed
            else f"Page count ({page_count}) exceeds limit of {max_pages} pages"
        )

        return self._create_result(
            rule,
            passed=passed,
            message=message,
            details={"max_pages": max_pages, "actual_pages": page_count},
        )

    def _check_word_count(
        self,
        rule: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check if document is within word count limit."""
        params = rule.get("params", {})
        max_words = params.get("max_words")
        min_words = params.get("min_words", 0)
        word_count = context.get("word_count")

        if word_count is None:
            return self._create_result(
                rule,
                passed=False,
                message="Word count not provided - cannot verify word limit",
                severity=RuleSeverity.WARNING.value,
                details={"max_words": max_words, "min_words": min_words, "actual_words": None},
            )

        passed = True
        messages = []

        if max_words is not None and word_count > max_words:
            passed = False
            messages.append(f"Word count ({word_count:,}) exceeds limit of {max_words:,} words")

        if min_words and word_count < min_words:
            passed = False
            messages.append(f"Word count ({word_count:,}) is below minimum of {min_words:,} words")

        if passed:
            message = f"Word count ({word_count:,}) is within limits"
        else:
            message = "; ".join(messages)

        return self._create_result(
            rule,
            passed=passed,
            message=message,
            details={
                "max_words": max_words,
                "min_words": min_words,
                "actual_words": word_count,
            },
        )

    def _check_required_section(
        self,
        rule: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check if required section is present in document."""
        params = rule.get("params", {})
        required_section = params.get("section_name", "")
        section_patterns = params.get("patterns", [required_section])
        sections_found = context.get("sections_found", [])
        content = context.get("content", "")

        # Normalize sections found for comparison
        normalized_sections = [s.lower().strip() for s in sections_found]

        # Check if any pattern matches
        found = False
        matched_section = None

        for pattern in section_patterns:
            pattern_lower = pattern.lower().strip()

            # Check in sections list
            for section in normalized_sections:
                if pattern_lower in section or section in pattern_lower:
                    found = True
                    matched_section = section
                    break

            # If not found in sections list, try to find in content
            if not found and content:
                # Look for section header pattern
                header_pattern = rf"(?i)(?:^|\n)\s*(?:\d+\.?\s*)?{re.escape(pattern)}\s*(?:\n|:)"
                if re.search(header_pattern, content):
                    found = True
                    matched_section = pattern

        if found:
            message = f"Required section '{required_section}' found"
            if matched_section and matched_section.lower() != required_section.lower():
                message += f" (as '{matched_section}')"
        else:
            message = f"Required section '{required_section}' not found"

        return self._create_result(
            rule,
            passed=found,
            message=message,
            details={
                "required_section": required_section,
                "sections_found": sections_found,
                "matched_section": matched_section,
            },
        )

    def _check_budget_arithmetic(
        self,
        rule: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate budget arithmetic (totals match line items)."""
        params = rule.get("params", {})
        budget_data = context.get("budget_data", {})

        if not budget_data:
            return self._create_result(
                rule,
                passed=False,
                message="Budget data not provided - cannot verify arithmetic",
                severity=RuleSeverity.WARNING.value,
                details={},
            )

        errors = []
        warnings = []

        # Check total calculation
        if "line_items" in budget_data and "total" in budget_data:
            line_items = budget_data["line_items"]
            stated_total = budget_data["total"]

            if isinstance(line_items, list):
                calculated_total = sum(
                    item.get("amount", 0) for item in line_items
                    if isinstance(item, dict)
                )
            elif isinstance(line_items, dict):
                calculated_total = sum(
                    v for v in line_items.values()
                    if isinstance(v, (int, float))
                )
            else:
                calculated_total = 0

            if abs(calculated_total - stated_total) > 0.01:
                errors.append(
                    f"Budget total mismatch: stated ${stated_total:,.2f}, "
                    f"calculated ${calculated_total:,.2f}"
                )

        # Check yearly totals if multi-year budget
        if "yearly_budgets" in budget_data:
            for year, year_data in budget_data["yearly_budgets"].items():
                if "line_items" in year_data and "total" in year_data:
                    items = year_data["line_items"]
                    stated = year_data["total"]

                    if isinstance(items, list):
                        calculated = sum(
                            item.get("amount", 0) for item in items
                            if isinstance(item, dict)
                        )
                    elif isinstance(items, dict):
                        calculated = sum(
                            v for v in items.values()
                            if isinstance(v, (int, float))
                        )
                    else:
                        calculated = 0

                    if abs(calculated - stated) > 0.01:
                        errors.append(
                            f"Year {year} budget mismatch: stated ${stated:,.2f}, "
                            f"calculated ${calculated:,.2f}"
                        )

        # Check budget limit if specified
        max_budget = params.get("max_total")
        if max_budget and "total" in budget_data:
            if budget_data["total"] > max_budget:
                errors.append(
                    f"Total budget (${budget_data['total']:,.2f}) exceeds "
                    f"maximum allowed (${max_budget:,.2f})"
                )

        # Check modular budget constraints for NIH
        if params.get("modular_budget"):
            total = budget_data.get("direct_costs_total", budget_data.get("total", 0))
            module_size = params.get("module_size", 25000)
            if total % module_size != 0:
                warnings.append(
                    f"Direct costs (${total:,.2f}) should be a multiple of ${module_size:,}"
                )

        passed = len(errors) == 0

        if errors:
            message = "; ".join(errors)
        elif warnings:
            message = "Budget arithmetic correct. " + "; ".join(warnings)
        else:
            message = "Budget arithmetic verified - all totals match"

        return self._create_result(
            rule,
            passed=passed,
            message=message,
            severity=rule.get("severity", RuleSeverity.ERROR.value) if errors else RuleSeverity.WARNING.value if warnings else RuleSeverity.INFO.value,
            details={
                "errors": errors,
                "warnings": warnings,
                "budget_data_keys": list(budget_data.keys()),
            },
        )

    def _check_font_size(
        self,
        rule: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check if document uses compliant font size."""
        params = rule.get("params", {})
        min_size = params.get("min_size", 11)
        max_size = params.get("max_size")
        allowed_fonts = params.get("allowed_fonts", [])
        font_info = context.get("font_info", {})

        if not font_info:
            return self._create_result(
                rule,
                passed=False,
                message="Font information not provided - cannot verify font compliance",
                severity=RuleSeverity.WARNING.value,
                details={"min_size": min_size, "max_size": max_size},
            )

        issues = []

        # Check font size
        actual_size = font_info.get("size")
        if actual_size is not None:
            if actual_size < min_size:
                issues.append(f"Font size ({actual_size}pt) is below minimum ({min_size}pt)")
            if max_size and actual_size > max_size:
                issues.append(f"Font size ({actual_size}pt) exceeds maximum ({max_size}pt)")

        # Check font family if specified
        actual_font = font_info.get("family", "").lower()
        if allowed_fonts and actual_font:
            allowed_lower = [f.lower() for f in allowed_fonts]
            if not any(af in actual_font or actual_font in af for af in allowed_lower):
                issues.append(
                    f"Font '{font_info.get('family')}' may not be compliant. "
                    f"Recommended fonts: {', '.join(allowed_fonts)}"
                )

        passed = len(issues) == 0

        if passed:
            message = f"Font compliance verified (size: {actual_size}pt)"
        else:
            message = "; ".join(issues)

        return self._create_result(
            rule,
            passed=passed,
            message=message,
            details={
                "min_size": min_size,
                "max_size": max_size,
                "allowed_fonts": allowed_fonts,
                "actual_size": actual_size,
                "actual_font": font_info.get("family"),
            },
        )

    def _check_margin(
        self,
        rule: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check if document uses compliant margins."""
        params = rule.get("params", {})
        min_margin = params.get("min_margin", 0.5)  # Default 0.5 inches
        margin_info = context.get("margin_info", {})

        if not margin_info:
            return self._create_result(
                rule,
                passed=False,
                message="Margin information not provided - cannot verify margin compliance",
                severity=RuleSeverity.WARNING.value,
                details={"min_margin": min_margin},
            )

        issues = []

        # Check each margin
        for side in ["top", "bottom", "left", "right"]:
            actual = margin_info.get(side)
            side_min = params.get(f"min_{side}", min_margin)

            if actual is not None and actual < side_min:
                issues.append(f"{side.title()} margin ({actual}in) is below minimum ({side_min}in)")

        passed = len(issues) == 0

        if passed:
            margins_str = ", ".join(
                f"{side}: {margin_info.get(side, 'N/A')}in"
                for side in ["top", "bottom", "left", "right"]
            )
            message = f"Margin compliance verified ({margins_str})"
        else:
            message = "; ".join(issues)

        return self._create_result(
            rule,
            passed=passed,
            message=message,
            details={
                "min_margin": min_margin,
                "actual_margins": margin_info,
            },
        )

    def _check_line_spacing(
        self,
        rule: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check if document uses compliant line spacing."""
        params = rule.get("params", {})
        min_spacing = params.get("min_spacing", 1.0)
        max_spacing = params.get("max_spacing")
        line_spacing = context.get("line_spacing")

        if line_spacing is None:
            return self._create_result(
                rule,
                passed=False,
                message="Line spacing not provided - cannot verify compliance",
                severity=RuleSeverity.WARNING.value,
                details={"min_spacing": min_spacing, "max_spacing": max_spacing},
            )

        issues = []

        if line_spacing < min_spacing:
            issues.append(
                f"Line spacing ({line_spacing}) is below minimum ({min_spacing})"
            )

        if max_spacing and line_spacing > max_spacing:
            issues.append(
                f"Line spacing ({line_spacing}) exceeds maximum ({max_spacing})"
            )

        passed = len(issues) == 0

        if passed:
            message = f"Line spacing ({line_spacing}) is compliant"
        else:
            message = "; ".join(issues)

        return self._create_result(
            rule,
            passed=passed,
            message=message,
            details={
                "min_spacing": min_spacing,
                "max_spacing": max_spacing,
                "actual_spacing": line_spacing,
            },
        )

    def _check_file_format(
        self,
        rule: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check if file format is acceptable."""
        params = rule.get("params", {})
        allowed_formats = params.get("allowed_formats", ["pdf"])
        # This would typically be extracted from the uploaded file
        # For now, return a placeholder result

        return self._create_result(
            rule,
            passed=True,
            message="File format check not implemented in this scan context",
            severity=RuleSeverity.INFO.value,
            details={"allowed_formats": allowed_formats},
        )

    def _check_citation_format(
        self,
        rule: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check citation format compliance (basic check)."""
        params = rule.get("params", {})
        required_format = params.get("format", "any")
        content = context.get("content", "")

        if not content:
            return self._create_result(
                rule,
                passed=False,
                message="Document content not provided - cannot verify citation format",
                severity=RuleSeverity.WARNING.value,
                details={"required_format": required_format},
            )

        # Basic citation pattern detection
        patterns = {
            "numeric": r"\[\d+\]",  # [1], [2], etc.
            "author_year": r"\([A-Z][a-z]+(?:\s+et\s+al\.?)?,?\s*\d{4}\)",  # (Smith, 2020)
            "superscript": r"\d+(?:,\d+)*",  # Would need actual superscript detection
        }

        citations_found = []
        for style, pattern in patterns.items():
            if re.search(pattern, content):
                citations_found.append(style)

        if required_format == "any":
            passed = len(citations_found) > 0
            message = (
                f"Citations detected (styles: {', '.join(citations_found)})"
                if passed
                else "No citations detected in document"
            )
        else:
            passed = required_format in citations_found
            message = (
                f"Required citation format '{required_format}' detected"
                if passed
                else f"Required citation format '{required_format}' not detected. Found: {citations_found or 'none'}"
            )

        return self._create_result(
            rule,
            passed=passed,
            message=message,
            details={
                "required_format": required_format,
                "citations_found": citations_found,
            },
        )

    def _check_custom_rule(
        self,
        rule: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle custom rule types (placeholder for extensibility)."""
        params = rule.get("params", {})
        check_type = params.get("check_type", "unknown")

        return self._create_result(
            rule,
            passed=True,
            message=f"Custom rule '{check_type}' not implemented",
            severity=RuleSeverity.INFO.value,
            details={"check_type": check_type, "params": params},
        )

    def _create_result(
        self,
        rule: Dict[str, Any],
        passed: bool,
        message: str,
        severity: Optional[str] = None,
        location: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a standardized result dictionary."""
        return {
            "rule_id": rule.get("id", str(uuid4())),
            "rule_name": rule.get("name", "Unknown Rule"),
            "rule_type": rule.get("type", "unknown"),
            "passed": passed,
            "severity": severity or rule.get("severity", RuleSeverity.ERROR.value),
            "message": rule.get("message", message) if not passed else message,
            "location": location,
            "details": details or {},
        }

    def validate_document_content(
        self,
        content: Optional[str],
        document_type: DocumentType,
    ) -> None:
        """
        Validate document content before scanning.

        Performs basic validation to ensure the content is suitable for scanning.
        Raises ValueError if validation fails.

        Args:
            content: Text content to validate.
            document_type: Type of document being scanned.

        Raises:
            ValueError: If content is invalid or empty when required.
        """
        # Check for empty content on document types that require it
        required_content_types = [
            DocumentType.SPECIFIC_AIMS,
            DocumentType.RESEARCH_STRATEGY,
            DocumentType.ABSTRACT,
            DocumentType.PROJECT_NARRATIVE,
        ]

        if document_type in required_content_types and not content:
            logger.warning(
                f"Empty content for document type that typically requires content: {document_type.value}"
            )
            # Don't raise error, just log warning - content might be provided via metadata

        if content:
            # Check for minimum content length
            if len(content.strip()) < 10:
                raise ValueError(
                    "Document content is too short (less than 10 characters)"
                )

            # Check for excessively large content (potential DoS)
            max_content_size = 10 * 1024 * 1024  # 10 MB
            if len(content) > max_content_size:
                raise ValueError(
                    f"Document content exceeds maximum size ({max_content_size // (1024 * 1024)} MB)"
                )

            # Check for binary content that might have been incorrectly uploaded
            # Binary files often have null bytes
            if "\x00" in content:
                raise ValueError(
                    "Document content appears to be binary. Please extract text first."
                )

    @staticmethod
    def calculate_content_hash(content: str) -> str:
        """Calculate SHA-256 hash of content for duplicate detection."""
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def extract_sections_from_content(content: str) -> List[str]:
        """
        Extract section headings from document content.

        This is a basic implementation that looks for common
        heading patterns. A more robust implementation would
        use document parsing libraries.
        """
        sections = []

        # Common heading patterns
        patterns = [
            r"^(?:\d+\.?\s+)?([A-Z][A-Z\s]+)$",  # ALL CAPS headings
            r"^(?:\d+\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*):?\s*$",  # Title Case headings
            r"^\*\*(.+?)\*\*$",  # **Bold** markdown headings
            r"^#+\s+(.+)$",  # Markdown # headings
        ]

        for line in content.split("\n"):
            line = line.strip()
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    sections.append(match.group(1).strip())
                    break

        return sections
