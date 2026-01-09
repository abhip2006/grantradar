"""Permission template service for managing custom permission templates."""
from typing import Optional, List
from uuid import UUID

import structlog
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import PermissionTemplate, LabMember
from backend.core.exceptions import NotFoundError, ValidationError, ConflictError
from backend.schemas.team import MemberPermissions


logger = structlog.get_logger(__name__)


# Default permission templates
DEFAULT_TEMPLATES = [
    {
        "name": "Full Access",
        "description": "Complete access to all features, equivalent to admin role.",
        "permissions": {
            "can_view": True,
            "can_edit": True,
            "can_create": True,
            "can_delete": True,
            "can_invite": True,
            "can_manage_grants": True,
            "can_export": True,
        },
    },
    {
        "name": "Contributor",
        "description": "Can view, edit, and create items but cannot delete or invite.",
        "permissions": {
            "can_view": True,
            "can_edit": True,
            "can_create": True,
            "can_delete": False,
            "can_invite": False,
            "can_manage_grants": False,
            "can_export": True,
        },
    },
    {
        "name": "Viewer",
        "description": "Read-only access to view all data.",
        "permissions": {
            "can_view": True,
            "can_edit": False,
            "can_create": False,
            "can_delete": False,
            "can_invite": False,
            "can_manage_grants": False,
            "can_export": False,
        },
    },
    {
        "name": "Grant Manager",
        "description": "Can manage grants with view and edit access but no team management.",
        "permissions": {
            "can_view": True,
            "can_edit": True,
            "can_create": True,
            "can_delete": False,
            "can_invite": False,
            "can_manage_grants": True,
            "can_export": True,
        },
    },
]


class PermissionTemplateService:
    """
    Service for managing custom permission templates.

    Provides methods to create, list, update, and delete permission
    templates that can be applied to team members.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the permission template service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def create_template(
        self,
        owner_id: UUID,
        name: str,
        description: Optional[str],
        permissions: dict,
    ) -> PermissionTemplate:
        """
        Create a new permission template.

        Args:
            owner_id: ID of the user creating the template.
            name: Template name.
            description: Template description.
            permissions: Permission settings dict.

        Returns:
            Created PermissionTemplate record.

        Raises:
            ConflictError: If template with same name already exists.
            ValidationError: If permissions are invalid.
        """
        # Validate permissions structure
        self._validate_permissions(permissions)

        # Check for duplicate name
        existing = await self._get_template_by_name(owner_id, name)
        if existing:
            raise ConflictError(f"A template named '{name}' already exists")

        template = PermissionTemplate(
            owner_id=owner_id,
            name=name,
            description=description,
            permissions=permissions,
            is_default=False,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)

        logger.info(
            "permission_template_created",
            template_id=str(template.id),
            owner_id=str(owner_id),
            name=name,
        )

        return template

    async def list_templates(
        self,
        owner_id: UUID,
    ) -> List[PermissionTemplate]:
        """
        List all permission templates for a user.

        Args:
            owner_id: ID of the template owner.

        Returns:
            List of PermissionTemplate records.
        """
        result = await self.db.execute(
            select(PermissionTemplate)
            .where(PermissionTemplate.owner_id == owner_id)
            .order_by(PermissionTemplate.name)
        )
        return list(result.scalars().all())

    async def get_template(
        self,
        owner_id: UUID,
        template_id: UUID,
    ) -> PermissionTemplate:
        """
        Get a specific permission template.

        Args:
            owner_id: ID of the template owner.
            template_id: ID of the template.

        Returns:
            PermissionTemplate record.

        Raises:
            NotFoundError: If template not found.
        """
        result = await self.db.execute(
            select(PermissionTemplate).where(
                and_(
                    PermissionTemplate.id == template_id,
                    PermissionTemplate.owner_id == owner_id,
                )
            )
        )
        template = result.scalar_one_or_none()

        if not template:
            raise NotFoundError("Permission template", str(template_id))

        return template

    async def update_template(
        self,
        owner_id: UUID,
        template_id: UUID,
        data: dict,
    ) -> PermissionTemplate:
        """
        Update a permission template.

        Args:
            owner_id: ID of the template owner.
            template_id: ID of the template to update.
            data: Dictionary with fields to update (name, description, permissions).

        Returns:
            Updated PermissionTemplate record.

        Raises:
            NotFoundError: If template not found.
            ConflictError: If new name already exists.
            ValidationError: If permissions are invalid.
        """
        template = await self.get_template(owner_id, template_id)

        # Check name uniqueness if being updated
        if "name" in data and data["name"] != template.name:
            existing = await self._get_template_by_name(owner_id, data["name"])
            if existing:
                raise ConflictError(f"A template named '{data['name']}' already exists")
            template.name = data["name"]

        if "description" in data:
            template.description = data["description"]

        if "permissions" in data:
            self._validate_permissions(data["permissions"])
            template.permissions = data["permissions"]

        if "is_default" in data:
            if data["is_default"]:
                # Clear any existing default
                await self._clear_default_template(owner_id)
            template.is_default = data["is_default"]

        await self.db.commit()
        await self.db.refresh(template)

        logger.info(
            "permission_template_updated",
            template_id=str(template_id),
            owner_id=str(owner_id),
        )

        return template

    async def delete_template(
        self,
        owner_id: UUID,
        template_id: UUID,
    ) -> None:
        """
        Delete a permission template.

        Args:
            owner_id: ID of the template owner.
            template_id: ID of the template to delete.

        Raises:
            NotFoundError: If template not found.
            ValidationError: If template is in use by members.
        """
        template = await self.get_template(owner_id, template_id)

        # Check if template is in use
        members_using = await self.db.execute(
            select(LabMember).where(LabMember.permission_template_id == template_id)
        )
        if members_using.scalars().first():
            raise ValidationError(
                "Cannot delete template that is currently assigned to team members. "
                "Please reassign or remove the template from members first."
            )

        await self.db.delete(template)
        await self.db.commit()

        logger.info(
            "permission_template_deleted",
            template_id=str(template_id),
            owner_id=str(owner_id),
        )

    async def apply_template_to_member(
        self,
        owner_id: UUID,
        member_id: UUID,
        template_id: UUID,
    ) -> LabMember:
        """
        Apply a permission template to a team member.

        Args:
            owner_id: ID of the lab owner.
            member_id: ID of the lab member.
            template_id: ID of the template to apply.

        Returns:
            Updated LabMember record.

        Raises:
            NotFoundError: If template or member not found.
        """
        # Get the template
        template = await self.get_template(owner_id, template_id)

        # Get the member
        result = await self.db.execute(
            select(LabMember).where(
                and_(
                    LabMember.id == member_id,
                    LabMember.lab_owner_id == owner_id,
                )
            )
        )
        member = result.scalar_one_or_none()

        if not member:
            raise NotFoundError("Team member", str(member_id))

        # Apply template permissions
        member.permissions = template.permissions
        member.permission_template_id = template_id

        await self.db.commit()
        await self.db.refresh(member)

        logger.info(
            "template_applied_to_member",
            template_id=str(template_id),
            member_id=str(member_id),
            owner_id=str(owner_id),
        )

        return member

    def get_default_templates(self) -> List[dict]:
        """
        Get the list of built-in default templates.

        These templates are predefined and represent common permission
        configurations that users can apply or use as a starting point.

        Returns:
            List of default template configurations.
        """
        return DEFAULT_TEMPLATES.copy()

    async def ensure_default_templates(self, owner_id: UUID) -> List[PermissionTemplate]:
        """
        Ensure default templates exist for a user.

        Creates the built-in templates if they don't already exist.

        Args:
            owner_id: ID of the user.

        Returns:
            List of the user's templates including defaults.
        """
        created = []

        for default in DEFAULT_TEMPLATES:
            existing = await self._get_template_by_name(owner_id, default["name"])
            if not existing:
                template = PermissionTemplate(
                    owner_id=owner_id,
                    name=default["name"],
                    description=default["description"],
                    permissions=default["permissions"],
                    is_default=False,
                )
                self.db.add(template)
                created.append(template)

        if created:
            await self.db.commit()
            logger.info(
                "default_templates_created",
                owner_id=str(owner_id),
                count=len(created),
            )

        return await self.list_templates(owner_id)

    def _validate_permissions(self, permissions: dict) -> None:
        """
        Validate permission settings structure.

        Args:
            permissions: Permissions dict to validate.

        Raises:
            ValidationError: If permissions are invalid.
        """
        required_keys = {"can_view", "can_edit", "can_create", "can_delete", "can_invite"}
        optional_keys = {"can_manage_grants", "can_export"}
        allowed_keys = required_keys | optional_keys

        if not isinstance(permissions, dict):
            raise ValidationError("Permissions must be a dictionary")

        # Check for required keys
        missing = required_keys - set(permissions.keys())
        if missing:
            raise ValidationError(f"Missing required permissions: {', '.join(missing)}")

        # Check for invalid keys
        invalid = set(permissions.keys()) - allowed_keys
        if invalid:
            raise ValidationError(f"Invalid permission keys: {', '.join(invalid)}")

        # Validate values are boolean
        for key, value in permissions.items():
            if not isinstance(value, bool):
                raise ValidationError(f"Permission '{key}' must be a boolean value")

    async def _get_template_by_name(
        self,
        owner_id: UUID,
        name: str,
    ) -> Optional[PermissionTemplate]:
        """Get a template by name for a specific owner."""
        result = await self.db.execute(
            select(PermissionTemplate).where(
                and_(
                    PermissionTemplate.owner_id == owner_id,
                    PermissionTemplate.name == name,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _clear_default_template(self, owner_id: UUID) -> None:
        """Clear the is_default flag from all templates for an owner."""
        result = await self.db.execute(
            select(PermissionTemplate).where(
                and_(
                    PermissionTemplate.owner_id == owner_id,
                    PermissionTemplate.is_default == True,
                )
            )
        )
        templates = result.scalars().all()
        for template in templates:
            template.is_default = False
