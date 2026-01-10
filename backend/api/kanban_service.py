"""Kanban board service layer for business logic."""

from datetime import datetime, timezone
from typing import Optional, List, Any
from uuid import UUID

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models import (
    GrantApplication,
    ApplicationSubtask,
    ApplicationActivity,
    ApplicationAttachment,
    CustomFieldDefinition,
    CustomFieldValue,
    LabMember,
    ApplicationAssignee,
    Grant,
    User,
)
from backend.schemas.kanban import (
    ApplicationStage,
    SubtaskCreate,
    SubtaskUpdate,
    FieldDefinitionCreate,
    FieldDefinitionUpdate,
    TeamInvite,
    CardUpdate,
    ReorderRequest,
)


class KanbanService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ===== Board Operations =====

    async def get_board(
        self,
        user_id: UUID,
        stages: Optional[List[str]] = None,
        priorities: Optional[List[str]] = None,
        assignee_ids: Optional[List[UUID]] = None,
        search: Optional[str] = None,
        show_archived: bool = False,
    ) -> dict:
        """Get the full kanban board with all cards grouped by stage."""
        query = (
            select(GrantApplication)
            .options(
                selectinload(GrantApplication.grant),
                selectinload(GrantApplication.subtasks),
                selectinload(GrantApplication.attachments),
                selectinload(GrantApplication.assignees).selectinload(ApplicationAssignee.user),
                selectinload(GrantApplication.custom_field_values).selectinload(CustomFieldValue.field),
            )
            .where(GrantApplication.user_id == user_id)
        )

        if not show_archived:
            query = query.where(not GrantApplication.archived)

        if stages:
            query = query.where(GrantApplication.stage.in_(stages))

        if priorities:
            query = query.where(GrantApplication.priority.in_(priorities))

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    GrantApplication.notes.ilike(search_term),
                    GrantApplication.grant.has(Grant.title.ilike(search_term)),
                )
            )

        query = query.order_by(GrantApplication.position.asc())

        result = await self.db.execute(query)
        applications = result.unique().scalars().all()

        # Group by stage
        columns = {stage.value: [] for stage in ApplicationStage}
        for app in applications:
            card = self._build_card_response(app)
            # Handle both enum and string stage values
            stage_value = app.stage.value if hasattr(app.stage, "value") else str(app.stage)
            if stage_value in columns:
                columns[stage_value].append(card)

        # Get field definitions
        fields_result = await self.db.execute(
            select(CustomFieldDefinition)
            .where(CustomFieldDefinition.user_id == user_id)
            .order_by(CustomFieldDefinition.position)
        )
        field_definitions = fields_result.scalars().all()

        # Get team members
        team_result = await self.db.execute(
            select(LabMember).options(selectinload(LabMember.member_user)).where(LabMember.lab_owner_id == user_id)
        )
        team_members = team_result.scalars().all()

        # Calculate totals
        totals = {
            "total": len(applications),
            "by_stage": {stage: len(cards) for stage, cards in columns.items()},
            "overdue": sum(
                1
                for app in applications
                if app.target_date
                and app.target_date < datetime.now(timezone.utc)
                and (app.stage.value if hasattr(app.stage, "value") else str(app.stage)) not in ["awarded", "rejected"]
            ),
        }

        return {
            "columns": columns,
            "field_definitions": [self._build_field_response(f) for f in field_definitions],
            "team_members": [self._build_member_response(m) for m in team_members],
            "totals": totals,
        }

    async def reorder_card(self, user_id: UUID, data: ReorderRequest) -> GrantApplication:
        """Move a card to a new position/stage."""
        result = await self.db.execute(
            select(GrantApplication).where(
                GrantApplication.id == data.card_id,
                GrantApplication.user_id == user_id,
            )
        )
        app = result.scalar_one_or_none()
        if not app:
            raise ValueError("Application not found")

        old_stage = app.stage.value if hasattr(app.stage, "value") else str(app.stage)
        old_position = app.position

        # Update positions in old column
        if data.from_stage.value != data.to_stage.value:
            await self.db.execute(
                GrantApplication.__table__.update()
                .where(
                    GrantApplication.user_id == user_id,
                    GrantApplication.stage == data.from_stage.value,
                    GrantApplication.position > old_position,
                )
                .values(position=GrantApplication.position - 1)
            )

        # Update positions in new column
        await self.db.execute(
            GrantApplication.__table__.update()
            .where(
                GrantApplication.user_id == user_id,
                GrantApplication.stage == data.to_stage.value,
                GrantApplication.position >= data.new_position,
            )
            .values(position=GrantApplication.position + 1)
        )

        # Update the card
        app.stage = data.to_stage.value
        app.position = data.new_position

        # Log activity if stage changed
        if old_stage != data.to_stage.value:
            await self._log_activity(
                app.id,
                user_id,
                "stage_changed",
                {"from_stage": old_stage, "to_stage": data.to_stage.value},
            )

        await self.db.commit()
        await self.db.refresh(app)
        return app

    async def update_card(self, user_id: UUID, app_id: UUID, data: CardUpdate) -> GrantApplication:
        """Update a card's properties."""
        result = await self.db.execute(
            select(GrantApplication).where(
                GrantApplication.id == app_id,
                GrantApplication.user_id == user_id,
            )
        )
        app = result.scalar_one_or_none()
        if not app:
            raise ValueError("Application not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "stage" and value:
                value = value.value
            elif field == "priority" and value:
                value = value.value
            setattr(app, field, value)

        await self.db.commit()
        await self.db.refresh(app)
        return app

    # ===== Subtask Operations =====

    async def get_subtasks(self, user_id: UUID, app_id: UUID) -> List[ApplicationSubtask]:
        """Get all subtasks for an application."""
        # Verify ownership
        await self._verify_app_ownership(user_id, app_id)

        result = await self.db.execute(
            select(ApplicationSubtask)
            .where(ApplicationSubtask.application_id == app_id)
            .order_by(ApplicationSubtask.position)
        )
        return result.scalars().all()

    async def create_subtask(self, user_id: UUID, app_id: UUID, data: SubtaskCreate) -> ApplicationSubtask:
        """Create a new subtask."""
        await self._verify_app_ownership(user_id, app_id)

        # Get max position
        result = await self.db.execute(
            select(func.max(ApplicationSubtask.position)).where(ApplicationSubtask.application_id == app_id)
        )
        max_pos = result.scalar() or -1

        subtask = ApplicationSubtask(
            application_id=app_id,
            title=data.title,
            description=data.description,
            due_date=data.due_date,
            position=max_pos + 1,
        )
        self.db.add(subtask)

        await self._log_activity(app_id, user_id, "subtask_added", {"title": data.title})

        await self.db.commit()
        await self.db.refresh(subtask)
        return subtask

    async def update_subtask(self, user_id: UUID, subtask_id: UUID, data: SubtaskUpdate) -> ApplicationSubtask:
        """Update a subtask."""
        result = await self.db.execute(
            select(ApplicationSubtask)
            .options(selectinload(ApplicationSubtask.application))
            .where(ApplicationSubtask.id == subtask_id)
        )
        subtask = result.scalar_one_or_none()
        if not subtask:
            raise ValueError("Subtask not found")

        await self._verify_app_ownership(user_id, subtask.application_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle completion
        if "is_completed" in update_data:
            if update_data["is_completed"] and not subtask.is_completed:
                subtask.completed_at = datetime.now(timezone.utc)
                subtask.completed_by = user_id
                await self._log_activity(
                    subtask.application_id,
                    user_id,
                    "subtask_completed",
                    {"title": subtask.title},
                )
            elif not update_data["is_completed"] and subtask.is_completed:
                subtask.completed_at = None
                subtask.completed_by = None

        for field, value in update_data.items():
            setattr(subtask, field, value)

        await self.db.commit()
        await self.db.refresh(subtask)
        return subtask

    async def delete_subtask(self, user_id: UUID, subtask_id: UUID) -> None:
        """Delete a subtask."""
        result = await self.db.execute(select(ApplicationSubtask).where(ApplicationSubtask.id == subtask_id))
        subtask = result.scalar_one_or_none()
        if not subtask:
            raise ValueError("Subtask not found")

        await self._verify_app_ownership(user_id, subtask.application_id)

        await self._log_activity(
            subtask.application_id,
            user_id,
            "subtask_deleted",
            {"title": subtask.title},
        )

        await self.db.delete(subtask)
        await self.db.commit()

    async def reorder_subtasks(self, user_id: UUID, app_id: UUID, subtask_ids: List[UUID]) -> List[ApplicationSubtask]:
        """Reorder subtasks."""
        await self._verify_app_ownership(user_id, app_id)

        for position, subtask_id in enumerate(subtask_ids):
            await self.db.execute(
                ApplicationSubtask.__table__.update()
                .where(ApplicationSubtask.id == subtask_id)
                .values(position=position)
            )

        await self.db.commit()
        return await self.get_subtasks(user_id, app_id)

    # ===== Activity Operations =====

    async def get_activities(
        self, user_id: UUID, app_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[ApplicationActivity]:
        """Get activity log for an application."""
        await self._verify_app_ownership(user_id, app_id)

        result = await self.db.execute(
            select(ApplicationActivity)
            .options(selectinload(ApplicationActivity.user))
            .where(ApplicationActivity.application_id == app_id)
            .order_by(ApplicationActivity.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def add_comment(self, user_id: UUID, app_id: UUID, content: str) -> ApplicationActivity:
        """Add a comment to an application."""
        await self._verify_app_ownership(user_id, app_id)

        activity = await self._log_activity(app_id, user_id, "comment_added", {"content": content})
        await self.db.commit()
        await self.db.refresh(activity)
        return activity

    # ===== Attachment Operations =====

    async def get_attachments(self, user_id: UUID, app_id: UUID) -> List[ApplicationAttachment]:
        """Get all attachments for an application."""
        await self._verify_app_ownership(user_id, app_id)

        result = await self.db.execute(
            select(ApplicationAttachment)
            .options(selectinload(ApplicationAttachment.user))
            .where(ApplicationAttachment.application_id == app_id)
            .order_by(ApplicationAttachment.created_at.desc())
        )
        return result.scalars().all()

    async def create_attachment(
        self,
        user_id: UUID,
        app_id: UUID,
        filename: str,
        file_type: str,
        file_size: int,
        storage_path: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
    ) -> ApplicationAttachment:
        """Create an attachment record."""
        await self._verify_app_ownership(user_id, app_id)

        attachment = ApplicationAttachment(
            application_id=app_id,
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            storage_path=storage_path,
            description=description,
            category=category,
        )
        self.db.add(attachment)

        await self._log_activity(app_id, user_id, "attachment_added", {"filename": filename})

        await self.db.commit()
        await self.db.refresh(attachment)
        return attachment

    async def delete_attachment(self, user_id: UUID, attachment_id: UUID) -> str:
        """Delete an attachment and return the storage path."""
        result = await self.db.execute(select(ApplicationAttachment).where(ApplicationAttachment.id == attachment_id))
        attachment = result.scalar_one_or_none()
        if not attachment:
            raise ValueError("Attachment not found")

        await self._verify_app_ownership(user_id, attachment.application_id)

        storage_path = attachment.storage_path

        await self._log_activity(
            attachment.application_id,
            user_id,
            "attachment_deleted",
            {"filename": attachment.filename},
        )

        await self.db.delete(attachment)
        await self.db.commit()
        return storage_path

    async def get_attachment_by_id(self, user_id: UUID, attachment_id: UUID) -> ApplicationAttachment:
        """Get attachment by ID."""
        result = await self.db.execute(select(ApplicationAttachment).where(ApplicationAttachment.id == attachment_id))
        attachment = result.scalar_one_or_none()
        if not attachment:
            raise ValueError("Attachment not found")

        await self._verify_app_ownership(user_id, attachment.application_id)
        return attachment

    # ===== Custom Field Operations =====

    async def get_field_definitions(self, user_id: UUID) -> List[CustomFieldDefinition]:
        """Get all custom field definitions for a user."""
        result = await self.db.execute(
            select(CustomFieldDefinition)
            .where(CustomFieldDefinition.user_id == user_id)
            .order_by(CustomFieldDefinition.position)
        )
        return result.scalars().all()

    async def create_field_definition(self, user_id: UUID, data: FieldDefinitionCreate) -> CustomFieldDefinition:
        """Create a custom field definition."""
        # Get max position
        result = await self.db.execute(
            select(func.max(CustomFieldDefinition.position)).where(CustomFieldDefinition.user_id == user_id)
        )
        max_pos = result.scalar() or -1

        field = CustomFieldDefinition(
            user_id=user_id,
            name=data.name,
            field_type=data.field_type.value,
            options=[opt.model_dump() for opt in data.options] if data.options else None,
            is_required=data.is_required,
            show_in_card=data.show_in_card,
            position=max_pos + 1,
        )
        self.db.add(field)
        await self.db.commit()
        await self.db.refresh(field)
        return field

    async def update_field_definition(
        self, user_id: UUID, field_id: UUID, data: FieldDefinitionUpdate
    ) -> CustomFieldDefinition:
        """Update a custom field definition."""
        result = await self.db.execute(
            select(CustomFieldDefinition).where(
                CustomFieldDefinition.id == field_id,
                CustomFieldDefinition.user_id == user_id,
            )
        )
        field = result.scalar_one_or_none()
        if not field:
            raise ValueError("Field definition not found")

        update_data = data.model_dump(exclude_unset=True)
        if "options" in update_data and update_data["options"]:
            update_data["options"] = [
                opt.model_dump() if hasattr(opt, "model_dump") else opt for opt in update_data["options"]
            ]

        for key, value in update_data.items():
            setattr(field, key, value)

        await self.db.commit()
        await self.db.refresh(field)
        return field

    async def delete_field_definition(self, user_id: UUID, field_id: UUID) -> None:
        """Delete a custom field definition."""
        result = await self.db.execute(
            select(CustomFieldDefinition).where(
                CustomFieldDefinition.id == field_id,
                CustomFieldDefinition.user_id == user_id,
            )
        )
        field = result.scalar_one_or_none()
        if not field:
            raise ValueError("Field definition not found")

        await self.db.delete(field)
        await self.db.commit()

    async def update_card_fields(self, user_id: UUID, app_id: UUID, fields: dict[str, Any]) -> GrantApplication:
        """Update custom field values for an application."""
        await self._verify_app_ownership(user_id, app_id)

        for field_id_str, value in fields.items():
            field_id = UUID(field_id_str)

            # Check if value exists
            result = await self.db.execute(
                select(CustomFieldValue).where(
                    CustomFieldValue.application_id == app_id,
                    CustomFieldValue.field_id == field_id,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.value = {"value": value}
            else:
                new_value = CustomFieldValue(
                    application_id=app_id,
                    field_id=field_id,
                    value={"value": value},
                )
                self.db.add(new_value)

            await self._log_activity(app_id, user_id, "field_updated", {"field_id": str(field_id)})

        await self.db.commit()

        result = await self.db.execute(select(GrantApplication).where(GrantApplication.id == app_id))
        return result.scalar_one()

    # ===== Team Operations =====

    async def get_team_members(self, user_id: UUID) -> List[LabMember]:
        """Get all lab members for a user."""
        result = await self.db.execute(
            select(LabMember).options(selectinload(LabMember.member_user)).where(LabMember.lab_owner_id == user_id)
        )
        return result.scalars().all()

    async def invite_team_member(self, user_id: UUID, data: TeamInvite) -> LabMember:
        """Invite a new team member."""
        # Check if already invited
        result = await self.db.execute(
            select(LabMember).where(
                LabMember.lab_owner_id == user_id,
                LabMember.member_email == data.email,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError("Member already invited")

        # Check if user exists
        user_result = await self.db.execute(select(User).where(User.email == data.email))
        existing_user = user_result.scalar_one_or_none()

        member = LabMember(
            lab_owner_id=user_id,
            member_email=data.email,
            member_user_id=existing_user.id if existing_user else None,
            role=data.role.value,
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def remove_team_member(self, user_id: UUID, member_id: UUID) -> None:
        """Remove a team member."""
        result = await self.db.execute(
            select(LabMember).where(
                LabMember.id == member_id,
                LabMember.lab_owner_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise ValueError("Member not found")

        await self.db.delete(member)
        await self.db.commit()

    async def update_assignees(
        self, user_id: UUID, app_id: UUID, assignee_user_ids: List[UUID]
    ) -> List[ApplicationAssignee]:
        """Update assignees for an application."""
        await self._verify_app_ownership(user_id, app_id)

        # Remove existing assignees
        await self.db.execute(
            ApplicationAssignee.__table__.delete().where(ApplicationAssignee.application_id == app_id)
        )

        # Add new assignees
        for assignee_id in assignee_user_ids:
            assignee = ApplicationAssignee(
                application_id=app_id,
                user_id=assignee_id,
                assigned_by=user_id,
            )
            self.db.add(assignee)

        await self.db.commit()

        # Return updated assignees
        result = await self.db.execute(
            select(ApplicationAssignee)
            .options(selectinload(ApplicationAssignee.user))
            .where(ApplicationAssignee.application_id == app_id)
        )
        return result.scalars().all()

    # ===== Helper Methods =====

    async def _verify_app_ownership(self, user_id: UUID, app_id: UUID) -> None:
        """Verify that a user owns an application."""
        result = await self.db.execute(
            select(GrantApplication.id).where(
                GrantApplication.id == app_id,
                GrantApplication.user_id == user_id,
            )
        )
        if not result.scalar_one_or_none():
            raise ValueError("Application not found or access denied")

    async def _log_activity(self, app_id: UUID, user_id: UUID, action: str, details: dict) -> ApplicationActivity:
        """Create an activity log entry."""
        activity = ApplicationActivity(
            application_id=app_id,
            user_id=user_id,
            action=action,
            details=details,
        )
        self.db.add(activity)
        return activity

    def _build_card_response(self, app: GrantApplication) -> dict:
        """Build a card response from an application."""
        subtasks = app.subtasks or []
        completed = sum(1 for s in subtasks if s.is_completed)

        custom_fields = {}
        for fv in app.custom_field_values or []:
            custom_fields[str(fv.field_id)] = fv.value.get("value") if fv.value else None

        # Handle stage that could be enum or string
        stage_value = app.stage.value if hasattr(app.stage, "value") else str(app.stage)

        return {
            "id": str(app.id),
            "user_id": str(app.user_id),
            "grant_id": str(app.grant_id) if app.grant_id else None,
            "match_id": str(app.match_id) if app.match_id else None,
            "stage": stage_value,
            "position": app.position,
            "priority": app.priority or "medium",
            "color": app.color,
            "notes": app.notes,
            "target_date": app.target_date.isoformat() if app.target_date else None,
            "archived": app.archived or False,
            "subtask_progress": {"completed": completed, "total": len(subtasks)},
            "attachments_count": len(app.attachments or []),
            "assignees": [
                {
                    "application_id": str(a.application_id),
                    "user_id": str(a.user_id),
                    "user_name": a.user.name if a.user else None,
                    "user_email": a.user.email if a.user else None,
                    "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
                    "assigned_by": str(a.assigned_by) if a.assigned_by else None,
                }
                for a in (app.assignees or [])
            ],
            "custom_fields": custom_fields,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None,
            "grant_title": app.grant.title if app.grant else None,
            "grant_agency": app.grant.agency if app.grant else None,
            "grant_deadline": app.grant.deadline.isoformat() if app.grant and app.grant.deadline else None,
        }

    def _build_field_response(self, field: CustomFieldDefinition) -> dict:
        """Build a field definition response."""
        return {
            "id": str(field.id),
            "user_id": str(field.user_id),
            "name": field.name,
            "field_type": field.field_type,
            "options": field.options,
            "is_required": field.is_required,
            "show_in_card": field.show_in_card,
            "position": field.position,
            "created_at": field.created_at.isoformat() if field.created_at else None,
        }

    def _build_member_response(self, member: LabMember) -> dict:
        """Build a lab member response."""
        return {
            "id": str(member.id),
            "lab_owner_id": str(member.lab_owner_id),
            "member_email": member.member_email,
            "member_user_id": str(member.member_user_id) if member.member_user_id else None,
            "role": member.role,
            "invited_at": member.invited_at.isoformat() if member.invited_at else None,
            "accepted_at": member.accepted_at.isoformat() if member.accepted_at else None,
            "member_name": member.member_user.name if member.member_user else None,
        }
