"""
Two sets of serializers:
  * Public*  – only fields safe for anyone to see.
  * Admin*   – full fields, for authenticated staff.
Keeping them separate means a field added for staff is never exposed
publicly by accident.
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import LGA, Activity, Community, Sector


class LatLonSchema(serializers.Serializer):
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()


def point_to_dict(point):
    return None if point is None else {"latitude": point.y, "longitude": point.x}


# ---------- public ----------
class PublicLGASerializer(serializers.ModelSerializer):
    community_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = LGA
        fields = ["id", "name", "slug", "community_count"]


class PublicCommunitySerializer(serializers.ModelSerializer):
    lga = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    lga_name = serializers.CharField(source="lga.name", read_only=True)
    location = serializers.SerializerMethodField()

    class Meta:
        model = Community
        fields = ["id", "name", "slug", "lga", "lga_name", "location", "description", "is_survey_community"]

    @extend_schema_field(LatLonSchema(allow_null=True))
    def get_location(self, obj):
        return point_to_dict(obj.location)


class PublicSectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ["id", "name", "slug", "description", "icon"]


class PublicActivitySerializer(serializers.ModelSerializer):
    sector = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = Activity
        fields = ["id", "name", "slug", "sector", "description"]


# ---------- admin ----------
@extend_schema_field(LatLonSchema(allow_null=True))
class LatLonField(serializers.Field):
    """Accepts/returns {"latitude": .., "longitude": ..} – friendlier than WKT for forms."""

    def to_representation(self, value):
        return point_to_dict(value)

    def to_internal_value(self, data):
        from django.contrib.gis.geos import Point
        from django.core.exceptions import ValidationError as DjangoValidationError

        from apps.governance.validators import validate_point_in_bounds

        if data in (None, ""):
            return None
        try:
            lat, lon = float(data["latitude"]), float(data["longitude"])
        except (TypeError, KeyError, ValueError):
            raise serializers.ValidationError("Give latitude and longitude as numbers.")
        point = Point(lon, lat, srid=4326)
        try:
            validate_point_in_bounds(point)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return point


class AdminLGASerializer(serializers.ModelSerializer):
    class Meta:
        model = LGA
        fields = ["id", "name", "slug", "boundary_source", "is_active", "created_at", "updated_at"]


class AdminCommunitySerializer(serializers.ModelSerializer):
    location = LatLonField(required=False, allow_null=True)

    class Meta:
        model = Community
        fields = ["id", "lga", "name", "slug", "location", "location_source", "description",
                  "is_survey_community", "is_active", "created_at", "updated_at"]


class AdminSectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ["id", "name", "slug", "description", "icon", "display_order", "is_active"]


class AdminActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ["id", "name", "slug", "sector", "description", "display_order", "is_active"]
