"""
Tests for the audit logging system.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit import AuditLog
from backend.schemas.audit import (
    AuditAction,
    AuditExportFormat,
    AuditLogFilters,
    AuditLogResponse,
    AuditResourceType,
)
from backend.services.audit import AuditService, log_audit_action


class TestAuditLogModel:
    """Tests for the AuditLog model."""

    @pytest.mark.asyncio
    async def test_audit_log_creation(self, async_session: AsyncSession):
        """Test creating an audit log entry."""
        log = AuditLog(
            action="CREATE",
            resource_type="grant",
            resource_id=uuid.uuid4(),
            success=True,
            timestamp=datetime.now(timezone.utc),
        )
        async_session.add(log)
        await async_session.flush()

        assert log.id is not None
        assert log.action == "CREATE"
        assert log.resource_type == "grant"
        assert log.success is True

    @pytest.mark.asyncio
    async def test_audit_log_with_all_fields(self, async_session: AsyncSession):
        """Test creating an audit log with all fields populated."""
        user_id = uuid.uuid4()
        resource_id = uuid.uuid4()

        log = AuditLog(
            user_id=user_id,
            action="UPDATE",
            resource_type="user",
            resource_id=resource_id,
            old_values={"name": "Old Name"},
            new_values={"name": "New Name"},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            extra_data={"key": "value"},
            success=True,
            error_message=None,
            request_id="req-123",
            duration_ms=150,
            timestamp=datetime.now(timezone.utc),
        )
        async_session.add(log)
        await async_session.flush()

        assert log.user_id == user_id
        assert log.old_values == {"name": "Old Name"}
        assert log.new_values == {"name": "New Name"}
        assert log.ip_address == "192.168.1.1"
        assert log.extra_data == {"key": "value"}
        assert log.request_id == "req-123"
        assert log.duration_ms == 150

    @pytest.mark.asyncio
    async def test_audit_log_failed_action(self, async_session: AsyncSession):
        """Test logging a failed action."""
        log = AuditLog(
            action="DELETE",
            resource_type="grant",
            success=False,
            error_message="Permission denied",
            timestamp=datetime.now(timezone.utc),
        )
        async_session.add(log)
        await async_session.flush()

        assert log.success is False
        assert log.error_message == "Permission denied"

    @pytest.mark.asyncio
    async def test_audit_log_to_dict(self, async_session: AsyncSession):
        """Test converting audit log to dictionary."""
        log = AuditLog(
            action="CREATE",
            resource_type="team",
            success=True,
            timestamp=datetime.now(timezone.utc),
        )
        async_session.add(log)
        await async_session.flush()

        log_dict = log.to_dict()
        assert "id" in log_dict
        assert "timestamp" in log_dict
        assert log_dict["action"] == "CREATE"
        assert log_dict["resource_type"] == "team"
        assert log_dict["success"] is True


class TestAuditSchemas:
    """Tests for audit Pydantic schemas."""

    def test_audit_action_enum(self):
        """Test AuditAction enum values."""
        assert AuditAction.CREATE.value == "CREATE"
        assert AuditAction.UPDATE.value == "UPDATE"
        assert AuditAction.DELETE.value == "DELETE"
        assert AuditAction.LOGIN.value == "LOGIN"

    def test_audit_resource_type_enum(self):
        """Test AuditResourceType enum values."""
        assert AuditResourceType.GRANT.value == "grant"
        assert AuditResourceType.USER.value == "user"
        assert AuditResourceType.TEAM.value == "team"

    def test_audit_log_filters(self):
        """Test AuditLogFilters schema."""
        filters = AuditLogFilters(
            user_id=uuid.uuid4(),
            action="CREATE",
            resource_type="grant",
            success=True,
        )
        assert filters.action == "CREATE"
        assert filters.success is True

    def test_audit_log_response(self):
        """Test AuditLogResponse schema."""
        response = AuditLogResponse(
            id=uuid.uuid4(),
            timestamp=datetime.now(timezone.utc),
            action="UPDATE",
            resource_type="user",
            success=True,
        )
        assert response.action == "UPDATE"
        assert response.success is True

    def test_audit_export_format_enum(self):
        """Test AuditExportFormat enum."""
        assert AuditExportFormat.CSV.value == "csv"
        assert AuditExportFormat.JSON.value == "json"


class TestAuditService:
    """Tests for AuditService."""

    @pytest.mark.asyncio
    async def test_log_action(self, async_session: AsyncSession):
        """Test logging an action via service."""
        service = AuditService(async_session)

        log = await service.log_action(
            action="CREATE",
            resource_type="grant",
            resource_id=uuid.uuid4(),
            success=True,
        )

        assert log.id is not None
        assert log.action == "CREATE"
        assert log.resource_type == "grant"

    @pytest.mark.asyncio
    async def test_log_action_with_user(self, async_session: AsyncSession, db_user):
        """Test logging an action with user context."""
        service = AuditService(async_session)

        log = await service.log_action(
            action="UPDATE",
            resource_type="user",
            resource_id=db_user.id,
            user_id=db_user.id,
            old_values={"name": "Old"},
            new_values={"name": "New"},
            success=True,
        )

        assert log.user_id == db_user.id
        assert log.old_values == {"name": "Old"}
        assert log.new_values == {"name": "New"}

    @pytest.mark.asyncio
    async def test_get_audit_logs(self, async_session: AsyncSession):
        """Test querying audit logs."""
        service = AuditService(async_session)

        # Create some logs
        await service.log_action(action="CREATE", resource_type="grant", success=True)
        await service.log_action(action="UPDATE", resource_type="grant", success=True)
        await service.log_action(action="DELETE", resource_type="user", success=False)

        # Query all
        logs, total = await service.get_audit_logs(page=1, page_size=10)
        assert total >= 3
        assert len(logs) >= 3

    @pytest.mark.asyncio
    async def test_get_audit_logs_with_filters(self, async_session: AsyncSession):
        """Test querying audit logs with filters."""
        service = AuditService(async_session)

        # Create logs
        await service.log_action(action="CREATE", resource_type="grant", success=True)
        await service.log_action(action="UPDATE", resource_type="user", success=True)

        # Filter by action
        filters = AuditLogFilters(action="CREATE")
        logs, total = await service.get_audit_logs(filters=filters, page=1, page_size=10)

        for log in logs:
            assert log.action == "CREATE"

    @pytest.mark.asyncio
    async def test_get_user_activity(self, async_session: AsyncSession, db_user):
        """Test getting user activity summary."""
        service = AuditService(async_session)

        # Create logs for user
        await service.log_action(
            action="LOGIN",
            resource_type="auth",
            user_id=db_user.id,
            ip_address="192.168.1.1",
            success=True,
        )
        await service.log_action(
            action="CREATE",
            resource_type="grant",
            user_id=db_user.id,
            success=True,
        )

        summary = await service.get_user_activity(user_id=db_user.id)

        assert summary.user_id == db_user.id
        assert summary.total_actions >= 2
        assert summary.successful_actions >= 2
        assert "192.168.1.1" in summary.ip_addresses

    @pytest.mark.asyncio
    async def test_get_resource_history(self, async_session: AsyncSession):
        """Test getting resource change history."""
        service = AuditService(async_session)

        resource_id = uuid.uuid4()

        # Create history for resource
        await service.log_action(
            action="CREATE",
            resource_type="grant",
            resource_id=resource_id,
            new_values={"title": "Initial"},
            success=True,
        )
        await service.log_action(
            action="UPDATE",
            resource_type="grant",
            resource_id=resource_id,
            old_values={"title": "Initial"},
            new_values={"title": "Updated"},
            success=True,
        )

        history = await service.get_resource_history(
            resource_type="grant",
            resource_id=resource_id,
        )

        assert history.resource_type == "grant"
        assert history.resource_id == resource_id
        assert history.total_changes >= 2

    @pytest.mark.asyncio
    async def test_export_audit_logs_csv(self, async_session: AsyncSession):
        """Test exporting audit logs as CSV."""
        service = AuditService(async_session)

        # Create some logs
        await service.log_action(action="CREATE", resource_type="grant", success=True)

        content, filename = await service.export_audit_logs(
            format=AuditExportFormat.CSV,
            max_records=100,
        )

        assert filename.endswith(".csv")
        assert "id,timestamp" in content

    @pytest.mark.asyncio
    async def test_export_audit_logs_json(self, async_session: AsyncSession):
        """Test exporting audit logs as JSON."""
        service = AuditService(async_session)

        # Create some logs
        await service.log_action(action="CREATE", resource_type="grant", success=True)

        content, filename = await service.export_audit_logs(
            format=AuditExportFormat.JSON,
            max_records=100,
        )

        assert filename.endswith(".json")
        assert "export_timestamp" in content
        assert "logs" in content

    @pytest.mark.asyncio
    async def test_get_audit_stats(self, async_session: AsyncSession):
        """Test getting audit statistics."""
        service = AuditService(async_session)

        # Create some logs
        await service.log_action(action="CREATE", resource_type="grant", success=True)
        await service.log_action(action="LOGIN", resource_type="auth", success=True)
        await service.log_action(action="DELETE", resource_type="user", success=False)

        stats = await service.get_audit_stats()

        assert stats.total_logs >= 3
        assert "CREATE" in stats.actions_by_type
        assert "grant" in stats.resources_by_type
        assert 0 <= stats.success_rate <= 100


class TestLogAuditActionHelper:
    """Tests for the log_audit_action helper function."""

    @pytest.mark.asyncio
    async def test_log_audit_action_helper(self, async_session: AsyncSession):
        """Test the convenience helper function."""
        log = await log_audit_action(
            db=async_session,
            action="CREATE",
            resource_type="grant",
            success=True,
        )

        assert log.id is not None
        assert log.action == "CREATE"
