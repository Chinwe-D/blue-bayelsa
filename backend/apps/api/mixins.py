from apps.audit.models import AuditLog
from apps.audit.services import log


class AuditedModelMixin:
    """Write an audit entry for every create and update made through the admin API."""

    def perform_create(self, serializer):
        obj = serializer.save()
        log(AuditLog.Action.CREATE, actor=self.request.user, target=obj, request=self.request,
            details={"fields": sorted(serializer.validated_data)})

    def perform_update(self, serializer):
        obj = serializer.save()
        log(AuditLog.Action.UPDATE, actor=self.request.user, target=obj, request=self.request,
            details={"fields": sorted(serializer.validated_data)})
