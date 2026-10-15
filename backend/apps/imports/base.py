"""
Importer framework.

Each kind of upload (community GPS points now; enterprises, indicator values
and opportunities in later phases) is described by an Importer subclass that
lists its columns. The framework uses that one description to:

  * generate the Excel/CSV template (headers, dropdowns, instructions);
  * check each uploaded row and explain problems in plain language;
  * detect duplicates within the file and against existing records;
  * save valid rows when an authorised user commits the batch.
"""

from __future__ import annotations

import datetime as dt
import difflib
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from apps.accounts.roles import Capability


@dataclass
class Column:
    key: str
    header: str
    required: bool = False
    kind: str = "text"  # text | integer | decimal | date | choice
    help: str = ""
    example: str = ""
    max_length: int | None = None
    min_value: float | None = None
    max_value: float | None = None
    choices: Callable[[], list[str]] | None = None  # evaluated at use time, from the database
    width: int = 22


@dataclass
class RowResult:
    values: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, list[str]] = field(default_factory=dict)
    warnings: dict[str, list[str]] = field(default_factory=dict)
    action: str = "create"
    target: Any = None
    duplicate_key: tuple | None = None

    def error(self, column: str, message: str):
        self.errors.setdefault(column, []).append(message)

    def warn(self, column: str, message: str):
        self.warnings.setdefault(column, []).append(message)


def normalise_header(text: str) -> str:
    """'Latitude *' -> 'latitude'; 'Community name' -> 'community name'."""
    return re.sub(r"\s+", " ", str(text or "").replace("*", "")).strip().lower()


def suggest(value: str, options: list[str]) -> str:
    """'Did you mean …?' hint for a mistyped name, or ''."""
    lowered = {o.lower(): o for o in options}
    match = difflib.get_close_matches(value.lower(), list(lowered), n=1, cutoff=0.6)
    return f" Did you mean '{lowered[match[0]]}'?" if match else ""


class Importer:
    key: str = ""
    label: str = ""
    description: str = ""
    capability: Capability = Capability.ENTER_DATA
    columns: list[Column] = []

    # ---- hooks for subclasses -------------------------------------------
    def prepare(self):
        """Load lookups once per batch (called before checking rows)."""

    def check_row(self, result: RowResult) -> None:
        """Cross-field checks, lookups and duplicate detection. Add errors to `result`."""

    def save_row(self, values: dict, *, user, batch) -> Any:
        """Write one valid row to the real tables; return the saved object."""
        raise NotImplementedError

    def prefill_rows(self) -> list[dict]:
        """Optional rows to pre-fill in the template (e.g. the 24 communities)."""
        return []

    # ---- shared logic ----------------------------------------------------
    def column_map(self) -> dict[str, Column]:
        return {c.key: c for c in self.columns}

    def match_headers(self, headers: list[str]) -> tuple[dict[int, str], list[str], list[str]]:
        """Map file column positions to column keys.

        Returns (position -> key, missing required headers, unknown headers).
        Accepts the template header text or the internal key, in any case.
        """
        lookup = {}
        for c in self.columns:
            lookup[normalise_header(c.header)] = c.key
            lookup[normalise_header(c.key.replace("_", " "))] = c.key
            lookup[normalise_header(c.key)] = c.key
        mapping, unknown = {}, []
        for pos, h in enumerate(headers):
            if not str(h or "").strip():
                continue
            key = lookup.get(normalise_header(h))
            if key and key not in mapping.values():
                mapping[pos] = key
            else:
                unknown.append(str(h))
        found = set(mapping.values())
        missing = [c.header for c in self.columns if c.required and c.key not in found]
        return mapping, missing, unknown

    def clean_row(self, raw: dict[str, Any]) -> RowResult:
        result = RowResult()
        for col in self.columns:
            value = raw.get(col.key)
            if isinstance(value, str):
                value = value.strip()
            if value in (None, ""):
                if col.required:
                    result.error(col.key, f"{col.header} is required.")
                result.values[col.key] = None
                continue
            try:
                result.values[col.key] = self._convert(col, value)
            except ValueError as e:
                result.error(col.key, str(e))
                result.values[col.key] = None
        # Run lookups even when basic checks failed, so the user sees every problem at once.
        self.check_row(result)
        return result

    def _convert(self, col: Column, value: Any) -> Any:
        if col.kind == "text":
            text = str(value).strip()
            if isinstance(value, float) and value.is_integer():
                text = str(int(value))  # Excel turns 0803... phone numbers into floats
            if col.max_length and len(text) > col.max_length:
                raise ValueError(f"{col.header} is too long (maximum {col.max_length} characters).")
            return text
        if col.kind in ("decimal", "integer"):
            try:
                number = Decimal(str(value).replace(",", "").strip())
            except InvalidOperation:
                raise ValueError(f"{col.header} must be a number (got '{value}').")
            if col.kind == "integer":
                if number != number.to_integral_value():
                    raise ValueError(f"{col.header} must be a whole number (got '{value}').")
                number = int(number)
            if col.min_value is not None and number < Decimal(str(col.min_value)):
                raise ValueError(f"{col.header} must be at least {col.min_value} (got {value}).")
            if col.max_value is not None and number > Decimal(str(col.max_value)):
                raise ValueError(f"{col.header} must be at most {col.max_value} (got {value}).")
            return float(number) if col.kind == "decimal" else number
        if col.kind == "date":
            if isinstance(value, dt.datetime):
                return value.date().isoformat()
            if isinstance(value, dt.date):
                return value.isoformat()
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
                try:
                    return dt.datetime.strptime(str(value).strip(), fmt).date().isoformat()
                except ValueError:
                    pass
            raise ValueError(f"{col.header} must be a date like 2026-03-31 or 31/03/2026 (got '{value}').")
        if col.kind == "choice":
            options = col.choices() if col.choices else []
            lowered = {o.lower(): o for o in options}
            text = str(value).strip()
            if text.lower() in lowered:
                return lowered[text.lower()]
            raise ValueError(f"'{text}' is not a recognised {col.header}.{suggest(text, options)}")
        raise ValueError(f"Unsupported column type {col.kind}")


REGISTRY: dict[str, Importer] = {}


def register(cls):
    REGISTRY[cls.key] = cls()
    return cls


def get_importer(key: str) -> Importer | None:
    return REGISTRY.get(key)
