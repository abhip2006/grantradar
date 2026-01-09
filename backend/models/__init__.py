"""
GrantRadar Models Package
Provides SQLAlchemy ORM models for the application.

This package contains additional dashboard feature models for:
- Checklists (checklist templates and application checklists)
- Reviews (review workflows and internal review processes)
- Compliance (compliance rules and scan results)
- Workflow Analytics (event tracking and analytics)

Base classes are re-exported from the parent models.py file for convenience.
"""
import importlib.util
import os

# Load Base, GUID, JSONB from the parent models.py file
# This is needed because the models/ directory shadows the models.py file
_models_py_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models.py")
_spec = importlib.util.spec_from_file_location("backend_models_py", _models_py_path)
_models_py = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_models_py)

# Re-export key base classes and types
Base = _models_py.Base
GUID = _models_py.GUID
JSONB = _models_py.JSONB
TSVECTOR = _models_py.TSVECTOR
StringArray = _models_py.StringArray

# Re-export enums
ApplicationStage = _models_py.ApplicationStage
InvitationStatus = _models_py.InvitationStatus

# Re-export all model classes
Grant = _models_py.Grant
User = _models_py.User
LabProfile = _models_py.LabProfile
Match = _models_py.Match
AlertSent = _models_py.AlertSent
GrantApplication = _models_py.GrantApplication
SavedSearch = _models_py.SavedSearch
Deadline = _models_py.Deadline
DeadlineStatusHistory = _models_py.DeadlineStatusHistory
CalendarIntegration = _models_py.CalendarIntegration
ReminderSchedule = _models_py.ReminderSchedule
TemplateCategory = _models_py.TemplateCategory
Template = _models_py.Template
FundingAlertPreference = _models_py.FundingAlertPreference
GrantDeadlineHistory = _models_py.GrantDeadlineHistory
ChatSession = _models_py.ChatSession
ChatMessage = _models_py.ChatMessage
ResearchSession = _models_py.ResearchSession
ApplicationSubtask = _models_py.ApplicationSubtask
ApplicationActivity = _models_py.ApplicationActivity
ApplicationAttachment = _models_py.ApplicationAttachment
CustomFieldDefinition = _models_py.CustomFieldDefinition
CustomFieldValue = _models_py.CustomFieldValue
LabMember = _models_py.LabMember
ApplicationAssignee = _models_py.ApplicationAssignee
TeamActivityLog = _models_py.TeamActivityLog
PermissionTemplate = _models_py.PermissionTemplate
Notification = _models_py.Notification

# Team collaboration models
AssignmentRole = _models_py.AssignmentRole
AssignmentStatus = _models_py.AssignmentStatus
GrantAssignment = _models_py.GrantAssignment
TeamComment = _models_py.TeamComment
TeamNotification = _models_py.TeamNotification

# Import models from submodules
from backend.models.mechanisms import GrantMechanism, FundedProject, CompetitionSnapshot

# Clean up module namespace
del importlib, os, _models_py_path, _spec, _models_py

__all__ = [
    # Base classes and types
    "Base",
    "GUID",
    "JSONB",
    "TSVECTOR",
    "StringArray",
    # Enums
    "ApplicationStage",
    "InvitationStatus",
    "AssignmentRole",
    "AssignmentStatus",
    # Models
    "Grant",
    "User",
    "LabProfile",
    "Match",
    "AlertSent",
    "GrantApplication",
    "SavedSearch",
    "Deadline",
    "DeadlineStatusHistory",
    "CalendarIntegration",
    "ReminderSchedule",
    "TemplateCategory",
    "Template",
    "FundingAlertPreference",
    "GrantDeadlineHistory",
    "ChatSession",
    "ChatMessage",
    "ResearchSession",
    "ApplicationSubtask",
    "ApplicationActivity",
    "ApplicationAttachment",
    "CustomFieldDefinition",
    "CustomFieldValue",
    "LabMember",
    "ApplicationAssignee",
    "TeamActivityLog",
    "PermissionTemplate",
    "Notification",
    # Team collaboration models
    "GrantAssignment",
    "TeamComment",
    "TeamNotification",
    # Grant Intelligence Graph models
    "GrantMechanism",
    "FundedProject",
    "CompetitionSnapshot",
]
