from django.db.models import Count, Q
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.permissions import require
from apps.accounts.roles import Capability
from apps.api.mixins import AuditedModelMixin

from . import serializers as s
from .models import LGA, Activity, Community, Sector


# ---------- public (read-only, active records only) ----------
class PublicLGAViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = s.PublicLGASerializer
    lookup_field = "slug"
    pagination_class = None  # only 8 LGAs
    search_fields = ["name"]

    def get_queryset(self):
        return LGA.objects.active().annotate(
            community_count=Count("communities", filter=Q(communities__is_active=True))
        ).order_by("name")  # Meta.ordering is not applied to aggregate queries


class PublicCommunityViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = s.PublicCommunitySerializer
    lookup_field = "slug"
    filterset_fields = {"lga__slug": ["exact"], "is_survey_community": ["exact"]}
    search_fields = ["name", "lga__name"]
    ordering_fields = ["name", "lga__name"]

    def get_queryset(self):
        return Community.objects.active().filter(lga__is_active=True).select_related("lga")

    @action(detail=False, url_path="geojson", pagination_class=None)
    def geojson(self, request):
        """Communities with GPS points, as a GeoJSON FeatureCollection for the map."""
        qs = self.filter_queryset(self.get_queryset()).exclude(location__isnull=True)
        features = [{
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [c.location.x, c.location.y]},
            "properties": {"id": c.id, "name": c.name, "slug": c.slug, "lga": c.lga.name, "layer": "community"},
        } for c in qs]
        return Response({"type": "FeatureCollection", "features": features})


class PublicSectorViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = s.PublicSectorSerializer
    lookup_field = "slug"
    pagination_class = None

    def get_queryset(self):
        return Sector.objects.active()


class PublicActivityViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = s.PublicActivitySerializer
    lookup_field = "slug"
    pagination_class = None
    filterset_fields = {"sector__slug": ["exact"]}

    def get_queryset(self):
        return Activity.objects.active().select_related("sector")


# ---------- admin (create / read / update; no hard delete – deactivate instead) ----------
class _AdminReferenceViewSet(AuditedModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin,
                             viewsets.ReadOnlyModelViewSet):
    permission_classes = [require(Capability.MANAGE_REFERENCE)]


class AdminLGAViewSet(_AdminReferenceViewSet):
    queryset = LGA.objects.all()
    serializer_class = s.AdminLGASerializer
    search_fields = ["name"]


class AdminCommunityViewSet(_AdminReferenceViewSet):
    queryset = Community.objects.select_related("lga")
    serializer_class = s.AdminCommunitySerializer
    filterset_fields = ["lga", "is_active", "is_survey_community"]
    search_fields = ["name", "lga__name"]


class AdminSectorViewSet(_AdminReferenceViewSet):
    queryset = Sector.objects.all()
    serializer_class = s.AdminSectorSerializer


class AdminActivityViewSet(_AdminReferenceViewSet):
    queryset = Activity.objects.select_related("sector")
    serializer_class = s.AdminActivitySerializer
    filterset_fields = ["sector", "is_active"]
