from rest_framework import mixins, serializers, viewsets

from apps.accounts.permissions import require
from apps.accounts.roles import Capability
from apps.api.mixins import AuditedModelMixin

from .models import DataSource


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = ["id", "name", "organisation", "responsible_person", "description", "url",
                  "collection_start", "collection_end", "created_at", "updated_at"]

    def validate(self, attrs):
        start = attrs.get("collection_start", getattr(self.instance, "collection_start", None))
        end = attrs.get("collection_end", getattr(self.instance, "collection_end", None))
        if start and end and end < start:
            raise serializers.ValidationError({"collection_end": "End date is before start date."})
        return attrs


class DataSourceViewSet(AuditedModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin,
                        viewsets.ReadOnlyModelViewSet):
    permission_classes = [require(Capability.ENTER_DATA)]
    serializer_class = DataSourceSerializer
    queryset = DataSource.objects.all()
    search_fields = ["name", "organisation"]
