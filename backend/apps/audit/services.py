from django.contrib.contenttypes.models import ContentType

from .models import AuditLog


def client_ip(request):
    if request is None:
        return None
    # Nginx sets X-Real-IP; fall back to the socket address.
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")


def log(action, *, actor=None, target=None, details=None, request=None, actor_label=None):
    """Write one audit entry. `target` is any model instance (optional)."""
    if actor is not None and not getattr(actor, "is_authenticated", False):
        actor = None
    entry = AuditLog(
        action=action,
        actor=actor,
        actor_label=actor_label or (actor.get_username() if actor else ""),
        details=details or {},
        ip_address=client_ip(request),
    )
    if target is not None:
        entry.target_type = ContentType.objects.get_for_model(target)
        entry.target_id = str(target.pk)
        entry.target_label = str(target)[:300]
    entry.save()
    return entry
