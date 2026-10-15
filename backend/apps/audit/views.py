from rest_framework import serializers, viewsets

from apps.accounts.permissions import require
from apps.accounts.roles import Capability

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source="get_action_display", read_only=True)
    target_type = serializers.SlugRelatedField(slug_field="model", read_only=True)

    class Meta:
        model = AuditLog
        fields = ["id", "timestamp", "actor_label", "action", "action_label", "target_type",
                  "target_id", "target_label", "details", "ip_address"]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [require(Capability.VIEW_AUDIT)]
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.select_related("target_type")
    filterset_fields = {"action": ["exact"], "actor_label": ["exact"], "timestamp": ["gte", "lte"]}
    search_fields = ["actor_label", "target_label"]
