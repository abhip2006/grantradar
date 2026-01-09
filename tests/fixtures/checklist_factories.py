"""Factory classes for Checklist and Review test data."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from backend.models.checklists import ChecklistTemplate, ApplicationChecklist
from backend.models.reviews import (
    ReviewWorkflow,
    ApplicationReview,
    ReviewStageAction,
    ApplicationTeamMember,
)


class ChecklistTemplateFactory:
    """Factory for creating ChecklistTemplate instances."""

    _counter = 0

    # Default NIH R01 checklist items
    NIH_R01_ITEMS = [
        {
            "id": str(uuid.uuid4()),
            "title": "Specific Aims complete",
            "description": "1-page document outlining research objectives",
            "required": True,
            "weight": 2.0,
            "category": "scientific",
            "dependencies": [],
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Research Strategy drafted",
            "description": "12-page research plan including significance, innovation, approach",
            "required": True,
            "weight": 3.0,
            "category": "scientific",
            "dependencies": [],
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Budget prepared",
            "description": "Detailed budget with justification",
            "required": True,
            "weight": 2.0,
            "category": "budget",
            "dependencies": [],
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Biosketches updated",
            "description": "NIH biosketch for all key personnel",
            "required": True,
            "weight": 1.5,
            "category": "personnel",
            "dependencies": [],
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Facilities and Resources",
            "description": "Description of available facilities",
            "required": True,
            "weight": 1.0,
            "category": "administrative",
            "dependencies": [],
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Human Subjects protocol",
            "description": "IRB approval or exemption documentation",
            "required": False,
            "weight": 1.0,
            "category": "compliance",
            "dependencies": [],
        },
    ]

    # NSF CAREER checklist items
    NSF_CAREER_ITEMS = [
        {
            "id": str(uuid.uuid4()),
            "title": "Project Summary",
            "description": "One-page summary with intellectual merit and broader impacts",
            "required": True,
            "weight": 1.5,
            "category": "scientific",
            "dependencies": [],
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Project Description",
            "description": "15-page research and education plan",
            "required": True,
            "weight": 3.0,
            "category": "scientific",
            "dependencies": [],
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Education Plan",
            "description": "Integrated education and outreach activities",
            "required": True,
            "weight": 2.0,
            "category": "scientific",
            "dependencies": [],
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Department Letter",
            "description": "Letter from department chair supporting application",
            "required": True,
            "weight": 1.0,
            "category": "administrative",
            "dependencies": [],
        },
    ]

    @classmethod
    def create(
        cls,
        id: Optional[uuid.UUID] = None,
        funder: str = "NIH",
        mechanism: str = "R01",
        name: Optional[str] = None,
        description: Optional[str] = None,
        items: Optional[List[dict]] = None,
        is_system: bool = True,
        created_by: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> ChecklistTemplate:
        """Create a ChecklistTemplate instance with defaults."""
        cls._counter += 1

        if items is None:
            # Use default items based on funder/mechanism
            if funder.upper() == "NIH" and mechanism.upper() == "R01":
                items = cls.NIH_R01_ITEMS
            elif funder.upper() == "NSF" and mechanism.upper() == "CAREER":
                items = cls.NSF_CAREER_ITEMS
            else:
                # Generic template items
                items = [
                    {
                        "id": str(uuid.uuid4()),
                        "title": f"Task {i}",
                        "description": f"Description for task {i}",
                        "required": i < 3,
                        "weight": 1.0,
                        "category": "other",
                        "dependencies": [],
                    }
                    for i in range(1, 4)
                ]

        return ChecklistTemplate(
            id=id or uuid.uuid4(),
            funder=funder,
            mechanism=mechanism,
            name=name or f"{funder} {mechanism} Checklist Template {cls._counter}",
            description=description or f"Standard {funder} {mechanism} application checklist",
            items=items,
            is_system=is_system,
            created_by=created_by,
            **kwargs,
        )

    @classmethod
    def create_nih_r01(cls, **kwargs) -> ChecklistTemplate:
        """Create an NIH R01 checklist template."""
        return cls.create(
            funder="NIH",
            mechanism="R01",
            name="NIH R01 Application Checklist",
            description="Complete checklist for NIH R01 grant applications",
            items=cls.NIH_R01_ITEMS,
            **kwargs,
        )

    @classmethod
    def create_nsf_career(cls, **kwargs) -> ChecklistTemplate:
        """Create an NSF CAREER checklist template."""
        return cls.create(
            funder="NSF",
            mechanism="CAREER",
            name="NSF CAREER Application Checklist",
            description="Complete checklist for NSF CAREER proposals",
            items=cls.NSF_CAREER_ITEMS,
            **kwargs,
        )

    @classmethod
    def create_user_template(
        cls,
        user_id: uuid.UUID,
        name: str = "Custom Checklist",
        **kwargs,
    ) -> ChecklistTemplate:
        """Create a user-defined (non-system) checklist template."""
        return cls.create(
            is_system=False,
            created_by=user_id,
            name=name,
            **kwargs,
        )


class ApplicationChecklistFactory:
    """Factory for creating ApplicationChecklist instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        kanban_card_id: uuid.UUID,
        template_id: Optional[uuid.UUID] = None,
        name: Optional[str] = None,
        items: Optional[List[dict]] = None,
        progress_percent: float = 0.0,
        **kwargs,
    ) -> ApplicationChecklist:
        """Create an ApplicationChecklist instance with defaults."""
        cls._counter += 1

        if items is None:
            # Create default items with status fields
            items = [
                {
                    "item_id": str(uuid.uuid4()),
                    "title": f"Checklist Item {i}",
                    "description": f"Description for item {i}",
                    "required": i < 3,
                    "weight": 1.0,
                    "category": "other",
                    "dependencies": [],
                    "completed": False,
                    "completed_at": None,
                    "completed_by": None,
                    "notes": None,
                }
                for i in range(1, 4)
            ]

        return ApplicationChecklist(
            kanban_card_id=kanban_card_id,
            template_id=template_id,
            name=name or f"Application Checklist {cls._counter}",
            items=items,
            progress_percent=progress_percent,
            **kwargs,
        )

    @classmethod
    def create_from_template(
        cls,
        kanban_card_id: uuid.UUID,
        template: ChecklistTemplate,
        **kwargs,
    ) -> ApplicationChecklist:
        """Create a checklist from a template."""
        items = [
            {
                "item_id": item.get("id", str(uuid.uuid4())),
                "title": item.get("title", ""),
                "description": item.get("description"),
                "required": item.get("required", True),
                "weight": item.get("weight", 1.0),
                "category": item.get("category", "other"),
                "dependencies": item.get("dependencies", []),
                "completed": False,
                "completed_at": None,
                "completed_by": None,
                "notes": None,
            }
            for item in template.items
        ]

        return cls.create(
            kanban_card_id=kanban_card_id,
            template_id=template.id,
            name=template.name,
            items=items,
            **kwargs,
        )

    @classmethod
    def create_with_progress(
        cls,
        kanban_card_id: uuid.UUID,
        completed_count: int = 2,
        total_count: int = 5,
        user_id: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> ApplicationChecklist:
        """Create a checklist with some items marked as completed."""
        items = []
        completed_time = datetime.now(timezone.utc)

        for i in range(total_count):
            item = {
                "item_id": str(uuid.uuid4()),
                "title": f"Checklist Item {i + 1}",
                "description": f"Description for item {i + 1}",
                "required": True,
                "weight": 1.0,
                "category": "other",
                "dependencies": [],
                "completed": i < completed_count,
                "completed_at": completed_time.isoformat() if i < completed_count else None,
                "completed_by": str(user_id) if user_id and i < completed_count else None,
                "notes": f"Completed note {i}" if i < completed_count else None,
            }
            items.append(item)

        progress = (completed_count / total_count) * 100 if total_count > 0 else 0.0

        return cls.create(
            kanban_card_id=kanban_card_id,
            items=items,
            progress_percent=progress,
            **kwargs,
        )


class ReviewWorkflowFactory:
    """Factory for creating ReviewWorkflow instances."""

    _counter = 0

    # Standard workflow stages
    STANDARD_STAGES = [
        {
            "order": 0,
            "name": "Draft Review",
            "required_role": "grant_writer",
            "sla_hours": 48,
            "auto_escalate": False,
            "description": "Initial draft review by grant writer",
        },
        {
            "order": 1,
            "name": "PI Review",
            "required_role": "pi",
            "sla_hours": 72,
            "auto_escalate": True,
            "description": "Review and approval by Principal Investigator",
        },
        {
            "order": 2,
            "name": "Department Approval",
            "required_role": "admin",
            "sla_hours": 96,
            "auto_escalate": True,
            "description": "Final department approval",
        },
    ]

    # Quick workflow stages
    QUICK_STAGES = [
        {
            "order": 0,
            "name": "PI Review",
            "required_role": "pi",
            "sla_hours": 24,
            "auto_escalate": False,
            "description": "Quick PI approval",
        },
        {
            "order": 1,
            "name": "Admin Approval",
            "required_role": "admin",
            "sla_hours": 48,
            "auto_escalate": False,
            "description": "Admin final approval",
        },
    ]

    @classmethod
    def create(
        cls,
        user_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        stages: Optional[List[dict]] = None,
        is_default: bool = False,
        is_active: bool = True,
        **kwargs,
    ) -> ReviewWorkflow:
        """Create a ReviewWorkflow instance with defaults."""
        cls._counter += 1

        return ReviewWorkflow(
            user_id=user_id,
            name=name or f"Review Workflow {cls._counter}",
            description=description or f"Test review workflow {cls._counter}",
            stages=stages or cls.STANDARD_STAGES,
            is_default=is_default,
            is_active=is_active,
            **kwargs,
        )

    @classmethod
    def create_standard(cls, user_id: uuid.UUID, **kwargs) -> ReviewWorkflow:
        """Create a standard review workflow."""
        return cls.create(
            user_id=user_id,
            name="Standard Review Workflow",
            description="Standard internal review process",
            stages=cls.STANDARD_STAGES,
            **kwargs,
        )

    @classmethod
    def create_quick(cls, user_id: uuid.UUID, **kwargs) -> ReviewWorkflow:
        """Create a quick review workflow."""
        # Extract name from kwargs if provided, otherwise use default
        name = kwargs.pop("name", "Quick Review Workflow")
        description = kwargs.pop("description", "Expedited review for simple applications")
        stages = kwargs.pop("stages", cls.QUICK_STAGES)
        return cls.create(
            user_id=user_id,
            name=name,
            description=description,
            stages=stages,
            **kwargs,
        )

    @classmethod
    def create_default(cls, user_id: uuid.UUID, **kwargs) -> ReviewWorkflow:
        """Create a default workflow for a user."""
        # Extract name and stages from kwargs if provided
        name = kwargs.pop("name", None)
        stages = kwargs.pop("stages", None)
        return cls.create(
            user_id=user_id,
            name=name,
            stages=stages,
            is_default=True,
            **kwargs,
        )


class ApplicationReviewFactory:
    """Factory for creating ApplicationReview instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        kanban_card_id: uuid.UUID,
        workflow_id: Optional[uuid.UUID] = None,
        current_stage: int = 0,
        status: str = "in_review",
        started_by: Optional[uuid.UUID] = None,
        started_at: Optional[datetime] = None,
        stage_started_at: Optional[datetime] = None,
        escalation_sent: bool = False,
        **kwargs,
    ) -> ApplicationReview:
        """Create an ApplicationReview instance with defaults."""
        cls._counter += 1
        now = datetime.now(timezone.utc)

        return ApplicationReview(
            kanban_card_id=kanban_card_id,
            workflow_id=workflow_id,
            current_stage=current_stage,
            status=status,
            started_by=started_by,
            started_at=started_at or now,
            stage_started_at=stage_started_at or now,
            escalation_sent=escalation_sent,
            **kwargs,
        )

    @classmethod
    def create_pending(cls, kanban_card_id: uuid.UUID, **kwargs) -> ApplicationReview:
        """Create a review in pending status."""
        return cls.create(
            kanban_card_id=kanban_card_id,
            status="pending",
            **kwargs,
        )

    @classmethod
    def create_in_review(cls, kanban_card_id: uuid.UUID, **kwargs) -> ApplicationReview:
        """Create a review in active review status."""
        return cls.create(
            kanban_card_id=kanban_card_id,
            status="in_review",
            **kwargs,
        )

    @classmethod
    def create_approved(cls, kanban_card_id: uuid.UUID, **kwargs) -> ApplicationReview:
        """Create an approved review."""
        return cls.create(
            kanban_card_id=kanban_card_id,
            status="approved",
            completed_at=datetime.now(timezone.utc),
            **kwargs,
        )

    @classmethod
    def create_rejected(cls, kanban_card_id: uuid.UUID, **kwargs) -> ApplicationReview:
        """Create a rejected review."""
        return cls.create(
            kanban_card_id=kanban_card_id,
            status="rejected",
            completed_at=datetime.now(timezone.utc),
            **kwargs,
        )


class ReviewStageActionFactory:
    """Factory for creating ReviewStageAction instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        review_id: uuid.UUID,
        stage_order: int = 0,
        stage_name: str = "Draft Review",
        reviewer_id: Optional[uuid.UUID] = None,
        action: str = "approved",
        comments: Optional[str] = None,
        metadata_: Optional[dict] = None,
        **kwargs,
    ) -> ReviewStageAction:
        """Create a ReviewStageAction instance with defaults."""
        cls._counter += 1

        return ReviewStageAction(
            review_id=review_id,
            stage_order=stage_order,
            stage_name=stage_name,
            reviewer_id=reviewer_id,
            action=action,
            comments=comments or f"Action {cls._counter} comments",
            metadata_=metadata_,
            **kwargs,
        )

    @classmethod
    def create_approval(cls, review_id: uuid.UUID, reviewer_id: uuid.UUID, **kwargs) -> ReviewStageAction:
        """Create an approval action."""
        return cls.create(
            review_id=review_id,
            reviewer_id=reviewer_id,
            action="approved",
            comments="Approved - looks good",
            **kwargs,
        )

    @classmethod
    def create_rejection(cls, review_id: uuid.UUID, reviewer_id: uuid.UUID, **kwargs) -> ReviewStageAction:
        """Create a rejection action."""
        return cls.create(
            review_id=review_id,
            reviewer_id=reviewer_id,
            action="rejected",
            comments="Rejected - needs significant revision",
            **kwargs,
        )

    @classmethod
    def create_return(cls, review_id: uuid.UUID, reviewer_id: uuid.UUID, **kwargs) -> ReviewStageAction:
        """Create a return for revision action."""
        return cls.create(
            review_id=review_id,
            reviewer_id=reviewer_id,
            action="returned",
            comments="Returned for minor revisions",
            **kwargs,
        )


class ApplicationTeamMemberFactory:
    """Factory for creating ApplicationTeamMember instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        kanban_card_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = "reviewer",
        permissions: Optional[dict] = None,
        added_by: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> ApplicationTeamMember:
        """Create an ApplicationTeamMember instance with defaults."""
        cls._counter += 1

        if permissions is None:
            # Default permissions based on role
            permissions_map = {
                "pi": {"can_edit": True, "can_approve": True, "can_submit": True},
                "co_i": {"can_edit": True, "can_approve": True, "can_submit": False},
                "grant_writer": {"can_edit": True, "can_approve": False, "can_submit": False},
                "reviewer": {"can_edit": False, "can_approve": True, "can_submit": False},
                "admin": {"can_edit": True, "can_approve": True, "can_submit": True},
            }
            permissions = permissions_map.get(role, {"can_edit": False, "can_approve": False, "can_submit": False})

        return ApplicationTeamMember(
            kanban_card_id=kanban_card_id,
            user_id=user_id,
            role=role,
            permissions=permissions,
            added_by=added_by,
            **kwargs,
        )

    @classmethod
    def create_pi(cls, kanban_card_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> ApplicationTeamMember:
        """Create a PI team member."""
        return cls.create(
            kanban_card_id=kanban_card_id,
            user_id=user_id,
            role="pi",
            **kwargs,
        )

    @classmethod
    def create_reviewer(cls, kanban_card_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> ApplicationTeamMember:
        """Create a reviewer team member."""
        return cls.create(
            kanban_card_id=kanban_card_id,
            user_id=user_id,
            role="reviewer",
            **kwargs,
        )
