"""
Resource Sharing API Endpoints
API endpoints for fine-grained resource-level access control and sharing.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query

from backend.api.deps import AsyncSessionDep, CurrentUser, OptionalUser
from backend.core.config import settings
from backend.services.resource_permission import ResourcePermissionService
from backend.schemas.sharing import (
    # Request schemas
    ShareResourceRequest,
    CreateShareLinkRequest,
    UpdateShareLinkRequest,
    BatchShareRequest,
    CheckPermissionRequest,
    # Response schemas
    ResourcePermissionResponse,
    ResourcePermissionListResponse,
    ShareLinkResponse,
    ShareLinkListResponse,
    AccessShareLinkResponse,
    SharedResourceInfo,
    SharedWithMeResponse,
    CheckPermissionResponse,
    RevokePermissionResponse,
    BatchShareResponse,
    BatchShareResultItem,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/sharing",
    tags=["Sharing"],
)


# =============================================================================
# Helper Functions
# =============================================================================


def _build_permission_response(
    permission,
    include_user_info: bool = True,
) -> ResourcePermissionResponse:
    """Build a ResourcePermissionResponse from a ResourcePermission model."""
    response = ResourcePermissionResponse(
        id=permission.id,
        resource_type=permission.resource_type,
        resource_id=permission.resource_id,
        user_id=permission.user_id,
        team_id=permission.team_id,
        permission_level=permission.permission_level,
        granted_by=permission.granted_by,
        granted_at=permission.granted_at,
        expires_at=permission.expires_at,
        user_email=permission.user.email if permission.user else None,
        user_name=permission.user.name if permission.user else None,
        granter_email=permission.granter.email if permission.granter else None,
        granter_name=permission.granter.name if permission.granter else None,
    )
    return response


def _build_share_link_response(
    link,
    base_url: Optional[str] = None,
) -> ShareLinkResponse:
    """Build a ShareLinkResponse from a ShareLink model."""
    share_url = None
    if base_url:
        share_url = f"{base_url}/share/{link.token}"

    return ShareLinkResponse(
        id=link.id,
        resource_type=link.resource_type,
        resource_id=link.resource_id,
        token=link.token,
        permission_level=link.permission_level,
        created_by=link.created_by,
        created_at=link.created_at,
        expires_at=link.expires_at,
        max_uses=link.max_uses,
        use_count=link.use_count,
        is_active=link.is_active,
        is_password_protected=link.password_hash is not None,
        name=link.name,
        share_url=share_url,
        creator_email=link.creator.email if link.creator else None,
        creator_name=link.creator.name if link.creator else None,
    )


async def _build_shared_resource_info(
    permission,
    service: ResourcePermissionService,
) -> SharedResourceInfo:
    """Build a SharedResourceInfo from a ResourcePermission model."""
    # Get resource info
    resource_info = await service.get_resource_info(permission.resource_type, permission.resource_id)

    return SharedResourceInfo(
        permission_id=permission.id,
        resource_type=permission.resource_type,
        resource_id=permission.resource_id,
        permission_level=permission.permission_level,
        granted_at=permission.granted_at,
        expires_at=permission.expires_at,
        resource_title=resource_info.get("title") if resource_info else None,
        resource_description=resource_info.get("description") if resource_info else None,
        granted_by=permission.granted_by,
        granter_email=permission.granter.email if permission.granter else None,
        granter_name=permission.granter.name if permission.granter else None,
    )


# =============================================================================
# Grant Sharing Endpoints
# =============================================================================


@router.post(
    "/grant/{grant_id}",
    response_model=ResourcePermissionResponse,
    status_code=201,
    summary="Share a grant",
    description="Share a grant with a specific user.",
)
async def share_grant(
    grant_id: UUID,
    data: ShareResourceRequest,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> ResourcePermissionResponse:
    """
    Share a grant with a user.

    The current user must have admin permission on the grant to share it.
    """
    service = ResourcePermissionService(db)
    permission = await service.share_resource(
        owner_id=current_user.id,
        resource_type="grant",
        resource_id=grant_id,
        data=data,
    )

    # Optionally send notification
    if data.notify:
        # TODO: Implement notification sending
        logger.info(f"Notification to be sent for grant share: {permission.id}")

    return _build_permission_response(permission)


@router.get(
    "/grant/{grant_id}",
    response_model=ResourcePermissionListResponse,
    summary="List grant permissions",
    description="List all users who have access to a grant.",
)
async def list_grant_permissions(
    grant_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> ResourcePermissionListResponse:
    """
    List all permissions for a grant.

    Only the grant owner or users with admin permission can view this list.
    """
    service = ResourcePermissionService(db)
    permissions = await service.list_resource_permissions(
        owner_id=current_user.id,
        resource_type="grant",
        resource_id=grant_id,
    )

    return ResourcePermissionListResponse(
        permissions=[_build_permission_response(p) for p in permissions],
        total=len(permissions),
        resource_type="grant",
        resource_id=grant_id,
    )


@router.delete(
    "/grant/{grant_id}/user/{user_id}",
    response_model=RevokePermissionResponse,
    summary="Revoke grant access",
    description="Revoke a user's access to a grant.",
)
async def revoke_grant_permission(
    grant_id: UUID,
    user_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> RevokePermissionResponse:
    """
    Revoke a user's permission on a grant.

    Only the grant owner or users with admin permission can revoke access.
    """
    service = ResourcePermissionService(db)
    await service.revoke_permission(
        owner_id=current_user.id,
        resource_type="grant",
        resource_id=grant_id,
        user_id=user_id,
    )

    logger.info(f"Revoked grant permission: grant={grant_id}, user={user_id}")

    return RevokePermissionResponse(
        success=True,
        message=f"Access revoked for user {user_id}",
    )


# =============================================================================
# Application Sharing Endpoints
# =============================================================================


@router.post(
    "/application/{application_id}",
    response_model=ResourcePermissionResponse,
    status_code=201,
    summary="Share an application",
    description="Share an application with a specific user.",
)
async def share_application(
    application_id: UUID,
    data: ShareResourceRequest,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> ResourcePermissionResponse:
    """
    Share an application with a user.

    The current user must own the application or have admin permission.
    """
    service = ResourcePermissionService(db)
    permission = await service.share_resource(
        owner_id=current_user.id,
        resource_type="application",
        resource_id=application_id,
        data=data,
    )

    return _build_permission_response(permission)


@router.get(
    "/application/{application_id}",
    response_model=ResourcePermissionListResponse,
    summary="List application permissions",
    description="List all users who have access to an application.",
)
async def list_application_permissions(
    application_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> ResourcePermissionListResponse:
    """
    List all permissions for an application.
    """
    service = ResourcePermissionService(db)
    permissions = await service.list_resource_permissions(
        owner_id=current_user.id,
        resource_type="application",
        resource_id=application_id,
    )

    return ResourcePermissionListResponse(
        permissions=[_build_permission_response(p) for p in permissions],
        total=len(permissions),
        resource_type="application",
        resource_id=application_id,
    )


@router.delete(
    "/application/{application_id}/user/{user_id}",
    response_model=RevokePermissionResponse,
    summary="Revoke application access",
    description="Revoke a user's access to an application.",
)
async def revoke_application_permission(
    application_id: UUID,
    user_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> RevokePermissionResponse:
    """
    Revoke a user's permission on an application.
    """
    service = ResourcePermissionService(db)
    await service.revoke_permission(
        owner_id=current_user.id,
        resource_type="application",
        resource_id=application_id,
        user_id=user_id,
    )

    return RevokePermissionResponse(
        success=True,
        message=f"Access revoked for user {user_id}",
    )


# =============================================================================
# Share Link Endpoints
# =============================================================================


@router.post(
    "/link",
    response_model=ShareLinkResponse,
    status_code=201,
    summary="Create share link",
    description="Create a shareable link for a resource.",
)
async def create_share_link(
    data: CreateShareLinkRequest,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> ShareLinkResponse:
    """
    Create a shareable link for a resource.

    The link can be optionally password protected and can have
    an expiration date or maximum use count.
    """
    service = ResourcePermissionService(db)
    link = await service.create_share_link(
        owner_id=current_user.id,
        data=data,
    )

    base_url = getattr(settings, "frontend_url", None)
    return _build_share_link_response(link, base_url)


@router.get(
    "/link/{token}",
    response_model=AccessShareLinkResponse,
    summary="Access via share link",
    description="Access a resource using a share link token.",
)
async def access_share_link(
    token: str,
    db: AsyncSessionDep,
    current_user: OptionalUser = None,
    password: Optional[str] = Query(None, description="Password if link is protected"),
) -> AccessShareLinkResponse:
    """
    Access a resource via share link.

    No authentication required, but password may be needed if the link is protected.
    """
    service = ResourcePermissionService(db)
    success, link, message = await service.access_via_share_link(
        token=token,
        password=password,
    )

    if not success:
        return AccessShareLinkResponse(
            success=False,
            resource_type=link.resource_type if link else "unknown",
            resource_id=link.resource_id if link else UUID("00000000-0000-0000-0000-000000000000"),
            permission_level="none",
            resource_data=None,
            message=message,
        )

    # Get resource data
    resource_info = await service.get_resource_info(link.resource_type, link.resource_id)

    return AccessShareLinkResponse(
        success=True,
        resource_type=link.resource_type,
        resource_id=link.resource_id,
        permission_level=link.permission_level,
        resource_data=resource_info,
        message=message,
    )


@router.get(
    "/links",
    response_model=ShareLinkListResponse,
    summary="List share links",
    description="List all share links created by the current user.",
)
async def list_share_links(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[UUID] = Query(None, description="Filter by resource ID"),
    include_inactive: bool = Query(False, description="Include inactive links"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Skip first N results"),
) -> ShareLinkListResponse:
    """
    List share links created by the current user.
    """
    service = ResourcePermissionService(db)
    links, total = await service.list_share_links(
        owner_id=current_user.id,
        resource_type=resource_type,
        resource_id=resource_id,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )

    base_url = getattr(settings, "frontend_url", None)
    return ShareLinkListResponse(
        links=[_build_share_link_response(link, base_url) for link in links],
        total=total,
    )


@router.patch(
    "/link/{link_id}",
    response_model=ShareLinkResponse,
    summary="Update share link",
    description="Update a share link's settings.",
)
async def update_share_link(
    link_id: UUID,
    data: UpdateShareLinkRequest,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> ShareLinkResponse:
    """
    Update a share link's settings.

    Only the link creator can update it.
    """
    service = ResourcePermissionService(db)
    link = await service.update_share_link(
        owner_id=current_user.id,
        link_id=link_id,
        data=data,
    )

    base_url = getattr(settings, "frontend_url", None)
    return _build_share_link_response(link, base_url)


@router.delete(
    "/link/{link_id}",
    status_code=204,
    summary="Delete share link",
    description="Delete a share link.",
)
async def delete_share_link(
    link_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> None:
    """
    Delete a share link.

    Only the link creator can delete it.
    """
    service = ResourcePermissionService(db)
    await service.delete_share_link(
        owner_id=current_user.id,
        link_id=link_id,
    )


# =============================================================================
# Shared With Me Endpoints
# =============================================================================


@router.get(
    "/shared-with-me",
    response_model=SharedWithMeResponse,
    summary="List shared resources",
    description="List all resources shared with the current user.",
)
async def list_shared_with_me(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Skip first N results"),
) -> SharedWithMeResponse:
    """
    List all resources that have been shared with the current user.
    """
    service = ResourcePermissionService(db)
    permissions, total = await service.list_shared_with_me(
        user_id=current_user.id,
        resource_type=resource_type,
        limit=limit,
        offset=offset,
    )

    # Build response with resource info
    resources = []
    grants_count = 0
    applications_count = 0
    documents_count = 0

    for permission in permissions:
        resource_info = await _build_shared_resource_info(permission, service)
        resources.append(resource_info)

        # Count by type
        if permission.resource_type == "grant":
            grants_count += 1
        elif permission.resource_type == "application":
            applications_count += 1
        elif permission.resource_type == "document":
            documents_count += 1

    return SharedWithMeResponse(
        resources=resources,
        total=total,
        grants_count=grants_count,
        applications_count=applications_count,
        documents_count=documents_count,
    )


# =============================================================================
# Permission Check Endpoints
# =============================================================================


@router.post(
    "/check-permission",
    response_model=CheckPermissionResponse,
    summary="Check permission",
    description="Check if the current user has a specific permission on a resource.",
)
async def check_permission(
    data: CheckPermissionRequest,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> CheckPermissionResponse:
    """
    Check if the current user has the required permission level on a resource.
    """
    service = ResourcePermissionService(db)
    has_permission, actual_level, source = await service.check_permission(
        user_id=current_user.id,
        resource_type=data.resource_type.value,
        resource_id=data.resource_id,
        required_level=data.required_level.value,
    )

    return CheckPermissionResponse(
        has_permission=has_permission,
        actual_level=actual_level,
        source=source,
    )


# =============================================================================
# Batch Operations
# =============================================================================


@router.post(
    "/grant/{grant_id}/batch",
    response_model=BatchShareResponse,
    status_code=201,
    summary="Share grant with multiple users",
    description="Share a grant with multiple users at once.",
)
async def batch_share_grant(
    grant_id: UUID,
    data: BatchShareRequest,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> BatchShareResponse:
    """
    Share a grant with multiple users at once.

    Each share request is processed independently, so some may succeed
    while others fail.
    """
    service = ResourcePermissionService(db)
    results = []
    successful_count = 0
    failed_count = 0

    for share_request in data.users:
        try:
            permission = await service.share_resource(
                owner_id=current_user.id,
                resource_type="grant",
                resource_id=grant_id,
                data=share_request,
            )

            results.append(
                BatchShareResultItem(
                    user_id=share_request.user_id,
                    email=share_request.email,
                    success=True,
                    message="Shared successfully",
                    permission=_build_permission_response(permission),
                )
            )
            successful_count += 1

        except Exception as e:
            results.append(
                BatchShareResultItem(
                    user_id=share_request.user_id,
                    email=share_request.email,
                    success=False,
                    message=str(e.detail) if hasattr(e, "detail") else str(e),
                    permission=None,
                )
            )
            failed_count += 1

    return BatchShareResponse(
        total_requested=len(data.users),
        successful=successful_count,
        failed=failed_count,
        results=results,
    )


@router.post(
    "/application/{application_id}/batch",
    response_model=BatchShareResponse,
    status_code=201,
    summary="Share application with multiple users",
    description="Share an application with multiple users at once.",
)
async def batch_share_application(
    application_id: UUID,
    data: BatchShareRequest,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> BatchShareResponse:
    """
    Share an application with multiple users at once.
    """
    service = ResourcePermissionService(db)
    results = []
    successful_count = 0
    failed_count = 0

    for share_request in data.users:
        try:
            permission = await service.share_resource(
                owner_id=current_user.id,
                resource_type="application",
                resource_id=application_id,
                data=share_request,
            )

            results.append(
                BatchShareResultItem(
                    user_id=share_request.user_id,
                    email=share_request.email,
                    success=True,
                    message="Shared successfully",
                    permission=_build_permission_response(permission),
                )
            )
            successful_count += 1

        except Exception as e:
            results.append(
                BatchShareResultItem(
                    user_id=share_request.user_id,
                    email=share_request.email,
                    success=False,
                    message=str(e.detail) if hasattr(e, "detail") else str(e),
                    permission=None,
                )
            )
            failed_count += 1

    return BatchShareResponse(
        total_requested=len(data.users),
        successful=successful_count,
        failed=failed_count,
        results=results,
    )
