"""
Data governance building blocks shared by every record that is published.

`GovernedModel` is an abstract base class. Enterprises, indicator values,
investment opportunities, infrastructure and map locations will inherit
from it in Phase 3, which gives each of them the same provenance fields
and the same Draft -> Submitted -> Approved publication workflow.
"""

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Status(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted for approval"
    RETURNED = "returned", "Returned for correction"
    APPROVED = "approved", "Approved and published"
    REJECTED = "rejected", "Rejected"
    ARCHIVED = "archived", "Archived"


class VerificationStatus(models.TextChoices):
    UNVERIFIED = "unverified", "Not yet verified"
    VERIFIED = "verified", "Verified"
    DISPUTED = "disputed", "Disputed"


class DataSource(models.Model):
    """Where data came from: a survey round, an agency report, a field visit."""

    name = models.CharField(max_length=200, unique=True)
    organisation = models.CharField(max_length=200, blank=True)
    responsible_person = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)
    collection_start = models.DateField(null=True, blank=True)
    collection_end = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PublishedQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Status.APPROVED)


class GovernedModel(models.Model):
    """Abstract base: provenance + approval workflow fields."""

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    verification_status = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.UNVERIFIED
    )
    data_source = models.ForeignKey(DataSource, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    date_collected = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    archived_reason = models.TextField(blank=True)

    objects = PublishedQuerySet.as_manager()

    class Meta:
        abstract = True

    @property
    def is_published(self) -> bool:
        return self.status == Status.APPROVED


class ApprovalRecord(models.Model):
    """One entry per workflow transition, for any governed record."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64)
    action = models.CharField(max_length=20)
    from_status = models.CharField(max_length=20, choices=Status.choices)
    to_status = models.CharField(max_length=20, choices=Status.choices)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    comment = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self):
        return f"{self.action}: {self.from_status} -> {self.to_status}"
