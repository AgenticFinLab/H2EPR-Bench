from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from huggingface_hub import hf_hub_download
from huggingface_hub.errors import EntryNotFoundError
import pandas as pd
import pyarrow.parquet as parquet

from .constants import (
    ARROW_BOOL_COLUMNS,
    ARROW_INT64_COLUMNS,
    CATALOG_PARQUET,
    CATALOG_SCHEMA,
    DRAFT_AVAILABILITY_PARQUET,
    DRAFT_AVAILABILITY_SCHEMA,
    DRAFT_EPG_PATH_TEMPLATE,
    DRAFT_UNAVAILABLE_MESSAGE,
    EVENT_ID_MAX,
    EVENT_ID_MIN,
    EVENT_ID_PATTERN,
    EVENT_INSTANCES_PARQUET,
    EVENT_INSTANCES_SCHEMA,
    EXPECTED_AVAILABLE_DRAFT_COUNT,
    EXPECTED_EVENT_COUNT,
    EXPECTED_STAGE_ROW_COUNT,
    EXPECTED_UNAVAILABLE_DRAFT_COUNT,
    FINALCASCADE_SUMMARY_PARQUET,
    FINALCASCADE_SUMMARY_SCHEMA,
    GRAPH_COUNT_COLUMNS,
    LOCAL_DATASET_ENV,
    PUBLIC_DATASET_REPO,
    PUBLIC_DATASET_REVISION,
    STAGES_PARQUET,
    STAGES_SCHEMA,
)


class ExplorerDataError(RuntimeError):
    """Base error for public Explorer data access."""


class DatasetTransportError(ExplorerDataError):
    """A pinned public dataset asset could not be retrieved."""


class ReleaseContractError(ExplorerDataError):
    """The loaded files do not form the expected Unified-3000 release."""


class DraftAssetMissing(ExplorerDataError):
    """An available event is missing its required direct Draft EPG file."""


class DraftIntegrityError(ExplorerDataError):
    """A direct Draft EPG failed identity or digest validation."""


class InvalidEventId(ValueError):
    """An identifier is not a canonical Unified-3000 event ID."""


@dataclass(frozen=True)
class DraftUnavailable:
    event_id: str
    message: str = DRAFT_UNAVAILABLE_MESSAGE


@dataclass
class ExplorerRelease:
    events: pd.DataFrame
    stages: pd.DataFrame
    stages_by_event: dict[str, pd.DataFrame]
    revision: str = PUBLIC_DATASET_REVISION

    def event_row(self, event_id: str) -> pd.Series:
        validate_event_id(event_id)
        rows = self.events.loc[self.events["event_id"].eq(event_id)]
        if rows.empty:
            raise InvalidEventId(f"Unknown Unified-3000 event ID: {event_id}")
        if len(rows) != 1:
            raise ReleaseContractError(f"Duplicate event identity in joined view: {event_id}")
        return rows.iloc[0]

    def stage_frame(self, event_id: str) -> pd.DataFrame:
        self.event_row(event_id)
        frame = self.stages_by_event.get(event_id)
        if frame is None:
            return self.stages.iloc[0:0].copy()
        return frame.copy()


def _as_local_root(local_dataset_dir: Path | str | None = None) -> Path | None:
    value = local_dataset_dir or os.environ.get(LOCAL_DATASET_ENV)
    if not value:
        return None
    return Path(value).expanduser().resolve()


def validate_event_id(event_id: str) -> str:
    if not isinstance(event_id, str) or not re.fullmatch(EVENT_ID_PATTERN, event_id):
        raise InvalidEventId(f"Invalid Unified-3000 event ID: {event_id!r}")
    number = int(event_id.rsplit("-", 1)[1])
    if not EVENT_ID_MIN <= number <= EVENT_ID_MAX:
        raise InvalidEventId(f"Unified-3000 event ID is out of range: {event_id}")
    return event_id


def resolve_dataset_file(filename: str, local_dataset_dir: Path | str | None = None) -> Path:
    local_root = _as_local_root(local_dataset_dir)
    if local_root is not None:
        path = (local_root / filename).resolve()
        if not path.is_relative_to(local_root):
            raise ValueError(f"Refusing to read outside local dataset root: {filename}")
        if not path.is_file():
            raise FileNotFoundError(path)
        return path

    try:
        return Path(
            hf_hub_download(
                repo_id=PUBLIC_DATASET_REPO,
                repo_type="dataset",
                filename=filename,
                revision=PUBLIC_DATASET_REVISION,
            )
        )
    except EntryNotFoundError as exc:
        raise FileNotFoundError(filename) from exc
    except Exception as exc:
        raise DatasetTransportError(
            f"Unable to retrieve {filename!r} from pinned dataset revision "
            f"{PUBLIC_DATASET_REVISION}."
        ) from exc


def _read_required_parquet(
    filename: str,
    expected_schema: tuple[str, ...],
    local_dataset_dir: Path | str | None = None,
) -> pd.DataFrame:
    try:
        path = resolve_dataset_file(filename, local_dataset_dir=local_dataset_dir)
        arrow_schema = parquet.read_schema(path)
        frame = pd.read_parquet(path)
    except DatasetTransportError:
        raise
    except Exception as exc:
        raise ReleaseContractError(f"Unable to read required Parquet table: {filename}") from exc

    observed = tuple(frame.columns)
    observed_arrow = tuple((field.name, str(field.type)) for field in arrow_schema)
    expected_arrow = tuple(
        (
            column,
            "int64"
            if column in ARROW_INT64_COLUMNS
            else "bool"
            if column in ARROW_BOOL_COLUMNS
            else "string",
        )
        for column in expected_schema
    )
    if observed != expected_schema or observed_arrow != expected_arrow:
        raise ReleaseContractError(
            f"Schema mismatch for {filename}: expected {expected_arrow}, observed {observed_arrow}"
        )
    return frame


def _require_row_count(frame: pd.DataFrame, expected: int, table_name: str) -> None:
    if len(frame) != expected:
        raise ReleaseContractError(
            f"{table_name} row count mismatch: expected {expected}, observed {len(frame)}"
        )


def _require_unique(frame: pd.DataFrame, columns: list[str], table_name: str) -> None:
    if frame.duplicated(columns).any():
        raise ReleaseContractError(f"{table_name} has duplicate identity rows for {columns}")


def _require_equal_ids(frame: pd.DataFrame, table_name: str) -> None:
    if not frame["event_id"].equals(frame["public_event_id"]):
        raise ReleaseContractError(f"{table_name} event_id/public_event_id mismatch")


def _require_semantic_equality(
    catalog: pd.DataFrame,
    other: pd.DataFrame,
    columns: tuple[str, ...],
    other_name: str,
) -> None:
    left = catalog.set_index("event_id").sort_index()
    right = other.set_index("event_id").sort_index()
    for column in columns:
        if not left[column].equals(right[column]):
            raise ReleaseContractError(f"{column} disagrees between catalog and {other_name}")


def build_explorer_view(
    catalog: pd.DataFrame,
    instances: pd.DataFrame,
    summary: pd.DataFrame,
    availability: pd.DataFrame,
) -> pd.DataFrame:
    """Build the validated one-row-per-event Unified-3000 Explorer view."""

    for frame, schema, name in (
        (catalog, CATALOG_SCHEMA, "event_catalog"),
        (instances, EVENT_INSTANCES_SCHEMA, "event_instances"),
        (summary, FINALCASCADE_SUMMARY_SCHEMA, "finalcascade_summary"),
        (availability, DRAFT_AVAILABILITY_SCHEMA, "draft_availability"),
    ):
        if tuple(frame.columns) != schema:
            raise ReleaseContractError(f"Schema mismatch for {name}")
        _require_row_count(frame, EXPECTED_EVENT_COUNT, name)

    expected_ids = {f"H2EPR-{index:04d}" for index in range(EVENT_ID_MIN, EVENT_ID_MAX + 1)}
    _require_unique(catalog, ["public_event_id", "event_id"], "event_catalog")
    _require_unique(instances, ["public_event_id", "event_id"], "event_instances")
    _require_unique(summary, ["public_event_id", "event_id"], "finalcascade_summary")
    _require_unique(availability, ["public_event_id"], "draft_availability")
    _require_equal_ids(catalog, "event_catalog")
    _require_equal_ids(instances, "event_instances")
    _require_equal_ids(summary, "finalcascade_summary")
    if set(catalog["event_id"]) != expected_ids:
        raise ReleaseContractError("event_catalog does not contain the exact Unified-3000 ID set")
    if set(instances["event_id"]) != expected_ids or set(summary["event_id"]) != expected_ids:
        raise ReleaseContractError("instance/summary event identity does not match the catalog")
    if set(availability["public_event_id"]) != expected_ids:
        raise ReleaseContractError("availability identity does not match the catalog")

    _require_semantic_equality(
        catalog, instances, ("domain", "category", "draft_status"), "event_instances"
    )
    _require_semantic_equality(
        catalog, summary, ("domain", "category", "draft_status"), "finalcascade_summary"
    )
    catalog_status = catalog.set_index("public_event_id")["draft_status"].sort_index()
    availability_status = availability.set_index("public_event_id")["draft_status"].sort_index()
    if not catalog_status.equals(availability_status):
        raise ReleaseContractError("draft_status disagrees between catalog and availability")

    status_counts = availability["draft_status"].value_counts(dropna=False).to_dict()
    expected_status_counts = {
        "draft_available": EXPECTED_AVAILABLE_DRAFT_COUNT,
        "draft_unavailable": EXPECTED_UNAVAILABLE_DRAFT_COUNT,
    }
    if status_counts != expected_status_counts:
        raise ReleaseContractError(
            f"Draft availability mismatch: expected {expected_status_counts}, observed {status_counts}"
        )

    access_fields = [
        "public_event_id",
        "event_id",
        "has_finalcascade",
        "finalcascade_access_level",
        "gold_reference_access_level",
        "evidence_context_access_level",
    ]
    summary_fields = [
        "event_id",
        *GRAPH_COUNT_COLUMNS,
        "event_start_time",
        "event_end_time",
        "event_boundary_time_status",
        "known_action_time_anchor_count",
        "known_action_time_anchors",
        "relative_order_available",
    ]
    availability_fields = [
        "public_event_id",
        "draft_source_kind",
        "draft_schema",
        "draft_asset",
        "draft_record_index",
        "draft_sha256",
        "source_payload_sha256",
        "has_reference_epg",
    ]

    try:
        joined = catalog.merge(
            instances[access_fields],
            on=["public_event_id", "event_id"],
            how="left",
            validate="one_to_one",
        )
        joined = joined.merge(
            summary[summary_fields], on="event_id", how="left", validate="one_to_one"
        )
        joined = joined.merge(
            availability[availability_fields],
            on="public_event_id",
            how="left",
            validate="one_to_one",
        )
    except Exception as exc:
        raise ReleaseContractError("Unified-3000 Explorer join multiplicity failure") from exc

    _require_row_count(joined, EXPECTED_EVENT_COUNT, "joined Explorer view")
    _require_unique(joined, ["public_event_id", "event_id"], "joined Explorer view")
    if joined[access_fields[2:] + availability_fields[1:]].isna().all(axis=1).any():
        raise ReleaseContractError("Joined Explorer view contains unmatched access/availability rows")

    available = joined["draft_status"].eq("draft_available")
    unavailable = joined["draft_status"].eq("draft_unavailable")
    if joined.loc[available, list(GRAPH_COUNT_COLUMNS)].isna().any().any():
        raise ReleaseContractError("Available drafts have null graph counts")
    if not joined.loc[unavailable, list(GRAPH_COUNT_COLUMNS)].isna().all().all():
        raise ReleaseContractError("Unavailable drafts contain observed graph counts")
    if not joined.loc[available, "has_finalcascade"].eq(True).all():
        raise ReleaseContractError("Available draft rows disagree with has_finalcascade")
    if not joined.loc[unavailable, "has_finalcascade"].eq(False).all():
        raise ReleaseContractError("Unavailable draft rows disagree with has_finalcascade")
    return joined.sort_values("event_id", kind="stable").reset_index(drop=True)


def _validate_stages(stages: pd.DataFrame, events: pd.DataFrame) -> None:
    if tuple(stages.columns) != STAGES_SCHEMA:
        raise ReleaseContractError("Schema mismatch for event_stages")
    _require_row_count(stages, EXPECTED_STAGE_ROW_COUNT, "event_stages")
    _require_equal_ids(stages, "event_stages")
    if stages[["event_id", "stage_id"]].duplicated().any():
        raise ReleaseContractError("event_stages contains duplicate stage identity")
    if stages[["event_id", "stage_index"]].duplicated().any():
        raise ReleaseContractError("event_stages contains duplicate stage_index")
    invalid_stage_index = stages["stage_index"].map(
        lambda value: pd.isna(value) or int(value) != value or int(value) <= 0
    )
    if invalid_stage_index.any():
        raise ReleaseContractError("event_stages stage_index values must be positive integers")
    if not stages["event_id"].map(
        lambda value: isinstance(value, str) and bool(re.fullmatch(EVENT_ID_PATTERN, value))
    ).all():
        raise ReleaseContractError("event_stages contains a malformed event ID")
    available_ids = set(events.loc[events["draft_status"].eq("draft_available"), "event_id"])
    if set(stages["event_id"]) != available_ids:
        raise ReleaseContractError("Stage coverage does not equal the draft-available event set")

    available_summary = events.loc[
        events["draft_status"].eq("draft_available"),
        ["event_id", *GRAPH_COUNT_COLUMNS],
    ].set_index("event_id")
    for event_id in sorted(available_ids):
        event_stages = stages.loc[stages["event_id"].eq(event_id)]
        expected_stage_count = available_summary.at[event_id, "stage_count"]
        if (
            pd.isna(expected_stage_count)
            or int(expected_stage_count) != expected_stage_count
            or int(expected_stage_count) <= 0
            or len(event_stages) != int(expected_stage_count)
        ):
            raise ReleaseContractError(f"stage_count closure mismatch for {event_id}")

        observed_indices = sorted(int(value) for value in event_stages["stage_index"])
        expected_indices = list(range(1, int(expected_stage_count) + 1))
        if observed_indices != expected_indices:
            raise ReleaseContractError(f"Non-contiguous stage_index values for {event_id}")

        for column in GRAPH_COUNT_COLUMNS[1:]:
            expected_count = available_summary.at[event_id, column]
            observed_count = event_stages[column].sum(min_count=1)
            if pd.isna(expected_count) or pd.isna(observed_count) or observed_count != expected_count:
                raise ReleaseContractError(f"{column} closure mismatch for {event_id}")


@lru_cache(maxsize=8)
def _load_release_cached(local_root_value: str | None) -> ExplorerRelease:
    local_root = Path(local_root_value) if local_root_value else None
    catalog = _read_required_parquet(CATALOG_PARQUET, CATALOG_SCHEMA, local_root)
    instances = _read_required_parquet(
        EVENT_INSTANCES_PARQUET, EVENT_INSTANCES_SCHEMA, local_root
    )
    summary = _read_required_parquet(
        FINALCASCADE_SUMMARY_PARQUET, FINALCASCADE_SUMMARY_SCHEMA, local_root
    )
    availability = _read_required_parquet(
        DRAFT_AVAILABILITY_PARQUET, DRAFT_AVAILABILITY_SCHEMA, local_root
    )
    stages = _read_required_parquet(STAGES_PARQUET, STAGES_SCHEMA, local_root)
    events = build_explorer_view(catalog, instances, summary, availability)
    _validate_stages(stages, events)
    stages = stages.sort_values(["event_id", "stage_index", "stage_id"], kind="stable")
    stages_by_event = {
        event_id: group.reset_index(drop=True)
        for event_id, group in stages.groupby("event_id", sort=False)
    }
    return ExplorerRelease(
        events=events,
        stages=stages.reset_index(drop=True),
        stages_by_event=stages_by_event,
    )


def load_release(local_dataset_dir: Path | str | None = None) -> ExplorerRelease:
    local_root = _as_local_root(local_dataset_dir)
    return _load_release_cached(str(local_root) if local_root is not None else None)


def clear_caches() -> None:
    _load_release_cached.cache_clear()
    _load_event_graph_cached.cache_clear()


def _canonical_graph_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _validate_graph(payload: Any, event_id: str, event_row: pd.Series) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise DraftIntegrityError(f"Draft EPG for {event_id} is not a JSON object")
    if payload.get("event_id") != event_id or payload.get("public_event_id") != event_id:
        raise DraftIntegrityError(f"Draft EPG identity mismatch for {event_id}")
    nested_event = payload.get("event")
    if not isinstance(nested_event, dict):
        raise DraftIntegrityError(f"Nested Draft EPG event must be an object for {event_id}")
    if nested_event.get("event_id") != event_id:
        raise DraftIntegrityError(f"Nested Draft EPG identity mismatch for {event_id}")
    if payload.get("source_payload_sha256") != event_row.get("source_payload_sha256"):
        raise DraftIntegrityError(f"Draft EPG source payload digest mismatch for {event_id}")
    if _canonical_graph_sha256(payload) != event_row.get("draft_sha256"):
        raise DraftIntegrityError(f"Draft EPG canonical digest mismatch for {event_id}")
    return payload


@lru_cache(maxsize=256)
def _load_event_graph_cached(
    event_id: str,
    local_root_value: str | None,
    expected_source_sha256: str,
    expected_draft_sha256: str,
) -> dict[str, Any]:
    filename = DRAFT_EPG_PATH_TEMPLATE.format(event_id=event_id)
    local_root = Path(local_root_value) if local_root_value else None
    try:
        path = resolve_dataset_file(filename, local_dataset_dir=local_root)
    except FileNotFoundError as exc:
        raise DraftAssetMissing(f"Available Draft EPG file is missing: {filename}") from exc
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception as exc:
        raise DraftIntegrityError(f"Unable to parse Draft EPG JSON for {event_id}") from exc
    expected = pd.Series(
        {
            "source_payload_sha256": expected_source_sha256,
            "draft_sha256": expected_draft_sha256,
        }
    )
    return _validate_graph(payload, event_id, expected)


def load_event_graph(
    event_id: str,
    *,
    release: ExplorerRelease | None = None,
    local_dataset_dir: Path | str | None = None,
) -> dict[str, Any] | DraftUnavailable:
    """Load one direct public Draft EPG after catalog and availability checks."""

    validate_event_id(event_id)
    selected_release = release or load_release(local_dataset_dir=local_dataset_dir)
    event_row = selected_release.event_row(event_id)
    if event_row["draft_status"] == "draft_unavailable":
        return DraftUnavailable(event_id)
    if event_row["draft_status"] != "draft_available":
        raise ReleaseContractError(f"Unknown draft_status for {event_id}")

    local_root = _as_local_root(local_dataset_dir)
    return _load_event_graph_cached(
        event_id,
        str(local_root) if local_root is not None else None,
        str(event_row["source_payload_sha256"]),
        str(event_row["draft_sha256"]),
    )
