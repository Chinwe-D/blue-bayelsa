"""
Bulk upload staging.

An uploaded file becomes an ImportBatch. Each data row becomes an ImportRow
holding the raw values exactly as typed, the cleaned values, and any errors.
Nothing touches the real tables until an authorised user commits the batch,
so administrators can preview, correct and re-check rows first. Batches are
kept afterwards, so every imported record can be traced to its source file.
"""

import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models

from apps.governance.models import DataSource

private_storage = FileSystemStorage(location=settings.PRIVATE_UPLOAD_ROOT)


class ImportBatch(models.Model):
    class Status(models.TextChoices):
        VALIDATED = "validated", "Checked – waiting for review"
        COMMITTED = "committed", "Imported"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    importer = models.CharField(max_length=50)
    original_filename = models.CharField(max_length=255)
    file = models.FileField(storage=private_storage, upload_to="imports/%Y/%m/")
    data_source = models.ForeignKey(DataSource, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.VALIDATED)
    file_warnings = models.JSONField(default=list, blank=True)

    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    committed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name="+")
    committed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name_plural = "import batches"

    def __str__(self):
        return f"{self.original_filename} ({self.importer})"

    def counts(self) -> dict:
        out = {s: 0 for s in ImportRow.Status.values}
        for row in self.rows.values("status").annotate(n=models.Count("id")):
            out[row["status"]] = row["n"]
        out["total"] = sum(out[s] for s in ImportRow.Status.values)
        return out


class ImportRow(models.Model):
    class Status(models.TextChoices):
        VALID = "valid", "Ready to import"
        ERROR = "error", "Has errors"
        DUPLICATE = "duplicate", "Duplicate"
        SKIPPED = "skipped", "Skipped"
        IMPORTED = "imported", "Imported"

    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="rows")
    row_number = models.PositiveIntegerField(help_text="Row number as shown in Excel (header is row 1).")
    raw = models.JSONField(help_text="Values exactly as uploaded or corrected, keyed by column.")
    values = models.JSONField(default=dict, blank=True, help_text="Cleaned values ready to save.")
    errors = models.JSONField(default=dict, blank=True, help_text="{column: [messages]}; '_row' for whole-row errors.")
    warnings = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, db_index=True)
    action = models.CharField(max_length=10, blank=True, help_text="create or update")
    target_id = models.CharField(max_length=64, blank=True, help_text="ID of the record created or updated.")
    corrected = models.BooleanField(default=False)

    class Meta:
        ordering = ["row_number"]
        constraints = [models.UniqueConstraint(fields=["batch", "row_number"], name="unique_row_per_batch")]

    def __str__(self):
        return f"Row {self.row_number} ({self.status})"
