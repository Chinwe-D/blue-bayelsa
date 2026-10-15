"""
Reference data: Local Government Areas, communities, sectors and activities.

These are managed by administrators in the database, never hard-coded in
application logic. Initial values come from the project documents and are
loaded by a data migration (0002_seed_reference_data).
"""

from django.contrib.gis.db import models
from simple_history.models import HistoricalRecords

from apps.governance.validators import validate_point_in_bounds


class ActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class LGA(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    boundary = models.MultiPolygonField(srid=4326, null=True, blank=True)
    boundary_source = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActiveQuerySet.as_manager()
    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]
        verbose_name = "Local Government Area"

    def __str__(self):
        return self.name


class Community(models.Model):
    lga = models.ForeignKey(LGA, on_delete=models.PROTECT, related_name="communities")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True)
    location = models.PointField(srid=4326, null=True, blank=True, validators=[validate_point_in_bounds],
                                 help_text="GPS point (WGS84). Longitude = x, latitude = y.")
    location_source = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    is_survey_community = models.BooleanField(
        default=True, help_text="One of the communities selected for the Blue-Bayelsa survey."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActiveQuerySet.as_manager()
    history = HistoricalRecords()

    class Meta:
        ordering = ["lga__name", "name"]
        verbose_name_plural = "communities"
        constraints = [models.UniqueConstraint(fields=["lga", "name"], name="unique_community_per_lga")]

    def __str__(self):
        return f"{self.name} ({self.lga.name})"


class Sector(models.Model):
    """Blue-economy sector. The project documents refer to eight sectors that
    are not yet defined, so none are seeded."""

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon name used on sector cards.")
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    objects = ActiveQuerySet.as_manager()
    history = HistoricalRecords()

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class Activity(models.Model):
    """Blue-economy activity, as listed in the survey documents."""

    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    sector = models.ForeignKey(Sector, null=True, blank=True, on_delete=models.SET_NULL, related_name="activities")
    description = models.TextField(blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    objects = ActiveQuerySet.as_manager()
    history = HistoricalRecords()

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "activities"

    def __str__(self):
        return self.name
