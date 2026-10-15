"""
Publication workflow.

    Draft ──submit──► Submitted ──approve──► Approved (published)
      ▲                  │  │
      └────return────────┘  └──reject──► Rejected
    Any non-archived state ──archive──► Archived   (administrators only)

Rules enforced here (not only in the user interface):
  * each action requires a role capability;
  * returning, rejecting and archiving require a written reason;
  * maker-checker: a user cannot approve a record they created,
    unless settings.ALLOW_SELF_APPROVAL is switched on;
  * every transition writes an ApprovalRecord and an audit log entry.
"""

from dataclasses import dataclass

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from apps.accounts.roles import Capability, has_capability
from apps.audit.models import AuditLog
from apps.audit.services import log

from .models import ApprovalRecord, Status


class WorkflowError(Exception):
    """Raised when a transition is not allowed. The message is safe to show users."""


@dataclass(frozen=True)
class Transition:
    sources: frozenset
    target: str
    capability: Capability
    audit_action: str
    needs_comment: bool = False


TRANSITIONS: dict[str, Transition] = {
    "submit": Transition(frozenset({Status.DRAFT, Status.RETURNED}), Status.SUBMITTED,
                         Capability.ENTER_DATA, AuditLog.Action.SUBMIT),
    "approve": Transition(frozenset({Status.SUBMITTED}), Status.APPROVED,
                          Capability.APPROVE, AuditLog.Action.APPROVE),
    "return": Transition(frozenset({Status.SUBMITTED}), Status.RETURNED,
                         Capability.APPROVE, AuditLog.Action.RETURN, needs_comment=True),
    "reject": Transition(frozenset({Status.SUBMITTED}), Status.REJECTED,
                         Capability.APPROVE, AuditLog.Action.REJECT, needs_comment=True),
    "archive": Transition(frozenset({Status.DRAFT, Status.SUBMITTED, Status.RETURNED,
                                     Status.APPROVED, Status.REJECTED}), Status.ARCHIVED,
                          Capability.ARCHIVE, AuditLog.Action.ARCHIVE, needs_comment=True),
}


def available_actions(obj, user) -> list[str]:
    """Actions this user may perform on this record right now (for the UI)."""
    out = []
    for name, t in TRANSITIONS.items():
        if obj.status in t.sources and has_capability(user, t.capability):
            if name == "approve" and not _may_self_approve(obj, user):
                continue
            out.append(name)
    return out


def _may_self_approve(obj, user) -> bool:
    return settings.ALLOW_SELF_APPROVAL or obj.created_by_id is None or obj.created_by_id != user.pk


@transaction.atomic
def perform(obj, action: str, user, comment: str = "", request=None):
    """Apply a workflow action to a GovernedModel instance and record it."""
    t = TRANSITIONS.get(action)
    if t is None:
        raise WorkflowError(f"Unknown action '{action}'.")
    if not has_capability(user, t.capability):
        raise WorkflowError("You do not have permission to perform this action.")

    obj = type(obj).objects.select_for_update().get(pk=obj.pk)
    if obj.status not in t.sources:
        raise WorkflowError(
            f"Cannot {action} a record that is '{Status(obj.status).label}'."
        )
    comment = (comment or "").strip()
    if t.needs_comment and not comment:
        raise WorkflowError(f"Please give a reason to {action} this record.")
    if action == "approve" and not _may_self_approve(obj, user):
        raise WorkflowError("You cannot approve a record you created. Another reviewer must approve it.")

    previous = obj.status
    now = timezone.now()
    obj.status = t.target
    obj.updated_by = user
    update_fields = ["status", "updated_by", "updated_at"]
    if action == "submit":
        obj.submitted_at = now
        update_fields.append("submitted_at")
    elif action == "approve":
        obj.approved_at, obj.approved_by = now, user
        update_fields += ["approved_at", "approved_by"]
    elif action == "archive":
        obj.archived_reason = comment
        update_fields.append("archived_reason")
    obj.save(update_fields=update_fields)

    ApprovalRecord.objects.create(
        content_type=ContentType.objects.get_for_model(obj), object_id=str(obj.pk),
        action=action, from_status=previous, to_status=t.target, actor=user, comment=comment,
    )
    log(t.audit_action, actor=user, target=obj, request=request,
        details={"from": previous, "to": t.target, "comment": comment})
    return obj
