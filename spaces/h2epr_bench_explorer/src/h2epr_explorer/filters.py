from __future__ import annotations

import math
import re
from typing import Any, Iterable

from .constants import EVENT_ID_MAX, EVENT_ID_MIN, EVENT_ID_PATTERN


NAME_FIELDS = ("display_name", "title")
DESCRIPTION_FIELDS = ("event_descriptor",)
SEARCH_FIELDS = (
    "event_id",
    "public_event_id",
    "title",
    "display_name",
    "event_descriptor",
    "domain",
    "category",
    "keywords",
)


def _text_value(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return " ".join(str(item) for item in value)
    if value is None:
        return ""
    try:
        if value != value:
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _require_current_event_id(row: dict[str, Any]) -> None:
    event_id = _text_value(row.get("event_id")).strip()
    if not re.fullmatch(EVENT_ID_PATTERN, event_id):
        raise ValueError(f"Catalog filter received a non-canonical event ID: {event_id!r}")
    number = int(event_id.rsplit("-", 1)[1])
    if not EVENT_ID_MIN <= number <= EVENT_ID_MAX:
        raise ValueError(f"Catalog filter received an out-of-range event ID: {event_id}")


def event_name(row: dict[str, Any]) -> str:
    for field in NAME_FIELDS:
        value = _text_value(row.get(field)).strip()
        if value:
            return value
    return _text_value(row.get("event_id")).strip() or "Unnamed event"


def event_description(row: dict[str, Any]) -> str:
    for field in DESCRIPTION_FIELDS:
        value = _text_value(row.get(field)).strip()
        if value:
            return value
    return ""


def event_display_label(row: dict[str, Any]) -> str:
    event_id = _text_value(row.get("event_id")).strip()
    name = event_name(row)
    return f"{event_id} · {name}" if event_id else name


def _contains_query(row: dict[str, Any], query: str) -> bool:
    if not query:
        return True
    needle = query.casefold()
    return any(needle in _text_value(row.get(field)).casefold() for field in SEARCH_FIELDS)


def filter_catalog(
    rows: Iterable[dict[str, Any]],
    *,
    query: str = "",
    domains: list[str] | None = None,
    categories: list[str] | None = None,
    min_stage_count: int = 0,
) -> list[dict[str, Any]]:
    domain_set = set(domains or [])
    category_set = set(categories or [])
    filtered: list[dict[str, Any]] = []
    for row in rows:
        _require_current_event_id(row)
        if domain_set and row.get("domain") not in domain_set:
            continue
        if category_set and row.get("category") not in category_set:
            continue
        stage_count = _optional_int(row.get("stage_count"))
        if min_stage_count > 0 and (stage_count is None or stage_count < min_stage_count):
            continue
        if not _contains_query(row, query.strip()):
            continue
        filtered.append(row)
    return filtered
