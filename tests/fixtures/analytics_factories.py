"""
Factory classes for Analytics and Team test data.

Provides factories for creating:
- WorkflowEvent instances for workflow analytics testing
- LabMember instances for team collaboration testing
- TeamActivityLog instances for activity feed testing
"""
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from backend.models import (
    LabMember,
    TeamActivityLog,
    InvitationStatus,
)
from backend.models.workflow_analytics import (
    WorkflowEvent,
    WorkflowAnalytics,
    WorkflowEventType,
    WorkflowStage,
)


class WorkflowEventFactory:
    """Factory for creating WorkflowEvent instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        kanban_card_id: uuid.UUID,
        id: Optional[uuid.UUID] = None,
        event_type: str = "stage_enter",
        stage: Optional[str] = None,
        previous_stage: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        user_id: Optional[uuid.UUID] = None,
        occurred_at: Optional[datetime] = None,
    ) -> WorkflowEvent:
        """
        Create a WorkflowEvent instance with defaults.

        Args:
            kanban_card_id: ID of the grant application
            id: Optional event ID (auto-generated if not provided)
            event_type: Type of event (default: 'stage_enter')
            stage: Current stage name
            previous_stage: Previous stage for transitions
            metadata: Additional event data
            user_id: User who triggered the event
            occurred_at: When the event occurred (default: now)

        Returns:
            WorkflowEvent instance
        """
        cls._counter += 1
        return WorkflowEvent(
            id=id or uuid.uuid4(),
            kanban_card_id=kanban_card_id,
            event_type=event_type,
            stage=stage or WorkflowStage.RESEARCHING,
            previous_stage=previous_stage,
            metadata_=metadata,
            user_id=user_id,
            occurred_at=occurred_at or datetime.now(timezone.utc),
        )

    @classmethod
    def create_stage_enter(
        cls,
        kanban_card_id: uuid.UUID,
        stage: str,
        previous_stage: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        occurred_at: Optional[datetime] = None,
    ) -> WorkflowEvent:
        """Create a stage enter event."""
        return cls.create(
            kanban_card_id=kanban_card_id,
            event_type=WorkflowEventType.STAGE_ENTER,
            stage=stage,
            previous_stage=previous_stage,
            user_id=user_id,
            occurred_at=occurred_at,
        )

    @classmethod
    def create_stage_exit(
        cls,
        kanban_card_id: uuid.UUID,
        stage: str,
        new_stage: str,
        user_id: Optional[uuid.UUID] = None,
        occurred_at: Optional[datetime] = None,
    ) -> WorkflowEvent:
        """Create a stage exit event."""
        return cls.create(
            kanban_card_id=kanban_card_id,
            event_type=WorkflowEventType.STAGE_EXIT,
            stage=stage,
            metadata={"new_stage": new_stage},
            user_id=user_id,
            occurred_at=occurred_at,
        )

    @classmethod
    def create_stage_progression(
        cls,
        kanban_card_id: uuid.UUID,
        stages: Optional[list[str]] = None,
        user_id: Optional[uuid.UUID] = None,
        days_per_stage: int = 3,
    ) -> list[WorkflowEvent]:
        """
        Create a series of stage change events simulating progression.

        Args:
            kanban_card_id: ID of the grant application
            stages: List of stages to progress through
            user_id: User who triggered the events
            days_per_stage: Days spent in each stage

        Returns:
            List of WorkflowEvent instances
        """
        if stages is None:
            stages = [
                WorkflowStage.RESEARCHING,
                WorkflowStage.WRITING,
                WorkflowStage.SUBMITTED,
            ]

        events = []
        base_time = datetime.now(timezone.utc) - timedelta(days=len(stages) * days_per_stage)
        prev_stage = None

        for i, stage in enumerate(stages):
            time_offset = timedelta(days=i * days_per_stage)

            # Create stage enter event
            enter_event = cls.create_stage_enter(
                kanban_card_id=kanban_card_id,
                stage=stage,
                previous_stage=prev_stage,
                user_id=user_id,
                occurred_at=base_time + time_offset,
            )
            events.append(enter_event)

            # Create stage exit event if not the last stage
            if i < len(stages) - 1:
                exit_time = base_time + time_offset + timedelta(days=days_per_stage - 0.5)
                exit_event = cls.create_stage_exit(
                    kanban_card_id=kanban_card_id,
                    stage=stage,
                    new_stage=stages[i + 1],
                    user_id=user_id,
                    occurred_at=exit_time,
                )
                events.append(exit_event)

            prev_stage = stage

        return events

    @classmethod
    def create_action_event(
        cls,
        kanban_card_id: uuid.UUID,
        action_type: str,
        metadata: Optional[dict[str, Any]] = None,
        user_id: Optional[uuid.UUID] = None,
        occurred_at: Optional[datetime] = None,
    ) -> WorkflowEvent:
        """Create a general action event (note added, subtask completed, etc.)."""
        return cls.create(
            kanban_card_id=kanban_card_id,
            event_type=action_type,
            metadata=metadata,
            user_id=user_id,
            occurred_at=occurred_at,
        )


class WorkflowAnalyticsFactory:
    """Factory for creating WorkflowAnalytics instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        user_id: uuid.UUID,
        id: Optional[uuid.UUID] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        period_type: str = "weekly",
        metrics: Optional[dict[str, Any]] = None,
        generated_at: Optional[datetime] = None,
    ) -> WorkflowAnalytics:
        """Create a WorkflowAnalytics instance with defaults."""
        cls._counter += 1
        now = datetime.now(timezone.utc)

        default_metrics = {
            "avg_time_per_stage": {
                "researching": 72.5,
                "writing": 120.0,
                "submitted": 0,
            },
            "bottlenecks": [],
            "completion_rate": 0.75,
            "total_applications": 10,
        }

        return WorkflowAnalytics(
            id=id or uuid.uuid4(),
            user_id=user_id,
            period_start=period_start or (now - timedelta(days=7)).date(),
            period_end=period_end or now.date(),
            period_type=period_type,
            metrics=metrics or default_metrics,
            generated_at=generated_at or now,
        )


class LabMemberFactory:
    """Factory for creating LabMember instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        lab_owner_id: uuid.UUID,
        id: Optional[uuid.UUID] = None,
        member_email: Optional[str] = None,
        member_user_id: Optional[uuid.UUID] = None,
        role: str = "member",
        invitation_status: str = "pending",
        invitation_token: Optional[str] = None,
        invitation_expires_at: Optional[datetime] = None,
        invited_at: Optional[datetime] = None,
        accepted_at: Optional[datetime] = None,
        declined_at: Optional[datetime] = None,
        permissions: Optional[dict[str, bool]] = None,
    ) -> LabMember:
        """
        Create a LabMember instance with defaults.

        Args:
            lab_owner_id: ID of the lab owner/PI
            id: Optional member ID (auto-generated if not provided)
            member_email: Email of the invited member
            member_user_id: User ID if member has registered
            role: Role in the lab (admin, member, viewer)
            invitation_status: Status of invitation
            invitation_token: Token for accepting invitation
            invitation_expires_at: When invitation expires
            invited_at: When invitation was sent
            accepted_at: When invitation was accepted
            declined_at: When invitation was declined
            permissions: Role-based permissions

        Returns:
            LabMember instance
        """
        cls._counter += 1
        now = datetime.now(timezone.utc)

        default_permissions = {
            "can_view": True,
            "can_edit": True,
            "can_create": True,
            "can_delete": False,
            "can_invite": False,
        }

        return LabMember(
            id=id or uuid.uuid4(),
            lab_owner_id=lab_owner_id,
            member_email=member_email or f"member{cls._counter}@university.edu",
            member_user_id=member_user_id,
            role=role,
            invitation_status=invitation_status,
            invitation_token=invitation_token or (secrets.token_urlsafe(32) if invitation_status == "pending" else None),
            invitation_expires_at=invitation_expires_at or (now + timedelta(days=7) if invitation_status == "pending" else None),
            invited_at=invited_at or now,
            accepted_at=accepted_at,
            declined_at=declined_at,
            permissions=permissions or default_permissions,
        )

    @classmethod
    def create_pending(
        cls,
        lab_owner_id: uuid.UUID,
        **kwargs,
    ) -> LabMember:
        """Create a pending team member invitation."""
        return cls.create(
            lab_owner_id=lab_owner_id,
            invitation_status=InvitationStatus.PENDING.value,
            **kwargs,
        )

    @classmethod
    def create_accepted(
        cls,
        lab_owner_id: uuid.UUID,
        member_user_id: uuid.UUID,
        **kwargs,
    ) -> LabMember:
        """Create an accepted team member."""
        now = datetime.now(timezone.utc)
        return cls.create(
            lab_owner_id=lab_owner_id,
            member_user_id=member_user_id,
            invitation_status=InvitationStatus.ACCEPTED.value,
            invitation_token=None,
            invitation_expires_at=None,
            accepted_at=kwargs.pop("accepted_at", now),
            **kwargs,
        )

    @classmethod
    def create_admin(
        cls,
        lab_owner_id: uuid.UUID,
        member_user_id: uuid.UUID,
        **kwargs,
    ) -> LabMember:
        """Create an admin team member."""
        admin_permissions = {
            "can_view": True,
            "can_edit": True,
            "can_create": True,
            "can_delete": True,
            "can_invite": True,
        }
        return cls.create_accepted(
            lab_owner_id=lab_owner_id,
            member_user_id=member_user_id,
            role="admin",
            permissions=admin_permissions,
            **kwargs,
        )

    @classmethod
    def create_viewer(
        cls,
        lab_owner_id: uuid.UUID,
        member_user_id: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> LabMember:
        """Create a viewer team member."""
        viewer_permissions = {
            "can_view": True,
            "can_edit": False,
            "can_create": False,
            "can_delete": False,
            "can_invite": False,
        }
        if member_user_id:
            return cls.create_accepted(
                lab_owner_id=lab_owner_id,
                member_user_id=member_user_id,
                role="viewer",
                permissions=viewer_permissions,
                **kwargs,
            )
        return cls.create(
            lab_owner_id=lab_owner_id,
            role="viewer",
            permissions=viewer_permissions,
            **kwargs,
        )

    @classmethod
    def create_expired(
        cls,
        lab_owner_id: uuid.UUID,
        **kwargs,
    ) -> LabMember:
        """Create an expired invitation."""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        return cls.create(
            lab_owner_id=lab_owner_id,
            invitation_status=InvitationStatus.EXPIRED.value,
            invitation_expires_at=past_date,
            invitation_token=None,
            **kwargs,
        )

    @classmethod
    def create_declined(
        cls,
        lab_owner_id: uuid.UUID,
        **kwargs,
    ) -> LabMember:
        """Create a declined invitation."""
        now = datetime.now(timezone.utc)
        return cls.create(
            lab_owner_id=lab_owner_id,
            invitation_status=InvitationStatus.DECLINED.value,
            invitation_token=None,
            declined_at=kwargs.pop("declined_at", now),
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
        id: Optional[uuid.UUID] = None,
        action_type: str = "invitation_sent",
        entity_type: str = "invitation",
        entity_id: Optional[uuid.UUID] = None,
        entity_name: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
    ) -> TeamActivityLog:
        """
        Create a TeamActivityLog instance with defaults.

        Args:
            lab_owner_id: ID of the lab owner
            actor_id: ID of the user performing the action
            id: Optional log ID (auto-generated if not provided)
            action_type: Type of action
            entity_type: Type of entity affected
            entity_id: ID of affected entity
            entity_name: Name of affected entity
            metadata: Additional metadata
            created_at: When the activity occurred

        Returns:
            TeamActivityLog instance
        """
        cls._counter += 1
        return TeamActivityLog(
            id=id or uuid.uuid4(),
            lab_owner_id=lab_owner_id,
            actor_id=actor_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name or f"entity_{cls._counter}@example.com",
            metadata_=metadata,
            created_at=created_at or datetime.now(timezone.utc),
        )

    @classmethod
    def create_invitation_sent(
        cls,
        lab_owner_id: uuid.UUID,
        actor_id: uuid.UUID,
        member_email: str,
        role: str = "member",
        **kwargs,
    ) -> TeamActivityLog:
        """Create an invitation sent activity."""
        return cls.create(
            lab_owner_id=lab_owner_id,
            actor_id=actor_id,
            action_type="invitation_sent",
            entity_type="invitation",
            entity_name=member_email,
            metadata={"role": role},
            **kwargs,
        )

    @classmethod
    def create_invitation_accepted(
        cls,
        lab_owner_id: uuid.UUID,
        member_id: uuid.UUID,
        member_email: str,
        actor_id: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> TeamActivityLog:
        """Create an invitation accepted activity."""
        return cls.create(
            lab_owner_id=lab_owner_id,
            actor_id=actor_id,
            action_type="invitation_accepted",
            entity_type="member",
            entity_id=member_id,
            entity_name=member_email,
            **kwargs,
        )

    @classmethod
    def create_role_changed(
        cls,
        lab_owner_id: uuid.UUID,
        actor_id: uuid.UUID,
        member_id: uuid.UUID,
        member_email: str,
        old_role: str,
        new_role: str,
        **kwargs,
    ) -> TeamActivityLog:
        """Create a role changed activity."""
        return cls.create(
            lab_owner_id=lab_owner_id,
            actor_id=actor_id,
            action_type="role_changed",
            entity_type="member",
            entity_id=member_id,
            entity_name=member_email,
            metadata={"old_role": old_role, "new_role": new_role},
            **kwargs,
        )

    @classmethod
    def create_member_removed(
        cls,
        lab_owner_id: uuid.UUID,
        actor_id: uuid.UUID,
        member_id: uuid.UUID,
        member_email: str,
        **kwargs,
    ) -> TeamActivityLog:
        """Create a member removed activity."""
        return cls.create(
            lab_owner_id=lab_owner_id,
            actor_id=actor_id,
            action_type="member_removed",
            entity_type="member",
            entity_id=member_id,
            entity_name=member_email,
            **kwargs,
        )

    @classmethod
    def create_batch(
        cls,
        lab_owner_id: uuid.UUID,
        actor_id: uuid.UUID,
        count: int = 5,
        **kwargs,
    ) -> list[TeamActivityLog]:
        """Create multiple activity log entries."""
        activities = []
        base_time = datetime.now(timezone.utc) - timedelta(hours=count)

        action_types = [
            "invitation_sent",
            "invitation_accepted",
            "role_changed",
            "permissions_updated",
            "member_removed",
        ]

        for i in range(count):
            activities.append(
                cls.create(
                    lab_owner_id=lab_owner_id,
                    actor_id=actor_id,
                    action_type=action_types[i % len(action_types)],
                    created_at=base_time + timedelta(hours=i),
                    **kwargs,
                )
            )

        return activities


__all__ = [
    "WorkflowEventFactory",
    "WorkflowAnalyticsFactory",
    "LabMemberFactory",
    "TeamActivityLogFactory",
]
