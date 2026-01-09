"""Institution service layer for institutional dashboard business logic."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func, and_, or_, text, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.exceptions import NotFoundError, ValidationError, ConflictError, AuthorizationError
from backend.schemas.institution import (
    InstitutionCreate,
    InstitutionUpdate,
    InstitutionMemberCreate,
    InstitutionMemberUpdate,
    InstitutionMemberRole,
    InstitutionSettings,
    InstitutionMemberPermissions,
    GrantTrackedSummary,
    PortfolioAggregation,
    FundingPipelineMetric,
    DepartmentStats,
    DeadlineSummary,
)


class InstitutionService:
    """Service class for institution operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize the institution service.

        Args:
            db: Async database session.
        """
        self.db = db

    # =========================================================================
    # Institution CRUD Operations
    # =========================================================================

    async def create_institution(
        self,
        data: InstitutionCreate,
        created_by: UUID,
    ) -> dict:
        """
        Create a new institution.

        Args:
            data: Institution creation data.
            created_by: ID of the user creating the institution.

        Returns:
            Created institution record as dict.

        Raises:
            ConflictError: If institution with same name or domain already exists.
        """
        # Check for existing institution with same domain
        if data.domain:
            existing_query = text("""
                SELECT id FROM institutions WHERE domain = :domain
            """)
            result = await self.db.execute(existing_query, {"domain": data.domain.lower()})
            if result.fetchone():
                raise ConflictError(f"Institution with domain '{data.domain}' already exists")

        # Create institution
        institution_id = uuid.uuid4()
        settings_json = data.settings.model_dump() if data.settings else None

        insert_query = text("""
            INSERT INTO institutions (id, name, type, domain, description, logo_url, website, address, settings, created_by, created_at, updated_at)
            VALUES (:id, :name, :type, :domain, :description, :logo_url, :website, :address, :settings, :created_by, NOW(), NOW())
            RETURNING id, name, type, domain, description, logo_url, website, address, settings, created_by, created_at, updated_at
        """)

        result = await self.db.execute(insert_query, {
            "id": institution_id,
            "name": data.name,
            "type": data.type.value,
            "domain": data.domain.lower() if data.domain else None,
            "description": data.description,
            "logo_url": data.logo_url,
            "website": data.website,
            "address": data.address,
            "settings": settings_json,
            "created_by": created_by,
        })
        institution = result.fetchone()

        # Add creator as admin member
        member_id = uuid.uuid4()
        admin_permissions = InstitutionMemberPermissions(
            can_view_all_portfolios=True,
            can_view_metrics=True,
            can_manage_members=True,
            can_edit_settings=True,
            can_export_data=True,
        )

        member_query = text("""
            INSERT INTO institution_members (id, institution_id, user_id, role, permissions, added_at, added_by, updated_at)
            VALUES (:id, :institution_id, :user_id, :role, :permissions, NOW(), :added_by, NOW())
        """)

        await self.db.execute(member_query, {
            "id": member_id,
            "institution_id": institution_id,
            "user_id": created_by,
            "role": InstitutionMemberRole.ADMIN.value,
            "permissions": admin_permissions.model_dump(),
            "added_by": created_by,
        })

        await self.db.commit()

        return {
            "id": institution.id,
            "name": institution.name,
            "type": institution.type,
            "domain": institution.domain,
            "description": institution.description,
            "logo_url": institution.logo_url,
            "website": institution.website,
            "address": institution.address,
            "settings": institution.settings,
            "created_by": institution.created_by,
            "created_at": institution.created_at,
            "updated_at": institution.updated_at,
            "member_count": 1,
        }

    async def get_institution(self, institution_id: UUID) -> dict:
        """
        Get institution details by ID.

        Args:
            institution_id: Institution ID.

        Returns:
            Institution record as dict.

        Raises:
            NotFoundError: If institution not found.
        """
        query = text("""
            SELECT
                i.id, i.name, i.type, i.domain, i.description, i.logo_url,
                i.website, i.address, i.settings, i.created_by, i.created_at, i.updated_at,
                COUNT(im.id) as member_count
            FROM institutions i
            LEFT JOIN institution_members im ON im.institution_id = i.id
            WHERE i.id = :id
            GROUP BY i.id
        """)

        result = await self.db.execute(query, {"id": institution_id})
        row = result.fetchone()

        if not row:
            raise NotFoundError("Institution", str(institution_id))

        return {
            "id": row.id,
            "name": row.name,
            "type": row.type,
            "domain": row.domain,
            "description": row.description,
            "logo_url": row.logo_url,
            "website": row.website,
            "address": row.address,
            "settings": row.settings,
            "created_by": row.created_by,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "member_count": row.member_count,
        }

    async def update_institution(
        self,
        institution_id: UUID,
        data: InstitutionUpdate,
        user_id: UUID,
    ) -> dict:
        """
        Update an institution.

        Args:
            institution_id: Institution ID.
            data: Update data.
            user_id: ID of the user making the update.

        Returns:
            Updated institution record.

        Raises:
            NotFoundError: If institution not found.
            AuthorizationError: If user is not an admin.
        """
        # Verify user is admin
        await self._verify_admin(institution_id, user_id)

        # Build update query dynamically
        updates = []
        params = {"id": institution_id}

        if data.name is not None:
            updates.append("name = :name")
            params["name"] = data.name
        if data.type is not None:
            updates.append("type = :type")
            params["type"] = data.type.value
        if data.domain is not None:
            updates.append("domain = :domain")
            params["domain"] = data.domain.lower() if data.domain else None
        if data.description is not None:
            updates.append("description = :description")
            params["description"] = data.description
        if data.logo_url is not None:
            updates.append("logo_url = :logo_url")
            params["logo_url"] = data.logo_url
        if data.website is not None:
            updates.append("website = :website")
            params["website"] = data.website
        if data.address is not None:
            updates.append("address = :address")
            params["address"] = data.address
        if data.settings is not None:
            updates.append("settings = :settings")
            params["settings"] = data.settings.model_dump()

        if not updates:
            return await self.get_institution(institution_id)

        updates.append("updated_at = NOW()")
        update_str = ", ".join(updates)

        query = text(f"""
            UPDATE institutions
            SET {update_str}
            WHERE id = :id
        """)

        await self.db.execute(query, params)
        await self.db.commit()

        return await self.get_institution(institution_id)

    async def delete_institution(
        self,
        institution_id: UUID,
        user_id: UUID,
    ) -> None:
        """
        Delete an institution.

        Args:
            institution_id: Institution ID.
            user_id: ID of the user deleting.

        Raises:
            NotFoundError: If institution not found.
            AuthorizationError: If user is not an admin.
        """
        await self._verify_admin(institution_id, user_id)

        # Delete institution (cascade will handle members)
        query = text("DELETE FROM institutions WHERE id = :id")
        await self.db.execute(query, {"id": institution_id})
        await self.db.commit()

    # =========================================================================
    # Member Operations
    # =========================================================================

    async def add_member(
        self,
        institution_id: UUID,
        data: InstitutionMemberCreate,
        added_by: UUID,
    ) -> dict:
        """
        Add a member to an institution.

        Args:
            institution_id: Institution ID.
            data: Member creation data.
            added_by: ID of the user adding the member.

        Returns:
            Created member record.

        Raises:
            NotFoundError: If institution or user not found.
            ConflictError: If user is already a member.
            AuthorizationError: If actor cannot manage members.
        """
        # Verify actor can manage members
        await self._verify_can_manage_members(institution_id, added_by)

        # Determine user_id
        user_id = data.user_id
        if not user_id and data.email:
            # Find user by email
            user_query = text("SELECT id, name, email FROM users WHERE email = :email")
            result = await self.db.execute(user_query, {"email": data.email.lower()})
            user = result.fetchone()
            if not user:
                raise NotFoundError("User", data.email)
            user_id = user.id

        if not user_id:
            raise ValidationError("Either user_id or email must be provided")

        # Check if already a member
        check_query = text("""
            SELECT id FROM institution_members
            WHERE institution_id = :institution_id AND user_id = :user_id
        """)
        result = await self.db.execute(check_query, {
            "institution_id": institution_id,
            "user_id": user_id,
        })
        if result.fetchone():
            raise ConflictError("User is already a member of this institution")

        # Create member
        member_id = uuid.uuid4()
        permissions_json = data.permissions.model_dump() if data.permissions else None

        insert_query = text("""
            INSERT INTO institution_members
            (id, institution_id, user_id, role, department, title, permissions, added_at, added_by, updated_at)
            VALUES (:id, :institution_id, :user_id, :role, :department, :title, :permissions, NOW(), :added_by, NOW())
            RETURNING id, institution_id, user_id, role, department, title, permissions, added_at, added_by, updated_at
        """)

        result = await self.db.execute(insert_query, {
            "id": member_id,
            "institution_id": institution_id,
            "user_id": user_id,
            "role": data.role.value,
            "department": data.department,
            "title": data.title,
            "permissions": permissions_json,
            "added_by": added_by,
        })
        member = result.fetchone()
        await self.db.commit()

        # Get user details
        user_query = text("SELECT name, email FROM users WHERE id = :id")
        user_result = await self.db.execute(user_query, {"id": user_id})
        user = user_result.fetchone()

        return {
            "id": member.id,
            "institution_id": member.institution_id,
            "user_id": member.user_id,
            "role": member.role,
            "department": member.department,
            "title": member.title,
            "permissions": member.permissions,
            "added_at": member.added_at,
            "added_by": member.added_by,
            "updated_at": member.updated_at,
            "user_name": user.name if user else None,
            "user_email": user.email if user else None,
        }

    async def list_members(
        self,
        institution_id: UUID,
        user_id: UUID,
        department: Optional[str] = None,
        role: Optional[str] = None,
    ) -> Tuple[List[dict], int, dict, dict]:
        """
        List institution members with optional filtering.

        Args:
            institution_id: Institution ID.
            user_id: ID of the user requesting.
            department: Optional department filter.
            role: Optional role filter.

        Returns:
            Tuple of (members list, total, by_department counts, by_role counts).

        Raises:
            AuthorizationError: If user is not a member.
        """
        # Verify user is a member
        await self._verify_member(institution_id, user_id)

        # Build query
        params = {"institution_id": institution_id}
        where_clauses = ["im.institution_id = :institution_id"]

        if department:
            where_clauses.append("im.department = :department")
            params["department"] = department
        if role:
            where_clauses.append("im.role = :role")
            params["role"] = role

        where_str = " AND ".join(where_clauses)

        query = text(f"""
            SELECT
                im.id, im.institution_id, im.user_id, im.role, im.department,
                im.title, im.permissions, im.added_at, im.added_by, im.updated_at,
                u.name as user_name, u.email as user_email
            FROM institution_members im
            JOIN users u ON u.id = im.user_id
            WHERE {where_str}
            ORDER BY im.added_at DESC
        """)

        result = await self.db.execute(query, params)
        rows = result.fetchall()

        members = []
        for row in rows:
            members.append({
                "id": row.id,
                "institution_id": row.institution_id,
                "user_id": row.user_id,
                "role": row.role,
                "department": row.department,
                "title": row.title,
                "permissions": row.permissions,
                "added_at": row.added_at,
                "added_by": row.added_by,
                "updated_at": row.updated_at,
                "user_name": row.user_name,
                "user_email": row.user_email,
            })

        # Get counts by department and role
        count_query = text("""
            SELECT
                department, role, COUNT(*) as count
            FROM institution_members
            WHERE institution_id = :institution_id
            GROUP BY department, role
        """)
        count_result = await self.db.execute(count_query, {"institution_id": institution_id})
        count_rows = count_result.fetchall()

        by_department = {}
        by_role = {}
        for row in count_rows:
            dept = row.department or "Unassigned"
            if dept not in by_department:
                by_department[dept] = 0
            by_department[dept] += row.count

            if row.role not in by_role:
                by_role[row.role] = 0
            by_role[row.role] += row.count

        return members, len(members), by_department, by_role

    async def update_member(
        self,
        institution_id: UUID,
        member_id: UUID,
        data: InstitutionMemberUpdate,
        actor_id: UUID,
    ) -> dict:
        """
        Update a member's role or details.

        Args:
            institution_id: Institution ID.
            member_id: Member record ID.
            data: Update data.
            actor_id: ID of the user making the update.

        Returns:
            Updated member record.

        Raises:
            NotFoundError: If member not found.
            AuthorizationError: If actor cannot manage members.
        """
        await self._verify_can_manage_members(institution_id, actor_id)

        # Build update
        updates = []
        params = {"id": member_id, "institution_id": institution_id}

        if data.role is not None:
            updates.append("role = :role")
            params["role"] = data.role.value
        if data.department is not None:
            updates.append("department = :department")
            params["department"] = data.department
        if data.title is not None:
            updates.append("title = :title")
            params["title"] = data.title
        if data.permissions is not None:
            updates.append("permissions = :permissions")
            params["permissions"] = data.permissions.model_dump()

        if not updates:
            # Return current state
            return await self._get_member_by_id(institution_id, member_id)

        updates.append("updated_at = NOW()")
        update_str = ", ".join(updates)

        query = text(f"""
            UPDATE institution_members
            SET {update_str}
            WHERE id = :id AND institution_id = :institution_id
        """)

        await self.db.execute(query, params)
        await self.db.commit()

        return await self._get_member_by_id(institution_id, member_id)

    async def remove_member(
        self,
        institution_id: UUID,
        user_id: UUID,
        actor_id: UUID,
    ) -> None:
        """
        Remove a member from an institution.

        Args:
            institution_id: Institution ID.
            user_id: User ID to remove.
            actor_id: ID of the user performing the removal.

        Raises:
            NotFoundError: If member not found.
            AuthorizationError: If actor cannot manage members.
            ValidationError: If trying to remove last admin.
        """
        await self._verify_can_manage_members(institution_id, actor_id)

        # Check if this is the last admin
        admin_count_query = text("""
            SELECT COUNT(*) FROM institution_members
            WHERE institution_id = :institution_id AND role = 'admin'
        """)
        result = await self.db.execute(admin_count_query, {"institution_id": institution_id})
        admin_count = result.scalar()

        # Check if user being removed is an admin
        member_query = text("""
            SELECT role FROM institution_members
            WHERE institution_id = :institution_id AND user_id = :user_id
        """)
        result = await self.db.execute(member_query, {
            "institution_id": institution_id,
            "user_id": user_id,
        })
        member = result.fetchone()

        if not member:
            raise NotFoundError("Member", str(user_id))

        if member.role == "admin" and admin_count <= 1:
            raise ValidationError("Cannot remove the last admin from an institution")

        # Remove member
        delete_query = text("""
            DELETE FROM institution_members
            WHERE institution_id = :institution_id AND user_id = :user_id
        """)
        await self.db.execute(delete_query, {
            "institution_id": institution_id,
            "user_id": user_id,
        })
        await self.db.commit()

    # =========================================================================
    # Portfolio Operations
    # =========================================================================

    async def get_portfolio(
        self,
        institution_id: UUID,
        user_id: UUID,
        department: Optional[str] = None,
    ) -> PortfolioAggregation:
        """
        Get aggregated portfolio view across institution members.

        Args:
            institution_id: Institution ID.
            user_id: ID of the user requesting.
            department: Optional department filter.

        Returns:
            PortfolioAggregation with aggregated data.

        Raises:
            AuthorizationError: If user is not a member.
        """
        await self._verify_member(institution_id, user_id)

        # Get member user IDs for this institution
        member_ids_query = text("""
            SELECT user_id, department FROM institution_members
            WHERE institution_id = :institution_id
        """)
        if department:
            member_ids_query = text("""
                SELECT user_id, department FROM institution_members
                WHERE institution_id = :institution_id AND department = :department
            """)

        params = {"institution_id": institution_id}
        if department:
            params["department"] = department

        result = await self.db.execute(member_ids_query, params)
        members = result.fetchall()
        user_ids = [m.user_id for m in members]
        user_departments = {m.user_id: m.department for m in members}

        if not user_ids:
            return PortfolioAggregation(
                total_grants_tracked=0,
                grants_by_stage={},
                grants_by_department={},
                total_potential_funding=0,
                upcoming_deadlines=[],
                recent_submissions=[],
                recent_awards=[],
            )

        # Get all applications from these users
        # Convert UUIDs to string for IN clause
        user_ids_str = ", ".join([f"'{str(uid)}'" for uid in user_ids])

        apps_query = text(f"""
            SELECT
                ga.id, ga.user_id, ga.grant_id, ga.stage, ga.created_at, ga.updated_at,
                g.title, g.agency, g.deadline, g.amount_min, g.amount_max,
                u.name as user_name
            FROM grant_applications ga
            JOIN grants g ON g.id = ga.grant_id
            JOIN users u ON u.id = ga.user_id
            WHERE ga.user_id IN ({user_ids_str})
            ORDER BY ga.updated_at DESC
        """)

        result = await self.db.execute(apps_query)
        applications = result.fetchall()

        # Aggregate stats
        grants_by_stage = {}
        grants_by_department = {}
        total_potential = 0
        upcoming_deadlines = []
        recent_submissions = []
        recent_awards = []

        now = datetime.now(timezone.utc)
        week_later = now + timedelta(days=30)

        for app in applications:
            # Stage count
            stage = app.stage if isinstance(app.stage, str) else app.stage.value
            grants_by_stage[stage] = grants_by_stage.get(stage, 0) + 1

            # Department count
            dept = user_departments.get(app.user_id) or "Unassigned"
            grants_by_department[dept] = grants_by_department.get(dept, 0) + 1

            # Potential funding
            if app.amount_max:
                total_potential += app.amount_max

            summary = GrantTrackedSummary(
                grant_id=app.grant_id,
                title=app.title,
                agency=app.agency,
                deadline=app.deadline,
                amount_min=app.amount_min,
                amount_max=app.amount_max,
                stage=stage,
                user_id=app.user_id,
                user_name=app.user_name,
                department=user_departments.get(app.user_id),
            )

            # Upcoming deadlines (within 30 days, not submitted/awarded/rejected)
            if app.deadline and app.deadline > now and app.deadline < week_later:
                if stage in ["researching", "writing"]:
                    upcoming_deadlines.append(summary)

            # Recent submissions
            if stage == "submitted":
                recent_submissions.append(summary)

            # Recent awards
            if stage == "awarded":
                recent_awards.append(summary)

        # Sort and limit
        upcoming_deadlines = sorted(upcoming_deadlines, key=lambda x: x.deadline or now)[:10]
        recent_submissions = recent_submissions[:10]
        recent_awards = recent_awards[:10]

        return PortfolioAggregation(
            total_grants_tracked=len(applications),
            grants_by_stage=grants_by_stage,
            grants_by_department=grants_by_department,
            total_potential_funding=total_potential,
            upcoming_deadlines=upcoming_deadlines,
            recent_submissions=recent_submissions,
            recent_awards=recent_awards,
        )

    # =========================================================================
    # Metrics Operations
    # =========================================================================

    async def get_metrics(
        self,
        institution_id: UUID,
        user_id: UUID,
    ) -> dict:
        """
        Get institution-wide metrics and benchmarks.

        Args:
            institution_id: Institution ID.
            user_id: ID of the user requesting.

        Returns:
            Institution metrics.

        Raises:
            AuthorizationError: If user is not a member.
        """
        await self._verify_member(institution_id, user_id)

        # Get member user IDs
        member_ids_query = text("""
            SELECT user_id FROM institution_members
            WHERE institution_id = :institution_id
        """)
        result = await self.db.execute(member_ids_query, {"institution_id": institution_id})
        members = result.fetchall()
        user_ids = [m.user_id for m in members]

        if not user_ids:
            return {
                "total_members": 0,
                "total_grants_tracked": 0,
                "total_grants_submitted": 0,
                "total_grants_awarded": 0,
                "total_funding_received": 0,
                "overall_success_rate": None,
                "success_rate_by_funder": {},
                "success_rate_by_category": {},
                "pipeline_metrics": [],
                "avg_days_to_submission": None,
                "avg_days_to_decision": None,
                "monthly_submissions": {},
                "monthly_awards": {},
            }

        user_ids_str = ", ".join([f"'{str(uid)}'" for uid in user_ids])

        # Get application counts by stage
        stage_query = text(f"""
            SELECT stage, COUNT(*) as count
            FROM grant_applications
            WHERE user_id IN ({user_ids_str})
            GROUP BY stage
        """)
        result = await self.db.execute(stage_query)
        stage_counts = {row.stage if isinstance(row.stage, str) else row.stage.value: row.count for row in result.fetchall()}

        total_tracked = sum(stage_counts.values())
        total_submitted = stage_counts.get("submitted", 0)
        total_awarded = stage_counts.get("awarded", 0)
        total_rejected = stage_counts.get("rejected", 0)

        # Calculate success rate
        total_decided = total_awarded + total_rejected
        success_rate = (total_awarded / total_decided * 100) if total_decided > 0 else None

        # Get total funding received (from matches with award_amount)
        funding_query = text(f"""
            SELECT COALESCE(SUM(m.award_amount), 0) as total_funding
            FROM matches m
            WHERE m.user_id IN ({user_ids_str})
            AND m.application_status = 'awarded'
            AND m.award_amount IS NOT NULL
        """)
        result = await self.db.execute(funding_query)
        total_funding = result.scalar() or 0

        # Success rate by funder (agency)
        funder_query = text(f"""
            SELECT g.agency,
                   SUM(CASE WHEN ga.stage = 'awarded' THEN 1 ELSE 0 END) as awarded,
                   SUM(CASE WHEN ga.stage IN ('awarded', 'rejected') THEN 1 ELSE 0 END) as decided
            FROM grant_applications ga
            JOIN grants g ON g.id = ga.grant_id
            WHERE ga.user_id IN ({user_ids_str})
            AND ga.stage IN ('awarded', 'rejected', 'submitted')
            GROUP BY g.agency
        """)
        result = await self.db.execute(funder_query)
        success_by_funder = {}
        for row in result.fetchall():
            if row.agency and row.decided > 0:
                success_by_funder[row.agency] = round(row.awarded / row.decided * 100, 1)

        # Pipeline metrics
        pipeline_metrics = []
        for stage in ["researching", "writing", "submitted", "awarded", "rejected"]:
            count = stage_counts.get(stage, 0)
            # Get total potential for this stage
            potential_query = text(f"""
                SELECT COALESCE(SUM(g.amount_max), 0) as total
                FROM grant_applications ga
                JOIN grants g ON g.id = ga.grant_id
                WHERE ga.user_id IN ({user_ids_str})
                AND ga.stage = :stage
            """)
            result = await self.db.execute(potential_query, {"stage": stage})
            potential = result.scalar() or 0

            pipeline_metrics.append(FundingPipelineMetric(
                stage=stage,
                count=count,
                total_potential=potential,
                avg_time_in_stage_days=None,  # Would require tracking stage changes
            ))

        # Monthly submissions and awards (last 12 months)
        twelve_months_ago = datetime.now(timezone.utc) - timedelta(days=365)
        monthly_query = text(f"""
            SELECT
                TO_CHAR(ga.updated_at, 'YYYY-MM') as month,
                ga.stage,
                COUNT(*) as count
            FROM grant_applications ga
            WHERE ga.user_id IN ({user_ids_str})
            AND ga.stage IN ('submitted', 'awarded')
            AND ga.updated_at >= :start_date
            GROUP BY TO_CHAR(ga.updated_at, 'YYYY-MM'), ga.stage
            ORDER BY month
        """)
        result = await self.db.execute(monthly_query, {"start_date": twelve_months_ago})

        monthly_submissions = {}
        monthly_awards = {}
        for row in result.fetchall():
            stage = row.stage if isinstance(row.stage, str) else row.stage.value
            if stage == "submitted":
                monthly_submissions[row.month] = row.count
            elif stage == "awarded":
                monthly_awards[row.month] = row.count

        return {
            "total_members": len(user_ids),
            "total_grants_tracked": total_tracked,
            "total_grants_submitted": total_submitted,
            "total_grants_awarded": total_awarded,
            "total_funding_received": total_funding,
            "overall_success_rate": round(success_rate, 1) if success_rate else None,
            "success_rate_by_funder": success_by_funder,
            "success_rate_by_category": {},  # Would require category tracking
            "pipeline_metrics": [m.model_dump() for m in pipeline_metrics],
            "avg_days_to_submission": None,
            "avg_days_to_decision": None,
            "monthly_submissions": monthly_submissions,
            "monthly_awards": monthly_awards,
        }

    # =========================================================================
    # Department Operations
    # =========================================================================

    async def get_departments(
        self,
        institution_id: UUID,
        user_id: UUID,
    ) -> Tuple[List[DepartmentStats], int]:
        """
        Get departments with their statistics.

        Args:
            institution_id: Institution ID.
            user_id: ID of the user requesting.

        Returns:
            Tuple of (departments list, total count).

        Raises:
            AuthorizationError: If user is not a member.
        """
        await self._verify_member(institution_id, user_id)

        # Get departments with member counts
        dept_query = text("""
            SELECT
                COALESCE(department, 'Unassigned') as department,
                COUNT(*) as member_count,
                ARRAY_AGG(user_id) as user_ids
            FROM institution_members
            WHERE institution_id = :institution_id
            GROUP BY department
        """)
        result = await self.db.execute(dept_query, {"institution_id": institution_id})
        departments_raw = result.fetchall()

        departments = []
        for dept_row in departments_raw:
            user_ids = dept_row.user_ids
            user_ids_str = ", ".join([f"'{str(uid)}'" for uid in user_ids])

            # Get application stats for this department's users
            stats_query = text(f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN stage = 'submitted' THEN 1 ELSE 0 END) as submitted,
                    SUM(CASE WHEN stage = 'awarded' THEN 1 ELSE 0 END) as awarded,
                    SUM(CASE WHEN stage = 'rejected' THEN 1 ELSE 0 END) as rejected
                FROM grant_applications
                WHERE user_id IN ({user_ids_str})
            """)
            stats_result = await self.db.execute(stats_query)
            stats = stats_result.fetchone()

            # Get total funding
            funding_query = text(f"""
                SELECT COALESCE(SUM(m.award_amount), 0) as total
                FROM matches m
                WHERE m.user_id IN ({user_ids_str})
                AND m.application_status = 'awarded'
            """)
            funding_result = await self.db.execute(funding_query)
            total_funding = funding_result.scalar() or 0

            # Calculate success rate
            decided = (stats.awarded or 0) + (stats.rejected or 0)
            success_rate = round((stats.awarded or 0) / decided * 100, 1) if decided > 0 else None

            departments.append(DepartmentStats(
                department=dept_row.department,
                member_count=dept_row.member_count,
                grants_tracked=stats.total or 0,
                grants_submitted=stats.submitted or 0,
                grants_awarded=stats.awarded or 0,
                success_rate=success_rate,
                total_funding_received=total_funding,
            ))

        return departments, len(departments)

    # =========================================================================
    # Deadlines Operations
    # =========================================================================

    async def get_deadlines(
        self,
        institution_id: UUID,
        user_id: UUID,
        days_ahead: int = 90,
        department: Optional[str] = None,
    ) -> Tuple[List[DeadlineSummary], dict]:
        """
        Get all upcoming deadlines across institution members.

        Args:
            institution_id: Institution ID.
            user_id: ID of the user requesting.
            days_ahead: Number of days ahead to look.
            department: Optional department filter.

        Returns:
            Tuple of (deadlines list, summary stats).

        Raises:
            AuthorizationError: If user is not a member.
        """
        await self._verify_member(institution_id, user_id)

        # Get member user IDs
        member_params = {"institution_id": institution_id}
        member_query = text("""
            SELECT user_id, department FROM institution_members
            WHERE institution_id = :institution_id
        """)
        if department:
            member_query = text("""
                SELECT user_id, department FROM institution_members
                WHERE institution_id = :institution_id AND department = :department
            """)
            member_params["department"] = department

        result = await self.db.execute(member_query, member_params)
        members = result.fetchall()
        user_ids = [m.user_id for m in members]
        user_departments = {m.user_id: m.department for m in members}

        if not user_ids:
            return [], {"total": 0, "overdue_count": 0, "due_this_week": 0, "due_this_month": 0}

        user_ids_str = ", ".join([f"'{str(uid)}'" for uid in user_ids])
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days_ahead)

        # Get deadlines from grants via applications
        deadlines_query = text(f"""
            SELECT
                ga.id as application_id, ga.user_id, ga.grant_id, ga.stage, ga.priority,
                g.title, g.agency, g.deadline,
                u.name as user_name
            FROM grant_applications ga
            JOIN grants g ON g.id = ga.grant_id
            JOIN users u ON u.id = ga.user_id
            WHERE ga.user_id IN ({user_ids_str})
            AND g.deadline IS NOT NULL
            AND g.deadline <= :cutoff
            AND ga.stage IN ('researching', 'writing')
            ORDER BY g.deadline ASC
        """)

        result = await self.db.execute(deadlines_query, {"cutoff": cutoff})
        rows = result.fetchall()

        deadlines = []
        overdue = 0
        due_this_week = 0
        due_this_month = 0

        week_later = now + timedelta(days=7)
        month_later = now + timedelta(days=30)

        for row in rows:
            days_until = (row.deadline - now).days

            deadline = DeadlineSummary(
                deadline_id=None,
                grant_id=row.grant_id,
                application_id=row.application_id,
                title=row.title,
                agency=row.agency,
                deadline_date=row.deadline,
                days_until_deadline=days_until,
                status=row.stage if isinstance(row.stage, str) else row.stage.value,
                user_id=row.user_id,
                user_name=row.user_name,
                department=user_departments.get(row.user_id),
                priority=row.priority or "medium",
            )
            deadlines.append(deadline)

            if days_until < 0:
                overdue += 1
            elif row.deadline <= week_later:
                due_this_week += 1
            elif row.deadline <= month_later:
                due_this_month += 1

        return deadlines, {
            "total": len(deadlines),
            "overdue_count": overdue,
            "due_this_week": due_this_week,
            "due_this_month": due_this_month,
        }

    # =========================================================================
    # User's Institutions
    # =========================================================================

    async def get_user_institutions(self, user_id: UUID) -> List[dict]:
        """
        Get all institutions a user belongs to.

        Args:
            user_id: User ID.

        Returns:
            List of institutions with user's role.
        """
        query = text("""
            SELECT
                i.id, i.name, i.type, i.domain, i.logo_url,
                im.role, im.department
            FROM institutions i
            JOIN institution_members im ON im.institution_id = i.id
            WHERE im.user_id = :user_id
            ORDER BY i.name
        """)
        result = await self.db.execute(query, {"user_id": user_id})
        rows = result.fetchall()

        return [{
            "id": row.id,
            "name": row.name,
            "type": row.type,
            "domain": row.domain,
            "logo_url": row.logo_url,
            "user_role": row.role,
            "user_department": row.department,
        } for row in rows]

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _verify_admin(self, institution_id: UUID, user_id: UUID) -> None:
        """Verify user is an admin of the institution."""
        query = text("""
            SELECT role FROM institution_members
            WHERE institution_id = :institution_id AND user_id = :user_id
        """)
        result = await self.db.execute(query, {
            "institution_id": institution_id,
            "user_id": user_id,
        })
        row = result.fetchone()

        if not row:
            raise NotFoundError("Institution membership", str(user_id))
        if row.role != "admin":
            raise AuthorizationError("Admin privileges required for this action")

    async def _verify_member(self, institution_id: UUID, user_id: UUID) -> dict:
        """Verify user is a member of the institution."""
        query = text("""
            SELECT role, department, permissions FROM institution_members
            WHERE institution_id = :institution_id AND user_id = :user_id
        """)
        result = await self.db.execute(query, {
            "institution_id": institution_id,
            "user_id": user_id,
        })
        row = result.fetchone()

        if not row:
            raise AuthorizationError("You are not a member of this institution")

        return {"role": row.role, "department": row.department, "permissions": row.permissions}

    async def _verify_can_manage_members(self, institution_id: UUID, user_id: UUID) -> None:
        """Verify user can manage members (admin or manager)."""
        membership = await self._verify_member(institution_id, user_id)

        if membership["role"] == "admin":
            return

        if membership["role"] == "manager":
            # Check for specific permission
            perms = membership.get("permissions") or {}
            if perms.get("can_manage_members"):
                return

        raise AuthorizationError("You do not have permission to manage members")

    async def _get_member_by_id(self, institution_id: UUID, member_id: UUID) -> dict:
        """Get member by their record ID."""
        query = text("""
            SELECT
                im.id, im.institution_id, im.user_id, im.role, im.department,
                im.title, im.permissions, im.added_at, im.added_by, im.updated_at,
                u.name as user_name, u.email as user_email
            FROM institution_members im
            JOIN users u ON u.id = im.user_id
            WHERE im.id = :id AND im.institution_id = :institution_id
        """)
        result = await self.db.execute(query, {
            "id": member_id,
            "institution_id": institution_id,
        })
        row = result.fetchone()

        if not row:
            raise NotFoundError("Member", str(member_id))

        return {
            "id": row.id,
            "institution_id": row.institution_id,
            "user_id": row.user_id,
            "role": row.role,
            "department": row.department,
            "title": row.title,
            "permissions": row.permissions,
            "added_at": row.added_at,
            "added_by": row.added_by,
            "updated_at": row.updated_at,
            "user_name": row.user_name,
            "user_email": row.user_email,
        }
