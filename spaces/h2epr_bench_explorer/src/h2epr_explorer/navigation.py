from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from .constants import (
    DRAFT_EPG_PATH_TEMPLATE,
    EVENT_ID_MAX,
    EVENT_ID_MIN,
    EVENT_ID_PATTERN,
    GOLD_COMPANION_REPO,
    PUBLIC_DATASET_REPO,
    PUBLIC_DATASET_REVISION,
)


SPACE_URL = "https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer"
PUBLIC_DATASET_URL = f"https://huggingface.co/datasets/{PUBLIC_DATASET_REPO}"
GOLD_COMPANION_URL = f"https://huggingface.co/datasets/{GOLD_COMPANION_REPO}"
LEGACY_EVENT_ID_PATTERN = r"^P1000-([0-9]{4})$"


@dataclass(frozen=True)
class QueryEventResolution:
    raw_value: str
    canonical_id: str
    used_legacy_mapping: bool = False

    @property
    def unresolved(self) -> bool:
        return bool(self.raw_value) and not self.canonical_id


def _first_value(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return str(value[0]).strip() if value else ""
    return str(value or "").strip()


def _canonical_id(value: str) -> str:
    if not re.fullmatch(EVENT_ID_PATTERN, value):
        return ""
    number = int(value.rsplit("-", 1)[1])
    return value if EVENT_ID_MIN <= number <= EVENT_ID_MAX else ""


def normalize_query_event_id(value: Any) -> QueryEventResolution:
    """Normalize only inbound navigation IDs; all returned IDs are canonical."""

    raw_value = _first_value(value)
    canonical = _canonical_id(raw_value)
    if canonical:
        return QueryEventResolution(raw_value, canonical)

    match = re.fullmatch(LEGACY_EVENT_ID_PATTERN, raw_value)
    if not match:
        return QueryEventResolution(raw_value, "")
    legacy_number = int(match.group(1))
    if not 1 <= legacy_number <= 1000:
        return QueryEventResolution(raw_value, "")
    if legacy_number <= 359:
        canonical_number = legacy_number
    elif legacy_number == 360:
        canonical_number = 87
    else:
        canonical_number = legacy_number - 1
    return QueryEventResolution(
        raw_value,
        f"H2EPR-{canonical_number:04d}",
        used_legacy_mapping=True,
    )


def query_param_event_id(query_params: Mapping[str, Any]) -> QueryEventResolution:
    return normalize_query_event_id(query_params.get("event_id"))


def resolve_selected_event_index(rows: list[dict[str, Any]], requested_event_id: str = "") -> int:
    if not rows:
        return 0
    if requested_event_id:
        for index, row in enumerate(rows):
            if str(row.get("event_id", "")).strip() == requested_event_id:
                return index
    return 0


class ImmutableDatasetLinkUnavailable(RuntimeError):
    """A content link cannot be built until the published revision is known."""


def build_immutable_dataset_link(path: str | None = None) -> str:
    if not PUBLIC_DATASET_REVISION:
        raise ImmutableDatasetLinkUnavailable(
            "No immutable public dataset revision is assigned to this release candidate"
        )
    if path is None:
        return f"{PUBLIC_DATASET_URL}/tree/{PUBLIC_DATASET_REVISION}"
    normalized = path.strip("/")
    if not normalized or ".." in normalized.split("/"):
        raise ValueError(f"Invalid public dataset path: {path!r}")
    return f"{PUBLIC_DATASET_URL}/blob/{PUBLIC_DATASET_REVISION}/{normalized}"


def build_event_links(event_id: str) -> dict[str, str]:
    canonical = _canonical_id(event_id.strip())
    if not canonical:
        raise ValueError(f"Cannot build current-release links for event ID: {event_id!r}")
    links = {
        "explorer": f"{SPACE_URL}?event_id={canonical}",
        "public_dataset": PUBLIC_DATASET_URL,
        "reference_access": GOLD_COMPANION_URL,
    }
    if PUBLIC_DATASET_REVISION:
        links["public_dataset"] = build_immutable_dataset_link()
        draft_path = DRAFT_EPG_PATH_TEMPLATE.format(event_id=canonical)
        links["draft_epg"] = build_immutable_dataset_link(draft_path)
    return links


def filter_summary_text(filtered_count: int, total_count: int) -> str:
    return f"Showing {filtered_count:,} of {total_count:,} events"
