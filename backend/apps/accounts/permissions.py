from rest_framework.permissions import BasePermission

from .roles import Capability, has_capability


def require(capability: Capability):
    """DRF permission class factory: `permission_classes = [require(Capability.APPROVE)]`."""

    class _Require(BasePermission):
        message = "You do not have permission to perform this action."

        def has_permission(self, request, view):
            return has_capability(request.user, capability)

    _Require.__name__ = f"Require_{capability.value}"
    return _Require
