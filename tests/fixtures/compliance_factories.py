"""
Factory classes for Compliance and Component test data.

These factories create model instances with sensible defaults and customization options
for testing the Compliance Scanner and Component Library features.
"""

import uuid
from typing import Any, Dict, List, Optional

from backend.models.compliance import ComplianceRule, ComplianceScan
from backend.models.components import ComponentUsage, DocumentComponent, DocumentVersion


class ComplianceRuleFactory:
    """Factory for creating ComplianceRule instances."""

    _counter = 0

    # Sample rules for different funders
    NIH_RULES = [
        {
            "type": "page_limit",
            "name": "Page Limit",
            "params": {"max_pages": 12},
            "severity": "error",
            "message": "Document exceeds page limit of 12 pages",
        },
        {
            "type": "font_size",
            "name": "Font Size",
            "params": {"min_size": 11},
            "severity": "warning",
            "message": "Font size should be at least 11pt",
        },
        {
            "type": "margin",
            "name": "Margins",
            "params": {"min_margin": 0.5},
            "severity": "error",
            "message": "Margins must be at least 0.5 inches",
        },
        {
            "type": "line_spacing",
            "name": "Line Spacing",
            "params": {"min_spacing": 1.0},
            "severity": "warning",
            "message": "Line spacing should be at least single-spaced",
        },
    ]

    NSF_RULES = [
        {
            "type": "page_limit",
            "name": "Page Limit",
            "params": {"max_pages": 15},
            "severity": "error",
            "message": "Document exceeds page limit of 15 pages",
        },
        {
            "type": "font_size",
            "name": "Font Size",
            "params": {"min_size": 10},
            "severity": "warning",
            "message": "Font size should be at least 10pt",
        },
        {
            "type": "required_section",
            "name": "Required Sections",
            "params": {"sections": ["Abstract", "Introduction", "Methods"]},
            "severity": "error",
            "message": "Missing required section",
        },
    ]

    @classmethod
    def create(
        cls,
        id: Optional[uuid.UUID] = None,
        funder: str = "NIH",
        mechanism: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        rules: Optional[List[Dict[str, Any]]] = None,
        is_active: bool = True,
        is_system: bool = False,
        created_by: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> ComplianceRule:
        """Create a ComplianceRule instance with defaults."""
        cls._counter += 1

        # Select appropriate default rules based on funder
        if rules is None:
            if funder.upper() == "NIH":
                rules = cls.NIH_RULES
            elif funder.upper() == "NSF":
                rules = cls.NSF_RULES
            else:
                rules = cls.NIH_RULES  # Default to NIH rules

        return ComplianceRule(
            id=id or uuid.uuid4(),
            funder=funder,
            mechanism=mechanism,
            name=name or f"{funder} Compliance Rules {cls._counter}",
            description=description or f"Compliance rules for {funder} grants",
            rules=rules,
            is_active=is_active,
            is_system=is_system,
            created_by=created_by,
            **kwargs,
        )

    @classmethod
    def create_nih_r01(cls, created_by: Optional[uuid.UUID] = None, **kwargs) -> ComplianceRule:
        """Create NIH R01 specific rule set."""
        r01_rules = [
            {
                "type": "page_limit",
                "name": "Specific Aims Page Limit",
                "params": {"max_pages": 1, "document_type": "specific_aims"},
                "severity": "error",
                "message": "Specific Aims must be 1 page maximum",
            },
            {
                "type": "page_limit",
                "name": "Research Strategy Page Limit",
                "params": {"max_pages": 12, "document_type": "research_strategy"},
                "severity": "error",
                "message": "Research Strategy must be 12 pages maximum",
            },
            {
                "type": "font_size",
                "name": "Font Size",
                "params": {"min_size": 11},
                "severity": "error",
                "message": "Font size must be at least 11pt",
            },
            {
                "type": "margin",
                "name": "Margins",
                "params": {"min_margin": 0.5},
                "severity": "error",
                "message": "Margins must be at least 0.5 inches",
            },
        ]

        return cls.create(
            funder="NIH",
            mechanism="R01",
            name="NIH R01 Compliance Rules",
            description="Standard compliance rules for NIH R01 applications",
            rules=r01_rules,
            created_by=created_by,
            **kwargs,
        )

    @classmethod
    def create_nsf_standard(cls, created_by: Optional[uuid.UUID] = None, **kwargs) -> ComplianceRule:
        """Create NSF standard rule set."""
        return cls.create(
            funder="NSF",
            mechanism=None,
            name="NSF General Compliance Rules",
            description="Standard compliance rules for NSF applications",
            rules=cls.NSF_RULES,
            created_by=created_by,
            **kwargs,
        )

    @classmethod
    def create_system_rule(cls, funder: str = "NIH", **kwargs) -> ComplianceRule:
        """Create a system-defined rule set (read-only)."""
        return cls.create(
            funder=funder,
            is_system=True,
            created_by=None,
            **kwargs,
        )


class ComplianceScanFactory:
    """Factory for creating ComplianceScan instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        kanban_card_id: uuid.UUID,
        rule_set_id: Optional[uuid.UUID] = None,
        document_type: str = "specific_aims",
        file_name: Optional[str] = None,
        file_content_hash: Optional[str] = None,
        results: Optional[List[Dict[str, Any]]] = None,
        passed_count: int = 0,
        failed_count: int = 0,
        warning_count: int = 0,
        overall_status: str = "pending",
        scanned_by: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> ComplianceScan:
        """Create a ComplianceScan instance with defaults."""
        cls._counter += 1

        return ComplianceScan(
            id=kwargs.get("id", uuid.uuid4()),
            kanban_card_id=kanban_card_id,
            rule_set_id=rule_set_id,
            document_type=document_type,
            file_name=file_name or f"test_document_{cls._counter}.pdf",
            file_content_hash=file_content_hash,
            results=results or [],
            passed_count=passed_count,
            failed_count=failed_count,
            warning_count=warning_count,
            overall_status=overall_status,
            scanned_by=scanned_by,
            **kwargs,
        )

    @classmethod
    def create_passed(
        cls,
        kanban_card_id: uuid.UUID,
        rule_set_id: Optional[uuid.UUID] = None,
        scanned_by: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> ComplianceScan:
        """Create a scan that passed all checks."""
        passed_results = [
            {
                "rule_id": str(uuid.uuid4()),
                "rule_name": "Page Limit",
                "rule_type": "page_limit",
                "passed": True,
                "severity": "error",
                "message": "Document is within page limit",
                "details": {"actual": 10, "limit": 12},
            },
            {
                "rule_id": str(uuid.uuid4()),
                "rule_name": "Font Size",
                "rule_type": "font_size",
                "passed": True,
                "severity": "warning",
                "message": "Font size meets requirements",
                "details": {"actual": 11, "min": 11},
            },
            {
                "rule_id": str(uuid.uuid4()),
                "rule_name": "Margins",
                "rule_type": "margin",
                "passed": True,
                "severity": "error",
                "message": "Margins meet requirements",
                "details": {"actual": 0.5, "min": 0.5},
            },
        ]

        return cls.create(
            kanban_card_id=kanban_card_id,
            rule_set_id=rule_set_id,
            results=passed_results,
            passed_count=3,
            failed_count=0,
            warning_count=0,
            overall_status="passed",
            scanned_by=scanned_by,
            **kwargs,
        )

    @classmethod
    def create_failed(
        cls,
        kanban_card_id: uuid.UUID,
        rule_set_id: Optional[uuid.UUID] = None,
        scanned_by: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> ComplianceScan:
        """Create a scan with failures."""
        failed_results = [
            {
                "rule_id": str(uuid.uuid4()),
                "rule_name": "Page Limit",
                "rule_type": "page_limit",
                "passed": False,
                "severity": "error",
                "message": "Document exceeds page limit",
                "details": {"actual": 15, "limit": 12},
            },
            {
                "rule_id": str(uuid.uuid4()),
                "rule_name": "Font Size",
                "rule_type": "font_size",
                "passed": False,
                "severity": "warning",
                "message": "Font size below minimum",
                "details": {"actual": 10, "min": 11},
            },
            {
                "rule_id": str(uuid.uuid4()),
                "rule_name": "Margins",
                "rule_type": "margin",
                "passed": True,
                "severity": "error",
                "message": "Margins meet requirements",
                "details": {"actual": 0.5, "min": 0.5},
            },
        ]

        return cls.create(
            kanban_card_id=kanban_card_id,
            rule_set_id=rule_set_id,
            results=failed_results,
            passed_count=1,
            failed_count=1,
            warning_count=1,
            overall_status="failed",
            scanned_by=scanned_by,
            **kwargs,
        )

    @classmethod
    def create_with_warnings(
        cls,
        kanban_card_id: uuid.UUID,
        rule_set_id: Optional[uuid.UUID] = None,
        scanned_by: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> ComplianceScan:
        """Create a scan with warnings but no errors."""
        warning_results = [
            {
                "rule_id": str(uuid.uuid4()),
                "rule_name": "Page Limit",
                "rule_type": "page_limit",
                "passed": True,
                "severity": "error",
                "message": "Document is within page limit",
                "details": {"actual": 10, "limit": 12},
            },
            {
                "rule_id": str(uuid.uuid4()),
                "rule_name": "Font Size",
                "rule_type": "font_size",
                "passed": False,
                "severity": "warning",
                "message": "Font size slightly below recommendation",
                "details": {"actual": 10.5, "min": 11},
            },
            {
                "rule_id": str(uuid.uuid4()),
                "rule_name": "Line Spacing",
                "rule_type": "line_spacing",
                "passed": False,
                "severity": "warning",
                "message": "Line spacing could be increased",
                "details": {"actual": 1.0, "recommended": 1.15},
            },
        ]

        return cls.create(
            kanban_card_id=kanban_card_id,
            rule_set_id=rule_set_id,
            results=warning_results,
            passed_count=1,
            failed_count=0,
            warning_count=2,
            overall_status="warning",
            scanned_by=scanned_by,
            **kwargs,
        )


class DocumentComponentFactory:
    """Factory for creating DocumentComponent instances."""

    _counter = 0

    CATEGORIES = ["facilities", "equipment", "biosketch", "boilerplate", "institution", "other"]

    SAMPLE_CONTENT = {
        "facilities": "The research will be conducted in our state-of-the-art laboratory facility equipped with modern instrumentation for molecular biology and biochemistry research.",
        "equipment": "Major equipment includes: Illumina NovaSeq 6000 sequencer, BD FACSAria III cell sorter, Zeiss LSM 880 confocal microscope, and Bruker 600 MHz NMR spectrometer.",
        "biosketch": "Dr. Jane Smith is an Associate Professor with 15 years of experience in computational biology. She has published over 50 peer-reviewed articles.",
        "boilerplate": "All research involving human subjects will be conducted in accordance with the Declaration of Helsinki and approved by the Institutional Review Board.",
        "institution": "Our institution is a leading research university with over $1 billion in annual research funding and a strong track record of NIH-supported research.",
        "other": "Additional information relevant to the grant application.",
    }

    @classmethod
    def create(
        cls,
        user_id: uuid.UUID,
        id: Optional[uuid.UUID] = None,
        category: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        content: Optional[str] = None,
        metadata_: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        version: int = 1,
        is_current: bool = True,
        parent_id: Optional[uuid.UUID] = None,
        is_archived: bool = False,
        **kwargs,
    ) -> DocumentComponent:
        """Create a DocumentComponent instance with defaults."""
        cls._counter += 1

        # Use default category if not provided
        if category is None:
            category = cls.CATEGORIES[cls._counter % len(cls.CATEGORIES)]

        # Use category-appropriate default content
        if content is None:
            content = cls.SAMPLE_CONTENT.get(category, cls.SAMPLE_CONTENT["other"])

        return DocumentComponent(
            id=id or uuid.uuid4(),
            user_id=user_id,
            category=category,
            name=name or f"Test {category.title()} Component {cls._counter}",
            description=description or f"A test {category} component for testing",
            content=content,
            metadata_=metadata_ or {"word_count": len(content.split()), "version": version},
            tags=tags or [category, "test"],
            version=version,
            is_current=is_current,
            parent_id=parent_id,
            is_archived=is_archived,
            **kwargs,
        )

    @classmethod
    def create_facilities(cls, user_id: uuid.UUID, **kwargs) -> DocumentComponent:
        """Create a facilities component."""
        return cls.create(
            user_id=user_id,
            category="facilities",
            name=kwargs.pop("name", "Core Research Facilities"),
            content=kwargs.pop("content", cls.SAMPLE_CONTENT["facilities"]),
            tags=["facilities", "core", "research"],
            **kwargs,
        )

    @classmethod
    def create_biosketch(cls, user_id: uuid.UUID, **kwargs) -> DocumentComponent:
        """Create a biosketch component."""
        return cls.create(
            user_id=user_id,
            category="biosketch",
            name=kwargs.pop("name", "PI Biographical Sketch"),
            content=kwargs.pop("content", cls.SAMPLE_CONTENT["biosketch"]),
            metadata_=kwargs.pop("metadata_", {"author": "Dr. Jane Smith", "position": "Associate Professor"}),
            tags=["biosketch", "PI", "credentials"],
            **kwargs,
        )

    @classmethod
    def create_boilerplate(cls, user_id: uuid.UUID, **kwargs) -> DocumentComponent:
        """Create a boilerplate component."""
        return cls.create(
            user_id=user_id,
            category="boilerplate",
            name=kwargs.pop("name", "Human Subjects Protection"),
            content=kwargs.pop("content", cls.SAMPLE_CONTENT["boilerplate"]),
            tags=["boilerplate", "IRB", "compliance"],
            **kwargs,
        )

    @classmethod
    def create_with_versions(cls, user_id: uuid.UUID, num_versions: int = 3, **kwargs) -> List[DocumentComponent]:
        """Create a component with multiple versions."""
        components = []
        parent_id = None

        for i in range(1, num_versions + 1):
            is_current = i == num_versions
            component = cls.create(
                user_id=user_id,
                version=i,
                is_current=is_current,
                parent_id=parent_id,
                content=f"Version {i} content: {cls.SAMPLE_CONTENT['other']}",
                **kwargs,
            )
            components.append(component)
            parent_id = component.id

        return components

    @classmethod
    def create_archived(cls, user_id: uuid.UUID, **kwargs) -> DocumentComponent:
        """Create an archived component."""
        return cls.create(
            user_id=user_id,
            is_archived=True,
            **kwargs,
        )


class ComponentUsageFactory:
    """Factory for creating ComponentUsage instances."""

    _counter = 0

    SECTIONS = ["specific_aims", "research_strategy", "facilities", "budget_justification", "abstract"]

    @classmethod
    def create(
        cls,
        component_id: uuid.UUID,
        kanban_card_id: uuid.UUID,
        id: Optional[uuid.UUID] = None,
        section: Optional[str] = None,
        inserted_by: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> ComponentUsage:
        """Create a ComponentUsage instance with defaults."""
        cls._counter += 1

        if section is None:
            section = cls.SECTIONS[cls._counter % len(cls.SECTIONS)]

        return ComponentUsage(
            id=id or uuid.uuid4(),
            component_id=component_id,
            kanban_card_id=kanban_card_id,
            section=section,
            inserted_by=inserted_by,
            **kwargs,
        )


class DocumentVersionFactory:
    """Factory for creating DocumentVersion instances."""

    _counter = 0

    SECTIONS = ["specific_aims", "research_strategy", "budget", "abstract", "data_management"]

    @classmethod
    def create(
        cls,
        kanban_card_id: uuid.UUID,
        id: Optional[uuid.UUID] = None,
        section: Optional[str] = None,
        version_number: Optional[int] = None,
        content: Optional[str] = None,
        snapshot_name: Optional[str] = None,
        change_summary: Optional[str] = None,
        file_path: Optional[str] = None,
        file_size: Optional[int] = None,
        file_type: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> DocumentVersion:
        """Create a DocumentVersion instance with defaults."""
        cls._counter += 1

        if section is None:
            section = cls.SECTIONS[cls._counter % len(cls.SECTIONS)]

        if version_number is None:
            version_number = cls._counter

        return DocumentVersion(
            id=id or uuid.uuid4(),
            kanban_card_id=kanban_card_id,
            section=section,
            version_number=version_number,
            content=content
            or f"Version {version_number} content for {section}. This is test content for the document version.",
            snapshot_name=snapshot_name,
            change_summary=change_summary or f"Version {version_number} changes",
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            created_by=created_by,
            **kwargs,
        )

    @classmethod
    def create_named_snapshot(
        cls,
        kanban_card_id: uuid.UUID,
        snapshot_name: str,
        created_by: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> DocumentVersion:
        """Create a named version snapshot."""
        return cls.create(
            kanban_card_id=kanban_card_id,
            snapshot_name=snapshot_name,
            change_summary=f"Created named snapshot: {snapshot_name}",
            created_by=created_by,
            **kwargs,
        )

    @classmethod
    def create_with_file(
        cls,
        kanban_card_id: uuid.UUID,
        file_name: str = "document.pdf",
        created_by: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> DocumentVersion:
        """Create a version with an attached file."""
        return cls.create(
            kanban_card_id=kanban_card_id,
            file_path=f"/uploads/versions/{uuid.uuid4()}/{file_name}",
            file_size=kwargs.pop("file_size", 102400),  # Default 100KB
            file_type=kwargs.pop("file_type", "application/pdf"),
            created_by=created_by,
            **kwargs,
        )

    @classmethod
    def create_version_chain(
        cls,
        kanban_card_id: uuid.UUID,
        section: str,
        num_versions: int = 3,
        created_by: Optional[uuid.UUID] = None,
    ) -> List[DocumentVersion]:
        """Create a chain of versions for a section."""
        versions = []
        for i in range(1, num_versions + 1):
            version = cls.create(
                kanban_card_id=kanban_card_id,
                section=section,
                version_number=i,
                content=f"Version {i} of {section}. This content was updated.",
                change_summary=f"Update {i}: Modified {section} content",
                created_by=created_by,
            )
            versions.append(version)
        return versions
