from __future__ import annotations

import csv
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
    DRAFT_EPG_PATH_TEMPLATE,
    DRAFT_SOURCE_HASHES_CSV,
    DRAFT_SOURCE_HASHES_SCHEMA,
    EVENT_GALLERY_PARQUET,
    EVENT_GALLERY_SCHEMA,
    EVENT_ID_MAX,
    EVENT_ID_MIN,
    EVENT_ID_PATTERN,
    EVENT_INSTANCES_PARQUET,
    EVENT_INSTANCES_SCHEMA,
    EVIDENCE_CONTEXT_ACCESS_LEVEL,
    EXPECTED_EVENT_COUNT,
    EXPECTED_STAGE_ROW_COUNT,
    FINALCASCADE_ACCESS_LEVEL,
    FINALCASCADE_SUMMARY_PARQUET,
    FINALCASCADE_SUMMARY_SCHEMA,
    GOLD_REFERENCE_ACCESS_LEVEL,
    GRAPH_COUNT_COLUMNS,
    LOCAL_DATASET_ENV,
    PUBLIC_DATASET_REPO,
    PUBLIC_DATASET_REVISION,
    RELEASE_ASSET_SHA256,
    STAGES_PARQUET,
    STAGES_SCHEMA,
    TABLE_SCHEMA_VERSIONS,
)


class ExplorerDataError(RuntimeError):
    """Base error for public Explorer data access."""


class DatasetTransportError(ExplorerDataError):
    """A pinned public dataset asset could not be retrieved."""


class DatasetRevisionUnavailable(DatasetTransportError):
    """Remote reads are disabled until an immutable release revision is set."""


class ReleaseContractError(ExplorerDataError):
    """The loaded files do not form the expected Unified-3000 release."""


class DraftAssetMissing(ExplorerDataError):
    """A required per-event Draft EPG file is missing."""


class DraftIntegrityError(ExplorerDataError):
    """A direct Draft EPG failed identity or digest validation."""


class InvalidEventId(ValueError):
    """An identifier is not a canonical Unified-3000 event ID."""


@dataclass
class ExplorerRelease:
    events: pd.DataFrame
    stages: pd.DataFrame
    stages_by_event: dict[str, pd.DataFrame]
    revision: str | None = PUBLIC_DATASET_REVISION

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
            raise ReleaseContractError(f"Validated release has no stage rows for {event_id}")
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

    if PUBLIC_DATASET_REVISION is None:
        raise DatasetRevisionUnavailable(
            "Remote Explorer reads are disabled for this release candidate because no "
            "immutable Hugging Face dataset revision has been assigned. Set "
            f"{LOCAL_DATASET_ENV} to the validated local release root."
        )

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


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_release_asset_digest(path: Path, filename: str) -> None:
    expected = RELEASE_ASSET_SHA256[filename]
    observed = _file_sha256(path)
    if observed != expected:
        raise ReleaseContractError(
            f"Release asset digest mismatch for {filename}: expected {expected}, observed {observed}"
        )


def _expected_arrow_schema(expected_schema: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    return tuple(
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


def _read_required_parquet(
    filename: str,
    expected_schema: tuple[str, ...],
    local_dataset_dir: Path | str | None = None,
) -> pd.DataFrame:
    try:
        path = resolve_dataset_file(filename, local_dataset_dir=local_dataset_dir)
    except (DatasetTransportError, FileNotFoundError):
        raise
    except Exception as exc:
        raise ReleaseContractError(f"Unable to resolve required Parquet table: {filename}") from exc

    _require_release_asset_digest(path, filename)
    try:
        table = parquet.read_table(path)
        frame = table.to_pandas()
    except Exception as exc:
        raise ReleaseContractError(f"Unable to read required Parquet table: {filename}") from exc

    observed_columns = tuple(frame.columns)
    observed_arrow = tuple((field.name, str(field.type)) for field in table.schema)
    expected_arrow = _expected_arrow_schema(expected_schema)
    if observed_columns != expected_schema or observed_arrow != expected_arrow:
        raise ReleaseContractError(
            f"Schema mismatch for {filename}: expected {expected_arrow}, observed {observed_arrow}"
        )
    return frame


def _read_source_hash_registry(
    local_dataset_dir: Path | str | None = None,
) -> pd.DataFrame:
    try:
        path = resolve_dataset_file(DRAFT_SOURCE_HASHES_CSV, local_dataset_dir=local_dataset_dir)
    except (DatasetTransportError, FileNotFoundError):
        raise
    except Exception as exc:
        raise ReleaseContractError("Unable to resolve Draft EPG source-hash registry") from exc

    _require_release_asset_digest(path, DRAFT_SOURCE_HASHES_CSV)
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != DRAFT_SOURCE_HASHES_SCHEMA:
                raise ReleaseContractError("Schema mismatch for draft_source_hashes")
            rows = list(reader)
    except ReleaseContractError:
        raise
    except Exception as exc:
        raise ReleaseContractError("Unable to read Draft EPG source-hash registry") from exc

    frame = pd.DataFrame(rows, columns=DRAFT_SOURCE_HASHES_SCHEMA)
    try:
        frame["draft_record_index"] = frame["draft_record_index"].map(int).astype("int64")
    except (TypeError, ValueError) as exc:
        raise ReleaseContractError("draft_record_index must contain decimal integers") from exc
    return frame


def _require_row_count(frame: pd.DataFrame, expected: int, table_name: str) -> None:
    if len(frame) != expected:
        raise ReleaseContractError(
            f"{table_name} row count mismatch: expected {expected}, observed {len(frame)}"
        )


def _require_unique(frame: pd.DataFrame, columns: list[str], table_name: str) -> None:
    if frame.duplicated(columns).any():
        raise ReleaseContractError(f"{table_name} has duplicate identity rows for {columns}")


def _require_no_nulls(frame: pd.DataFrame, table_name: str) -> None:
    columns = frame.columns[frame.isna().any()].tolist()
    if columns:
        raise ReleaseContractError(f"{table_name} contains null values in {columns}")


def _expected_event_ids() -> list[str]:
    return [f"H2EPR-{index:04d}" for index in range(EVENT_ID_MIN, EVENT_ID_MAX + 1)]


def _require_exact_event_order(frame: pd.DataFrame, column: str, table_name: str) -> None:
    if frame[column].tolist() != _expected_event_ids():
        raise ReleaseContractError(
            f"{table_name} does not contain the exact numeric Unified-3000 event order"
        )


def _require_equal_ids(frame: pd.DataFrame, table_name: str) -> None:
    if not frame["event_id"].equals(frame["public_event_id"]):
        raise ReleaseContractError(f"{table_name} event_id/public_event_id mismatch")


def _require_semantic_equality(
    catalog: pd.DataFrame,
    other: pd.DataFrame,
    columns: tuple[str, ...],
    other_name: str,
    *,
    catalog_id: str = "event_id",
    other_id: str = "event_id",
) -> None:
    left = catalog.set_index(catalog_id)
    right = other.set_index(other_id)
    for column in columns:
        if not left[column].equals(right[column]):
            raise ReleaseContractError(f"{column} disagrees between catalog and {other_name}")


def _require_schema_version(frame: pd.DataFrame, table_name: str) -> None:
    expected = TABLE_SCHEMA_VERSIONS[table_name]
    if not frame["schema_version"].eq(expected).all():
        raise ReleaseContractError(f"{table_name} schema_version must be {expected}")


def _require_integer_range(
    frame: pd.DataFrame,
    columns: tuple[str, ...],
    table_name: str,
    *,
    minimum: int,
) -> None:
    def invalid_integer(value: Any) -> bool:
        try:
            return bool(pd.isna(value)) or int(value) != value or int(value) < minimum
        except (TypeError, ValueError):
            return True

    for column in columns:
        invalid = frame[column].map(invalid_integer)
        if invalid.any():
            raise ReleaseContractError(
                f"{table_name}.{column} must contain integers greater than or equal to {minimum}"
            )


def _validate_source_hash_registry(source_hashes: pd.DataFrame) -> None:
    if tuple(source_hashes.columns) != DRAFT_SOURCE_HASHES_SCHEMA:
        raise ReleaseContractError("Schema mismatch for draft_source_hashes")
    _require_row_count(source_hashes, EXPECTED_EVENT_COUNT, "draft_source_hashes")
    _require_no_nulls(source_hashes, "draft_source_hashes")
    _require_unique(source_hashes, ["public_event_id"], "draft_source_hashes")
    _require_exact_event_order(source_hashes, "public_event_id", "draft_source_hashes")
    if source_hashes["draft_record_index"].tolist() != list(
        range(1, EXPECTED_EVENT_COUNT + 1)
    ):
        raise ReleaseContractError("draft_source_hashes has a non-canonical record index")
    sha_pattern = re.compile(r"[0-9a-f]{64}")
    for column in ("source_payload_sha256", "sanitized_record_sha256"):
        if not source_hashes[column].map(
            lambda value: isinstance(value, str) and bool(sha_pattern.fullmatch(value))
        ).all():
            raise ReleaseContractError(f"draft_source_hashes has malformed {column} values")
        if source_hashes[column].duplicated().any():
            raise ReleaseContractError(f"draft_source_hashes has duplicate {column} values")


def build_explorer_view(
    gallery: pd.DataFrame,
    catalog: pd.DataFrame,
    instances: pd.DataFrame,
    summary: pd.DataFrame,
    source_hashes: pd.DataFrame,
) -> pd.DataFrame:
    """Build the exact one-row-per-event Unified-3000 Explorer view."""

    tables = (
        (gallery, EVENT_GALLERY_SCHEMA, "event_gallery", "public_event_id"),
        (catalog, CATALOG_SCHEMA, "event_catalog", "event_id"),
        (instances, EVENT_INSTANCES_SCHEMA, "event_instances", "event_id"),
        (summary, FINALCASCADE_SUMMARY_SCHEMA, "finalcascade_summary", "event_id"),
    )
    for frame, schema, name, order_column in tables:
        if tuple(frame.columns) != schema:
            raise ReleaseContractError(f"Schema mismatch for {name}")
        _require_row_count(frame, EXPECTED_EVENT_COUNT, name)
        _require_no_nulls(frame, name)
        _require_unique(frame, [order_column], name)
        _require_exact_event_order(frame, order_column, name)
        _require_schema_version(frame, name)

    _validate_source_hash_registry(source_hashes)
    for frame, name in (
        (catalog, "event_catalog"),
        (instances, "event_instances"),
        (summary, "finalcascade_summary"),
    ):
        _require_equal_ids(frame, name)

    _require_integer_range(
        catalog,
        ("stage_count", "episode_count"),
        "event_catalog",
        minimum=1,
    )
    _require_integer_range(summary, GRAPH_COUNT_COLUMNS, "finalcascade_summary", minimum=0)
    if not summary["stage_count"].gt(0).all() or not summary["episode_count"].gt(0).all():
        raise ReleaseContractError("Every Draft EPG must contain stages and episodes")
    _require_integer_range(
        summary,
        ("known_action_time_anchor_count",),
        "finalcascade_summary",
        minimum=0,
    )

    _require_semantic_equality(
        catalog,
        gallery,
        ("title", "domain", "category", "event_descriptor"),
        "event_gallery",
        other_id="public_event_id",
    )
    _require_semantic_equality(
        catalog,
        instances,
        (
            "title",
            "display_name",
            "event_descriptor",
            "domain",
            "category",
            "keywords",
            "has_gold_reference",
        ),
        "event_instances",
    )
    _require_semantic_equality(
        catalog,
        summary,
        ("title", "domain", "category", "stage_count", "episode_count"),
        "finalcascade_summary",
    )

    if not catalog["has_gold_reference"].eq(True).all():
        raise ReleaseContractError("event_catalog has_gold_reference must be true for every event")
    required_access = {
        "finalcascade_access_level": FINALCASCADE_ACCESS_LEVEL,
        "gold_reference_access_level": GOLD_REFERENCE_ACCESS_LEVEL,
        "evidence_context_access_level": EVIDENCE_CONTEXT_ACCESS_LEVEL,
    }
    for column, expected in required_access.items():
        if not instances[column].eq(expected).all():
            raise ReleaseContractError(f"event_instances.{column} must be {expected}")

    access_fields = ["event_id", *required_access]
    summary_fields = [
        "event_id",
        "participant_count",
        "action_count",
        "transaction_count",
        "relation_count",
        "event_start_time",
        "event_end_time",
        "event_boundary_time_status",
        "known_action_time_anchor_count",
        "known_action_time_anchors",
        "relative_order_available",
    ]
    try:
        joined = catalog.merge(
            instances[access_fields], on="event_id", how="left", validate="one_to_one"
        )
        joined = joined.merge(
            summary[summary_fields], on="event_id", how="left", validate="one_to_one"
        )
        joined = joined.merge(
            source_hashes, on="public_event_id", how="left", validate="one_to_one"
        )
    except Exception as exc:
        raise ReleaseContractError("Unified-3000 Explorer join multiplicity failure") from exc

    _require_row_count(joined, EXPECTED_EVENT_COUNT, "joined Explorer view")
    _require_no_nulls(joined, "joined Explorer view")
    _require_unique(joined, ["public_event_id", "event_id"], "joined Explorer view")
    _require_exact_event_order(joined, "event_id", "joined Explorer view")
    return joined.reset_index(drop=True)


def _validate_stages(stages: pd.DataFrame, events: pd.DataFrame) -> None:
    if tuple(stages.columns) != STAGES_SCHEMA:
        raise ReleaseContractError("Schema mismatch for event_stages")
    _require_row_count(stages, EXPECTED_STAGE_ROW_COUNT, "event_stages")
    _require_no_nulls(stages, "event_stages")
    _require_equal_ids(stages, "event_stages")
    _require_schema_version(stages, "event_stages")
    if stages[["event_id", "stage_id"]].duplicated().any():
        raise ReleaseContractError("event_stages contains duplicate stage identity")
    if stages[["event_id", "stage_index"]].duplicated().any():
        raise ReleaseContractError("event_stages contains duplicate stage_index")
    _require_integer_range(stages, ("stage_index",), "event_stages", minimum=1)
    _require_integer_range(
        stages,
        (*GRAPH_COUNT_COLUMNS[1:], "known_action_time_anchor_count"),
        "event_stages",
        minimum=0,
    )
    if not stages["episode_count"].gt(0).all():
        raise ReleaseContractError("Every stage must contain at least one episode")

    expected_ids = _expected_event_ids()
    observed_event_order = list(dict.fromkeys(stages["event_id"].tolist()))
    if observed_event_order != expected_ids:
        raise ReleaseContractError("event_stages does not cover all events in numeric order")

    event_summary = events.set_index("event_id")
    for event_id, event_stages in stages.groupby("event_id", sort=False):
        expected_stage_count = int(event_summary.at[event_id, "stage_count"])
        if len(event_stages) != expected_stage_count:
            raise ReleaseContractError(f"stage_count closure mismatch for {event_id}")
        observed_indices = event_stages["stage_index"].astype(int).tolist()
        expected_indices = list(range(1, expected_stage_count + 1))
        if observed_indices != expected_indices:
            raise ReleaseContractError(f"Non-contiguous stage_index values for {event_id}")
        for column in GRAPH_COUNT_COLUMNS[1:]:
            observed_count = int(event_stages[column].sum())
            expected_count = int(event_summary.at[event_id, column])
            if observed_count != expected_count:
                raise ReleaseContractError(f"{column} closure mismatch for {event_id}")
        expected_relative_order = bool(event_summary.at[event_id, "relative_order_available"])
        if not event_stages["relative_order_available"].eq(expected_relative_order).all():
            raise ReleaseContractError(
                f"relative_order_available disagrees between event and stages for {event_id}"
            )


@lru_cache(maxsize=8)
def _load_release_cached(local_root_value: str | None) -> ExplorerRelease:
    local_root = Path(local_root_value) if local_root_value else None
    gallery = _read_required_parquet(EVENT_GALLERY_PARQUET, EVENT_GALLERY_SCHEMA, local_root)
    catalog = _read_required_parquet(CATALOG_PARQUET, CATALOG_SCHEMA, local_root)
    instances = _read_required_parquet(
        EVENT_INSTANCES_PARQUET, EVENT_INSTANCES_SCHEMA, local_root
    )
    summary = _read_required_parquet(
        FINALCASCADE_SUMMARY_PARQUET, FINALCASCADE_SUMMARY_SCHEMA, local_root
    )
    stages = _read_required_parquet(STAGES_PARQUET, STAGES_SCHEMA, local_root)
    source_hashes = _read_source_hash_registry(local_root)
    events = build_explorer_view(gallery, catalog, instances, summary, source_hashes)
    _validate_stages(stages, events)
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
    if _canonical_graph_sha256(payload) != event_row.get("sanitized_record_sha256"):
        raise DraftIntegrityError(f"Draft EPG sanitized record digest mismatch for {event_id}")
    return payload


@lru_cache(maxsize=256)
def _load_event_graph_cached(
    event_id: str,
    local_root_value: str | None,
    expected_source_sha256: str,
    expected_sanitized_sha256: str,
) -> dict[str, Any]:
    filename = DRAFT_EPG_PATH_TEMPLATE.format(event_id=event_id)
    local_root = Path(local_root_value) if local_root_value else None
    try:
        path = resolve_dataset_file(filename, local_dataset_dir=local_root)
    except FileNotFoundError as exc:
        raise DraftAssetMissing(f"Required Draft EPG file is missing: {filename}") from exc
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception as exc:
        raise DraftIntegrityError(f"Unable to parse Draft EPG JSON for {event_id}") from exc
    expected = pd.Series(
        {
            "source_payload_sha256": expected_source_sha256,
            "sanitized_record_sha256": expected_sanitized_sha256,
        }
    )
    return _validate_graph(payload, event_id, expected)


def load_event_graph(
    event_id: str,
    *,
    release: ExplorerRelease | None = None,
    local_dataset_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Load one direct public Draft EPG after release and digest validation."""

    validate_event_id(event_id)
    selected_release = release or load_release(local_dataset_dir=local_dataset_dir)
    event_row = selected_release.event_row(event_id)
    local_root = _as_local_root(local_dataset_dir)
    return _load_event_graph_cached(
        event_id,
        str(local_root) if local_root is not None else None,
        str(event_row["source_payload_sha256"]),
        str(event_row["sanitized_record_sha256"]),
    )
