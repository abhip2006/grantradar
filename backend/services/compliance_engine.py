"""
Compliance Engine Service

Service for managing compliance requirements, tasks, and templates.
Helps researchers stay compliant with funder requirements after grants are awarded.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.notification_service import InAppNotificationService

logger = structlog.get_logger(__name__)


class ComplianceEngineService:
    """
    Service for managing the compliance engine.

    Provides functionality for:
    - Managing funder requirements
    - Auto-generating compliance tasks when grants are awarded
    - Tracking compliance task status
    - Sending compliance deadline reminders
    - Generating compliance checklists
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the compliance engine service.

        Args:
            db: Async database session.
        """
        self.db = db
        self.notification_service = InAppNotificationService(db)

    # =========================================================================
    # Funder Requirements
    # =========================================================================

    async def get_all_requirements(
        self,
        funder_name: Optional[str] = None,
        requirement_type: Optional[str] = None,
        is_active: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[dict], int]:
        """
        Get all funder requirements with optional filtering.

        Args:
            funder_name: Filter by funder name.
            requirement_type: Filter by requirement type.
            is_active: Filter by active status.
            limit: Maximum results to return.
            offset: Number of results to skip.

        Returns:
            Tuple of (requirements list, total count).
        """
        from sqlalchemy import text

        conditions = []
        params = {"limit": limit, "offset": offset}

        if is_active is not None:
            conditions.append("is_active = :is_active")
            params["is_active"] = is_active

        if funder_name:
            conditions.append("LOWER(funder_name) LIKE LOWER(:funder_name)")
            params["funder_name"] = f"%{funder_name}%"

        if requirement_type:
            conditions.append("requirement_type = :requirement_type")
            params["requirement_type"] = requirement_type

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        count_query = text(f"SELECT COUNT(*) FROM funder_requirements WHERE {where_clause}")
        count_result = await self.db.execute(count_query, params)
        total = count_result.scalar() or 0

        # Get requirements
        query = text(f"""
            SELECT * FROM funder_requirements
            WHERE {where_clause}
            ORDER BY funder_name, requirement_type, created_at
            LIMIT :limit OFFSET :offset
        """)
        result = await self.db.execute(query, params)
        requirements = [dict(row._mapping) for row in result.fetchall()]

        return requirements, total

    async def get_requirements_for_funder(
        self,
        funder_name: str,
        mechanism: Optional[str] = None,
    ) -> List[dict]:
        """
        Get all requirements for a specific funder.

        Args:
            funder_name: Funder name to search for.
            mechanism: Optional specific mechanism.

        Returns:
            List of requirements.
        """
        from sqlalchemy import text

        params = {"funder_name": f"%{funder_name}%"}

        if mechanism:
            query = text("""
                SELECT * FROM funder_requirements
                WHERE LOWER(funder_name) LIKE LOWER(:funder_name)
                AND is_active = true
                AND (mechanism IS NULL OR mechanism = :mechanism)
                ORDER BY requirement_type, frequency
            """)
            params["mechanism"] = mechanism
        else:
            query = text("""
                SELECT * FROM funder_requirements
                WHERE LOWER(funder_name) LIKE LOWER(:funder_name)
                AND is_active = true
                ORDER BY requirement_type, frequency
            """)

        result = await self.db.execute(query, params)
        return [dict(row._mapping) for row in result.fetchall()]

    async def create_requirement(self, data: dict) -> dict:
        """
        Create a new funder requirement.

        Args:
            data: Requirement data.

        Returns:
            Created requirement.
        """
        from sqlalchemy import text

        requirement_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        await self.db.execute(
            text("""
                INSERT INTO funder_requirements (
                    id, funder_name, requirement_type, requirement_text,
                    frequency, deadline_offset_days, mechanism, notes,
                    is_active, created_at, updated_at
                ) VALUES (
                    :id, :funder_name, :requirement_type, :requirement_text,
                    :frequency, :deadline_offset_days, :mechanism, :notes,
                    :is_active, :created_at, :updated_at
                )
            """),
            {
                "id": requirement_id,
                "funder_name": data["funder_name"],
                "requirement_type": data["requirement_type"],
                "requirement_text": data["requirement_text"],
                "frequency": data["frequency"],
                "deadline_offset_days": data.get("deadline_offset_days"),
                "mechanism": data.get("mechanism"),
                "notes": data.get("notes"),
                "is_active": data.get("is_active", True),
                "created_at": now,
                "updated_at": now,
            },
        )
        await self.db.commit()

        # Fetch and return the created requirement
        result = await self.db.execute(text("SELECT * FROM funder_requirements WHERE id = :id"), {"id": requirement_id})
        return dict(result.fetchone()._mapping)

    # =========================================================================
    # Compliance Tasks
    # =========================================================================

    async def get_user_tasks(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[dict], int]:
        """
        Get compliance tasks for a user.

        Args:
            user_id: User ID.
            status: Optional status filter.
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            Tuple of (tasks list, total count).
        """
        from sqlalchemy import text

        conditions = ["user_id = :user_id"]
        params = {"user_id": user_id, "limit": limit, "offset": offset}

        if status:
            conditions.append("status = :status")
            params["status"] = status

        where_clause = " AND ".join(conditions)

        # Get total count
        count_query = text(f"SELECT COUNT(*) FROM compliance_tasks WHERE {where_clause}")
        count_result = await self.db.execute(count_query, params)
        total = count_result.scalar() or 0

        # Get tasks with computed fields
        query = text(f"""
            SELECT
                ct.*,
                CASE
                    WHEN ct.status != 'completed' AND ct.due_date < NOW() THEN true
                    ELSE false
                END as is_overdue,
                EXTRACT(DAY FROM ct.due_date - NOW())::integer as days_until_due
            FROM compliance_tasks ct
            WHERE {where_clause}
            ORDER BY ct.due_date ASC
            LIMIT :limit OFFSET :offset
        """)
        result = await self.db.execute(query, params)
        tasks = [dict(row._mapping) for row in result.fetchall()]

        return tasks, total

    async def get_upcoming_tasks(
        self,
        user_id: UUID,
        days_ahead: int = 30,
        limit: int = 20,
    ) -> List[dict]:
        """
        Get upcoming compliance deadlines for a user.

        Args:
            user_id: User ID.
            days_ahead: Number of days to look ahead.
            limit: Maximum results.

        Returns:
            List of upcoming tasks with grant info.
        """
        from sqlalchemy import text

        cutoff_date = datetime.now(timezone.utc) + timedelta(days=days_ahead)

        query = text("""
            SELECT
                ct.id as task_id,
                ct.title,
                ct.due_date,
                ct.status,
                EXTRACT(DAY FROM ct.due_date - NOW())::integer as days_until_due,
                g.title as grant_title,
                g.agency as funder_name,
                fr.requirement_type
            FROM compliance_tasks ct
            LEFT JOIN grants g ON ct.grant_id = g.id
            LEFT JOIN funder_requirements fr ON ct.requirement_id = fr.id
            WHERE ct.user_id = :user_id
            AND ct.status NOT IN ('completed')
            AND ct.due_date <= :cutoff_date
            ORDER BY ct.due_date ASC
            LIMIT :limit
        """)

        result = await self.db.execute(
            query,
            {
                "user_id": user_id,
                "cutoff_date": cutoff_date,
                "limit": limit,
            },
        )

        return [dict(row._mapping) for row in result.fetchall()]

    async def create_task(self, user_id: UUID, data: dict) -> dict:
        """
        Create a compliance task.

        Args:
            user_id: User ID.
            data: Task data.

        Returns:
            Created task.
        """
        from sqlalchemy import text

        task_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        await self.db.execute(
            text("""
                INSERT INTO compliance_tasks (
                    id, user_id, match_id, grant_id, application_id,
                    requirement_id, title, description, due_date,
                    status, notes, award_date, created_at, updated_at
                ) VALUES (
                    :id, :user_id, :match_id, :grant_id, :application_id,
                    :requirement_id, :title, :description, :due_date,
                    :status, :notes, :award_date, :created_at, :updated_at
                )
            """),
            {
                "id": task_id,
                "user_id": user_id,
                "match_id": data.get("match_id"),
                "grant_id": data.get("grant_id"),
                "application_id": data.get("application_id"),
                "requirement_id": data.get("requirement_id"),
                "title": data["title"],
                "description": data.get("description"),
                "due_date": data["due_date"],
                "status": "pending",
                "notes": data.get("notes"),
                "award_date": data.get("award_date"),
                "created_at": now,
                "updated_at": now,
            },
        )
        await self.db.commit()

        # Fetch and return created task
        result = await self.db.execute(
            text("""
                SELECT
                    *,
                    CASE WHEN status != 'completed' AND due_date < NOW() THEN true ELSE false END as is_overdue,
                    EXTRACT(DAY FROM due_date - NOW())::integer as days_until_due
                FROM compliance_tasks WHERE id = :id
            """),
            {"id": task_id},
        )
        return dict(result.fetchone()._mapping)

    async def complete_task(
        self,
        task_id: UUID,
        user_id: UUID,
        notes: Optional[str] = None,
    ) -> dict:
        """
        Mark a compliance task as completed.

        Args:
            task_id: Task ID.
            user_id: User completing the task.
            notes: Optional completion notes.

        Returns:
            Updated task.
        """
        from sqlalchemy import text

        now = datetime.now(timezone.utc)

        await self.db.execute(
            text("""
                UPDATE compliance_tasks
                SET status = 'completed',
                    completed_at = :completed_at,
                    completed_by = :completed_by,
                    notes = COALESCE(:notes, notes),
                    updated_at = :updated_at
                WHERE id = :id AND user_id = :user_id
            """),
            {
                "id": task_id,
                "user_id": user_id,
                "completed_at": now,
                "completed_by": user_id,
                "notes": notes,
                "updated_at": now,
            },
        )
        await self.db.commit()

        # Fetch and return updated task
        result = await self.db.execute(
            text("""
                SELECT
                    *,
                    false as is_overdue,
                    EXTRACT(DAY FROM due_date - NOW())::integer as days_until_due
                FROM compliance_tasks WHERE id = :id
            """),
            {"id": task_id},
        )
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return {}

    async def update_task_status(
        self,
        task_id: UUID,
        user_id: UUID,
        status: str,
    ) -> dict:
        """
        Update a compliance task status.

        Args:
            task_id: Task ID.
            user_id: User ID (for ownership check).
            status: New status.

        Returns:
            Updated task.
        """
        from sqlalchemy import text

        now = datetime.now(timezone.utc)

        update_params = {
            "id": task_id,
            "user_id": user_id,
            "status": status,
            "updated_at": now,
        }

        if status == "completed":
            await self.db.execute(
                text("""
                    UPDATE compliance_tasks
                    SET status = :status,
                        completed_at = :updated_at,
                        completed_by = :user_id,
                        updated_at = :updated_at
                    WHERE id = :id AND user_id = :user_id
                """),
                update_params,
            )
        else:
            await self.db.execute(
                text("""
                    UPDATE compliance_tasks
                    SET status = :status, updated_at = :updated_at
                    WHERE id = :id AND user_id = :user_id
                """),
                update_params,
            )
        await self.db.commit()

        # Fetch and return updated task
        result = await self.db.execute(
            text("""
                SELECT
                    *,
                    CASE WHEN status != 'completed' AND due_date < NOW() THEN true ELSE false END as is_overdue,
                    EXTRACT(DAY FROM due_date - NOW())::integer as days_until_due
                FROM compliance_tasks WHERE id = :id
            """),
            {"id": task_id},
        )
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return {}

    # =========================================================================
    # Auto-generate Tasks
    # =========================================================================

    async def generate_compliance_tasks(
        self,
        user_id: UUID,
        application_id: UUID,
        award_date: datetime,
        funder_name: Optional[str] = None,
        mechanism: Optional[str] = None,
    ) -> List[dict]:
        """
        Auto-generate compliance tasks when a grant is awarded.

        Args:
            user_id: User ID.
            application_id: Application ID.
            award_date: Award start date.
            funder_name: Funder name (auto-detected if not provided).
            mechanism: Grant mechanism.

        Returns:
            List of created tasks.
        """
        from sqlalchemy import text

        # If funder_name not provided, try to get from application/grant
        if not funder_name:
            result = await self.db.execute(
                text("""
                    SELECT g.agency, ga.grant_id
                    FROM grant_applications ga
                    JOIN grants g ON ga.grant_id = g.id
                    WHERE ga.id = :application_id
                """),
                {"application_id": application_id},
            )
            row = result.fetchone()
            if row:
                funder_name = row[0]
                grant_id = row[1]
            else:
                logger.warning(f"Could not find grant info for application {application_id}")
                return []
        else:
            # Get grant_id from application
            result = await self.db.execute(
                text("SELECT grant_id FROM grant_applications WHERE id = :id"), {"id": application_id}
            )
            row = result.fetchone()
            grant_id = row[0] if row else None

        # Get requirements for this funder
        requirements = await self.get_requirements_for_funder(funder_name, mechanism)

        if not requirements:
            logger.info(f"No requirements found for funder: {funder_name}")
            return []

        created_tasks = []
        now = datetime.now(timezone.utc)

        for req in requirements:
            # Calculate due date based on frequency and offset
            due_date = self._calculate_due_date(award_date, req["frequency"], req.get("deadline_offset_days", 0))

            task_id = uuid.uuid4()

            await self.db.execute(
                text("""
                    INSERT INTO compliance_tasks (
                        id, user_id, grant_id, application_id, requirement_id,
                        title, description, due_date, status, award_date,
                        created_at, updated_at
                    ) VALUES (
                        :id, :user_id, :grant_id, :application_id, :requirement_id,
                        :title, :description, :due_date, :status, :award_date,
                        :created_at, :updated_at
                    )
                """),
                {
                    "id": task_id,
                    "user_id": user_id,
                    "grant_id": grant_id,
                    "application_id": application_id,
                    "requirement_id": req["id"],
                    "title": f"{req['requirement_type'].title()}: {req['requirement_text'][:100]}",
                    "description": req["requirement_text"],
                    "due_date": due_date,
                    "status": "pending",
                    "award_date": award_date,
                    "created_at": now,
                    "updated_at": now,
                },
            )

            created_tasks.append(
                {
                    "id": task_id,
                    "title": f"{req['requirement_type'].title()}: {req['requirement_text'][:100]}",
                    "due_date": due_date,
                    "status": "pending",
                    "requirement_type": req["requirement_type"],
                }
            )

        await self.db.commit()

        logger.info(
            f"Generated {len(created_tasks)} compliance tasks for application {application_id}",
            user_id=str(user_id),
            funder=funder_name,
        )

        return created_tasks

    def _calculate_due_date(
        self,
        award_date: datetime,
        frequency: str,
        offset_days: int = 0,
    ) -> datetime:
        """
        Calculate due date based on award date and frequency.

        Args:
            award_date: Award start date.
            frequency: Requirement frequency.
            offset_days: Additional offset in days.

        Returns:
            Calculated due date.
        """
        offset = timedelta(days=offset_days) if offset_days else timedelta(days=0)

        if frequency == "one_time":
            # One-time requirements are due at offset from award date
            return award_date + offset
        elif frequency == "quarterly":
            # First quarterly report due 3 months after award
            return award_date + timedelta(days=90) + offset
        elif frequency == "annual":
            # Annual reports due 1 year after award
            return award_date + timedelta(days=365) + offset
        elif frequency == "final":
            # Final reports typically due 90 days after project end
            # Assuming 5-year project for now, can be adjusted
            return award_date + timedelta(days=365 * 5 + 90) + offset
        else:
            return award_date + offset

    # =========================================================================
    # Compliance Checklist
    # =========================================================================

    async def get_compliance_checklist(
        self,
        user_id: UUID,
        grant_id: UUID,
    ) -> dict:
        """
        Get compliance checklist for a specific grant.

        Args:
            user_id: User ID.
            grant_id: Grant ID.

        Returns:
            Checklist with requirements and task status.
        """
        from sqlalchemy import text

        # Get grant info
        result = await self.db.execute(text("SELECT id, title, agency FROM grants WHERE id = :id"), {"id": grant_id})
        grant_row = result.fetchone()

        if not grant_row:
            return {"error": "Grant not found"}

        funder_name = grant_row[2] or "Unknown"

        # Get application info for award date
        result = await self.db.execute(
            text("""
                SELECT id, created_at FROM grant_applications
                WHERE grant_id = :grant_id AND user_id = :user_id
            """),
            {"grant_id": grant_id, "user_id": user_id},
        )
        app_row = result.fetchone()
        award_date = app_row[1] if app_row else None

        # Get requirements for funder
        requirements = await self.get_requirements_for_funder(funder_name)

        # Get existing tasks for this grant
        result = await self.db.execute(
            text("""
                SELECT * FROM compliance_tasks
                WHERE grant_id = :grant_id AND user_id = :user_id
            """),
            {"grant_id": grant_id, "user_id": user_id},
        )
        existing_tasks = {
            row._mapping.get("requirement_id"): dict(row._mapping)
            for row in result.fetchall()
            if row._mapping.get("requirement_id")
        }

        # Build checklist items
        items = []
        completed = 0
        pending = 0
        overdue = 0

        now = datetime.now(timezone.utc)

        for req in requirements:
            task = existing_tasks.get(req["id"])
            is_completed = task and task["status"] == "completed"
            task_status = task["status"] if task else None
            due_date = task["due_date"] if task else None

            if is_completed:
                completed += 1
            elif task_status:
                if due_date and due_date < now:
                    overdue += 1
                else:
                    pending += 1
            else:
                pending += 1

            items.append(
                {
                    "requirement_id": req["id"],
                    "task_id": task["id"] if task else None,
                    "title": req["requirement_text"],
                    "description": req.get("notes"),
                    "requirement_type": req["requirement_type"],
                    "frequency": req["frequency"],
                    "due_date": due_date,
                    "status": task_status,
                    "is_completed": is_completed,
                }
            )

        return {
            "grant_id": grant_id,
            "funder_name": funder_name,
            "mechanism": None,  # Could be added if stored
            "award_date": award_date,
            "items": items,
            "total_items": len(items),
            "completed_items": completed,
            "pending_items": pending,
            "overdue_items": overdue,
        }

    # =========================================================================
    # Compliance Templates
    # =========================================================================

    async def get_templates_for_funder(
        self,
        funder_name: str,
        mechanism: Optional[str] = None,
    ) -> List[dict]:
        """
        Get compliance templates for a funder.

        Args:
            funder_name: Funder name.
            mechanism: Optional mechanism filter.

        Returns:
            List of templates.
        """
        from sqlalchemy import text

        params = {"funder_name": f"%{funder_name}%"}

        if mechanism:
            query = text("""
                SELECT * FROM compliance_templates
                WHERE LOWER(funder_name) LIKE LOWER(:funder_name)
                AND is_active = true
                AND (mechanism IS NULL OR mechanism = :mechanism)
                ORDER BY template_type, template_name
            """)
            params["mechanism"] = mechanism
        else:
            query = text("""
                SELECT * FROM compliance_templates
                WHERE LOWER(funder_name) LIKE LOWER(:funder_name)
                AND is_active = true
                ORDER BY template_type, template_name
            """)

        result = await self.db.execute(query, params)
        return [dict(row._mapping) for row in result.fetchall()]

    # =========================================================================
    # Reminder System
    # =========================================================================

    async def send_compliance_reminders(
        self,
        days_before: List[int] = [30, 14, 7, 3, 1],
    ) -> int:
        """
        Send reminders for upcoming compliance deadlines.

        This should be called by a scheduled task.

        Args:
            days_before: List of days before deadline to send reminders.

        Returns:
            Number of reminders sent.
        """
        from sqlalchemy import text

        reminders_sent = 0
        now = datetime.now(timezone.utc)

        for days in days_before:
            target_date = now + timedelta(days=days)

            # Find tasks due on target date that haven't had reminders sent
            result = await self.db.execute(
                text("""
                    SELECT ct.id, ct.user_id, ct.title, ct.due_date, g.title as grant_title
                    FROM compliance_tasks ct
                    LEFT JOIN grants g ON ct.grant_id = g.id
                    WHERE ct.status NOT IN ('completed')
                    AND DATE(ct.due_date) = DATE(:target_date)
                    AND (ct.reminder_sent_at IS NULL
                         OR DATE(ct.reminder_sent_at) < DATE(:now) - INTERVAL '1 day')
                """),
                {"target_date": target_date, "now": now},
            )

            tasks = result.fetchall()

            for task in tasks:
                # Send notification
                await self.notification_service.create_notification(
                    user_id=task[1],  # user_id
                    type="compliance_reminder",
                    title=f"Compliance Deadline in {days} Days",
                    message=f"Reminder: '{task[2]}' is due on {task[3].strftime('%B %d, %Y')}",
                    metadata={
                        "task_id": str(task[0]),
                        "days_until_due": days,
                        "grant_title": task[4],
                    },
                    action_url="/compliance/tasks",
                )

                # Mark reminder as sent
                await self.db.execute(
                    text("""
                        UPDATE compliance_tasks
                        SET reminder_sent_at = :now
                        WHERE id = :id
                    """),
                    {"id": task[0], "now": now},
                )

                reminders_sent += 1

        await self.db.commit()

        logger.info(f"Sent {reminders_sent} compliance reminders")
        return reminders_sent

    async def update_overdue_tasks(self) -> int:
        """
        Update status of overdue tasks.

        This should be called by a scheduled task.

        Returns:
            Number of tasks marked overdue.
        """
        from sqlalchemy import text

        now = datetime.now(timezone.utc)

        result = await self.db.execute(
            text("""
                UPDATE compliance_tasks
                SET status = 'overdue', updated_at = :now
                WHERE status IN ('pending', 'in_progress')
                AND due_date < :now
                RETURNING id
            """),
            {"now": now},
        )

        updated = result.fetchall()
        count = len(updated)

        await self.db.commit()

        if count > 0:
            logger.info(f"Marked {count} compliance tasks as overdue")

        return count
