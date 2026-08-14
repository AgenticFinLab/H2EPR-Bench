#!/usr/bin/env python3
"""Validate a local H2EPR-Bench public Dataset tree without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

import pandas as pd
import pyarrow.parquet as parquet


DEFAULT_CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "manifests"
    / "unified3000_release_contract.json"
)
GRAPH_COUNT_COLUMNS = (
    "stage_count",
    "episode_count",
    "participant_count",
    "action_count",
    "transaction_count",
    "relation_count",
)
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


class ReleaseValidationError(RuntimeError):
    """A local public Dataset tree violates its declared release contract."""


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        raise ReleaseValidationError(f"Unable to read JSON: {path.name}") from exc


def _load_contract(path: Path) -> dict[str, Any]:
    payload = _load_json(path.resolve())
    if not isinstance(payload, dict):
        raise ReleaseValidationError("Release contract must be a JSON object")
    required = {
        "contract_version",
        "dataset_repo",
        "dataset_revision",
        "event_identity",
        "counts",
        "paths",
        "arrow_types",
        "tables",
    }
    if set(payload) != required:
        raise ReleaseValidationError("Release contract has unexpected top-level fields")
    return payload


def _resolve_local(root: Path, relative_path: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path:
        raise ReleaseValidationError("Dataset path must be a non-empty string")
    pure = PurePosixPath(relative_path)
    if pure.is_absolute() or ".." in pure.parts or "\\" in relative_path:
        raise ReleaseValidationError(f"Unsafe Dataset-relative path: {relative_path!r}")
    candidate = (root / Path(*pure.parts)).resolve()
    if not candidate.is_relative_to(root):
        raise ReleaseValidationError(f"Dataset path escapes the local root: {relative_path!r}")
    return candidate


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _expected_event_ids(contract: dict[str, Any]) -> set[str]:
    identity = contract["event_identity"]
    first = identity.get("first")
    last = identity.get("last")
    pattern = identity.get("pattern")
    if (
        not isinstance(first, int)
        or not isinstance(last, int)
        or first < 1
        or last < first
        or not isinstance(pattern, str)
    ):
        raise ReleaseValidationError("Invalid event_identity contract")
    identifiers = {f"H2EPR-{index:04d}" for index in range(first, last + 1)}
    compiled = re.compile(pattern)
    if not all(compiled.fullmatch(value) for value in identifiers):
        raise ReleaseValidationError("event_identity range does not match its pattern")
    if len(identifiers) != contract["counts"].get("events"):
        raise ReleaseValidationError("event_identity range does not match event count")
    return identifiers


def _expected_arrow_schema(
    columns: list[str], arrow_types: dict[str, Any]
) -> tuple[tuple[str, str], ...]:
    bool_columns = set(arrow_types.get("bool", []))
    int_columns = set(arrow_types.get("int64", []))
    default = arrow_types.get("default")
    if default != "string" or bool_columns & int_columns:
        raise ReleaseValidationError("Invalid arrow_types contract")
    return tuple(
        (
            column,
            "bool" if column in bool_columns else "int64" if column in int_columns else default,
        )
        for column in columns
    )


def _read_tables(
    root: Path, contract: dict[str, Any]
) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    required_tables = {
        "event_gallery",
        "event_catalog",
        "event_instances",
        "event_stages",
        "finalcascade_summary",
        "draft_availability",
    }
    tables_contract = contract["tables"]
    if set(tables_contract) != required_tables:
        raise ReleaseValidationError("Release contract must declare exactly six viewer mirrors")

    frames: dict[str, pd.DataFrame] = {}
    hashes: dict[str, str] = {}
    for name, declared in tables_contract.items():
        path = _resolve_local(root, declared.get("path"))
        if not path.is_file():
            raise ReleaseValidationError(f"Missing required viewer mirror: {declared.get('path')}")
        observed_hash = _sha256_file(path)
        expected_hash = declared.get("sha256")
        if not isinstance(expected_hash, str) or observed_hash != expected_hash:
            raise ReleaseValidationError(f"SHA-256 mismatch for {name}")

        columns = declared.get("columns")
        if not isinstance(columns, list) or not all(isinstance(value, str) for value in columns):
            raise ReleaseValidationError(f"Invalid ordered column contract for {name}")
        expected_schema = _expected_arrow_schema(columns, contract["arrow_types"])
        try:
            arrow_schema = parquet.read_schema(path)
            frame = pd.read_parquet(path)
        except Exception as exc:
            raise ReleaseValidationError(f"Unable to read Parquet mirror: {name}") from exc
        observed_schema = tuple((field.name, str(field.type)) for field in arrow_schema)
        if observed_schema != expected_schema or tuple(frame.columns) != tuple(columns):
            raise ReleaseValidationError(f"Ordered Arrow schema mismatch for {name}")
        expected_rows = declared.get("rows")
        if not isinstance(expected_rows, int) or len(frame) != expected_rows:
            raise ReleaseValidationError(f"Row-count mismatch for {name}")
        frames[name] = frame
        hashes[name] = observed_hash
    return frames, hashes


def _require_unique(frame: pd.DataFrame, columns: list[str], table_name: str) -> None:
    if frame.duplicated(columns).any():
        raise ReleaseValidationError(f"Duplicate identity in {table_name}: {columns}")


def _require_equal_ids(frame: pd.DataFrame, table_name: str) -> None:
    if not frame["event_id"].equals(frame["public_event_id"]):
        raise ReleaseValidationError(f"event_id/public_event_id mismatch in {table_name}")


def _require_columns_equal(
    catalog: pd.DataFrame,
    other: pd.DataFrame,
    columns: tuple[str, ...],
    other_name: str,
) -> None:
    left = catalog.set_index("public_event_id").sort_index()
    right = other.set_index("public_event_id").sort_index()
    for column in columns:
        if not left[column].equals(right[column]):
            raise ReleaseValidationError(
                f"{column} disagrees between event_catalog and {other_name}"
            )


def _validate_identity_and_semantics(
    frames: dict[str, pd.DataFrame],
    expected_ids: set[str],
    contract: dict[str, Any],
) -> tuple[set[str], set[str]]:
    gallery = frames["event_gallery"]
    catalog = frames["event_catalog"]
    instances = frames["event_instances"]
    summary = frames["finalcascade_summary"]
    availability = frames["draft_availability"]

    for name, frame in (
        ("event_gallery", gallery),
        ("event_catalog", catalog),
        ("event_instances", instances),
        ("finalcascade_summary", summary),
        ("draft_availability", availability),
    ):
        _require_unique(frame, ["public_event_id"], name)
        if set(frame["public_event_id"]) != expected_ids:
            raise ReleaseValidationError(f"Event identity coverage mismatch in {name}")
    for name, frame in (
        ("event_catalog", catalog),
        ("event_instances", instances),
        ("finalcascade_summary", summary),
    ):
        _require_equal_ids(frame, name)

    _require_columns_equal(
        catalog,
        gallery,
        ("title", "domain", "category", "event_descriptor", "draft_status"),
        "event_gallery",
    )
    _require_columns_equal(
        catalog,
        instances,
        (
            "event_id",
            "title",
            "display_name",
            "event_descriptor",
            "domain",
            "category",
            "keywords",
            "release_split",
            "version",
            "draft_status",
            "has_gold_reference",
        ),
        "event_instances",
    )
    _require_columns_equal(
        catalog,
        summary,
        ("event_id", "title", "domain", "category", "draft_status"),
        "finalcascade_summary",
    )
    _require_columns_equal(
        catalog,
        availability,
        ("draft_status",),
        "draft_availability",
    )

    observed_status = availability["draft_status"].value_counts(dropna=False).to_dict()
    expected_status = {
        "draft_available": contract["counts"].get("draft_available"),
        "draft_unavailable": contract["counts"].get("draft_unavailable"),
    }
    if observed_status != expected_status:
        raise ReleaseValidationError(
            f"Draft availability counts mismatch: {observed_status!r}"
        )
    available_ids = set(
        availability.loc[availability["draft_status"].eq("draft_available"), "public_event_id"]
    )
    unavailable_ids = expected_ids - available_ids
    if not availability["has_reference_epg"].eq(True).all():
        raise ReleaseValidationError("Availability rows must preserve reference EPG existence")
    if not catalog["has_gold_reference"].eq(True).all():
        raise ReleaseValidationError("Catalog must preserve reference EPG existence")

    available = availability["draft_status"].eq("draft_available")
    unavailable = availability["draft_status"].eq("draft_unavailable")
    draft_fields = (
        "draft_source_kind",
        "draft_schema",
        "draft_asset",
        "draft_record_index",
        "draft_sha256",
        "source_payload_sha256",
    )
    if availability.loc[available, list(draft_fields)].isna().any().any():
        raise ReleaseValidationError("Available Draft metadata contains null fields")
    if not availability.loc[unavailable, list(draft_fields)].isna().all().all():
        raise ReleaseValidationError("Unavailable Draft metadata must be null")
    for column in ("draft_sha256", "source_payload_sha256"):
        if not availability.loc[available, column].map(
            lambda value: isinstance(value, str) and bool(SHA256_PATTERN.fullmatch(value))
        ).all():
            raise ReleaseValidationError(f"Invalid {column} in availability table")
    indices = availability.loc[available, "draft_record_index"].astype(int)
    if sorted(indices.tolist()) != list(range(1, len(indices) + 1)):
        raise ReleaseValidationError("draft_record_index must be unique and contiguous")

    joined_status = catalog.set_index("public_event_id")["draft_status"]
    expected_has_draft = joined_status.eq("draft_available")
    observed_has_draft = instances.set_index("public_event_id")["has_finalcascade"]
    if not expected_has_draft.sort_index().equals(observed_has_draft.sort_index()):
        raise ReleaseValidationError("has_finalcascade disagrees with Draft availability")

    counts = list(GRAPH_COUNT_COLUMNS)
    indexed_summary = summary.set_index("public_event_id")
    if indexed_summary.loc[sorted(available_ids), counts].isna().any().any():
        raise ReleaseValidationError("Available summary contains null graph counts")
    if not indexed_summary.loc[sorted(unavailable_ids), counts].isna().all().all():
        raise ReleaseValidationError("Unavailable summary contains observed graph counts")
    return available_ids, unavailable_ids


def _validate_stages(
    frames: dict[str, pd.DataFrame],
    available_ids: set[str],
    contract: dict[str, Any],
) -> None:
    stages = frames["event_stages"]
    summary = frames["finalcascade_summary"].set_index("public_event_id")
    _require_equal_ids(stages, "event_stages")
    _require_unique(stages, ["public_event_id", "stage_id"], "event_stages")
    _require_unique(stages, ["public_event_id", "stage_index"], "event_stages")
    if len(stages) != contract["counts"].get("stage_rows"):
        raise ReleaseValidationError("Stage row count disagrees with release counts")
    if stages["public_event_id"].nunique() != contract["counts"].get("stage_events"):
        raise ReleaseValidationError("Stage event count disagrees with release counts")
    if set(stages["public_event_id"]) != available_ids:
        raise ReleaseValidationError("Stage coverage differs from Draft-available events")

    for event_id in sorted(available_ids):
        rows = stages.loc[stages["public_event_id"].eq(event_id)]
        expected_stage_count = summary.at[event_id, "stage_count"]
        if (
            pd.isna(expected_stage_count)
            or int(expected_stage_count) != expected_stage_count
            or int(expected_stage_count) <= 0
            or len(rows) != int(expected_stage_count)
        ):
            raise ReleaseValidationError(f"stage_count closure mismatch for {event_id}")
        indices = sorted(int(value) for value in rows["stage_index"])
        if indices != list(range(1, len(rows) + 1)):
            raise ReleaseValidationError(f"Non-contiguous stage_index for {event_id}")
        for column in GRAPH_COUNT_COLUMNS[1:]:
            observed = rows[column].sum(min_count=1)
            expected = summary.at[event_id, column]
            if pd.isna(observed) or pd.isna(expected) or observed != expected:
                raise ReleaseValidationError(f"{column} closure mismatch for {event_id}")

        catalog_row = frames["event_catalog"].set_index("public_event_id").loc[event_id]
        for column in ("release_split", "version"):
            if not rows[column].eq(catalog_row[column]).all():
                raise ReleaseValidationError(f"Stage {column} mismatch for {event_id}")


def _validate_unavailable_marker(payload: Any, event_id: str) -> None:
    required = {
        "public_event_id",
        "draft_status",
        "unavailable_reason",
        "draft_source_kind",
        "draft_schema",
        "draft_asset",
        "draft_record_index",
        "draft_sha256",
        "source_payload_sha256",
        "has_reference_epg",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ReleaseValidationError(f"Invalid unavailable marker fields for {event_id}")
    if (
        payload["public_event_id"] != event_id
        or payload["draft_status"] != "draft_unavailable"
        or payload["has_reference_epg"] is not True
        or not isinstance(payload["unavailable_reason"], str)
        or not payload["unavailable_reason"]
    ):
        raise ReleaseValidationError(f"Invalid unavailable marker values for {event_id}")
    nullable = required - {
        "public_event_id",
        "draft_status",
        "unavailable_reason",
        "has_reference_epg",
    }
    if any(payload[field] is not None for field in nullable):
        raise ReleaseValidationError(f"Unavailable marker contains Draft metadata for {event_id}")


def _validate_direct_drafts(
    root: Path,
    frames: dict[str, pd.DataFrame],
    available_ids: set[str],
    unavailable_ids: set[str],
    contract: dict[str, Any],
) -> str:
    availability = frames["draft_availability"].set_index("public_event_id")
    draft_template = contract["paths"].get("draft_epg")
    unavailable_template = contract["paths"].get("draft_unavailable")
    if draft_template != "draft_events/{event_id}/draft_epg.json":
        raise ReleaseValidationError("Direct Draft path template is not canonical")
    if unavailable_template != "draft_events/{event_id}/draft_unavailable.json":
        raise ReleaseValidationError("Unavailable path template is not canonical")

    ledger = hashlib.sha256()
    for event_id in sorted(available_ids):
        # Deliberately derive from the validated identity. draft_asset is not a path.
        path = _resolve_local(root, draft_template.format(event_id=event_id))
        if not path.is_file():
            raise ReleaseValidationError(f"Missing direct Draft EPG for {event_id}")
        payload = _load_json(path)
        nested_event = payload.get("event") if isinstance(payload, dict) else None
        if (
            not isinstance(payload, dict)
            or payload.get("event_id") != event_id
            or payload.get("public_event_id") != event_id
            or not isinstance(nested_event, dict)
            or nested_event.get("event_id") != event_id
        ):
            raise ReleaseValidationError(f"Draft EPG identity mismatch for {event_id}")
        row = availability.loc[event_id]
        if payload.get("source_payload_sha256") != row["source_payload_sha256"]:
            raise ReleaseValidationError(f"Draft source hash mismatch for {event_id}")
        observed_hash = _canonical_json_sha256(payload)
        if observed_hash != row["draft_sha256"]:
            raise ReleaseValidationError(f"Draft canonical hash mismatch for {event_id}")
        ledger.update(f"{event_id}\t{observed_hash}\n".encode("ascii"))

    for event_id in sorted(unavailable_ids):
        draft_path = _resolve_local(root, draft_template.format(event_id=event_id))
        if draft_path.exists():
            raise ReleaseValidationError(f"Unavailable event exposes a Draft EPG: {event_id}")
        marker_path = _resolve_local(root, unavailable_template.format(event_id=event_id))
        if not marker_path.is_file():
            raise ReleaseValidationError(f"Missing unavailable marker for {event_id}")
        _validate_unavailable_marker(_load_json(marker_path), event_id)
    return ledger.hexdigest()


def validate_release(
    dataset_root: Path | str,
    contract_path: Path | str = DEFAULT_CONTRACT,
) -> dict[str, Any]:
    """Validate one explicit local public Dataset root and return a stable receipt."""

    root = Path(dataset_root).expanduser().resolve()
    if not root.is_dir():
        raise ReleaseValidationError("Dataset root must be an existing directory")
    contract = _load_contract(Path(contract_path))
    expected_ids = _expected_event_ids(contract)
    frames, table_hashes = _read_tables(root, contract)
    available_ids, unavailable_ids = _validate_identity_and_semantics(
        frames, expected_ids, contract
    )
    _validate_stages(frames, available_ids, contract)
    draft_ledger = _validate_direct_drafts(
        root, frames, available_ids, unavailable_ids, contract
    )
    return {
        "contract_version": contract["contract_version"],
        "dataset_repo": contract["dataset_repo"],
        "dataset_revision": contract["dataset_revision"],
        "counts": {
            "events": len(expected_ids),
            "draft_available": len(available_ids),
            "draft_unavailable": len(unavailable_ids),
            "stage_rows": len(frames["event_stages"]),
            "stage_events": frames["event_stages"]["public_event_id"].nunique(),
        },
        "table_sha256": dict(sorted(table_hashes.items())),
        "draft_ledger_sha256": draft_ledger,
        "gold_records_accessed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_root", type=Path)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    args = parser.parse_args()
    receipt = validate_release(args.dataset_root, args.contract)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
