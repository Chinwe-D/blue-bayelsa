"""
Upload → check → review/correct → import.

    stage_upload()   read the file, check every row, store results (nothing imported yet)
    correct_row()    replace a row's values with the user's corrections and re-check
    skip_row()       leave a row out of the import
    commit_batch()   import every row that is ready; record who did it
    cancel_batch()   abandon the upload
"""

from django.db import transaction
from django.utils import timezone

from apps.accounts.roles import has_capability
from apps.audit.models import AuditLog
from apps.audit.services import log

from .base import Importer
from .models import ImportBatch, ImportRow
from .parsing import FileRejected, read_table


class BatchError(Exception):
    """Raised for user-facing problems with a batch action."""


def _jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _check_all(importer: Importer, batch: ImportBatch):
    """(Re)check every pending row, including duplicates inside the file."""
    importer.prepare()
    seen: dict[tuple, int] = {}
    rows = list(batch.rows.exclude(status__in=[ImportRow.Status.SKIPPED, ImportRow.Status.IMPORTED]))
    for row in rows:
        result = importer.clean_row(row.raw)
        duplicate_of = None
        if result.duplicate_key and not result.errors:
            if result.duplicate_key in seen:
                duplicate_of = seen[result.duplicate_key]
                result.error("_row", f"Same record as row {duplicate_of}. Remove one of them or skip this row.")
            else:
                seen[result.duplicate_key] = row.row_number
        row.values = {k: _jsonable(v) for k, v in result.values.items()}
        row.errors = result.errors
        row.warnings = result.warnings
        row.action = result.action
        row.target_id = str(result.target.pk) if result.target is not None else ""
        if duplicate_of is not None:
            row.status = ImportRow.Status.DUPLICATE
        else:
            row.status = ImportRow.Status.ERROR if result.errors else ImportRow.Status.VALID
    ImportRow.objects.bulk_update(rows, ["values", "errors", "warnings", "action", "target_id", "status"])


@transaction.atomic
def stage_upload(importer: Importer, uploaded_file, *, user, data_source=None, request=None) -> ImportBatch:
    if not has_capability(user, importer.capability):
        raise BatchError("You do not have permission to upload this kind of data.")
    try:
        headers, data = read_table(uploaded_file)
    except FileRejected as e:
        raise BatchError(str(e))
    mapping, missing, unknown = importer.match_headers(headers)
    if missing:
        raise BatchError(
            "These required columns are missing: " + ", ".join(missing)
            + ". Please download the template and copy your data into it."
        )
    uploaded_file.seek(0)
    batch = ImportBatch.objects.create(
        importer=importer.key, original_filename=uploaded_file.name[:255], file=uploaded_file,
        data_source=data_source, uploaded_by=user,
        file_warnings=[f"Column '{h}' is not part of the template and was ignored." for h in unknown],
    )
    ImportRow.objects.bulk_create([
        ImportRow(batch=batch, row_number=n, status=ImportRow.Status.ERROR,
                  raw={key: _jsonable(cells[pos]) if pos < len(cells) else None for pos, key in mapping.items()})
        for n, cells in data
    ])
    _check_all(importer, batch)
    log(AuditLog.Action.CREATE, actor=user, target=batch, request=request,
        details={"stage": "uploaded", "importer": importer.key, **batch.counts()})
    return batch


def _pending(batch: ImportBatch):
    if batch.status != ImportBatch.Status.VALIDATED:
        raise BatchError("This upload has already been imported or cancelled.")


@transaction.atomic
def correct_row(importer: Importer, row: ImportRow, new_raw: dict, *, user) -> ImportRow:
    _pending(row.batch)
    if row.status == ImportRow.Status.IMPORTED:
        raise BatchError("This row has already been imported.")
    allowed = {c.key for c in importer.columns}
    row.raw = {**row.raw, **{k: _jsonable(v) for k, v in new_raw.items() if k in allowed}}
    row.corrected = True
    if row.status == ImportRow.Status.SKIPPED:
        row.status = ImportRow.Status.ERROR  # bring it back into checking
    row.save(update_fields=["raw", "corrected", "status"])
    _check_all(importer, row.batch)  # re-check all: a correction can create or clear a duplicate
    row.refresh_from_db()
    return row


@transaction.atomic
def skip_row(importer: Importer, row: ImportRow, *, user, skip=True) -> ImportRow:
    _pending(row.batch)
    if row.status == ImportRow.Status.IMPORTED:
        raise BatchError("This row has already been imported.")
    row.status = ImportRow.Status.SKIPPED if skip else ImportRow.Status.ERROR
    row.save(update_fields=["status"])
    _check_all(importer, row.batch)
    row.refresh_from_db()
    return row


@transaction.atomic
def commit_batch(importer: Importer, batch: ImportBatch, *, user, skip_problem_rows=False, request=None):
    batch = ImportBatch.objects.select_for_update().get(pk=batch.pk)
    _pending(batch)
    if not has_capability(user, importer.capability):
        raise BatchError("You do not have permission to import this kind of data.")
    _check_all(importer, batch)  # data may have changed since upload
    counts = batch.counts()
    problems = counts[ImportRow.Status.ERROR] + counts[ImportRow.Status.DUPLICATE]
    if problems and not skip_problem_rows:
        raise BatchError(
            f"{problems} row(s) still have problems. Correct them, or confirm that they should be left out."
        )
    if counts[ImportRow.Status.VALID] == 0:
        raise BatchError("There are no rows ready to import.")

    importer.prepare()
    imported = 0
    for row in batch.rows.filter(status=ImportRow.Status.VALID):
        result = importer.clean_row(row.raw)
        obj = importer.save_row(result.values, user=user, batch=batch)
        row.status, row.target_id = ImportRow.Status.IMPORTED, str(obj.pk)
        row.save(update_fields=["status", "target_id"])
        imported += 1
    batch.rows.filter(status__in=[ImportRow.Status.ERROR, ImportRow.Status.DUPLICATE]).update(
        status=ImportRow.Status.SKIPPED)
    batch.status = ImportBatch.Status.COMMITTED
    batch.committed_by, batch.committed_at = user, timezone.now()
    batch.save(update_fields=["status", "committed_by", "committed_at"])
    log(AuditLog.Action.IMPORT, actor=user, target=batch, request=request,
        details={"importer": importer.key, "imported": imported, "left_out": problems,
                 "file": batch.original_filename})
    return batch


def cancel_batch(batch: ImportBatch, *, user, request=None):
    _pending(batch)
    batch.status = ImportBatch.Status.CANCELLED
    batch.save(update_fields=["status"])
    log(AuditLog.Action.UPDATE, actor=user, target=batch, request=request, details={"stage": "cancelled"})
    return batch
