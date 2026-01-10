"""
Factory classes for Dashboard feature test data.

Provides factories for:
- Checklists (ChecklistTemplate, ApplicationChecklist)
- Reviews (ReviewWorkflow, ApplicationReview)
- Compliance (ComplianceRule, ComplianceScan)
- Components (DocumentComponent, DocumentVersion)
- Workflow Analytics (WorkflowEvent)
- Team (LabMember, TeamActivityLog)
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from backend.models import LabMember, TeamActivityLog


# =============================================================================
# Checklist Factories
# =============================================================================


class ChecklistTemplateFactory:
    """Factory for creating ChecklistTemplate instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        id: Optional[uuid.UUID] = None,
        name: Optional[str] = None,
        funder: str = "NIH",
        mechanism: str = "R01",
        items: Optional[list] = None,
        is_default: bool = False,
        **kwargs,
    ):
        """Create a ChecklistTemplate instance."""
        from backend.models.checklists import ChecklistTemplate

        cls._counter += 1
        default_items = [
            {
                "id": str(uuid.uuid4()),
                "text": "Specific Aims page complete",
                "category": "content",
                "required": True,
                "order": 0,
            },
            {
                "id": str(uuid.uuid4()),
                "text": "Research Strategy complete",
                "category": "content",
                "required": True,
                "order": 1,
            },
            {
                "id": str(uuid.uuid4()),
                "text": "Budget prepared",
                "category": "budget",
                "required": True,
                "order": 2,
            },
            {
                "id": str(uuid.uuid4()),
                "text": "Biosketches updated",
                "category": "personnel",
                "required": True,
                "order": 3,
            },
            {
                "id": str(uuid.uuid4()),
                "text": "Letters of support obtained",
                "category": "support",
                "required": False,
                "order": 4,
            },
        ]
        return ChecklistTemplate(
            id=id or uuid.uuid4(),
            name=name or f"Test Template {cls._counter}",
            funder=funder,
            mechanism=mechanism,
            items=items or default_items,
            is_default=is_default,
            **kwargs,
        )

    @classmethod
    def create_nih_r01(cls, **kwargs):
        """Create an NIH R01 template."""
        return cls.create(name="NIH R01 Checklist", funder="NIH", mechanism="R01", **kwargs)

    @classmethod
    def create_nsf_career(cls, **kwargs):
        """Create an NSF CAREER template."""
        return cls.create(name="NSF CAREER Checklist", funder="NSF", mechanism="CAREER", **kwargs)


class ApplicationChecklistFactory:
    """Factory for creating ApplicationChecklist instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        kanban_card_id: uuid.UUID,
        template_id: uuid.UUID,
        items: Optional[list] = None,
        **kwargs,
    ):
        """Create an ApplicationChecklist instance."""
        from backend.models.checklists import ApplicationChecklist

        cls._counter += 1
        default_items = [
            {
                "item_id": str(uuid.uuid4()),
                "text": "Specific Aims page complete",
                "category": "content",
                "required": True,
                "completed": False,
                "completed_at": None,
                "notes": None,
            },
            {
                "item_id": str(uuid.uuid4()),
                "text": "Budget prepared",
                "category": "budget",
                "required": True,
                "completed": True,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "notes": "Approved by finance",
            },
        ]
        return ApplicationChecklist(
            id=kwargs.get("id", uuid.uuid4()),
            kanban_card_id=kanban_card_id,
            template_id=template_id,
            items=items or default_items,
            **kwargs,
        )


# =============================================================================
# Review Workflow Factories
# =============================================================================


class ReviewWorkflowFactory:
    """Factory for creating ReviewWorkflow instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        user_id: uuid.UUID,
        name: Optional[str] = None,
        stages: Optional[list] = None,
        is_default: bool = False,
        **kwargs,
    ):
        """Create a ReviewWorkflow instance."""
        from backend.models.reviews import ReviewWorkflow

        cls._counter += 1
        default_stages = [
            {
                "name": "Initial Draft",
                "order": 0,
                "approvers_required": 1,
                "sla_hours": 48,
            },
            {
                "name": "PI Review",
                "order": 1,
                "approvers_required": 1,
                "sla_hours": 72,
            },
            {
                "name": "Final Review",
                "order": 2,
                "approvers_required": 2,
                "sla_hours": 24,
            },
        ]
        return ReviewWorkflow(
            id=kwargs.get("id", uuid.uuid4()),
            user_id=user_id,
            name=name or f"Test Workflow {cls._counter}",
            stages=stages or default_stages,
            is_default=is_default,
            **kwargs,
        )


class ApplicationReviewFactory:
    """Factory for creating ApplicationReview instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        kanban_card_id: uuid.UUID,
        workflow_id: uuid.UUID,
        current_stage: int = 0,
        status: str = "in_progress",
        **kwargs,
    ):
        """Create an ApplicationReview instance."""
        from backend.models.reviews import ApplicationReview

        cls._counter += 1
        return ApplicationReview(
            id=kwargs.get("id", uuid.uuid4()),
            kanban_card_id=kanban_card_id,
            workflow_id=workflow_id,
            current_stage=current_stage,
            status=status,
            started_at=kwargs.get("started_at", datetime.now(timezone.utc)),
            **kwargs,
        )


# =============================================================================
# Compliance Factories
# =============================================================================


class ComplianceRuleFactory:
    """Factory for creating ComplianceRule instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        name: Optional[str] = None,
        funder: str = "NIH",
        mechanism: str = "R01",
        rules: Optional[list] = None,
        is_active: bool = True,
        **kwargs,
    ):
        """Create a ComplianceRule instance."""
        from backend.models.compliance import ComplianceRule

        cls._counter += 1
        default_rules = [
            {
                "id": str(uuid.uuid4()),
                "name": "Page Limit",
                "description": "Research Strategy must not exceed 12 pages",
                "type": "format",
                "severity": "error",
                "check_type": "page_count",
                "params": {"max_pages": 12, "section": "research_strategy"},
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Font Size",
                "description": "Minimum font size is 11pt",
                "type": "format",
                "severity": "warning",
                "check_type": "font_size",
                "params": {"min_size": 11},
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Margins",
                "description": "Minimum margins of 0.5 inches",
                "type": "format",
                "severity": "error",
                "check_type": "margins",
                "params": {"min_margin": 0.5},
            },
        ]
        return ComplianceRule(
            id=kwargs.get("id", uuid.uuid4()),
            name=name or f"Test Rule Set {cls._counter}",
            funder=funder,
            mechanism=mechanism,
            rules=rules or default_rules,
            is_active=is_active,
            **kwargs,
        )


class ComplianceScanFactory:
    """Factory for creating ComplianceScan instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        kanban_card_id: uuid.UUID,
        rule_id: uuid.UUID,
        results: Optional[list] = None,
        score: int = 100,
        status: str = "passed",
        **kwargs,
    ):
        """Create a ComplianceScan instance."""
        from backend.models.compliance import ComplianceScan

        cls._counter += 1
        return ComplianceScan(
            id=kwargs.get("id", uuid.uuid4()),
            kanban_card_id=kanban_card_id,
            rule_id=rule_id,
            results=results or [],
            score=score,
            status=status,
            scanned_at=kwargs.get("scanned_at", datetime.now(timezone.utc)),
            **kwargs,
        )

    @classmethod
    def create_passed(cls, kanban_card_id: uuid.UUID, rule_id: uuid.UUID, **kwargs):
        """Create a scan that passed all checks."""
        return cls.create(
            kanban_card_id=kanban_card_id,
            rule_id=rule_id,
            results=[
                {"rule_name": "Page Limit", "status": "passed", "message": "Within limit"},
                {"rule_name": "Font Size", "status": "passed", "message": "Font size OK"},
            ],
            score=100,
            status="passed",
            **kwargs,
        )

    @classmethod
    def create_failed(cls, kanban_card_id: uuid.UUID, rule_id: uuid.UUID, **kwargs):
        """Create a scan with failures."""
        return cls.create(
            kanban_card_id=kanban_card_id,
            rule_id=rule_id,
            results=[
                {"rule_name": "Page Limit", "status": "failed", "message": "Exceeds 12 pages"},
                {"rule_name": "Font Size", "status": "warning", "message": "Some text below 11pt"},
            ],
            score=40,
            status="failed",
            **kwargs,
        )


# =============================================================================
# Component Library Factories
# =============================================================================


class DocumentComponentFactory:
    """Factory for creating DocumentComponent instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        user_id: uuid.UUID,
        name: Optional[str] = None,
        category: str = "specific_aims",
        content: Optional[str] = None,
        **kwargs,
    ):
        """Create a DocumentComponent instance."""
        from backend.models.components import DocumentComponent

        cls._counter += 1
        return DocumentComponent(
            id=kwargs.get("id", uuid.uuid4()),
            user_id=user_id,
            name=name or f"Test Component {cls._counter}",
            category=category,
            content=content
            or "This is test component content for grant applications. It includes sample text that might be used in a specific aims section.",
            metadata=kwargs.get("metadata", {"word_count": 50, "version": 1}),
            is_current=kwargs.get("is_current", True),
            version_number=kwargs.get("version_number", 1),
            **kwargs,
        )


class DocumentVersionFactory:
    """Factory for creating DocumentVersion instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        kanban_card_id: uuid.UUID,
        section: str = "specific_aims",
        content: Optional[str] = None,
        **kwargs,
    ):
        """Create a DocumentVersion instance."""
        from backend.models.components import DocumentVersion

        cls._counter += 1
        return DocumentVersion(
            id=kwargs.get("id", uuid.uuid4()),
            kanban_card_id=kanban_card_id,
            section=section,
            content=content or f"Document version {cls._counter} content.",
            version_number=kwargs.get("version_number", cls._counter),
            snapshot_name=kwargs.get("snapshot_name"),
            **kwargs,
        )


# =============================================================================
# Workflow Analytics Factories
# =============================================================================


class WorkflowEventFactory:
    """Factory for creating WorkflowEvent instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        kanban_card_id: uuid.UUID,
        event_type: str = "stage_change",
        stage: str = "researching",
        previous_stage: Optional[str] = None,
        **kwargs,
    ):
        """Create a WorkflowEvent instance."""
        from backend.models.workflow_analytics import WorkflowEvent

        cls._counter += 1
        return WorkflowEvent(
            id=kwargs.get("id", uuid.uuid4()),
            kanban_card_id=kanban_card_id,
            event_type=event_type,
            stage=stage,
            previous_stage=previous_stage,
            occurred_at=kwargs.get("occurred_at", datetime.now(timezone.utc)),
            metadata=kwargs.get("metadata", {}),
        )

    @classmethod
    def create_stage_progression(
        cls,
        kanban_card_id: uuid.UUID,
        stages: list[str] = None,
        days_between: int = 7,
    ):
        """Create a series of stage change events."""
        if stages is None:
            stages = ["researching", "writing", "submitted"]

        events = []
        prev_stage = None
        base_time = datetime.now(timezone.utc) - timedelta(days=len(stages) * days_between)

        for i, stage in enumerate(stages):
            event = cls.create(
                kanban_card_id=kanban_card_id,
                event_type="stage_change",
                stage=stage,
                previous_stage=prev_stage,
                occurred_at=base_time + timedelta(days=i * days_between),
            )
            events.append(event)
            prev_stage = stage

        return events


# =============================================================================
# Team Collaboration Factories
# =============================================================================


class LabMemberFactory:
    """Factory for creating LabMember instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        lab_owner_id: uuid.UUID,
        member_email: Optional[str] = None,
        member_user_id: Optional[uuid.UUID] = None,
        role: str = "member",
        invitation_status: str = "pending",
        **kwargs,
    ):
        """Create a LabMember instance."""
        cls._counter += 1
        default_permissions = {
            "can_view": True,
            "can_edit": role in ("admin", "member"),
            "can_create": role in ("admin", "member"),
            "can_delete": role == "admin",
            "can_invite": role == "admin",
        }
        return LabMember(
            id=kwargs.get("id", uuid.uuid4()),
            lab_owner_id=lab_owner_id,
            member_email=member_email or f"member{cls._counter}@university.edu",
            member_user_id=member_user_id,
            role=role,
            invitation_status=invitation_status,
            invitation_token=kwargs.get("invitation_token"),
            invitation_expires_at=kwargs.get("invitation_expires_at"),
            invited_at=kwargs.get("invited_at", datetime.now(timezone.utc)),
            accepted_at=kwargs.get("accepted_at"),
            declined_at=kwargs.get("declined_at"),
            permissions=kwargs.get("permissions", default_permissions),
        )

    @classmethod
    def create_pending(cls, lab_owner_id: uuid.UUID, **kwargs):
        """Create a pending invitation."""
        import secrets

        return cls.create(
            lab_owner_id=lab_owner_id,
            invitation_status="pending",
            invitation_token=secrets.token_urlsafe(32),
            invitation_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            **kwargs,
        )

    @classmethod
    def create_accepted(cls, lab_owner_id: uuid.UUID, member_user_id: uuid.UUID, **kwargs):
        """Create an accepted team member."""
        return cls.create(
            lab_owner_id=lab_owner_id,
            member_user_id=member_user_id,
            invitation_status="accepted",
            accepted_at=datetime.now(timezone.utc),
            **kwargs,
        )

    @classmethod
    def create_admin(cls, lab_owner_id: uuid.UUID, member_user_id: uuid.UUID, **kwargs):
        """Create an admin team member."""
        return cls.create_accepted(
            lab_owner_id=lab_owner_id,
            member_user_id=member_user_id,
            role="admin",
            **kwargs,
        )


class TeamActivityLogFactory:
    """Factory for creating TeamActivityLog instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        lab_owner_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        action_type: str = "member_invited",
        entity_type: str = "member",
        **kwargs,
    ):
        """Create a TeamActivityLog instance."""
        cls._counter += 1
        return TeamActivityLog(
            id=kwargs.get("id", uuid.uuid4()),
            lab_owner_id=lab_owner_id,
            actor_id=actor_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=kwargs.get("entity_id"),
            entity_name=kwargs.get("entity_name"),
            metadata=kwargs.get("metadata", {}),
            created_at=kwargs.get("created_at", datetime.now(timezone.utc)),
        )
