from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models


class AuditLog(models.Model):
    """Append-only record of important administrative actions."""

    class Action(models.TextChoices):
        LOGIN = "login", "Logged in"
        LOGIN_FAILED = "login_failed", "Failed login"
        LOGOUT = "logout", "Logged out"
        CREATE = "create", "Created"
        UPDATE = "update", "Updated"
        SUBMIT = "submit", "Submitted for approval"
        APPROVE = "approve", "Approved"
        RETURN = "return", "Returned for correction"
        REJECT = "reject", "Rejected"
        ARCHIVE = "archive", "Archived"
        DELETE = "delete", "Deleted"
        IMPORT = "import", "Bulk import"
        EXPORT = "export", "Export"
        ROLE_CHANGE = "role_change", "Role changed"
        SETTINGS_CHANGE = "settings_change", "Settings changed"

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    actor_label = models.CharField(max_length=200, blank=True, help_text="Username kept even if the user is removed")
    action = models.CharField(max_length=30, choices=Action.choices, db_index=True)
    target_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL)
    target_id = models.CharField(max_length=64, blank=True)
    target_label = models.CharField(max_length=300, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["target_type", "target_id"])]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.actor_label} {self.action} {self.target_label}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Audit log entries cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit log entries cannot be deleted.")
