"""
Roles and what each role may do.

Roles are stored as Django groups so administrators can assign them without
code changes. The mapping from role to capability lives here, in one place,
so permission checks across the system stay consistent.
"""

from enum import Enum


class Role(str, Enum):
    DATA_ENTRY = "Data entry officer"
    REVIEWER = "Reviewer"
    ADMINISTRATOR = "Administrator"


class Capability(str, Enum):
    ENTER_DATA = "enter_data"            # create/edit drafts, submit, upload
    APPROVE = "approve"                  # approve, return, reject submissions
    ARCHIVE = "archive"                  # archive published records
    MANAGE_REFERENCE = "manage_reference"  # LGAs, communities, sectors, activities
    MANAGE_SCORING = "manage_scoring"    # criteria and weight profiles
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT = "view_audit"


ROLE_CAPABILITIES: dict[Role, set[Capability]] = {
    Role.DATA_ENTRY: {Capability.ENTER_DATA},
    Role.REVIEWER: {Capability.ENTER_DATA, Capability.APPROVE, Capability.MANAGE_SCORING},
    Role.ADMINISTRATOR: set(Capability),
}


def capabilities_for(user) -> set[Capability]:
    if not user or not user.is_authenticated or not user.is_active:
        return set()
    if user.is_superuser:
        return set(Capability)
    caps: set[Capability] = set()
    names = set(user.groups.values_list("name", flat=True))
    for role in Role:
        if role.value in names:
            caps |= ROLE_CAPABILITIES[role]
    return caps


def has_capability(user, capability: Capability) -> bool:
    return capability in capabilities_for(user)
