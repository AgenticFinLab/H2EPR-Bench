#!/usr/bin/env python3
"""Validate one local H2EPR-Bench Unified-3000 v2 Dataset tree offline.

The checked-in contract may describe an unpublished local release candidate
(``dataset_revision: null``).  Pass ``--require-published`` at a publication
gate; that mode accepts only an immutable, lowercase 40-hex Git revision.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any

import pyarrow.parquet as parquet


DEFAULT_CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "manifests"
    / "unified3000_release_contract.json"
)

CONTRACT_VERSION = "h2epr-unified3000-public-release-v2"
DATASET_REPO = "AgenticFinLab/H2EPR-Bench"
EVENT_PATTERN = re.compile(r"^H2EPR-[0-9]{4}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
IMMUTABLE_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")

GRAPH_COUNT_COLUMNS = (
    "stage_count",
    "episode_count",
    "participant_count",
    "action_count",
    "transaction_count",
    "relation_count",
)
COUNT_KEYS = (
    "events",
    "draft_epgs",
    "stage_rows",
    "stage_events",
    "episodes",
    "participants",
    "actions",
    "transactions",
    "relations",
)
COUNT_TO_GRAPH_COLUMN = {
    "stage_rows": "stage_count",
    "episodes": "episode_count",
    "participants": "participant_count",
    "actions": "action_count",
    "transactions": "transaction_count",
    "relations": "relation_count",
}

SOURCE_HASH_FIELDS = (
    "public_event_id",
    "source_payload_sha256",
    "sanitized_record_sha256",
    "draft_record_index",
)
WRAPPER_FIELDS = {
    "artifact_role",
    "artifact_type",
    "event",
    "event_id",
    "not_gold_warning",
    "public_event_id",
    "quality_flags_public",
    "redaction_counts",
    "redaction_level",
    "schema_version",
    "source_artifact_name",
    "source_event_label",
    "source_payload_sha256",
    "workflow_family",
}
WRAPPER_METADATA = {
    "artifact_role": "reference_construction_artifact",
    "artifact_type": "finmycelium_finalcascade_public",
    "not_gold_warning": (
        "This FinMycelium FinalCascade draft is a construction artifact, "
        "not the Gold reference or scoring target."
    ),
    "quality_flags_public": [],
    "redaction_level": "public_sanitized_full_graph",
    "schema_version": "h2epr-finmycelium-finalcascade-public-v2",
    "source_artifact_name": "FinalEventCascade.json",
    "workflow_family": "FinMycelium",
}

TABLE_CONTRACTS = {
    "event_gallery": {
        "path": "data/viewer_mirrors/event_gallery.parquet",
        "schema_version": "h2epr-public-event-gallery-v3",
        "columns": (
            "public_event_id",
            "title",
            "domain",
            "category",
            "event_descriptor",
            "schema_version",
        ),
    },
    "event_catalog": {
        "path": "data/viewer_mirrors/event_catalog.parquet",
        "schema_version": "h2epr-public-event-catalog-v3",
        "columns": (
            "public_event_id",
            "event_id",
            "title",
            "display_name",
            "event_descriptor",
            "domain",
            "category",
            "keywords",
            "has_gold_reference",
            "stage_count",
            "episode_count",
            "schema_version",
        ),
    },
    "event_instances": {
        "path": "data/viewer_mirrors/event_instances.parquet",
        "schema_version": "h2epr-public-event-instances-v3",
        "columns": (
            "public_event_id",
            "event_id",
            "title",
            "display_name",
            "event_descriptor",
            "domain",
            "category",
            "keywords",
            "has_gold_reference",
            "finalcascade_access_level",
            "gold_reference_access_level",
            "evidence_context_access_level",
            "schema_version",
        ),
    },
    "event_stages": {
        "path": "data/viewer_mirrors/event_stages.parquet",
        "schema_version": "h2epr-public-event-stages-v3",
        "columns": (
            "public_event_id",
            "event_id",
            "stage_id",
            "stage_index",
            "stage_title",
            "stage_start_time",
            "stage_end_time",
            "stage_boundary_time_status",
            "episode_count",
            "participant_count",
            "action_count",
            "transaction_count",
            "relation_count",
            "known_action_time_anchor_count",
            "known_action_time_anchors",
            "relative_order_available",
            "schema_version",
        ),
    },
    "finalcascade_summary": {
        "path": "data/viewer_mirrors/finalcascade_summary.parquet",
        "schema_version": "h2epr-public-finalcascade-summary-v3",
        "columns": (
            "public_event_id",
            "event_id",
            "title",
            "domain",
            "category",
            "stage_count",
            "episode_count",
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
            "schema_version",
        ),
    },
}

BOOL_COLUMNS = ("has_gold_reference", "relative_order_available")
INT64_COLUMNS = (
    "stage_count",
    "episode_count",
    "participant_count",
    "action_count",
    "transaction_count",
    "relation_count",
    "stage_index",
    "known_action_time_anchor_count",
)


class ReleaseValidationError(RuntimeError):
    """A local public Dataset tree violates its release contract."""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _load_json(path: Path, label: str) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        raise ReleaseValidationError(f"Unable to read {label} JSON") from exc


def _safe_relative(relative: Any, *, label: str) -> str:
    if not isinstance(relative, str) or not relative:
        raise ReleaseValidationError(f"{label} must be a non-empty Dataset-relative path")
    pure = PurePosixPath(relative)
    if (
        pure.is_absolute()
        or pure == PurePosixPath(".")
        or ".." in pure.parts
        or "\\" in relative
        or any(part in {"", "."} for part in pure.parts)
    ):
        raise ReleaseValidationError(f"Unsafe Dataset-relative path in {label}: {relative!r}")
    return pure.as_posix()


def _resolve_local(root: Path, relative: Any, *, label: str) -> Path:
    normalized = _safe_relative(relative, label=label)
    candidate = root.joinpath(*PurePosixPath(normalized).parts)
    # Parent topology is independently checked without following symlinks.  This
    # lexical guard prevents a contract from escaping before that check runs.
    if not candidate.absolute().is_relative_to(root.absolute()):
        raise ReleaseValidationError(f"Dataset path escapes its root in {label}")
    return candidate


def _published_revision(contract: dict[str, Any], require_published: bool) -> bool:
    revision = contract.get("dataset_revision")
    if revision is None:
        if require_published:
            raise ReleaseValidationError(
                "Published validation requires an immutable 40-hex dataset_revision"
            )
        return False
    if not isinstance(revision, str) or not IMMUTABLE_REVISION_PATTERN.fullmatch(revision):
        raise ReleaseValidationError(
            "dataset_revision must be null or an immutable lowercase 40-hex revision"
        )
    return True


def _load_contract(path: Path, *, require_published: bool) -> tuple[dict[str, Any], bool]:
    payload = _load_json(path.resolve(), "release contract")
    if not isinstance(payload, dict):
        raise ReleaseValidationError("Release contract must be a JSON object")
    expected_top = {
        "contract_version",
        "dataset_repo",
        "dataset_revision",
        "event_identity",
        "counts",
        "paths",
        "artifacts",
        "arrow_types",
        "tables",
    }
    if set(payload) != expected_top:
        raise ReleaseValidationError("Release contract top-level field set is not exact")
    if payload["contract_version"] != CONTRACT_VERSION:
        raise ReleaseValidationError("Unexpected release contract version")
    if payload["dataset_repo"] != DATASET_REPO:
        raise ReleaseValidationError("Unexpected public Dataset repository")
    published = _published_revision(payload, require_published)

    identity = payload["event_identity"]
    if not isinstance(identity, dict) or set(identity) != {"pattern", "first", "last"}:
        raise ReleaseValidationError("event_identity field set is not exact")
    counts = payload["counts"]
    if not isinstance(counts, dict) or tuple(counts) != COUNT_KEYS:
        raise ReleaseValidationError("Release count field set/order is not exact")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 1
        for value in counts.values()
    ):
        raise ReleaseValidationError("Release counts must be positive integers")
    if (
        identity != {
            "pattern": "^H2EPR-[0-9]{4}$",
            "first": 1,
            "last": counts["events"],
        }
        or counts["events"] > 9999
    ):
        raise ReleaseValidationError("event_identity does not close over release events")
    if counts["draft_epgs"] != counts["events"]:
        raise ReleaseValidationError("Every release event must have one Draft EPG")
    if counts["stage_events"] != counts["events"]:
        raise ReleaseValidationError("Every release event must have stage coverage")

    if payload["paths"] != {"draft_epg": "draft_events/{event_id}/draft_epg.json"}:
        raise ReleaseValidationError("Direct Draft path contract is not exact")

    artifacts = payload["artifacts"]
    if not isinstance(artifacts, dict) or set(artifacts) != {
        "aggregate_drafts",
        "draft_source_hashes",
        "package_checksums",
    }:
        raise ReleaseValidationError("Release artifact contract is not exact")
    expected_artifacts = {
        "aggregate_drafts": {
            "path": "data/finmycelium_finalcascade_public.jsonl",
            "keys": {"path", "sha256", "rows"},
            "rows": counts["events"],
        },
        "draft_source_hashes": {
            "path": "manifests/draft_source_hashes.csv",
            "keys": {"path", "sha256", "rows", "columns"},
            "rows": counts["events"],
        },
        "package_checksums": {
            "path": "SHA256SUMS",
            "keys": {"path", "sha256", "entries"},
            "rows": None,
        },
    }
    for name, expected in expected_artifacts.items():
        declared = artifacts.get(name)
        if not isinstance(declared, dict) or set(declared) != expected["keys"]:
            raise ReleaseValidationError(f"{name} artifact fields are not exact")
        if declared.get("path") != expected["path"]:
            raise ReleaseValidationError(f"{name} artifact path is not canonical")
        if not isinstance(declared.get("sha256"), str) or not SHA256_PATTERN.fullmatch(
            declared["sha256"]
        ):
            raise ReleaseValidationError(f"{name} artifact hash is malformed")
        if expected["rows"] is not None and declared.get("rows") != expected["rows"]:
            raise ReleaseValidationError(f"{name} artifact row count is stale")
    entries = artifacts["package_checksums"].get("entries")
    if isinstance(entries, bool) or not isinstance(entries, int) or entries < 1:
        raise ReleaseValidationError("package_checksums entries must be positive")
    if tuple(artifacts["draft_source_hashes"].get("columns", ())) != SOURCE_HASH_FIELDS:
        raise ReleaseValidationError("Draft source-hash column contract is not exact")

    arrow_types = payload["arrow_types"]
    if arrow_types != {
        "default": "string",
        "bool": list(BOOL_COLUMNS),
        "int64": list(INT64_COLUMNS),
    }:
        raise ReleaseValidationError("Arrow type contract is not exact")

    tables = payload["tables"]
    if not isinstance(tables, dict) or tuple(tables) != tuple(TABLE_CONTRACTS):
        raise ReleaseValidationError("Release contract must declare exactly five viewer mirrors")
    for name, expected in TABLE_CONTRACTS.items():
        declared = tables[name]
        if not isinstance(declared, dict) or set(declared) != {
            "path",
            "sha256",
            "rows",
            "schema_version",
            "columns",
        }:
            raise ReleaseValidationError(f"Viewer contract fields are not exact: {name}")
        if (
            declared.get("path") != expected["path"]
            or declared.get("schema_version") != expected["schema_version"]
            or tuple(declared.get("columns", ())) != expected["columns"]
        ):
            raise ReleaseValidationError(f"Viewer contract is stale: {name}")
        expected_rows = counts["stage_rows"] if name == "event_stages" else counts["events"]
        if declared.get("rows") != expected_rows:
            raise ReleaseValidationError(f"Viewer row count contract is stale: {name}")
        if not isinstance(declared.get("sha256"), str) or not SHA256_PATTERN.fullmatch(
            declared["sha256"]
        ):
            raise ReleaseValidationError(f"Viewer hash is malformed: {name}")
    return payload, published


def _expected_event_ids(contract: dict[str, Any]) -> list[str]:
    count = contract["counts"]["events"]
    identifiers = [f"H2EPR-{index:04d}" for index in range(1, count + 1)]
    if any(not EVENT_PATTERN.fullmatch(event_id) for event_id in identifiers):
        raise ReleaseValidationError("Generated public identity does not match its pattern")
    return identifiers


def _inspect_files(root: Path) -> set[str]:
    """Return all files without following links; reject unsafe package topology."""

    files: set[str] = set()
    inodes: set[tuple[int, int]] = set()
    for current, directories, names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        for name in [*directories, *names]:
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            try:
                info = path.lstat()
            except OSError as exc:
                raise ReleaseValidationError(f"Unable to inspect package path: {relative}") from exc
            if stat.S_ISLNK(info.st_mode):
                raise ReleaseValidationError(f"Release package contains a symlink: {relative}")
            if name in directories:
                if not stat.S_ISDIR(info.st_mode):
                    raise ReleaseValidationError(f"Release package has a non-directory: {relative}")
                continue
            if not stat.S_ISREG(info.st_mode):
                raise ReleaseValidationError(f"Release package has a non-regular file: {relative}")
            inode = (info.st_dev, info.st_ino)
            if info.st_nlink != 1 or inode in inodes:
                raise ReleaseValidationError(f"Release package contains a hard link: {relative}")
            inodes.add(inode)
            files.add(relative)
    return files


def _validate_package_checksums(
    root: Path, contract: dict[str, Any]
) -> tuple[set[str], dict[str, str], str]:
    files = _inspect_files(root)
    declared = contract["artifacts"]["package_checksums"]
    checksum_relative = declared["path"]
    checksum_path = _resolve_local(root, checksum_relative, label="package_checksums")
    if checksum_relative not in files:
        raise ReleaseValidationError("Missing package SHA256SUMS")
    observed_checksum_hash = _sha256_file(checksum_path)
    if observed_checksum_hash != declared["sha256"]:
        raise ReleaseValidationError("SHA-256 mismatch for package SHA256SUMS")
    try:
        raw_lines = checksum_path.read_bytes().splitlines(keepends=True)
    except OSError as exc:
        raise ReleaseValidationError("Unable to read package SHA256SUMS") from exc
    if len(raw_lines) != declared["entries"]:
        raise ReleaseValidationError("SHA256SUMS entry count is not exact")
    entries: dict[str, str] = {}
    ordered_paths: list[str] = []
    for line_number, line in enumerate(raw_lines, start=1):
        if not line.endswith(b"\n") or line.count(b"\n") != 1 or b"\r" in line:
            raise ReleaseValidationError(f"Malformed SHA256SUMS framing at line {line_number}")
        try:
            text = line[:-1].decode("ascii")
        except UnicodeDecodeError as exc:
            raise ReleaseValidationError("SHA256SUMS must be ASCII") from exc
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", text)
        if not match:
            raise ReleaseValidationError(f"Malformed SHA256SUMS line {line_number}")
        digest, relative = match.groups()
        normalized = _safe_relative(relative, label="SHA256SUMS entry")
        if normalized != relative or relative == checksum_relative or relative in entries:
            raise ReleaseValidationError(f"Invalid or duplicate SHA256SUMS path: {relative}")
        entries[relative] = digest
        ordered_paths.append(relative)
    if ordered_paths != sorted(ordered_paths):
        raise ReleaseValidationError("SHA256SUMS paths are not in bytewise lexical order")
    expected_files = files - {checksum_relative}
    if set(entries) != expected_files:
        missing = sorted(expected_files - set(entries))
        extra = sorted(set(entries) - expected_files)
        raise ReleaseValidationError(
            f"SHA256SUMS file closure mismatch missing={missing} extra={extra}"
        )
    for relative, expected_hash in entries.items():
        path = _resolve_local(root, relative, label="SHA256SUMS entry")
        if _sha256_file(path) != expected_hash:
            raise ReleaseValidationError(f"SHA256SUMS payload mismatch: {relative}")

    expected_parquets = {spec["path"] for spec in TABLE_CONTRACTS.values()}
    observed_parquets = {relative for relative in files if relative.endswith(".parquet")}
    if observed_parquets != expected_parquets:
        raise ReleaseValidationError("Package must contain exactly five declared Parquet files")
    retired = [
        relative
        for relative in files
        if "draft_unavailable" in relative.lower()
        or "draft_availability" in relative.lower()
    ]
    if retired:
        raise ReleaseValidationError(f"Package contains retired Draft assets: {retired}")
    return files, entries, observed_checksum_hash


def _validate_direct_topology(root: Path, event_ids: list[str]) -> None:
    draft_root = root / "draft_events"
    if draft_root.is_symlink() or not draft_root.is_dir():
        raise ReleaseValidationError("draft_events must be a real directory")
    try:
        entries = list(draft_root.iterdir())
    except OSError as exc:
        raise ReleaseValidationError("Unable to inspect direct Draft topology") from exc
    names = {entry.name for entry in entries}
    expected = set(event_ids)
    if names != expected or len(entries) != len(expected):
        raise ReleaseValidationError("Direct Draft directory identity closure is not exact")
    for event_id in event_ids:
        directory = draft_root / event_id
        if directory.is_symlink() or not directory.is_dir():
            raise ReleaseValidationError(f"Draft event path is not a real directory: {event_id}")
        children = list(directory.iterdir())
        if len(children) != 1 or children[0].name != "draft_epg.json":
            raise ReleaseValidationError(
                f"Draft event directory must contain exactly draft_epg.json: {event_id}"
            )
        info = children[0].lstat()
        if (
            stat.S_ISLNK(info.st_mode)
            or not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
        ):
            raise ReleaseValidationError(f"Direct Draft file is unsafe: {event_id}")


def _validate_source_hashes(
    root: Path, contract: dict[str, Any], event_ids: list[str]
) -> list[dict[str, str]]:
    declared = contract["artifacts"]["draft_source_hashes"]
    path = _resolve_local(root, declared["path"], label="draft_source_hashes")
    if not path.is_file() or _sha256_file(path) != declared["sha256"]:
        raise ReleaseValidationError("SHA-256 mismatch for Draft source-hash CSV")
    raw_lines = path.read_bytes().splitlines(keepends=True)
    expected_header = (",".join(SOURCE_HASH_FIELDS) + "\n").encode("ascii")
    if (
        len(raw_lines) != declared["rows"] + 1
        or not raw_lines
        or raw_lines[0] != expected_header
        or any(not line.endswith(b"\n") or b"\r" in line for line in raw_lines)
    ):
        raise ReleaseValidationError("Draft source-hash CSV framing/header is not exact")
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != SOURCE_HASH_FIELDS:
                raise ReleaseValidationError("Draft source-hash CSV header is not exact")
            rows = [dict(row) for row in reader]
    except ReleaseValidationError:
        raise
    except Exception as exc:
        raise ReleaseValidationError("Unable to parse Draft source-hash CSV") from exc
    if len(rows) != len(event_ids):
        raise ReleaseValidationError("Draft source-hash CSV row count is not exact")
    if [row["public_event_id"] for row in rows] != event_ids:
        raise ReleaseValidationError("Draft source-hash CSV event order/closure is not exact")
    source_hashes: set[str] = set()
    sanitized_hashes: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if tuple(row) != SOURCE_HASH_FIELDS:
            raise ReleaseValidationError("Draft source-hash CSV field order is not exact")
        if row["draft_record_index"] != str(index):
            raise ReleaseValidationError("draft_record_index is not one-based and contiguous")
        source_hash = row["source_payload_sha256"]
        sanitized_hash = row["sanitized_record_sha256"]
        if not SHA256_PATTERN.fullmatch(source_hash) or not SHA256_PATTERN.fullmatch(
            sanitized_hash
        ):
            raise ReleaseValidationError("Draft source-hash CSV contains a malformed hash")
        if source_hash in source_hashes or sanitized_hash in sanitized_hashes:
            raise ReleaseValidationError("Draft source-hash CSV hashes are not unique")
        source_hashes.add(source_hash)
        sanitized_hashes.add(sanitized_hash)
    return rows


def _recursive_count(value: Any, keys: set[str]) -> int:
    if isinstance(value, dict):
        return sum(
            (len(child) if key in keys and isinstance(child, list) else 0)
            + _recursive_count(child, keys)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return sum(_recursive_count(item, keys) for item in value)
    return 0


def _display_value(value: Any) -> str | None:
    if isinstance(value, dict):
        return _display_value(value.get("value"))
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        text = str(value).strip()
        return text or None
    return None


def _unknown_time(value: Any) -> bool:
    text = _display_value(value)
    return text is None or text.lower() in {
        "unknown",
        "none",
        "null",
        "n/a",
        "na",
        "unspecified",
    }


def _time_anchors(value: Any) -> list[str]:
    anchors: list[str] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if "timestamp" in node:
                text = _display_value(node.get("timestamp"))
                if text and not _unknown_time(text) and text not in anchors:
                    anchors.append(text)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return anchors


def _boundary_status(start: Any, end: Any, anchors: list[str]) -> str:
    start_known = not _unknown_time(start)
    end_known = not _unknown_time(end)
    if start_known and end_known:
        return "explicit_boundary"
    if start_known or end_known:
        return "partial_boundary"
    return "unknown_boundary_with_action_anchors" if anchors else "unknown_boundary_no_action_anchors"


def _graph_summary(event: dict[str, Any]) -> dict[str, Any]:
    stages = event.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ReleaseValidationError("Public Draft EPG stages must be a non-empty array")
    anchors = _time_anchors(event)
    return {
        "stage_count": len(stages),
        "episode_count": _recursive_count(stages, {"episodes"}),
        "participant_count": _recursive_count(stages, {"participants"}),
        "action_count": _recursive_count(stages, {"actions"}),
        "transaction_count": _recursive_count(stages, {"transactions"}),
        "relation_count": _recursive_count(stages, {"participant_relations", "relations"}),
        "event_start_time": _display_value(event.get("start_time")),
        "event_end_time": _display_value(event.get("end_time")),
        "event_boundary_time_status": _boundary_status(
            event.get("start_time"), event.get("end_time"), anchors
        ),
        "known_action_time_anchor_count": len(anchors),
        "known_action_time_anchors": anchors,
        "relative_order_available": len(stages) > 1,
    }


def _stage_rows(event_id: str, event: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    stages = event["stages"]
    relative_order = len(stages) > 1
    for index, stage in enumerate(stages, start=1):
        if not isinstance(stage, dict):
            raise ReleaseValidationError(f"Draft stage is not an object: {event_id}:{index}")
        stage_id = _display_value(stage.get("stage_id") or stage.get("id"))
        if not stage_id:
            raise ReleaseValidationError(f"Draft stage ID is absent: {event_id}:{index}")
        start = _display_value(stage.get("start_time") or stage.get("stage_start_time"))
        end = _display_value(stage.get("end_time") or stage.get("stage_end_time"))
        anchors = _time_anchors(stage)
        result.append(
            {
                "public_event_id": event_id,
                "event_id": event_id,
                "stage_id": stage_id,
                "stage_index": index,
                "stage_title": _display_value(
                    stage.get("stage_title") or stage.get("title") or stage.get("name")
                ),
                "stage_start_time": start,
                "stage_end_time": end,
                "stage_boundary_time_status": _boundary_status(start, end, anchors),
                "episode_count": _recursive_count(stage, {"episodes"}),
                "participant_count": _recursive_count(stage, {"participants"}),
                "action_count": _recursive_count(stage, {"actions"}),
                "transaction_count": _recursive_count(stage, {"transactions"}),
                "relation_count": _recursive_count(
                    stage, {"participant_relations", "relations"}
                ),
                "known_action_time_anchor_count": len(anchors),
                "known_action_time_anchors": anchors,
                "relative_order_available": relative_order,
                "schema_version": TABLE_CONTRACTS["event_stages"]["schema_version"],
            }
        )
    if len({row["stage_id"] for row in result}) != len(result):
        raise ReleaseValidationError(f"Draft stage IDs are not unique: {event_id}")
    return result


def _validate_wrappers(
    root: Path,
    contract: dict[str, Any],
    event_ids: list[str],
    source_rows: list[dict[str, str]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], str]:
    declared = contract["artifacts"]["aggregate_drafts"]
    aggregate_path = _resolve_local(root, declared["path"], label="aggregate_drafts")
    if not aggregate_path.is_file() or _sha256_file(aggregate_path) != declared["sha256"]:
        raise ReleaseValidationError("SHA-256 mismatch for aggregate Draft JSONL")
    aggregate_lines = aggregate_path.read_bytes().splitlines(keepends=True)
    if len(aggregate_lines) != declared["rows"]:
        raise ReleaseValidationError("Aggregate Draft JSONL row count is not exact")

    summaries: dict[str, dict[str, Any]] = {}
    expected_stage_rows: list[dict[str, Any]] = []
    ledger = hashlib.sha256()
    for event_id, line, source_row in zip(
        event_ids, aggregate_lines, source_rows, strict=True
    ):
        if not line.endswith(b"\n") or line.count(b"\n") != 1 or b"\r" in line:
            raise ReleaseValidationError(f"Aggregate Draft framing is not exact: {event_id}")
        direct_path = root / "draft_events" / event_id / "draft_epg.json"
        try:
            direct_bytes = direct_path.read_bytes()
        except OSError as exc:
            raise ReleaseValidationError(f"Missing direct Draft EPG: {event_id}") from exc
        if direct_bytes != line:
            raise ReleaseValidationError(f"Aggregate/direct Draft byte mismatch: {event_id}")
        body = line[:-1]
        try:
            wrapper = json.loads(body.decode("utf-8"))
        except Exception as exc:
            raise ReleaseValidationError(f"Invalid public Draft JSON: {event_id}") from exc
        if not isinstance(wrapper, dict) or set(wrapper) != WRAPPER_FIELDS:
            raise ReleaseValidationError(f"Public Draft wrapper field set is not exact: {event_id}")
        if _canonical_json_bytes(wrapper) != body:
            raise ReleaseValidationError(f"Public Draft is not canonical JSON: {event_id}")
        sanitized_hash = _sha256_bytes(body)
        if sanitized_hash != source_row["sanitized_record_sha256"]:
            raise ReleaseValidationError(f"Public Draft sanitized hash mismatch: {event_id}")
        if (
            wrapper.get("public_event_id") != event_id
            or wrapper.get("event_id") != event_id
        ):
            raise ReleaseValidationError(f"Public Draft identity mismatch: {event_id}")
        if {key: wrapper.get(key) for key in WRAPPER_METADATA} != WRAPPER_METADATA:
            raise ReleaseValidationError(f"Public Draft wrapper metadata mismatch: {event_id}")
        if wrapper.get("source_payload_sha256") != source_row["source_payload_sha256"]:
            raise ReleaseValidationError(f"Public Draft source hash mismatch: {event_id}")
        if not isinstance(wrapper.get("source_event_label"), str) or not wrapper[
            "source_event_label"
        ].strip():
            raise ReleaseValidationError(f"Public Draft source label is invalid: {event_id}")
        redactions = wrapper.get("redaction_counts")
        if not isinstance(redactions, dict) or any(
            not isinstance(key, str)
            or not key
            or isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for key, value in redactions.items()
        ):
            raise ReleaseValidationError(f"Public Draft redaction counts are invalid: {event_id}")
        event = wrapper.get("event")
        if not isinstance(event, dict) or event.get("event_id") != event_id:
            raise ReleaseValidationError(f"Public nested event identity mismatch: {event_id}")
        summaries[event_id] = _graph_summary(event)
        expected_stage_rows.extend(_stage_rows(event_id, event))
        ledger.update(f"{event_id}\t{sanitized_hash}\n".encode("ascii"))
    return summaries, expected_stage_rows, ledger.hexdigest()


def _expected_arrow_schema(columns: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    return tuple(
        (
            column,
            "bool"
            if column in BOOL_COLUMNS
            else "int64"
            if column in INT64_COLUMNS
            else "string",
        )
        for column in columns
    )


def _read_tables(
    root: Path, contract: dict[str, Any]
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
    rows: dict[str, list[dict[str, Any]]] = {}
    hashes: dict[str, str] = {}
    for name, expected in TABLE_CONTRACTS.items():
        declared = contract["tables"][name]
        path = _resolve_local(root, declared["path"], label=f"viewer table {name}")
        if not path.is_file():
            raise ReleaseValidationError(f"Missing required viewer Parquet: {name}")
        observed_hash = _sha256_file(path)
        if observed_hash != declared["sha256"]:
            raise ReleaseValidationError(f"SHA-256 mismatch for {name}")
        try:
            schema = parquet.read_schema(path)
            table = parquet.read_table(path)
        except Exception as exc:
            raise ReleaseValidationError(f"Unable to read viewer Parquet: {name}") from exc
        observed_schema = tuple((field.name, str(field.type)) for field in schema)
        if observed_schema != _expected_arrow_schema(expected["columns"]):
            raise ReleaseValidationError(f"Ordered Arrow schema mismatch for {name}")
        if table.num_rows != declared["rows"]:
            raise ReleaseValidationError(f"Row-count mismatch for {name}")
        values = table.to_pylist()
        if any(
            row.get("schema_version") != expected["schema_version"]
            for row in values
        ):
            raise ReleaseValidationError(f"Schema-version values mismatch for {name}")
        rows[name] = values
        hashes[name] = observed_hash
    return rows, hashes


def _parse_anchors(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, str):
        raise ReleaseValidationError(f"Anchor mirror is not a string: {label}")
    anchors = [] if not value else value.split(" | ")
    if any(not anchor or " | " in anchor for anchor in anchors) or len(anchors) != len(
        set(anchors)
    ):
        raise ReleaseValidationError(f"Anchor mirror is malformed: {label}")
    return anchors


def _compare_derived_row(
    actual: dict[str, Any], expected: dict[str, Any], *, label: str
) -> None:
    if set(actual) != set(expected):
        raise ReleaseValidationError(f"Derived row field set mismatch: {label}")
    actual_anchors = _parse_anchors(actual["known_action_time_anchors"], label=label)
    expected_anchors = expected["known_action_time_anchors"]
    if (
        len(actual_anchors) != actual["known_action_time_anchor_count"]
        or len(expected_anchors) != expected["known_action_time_anchor_count"]
        or set(actual_anchors) != set(expected_anchors)
    ):
        raise ReleaseValidationError(f"Derived anchor closure mismatch: {label}")
    actual_without = dict(actual)
    expected_without = dict(expected)
    actual_without.pop("known_action_time_anchors")
    expected_without.pop("known_action_time_anchors")
    if actual_without != expected_without:
        raise ReleaseValidationError(f"Derived graph row mismatch: {label}")


def _validate_table_closure(
    tables: dict[str, list[dict[str, Any]]],
    event_ids: list[str],
    summaries: dict[str, dict[str, Any]],
    expected_stage_rows: list[dict[str, Any]],
    contract: dict[str, Any],
) -> dict[str, int]:
    gallery = tables["event_gallery"]
    catalog = tables["event_catalog"]
    instances = tables["event_instances"]
    stages = tables["event_stages"]
    summary_rows = tables["finalcascade_summary"]
    for name, rows in (
        ("event_gallery", gallery),
        ("event_catalog", catalog),
        ("event_instances", instances),
        ("finalcascade_summary", summary_rows),
    ):
        if [row["public_event_id"] for row in rows] != event_ids:
            raise ReleaseValidationError(f"Public event ID order/closure mismatch in {name}")
        if len({row["public_event_id"] for row in rows}) != len(rows):
            raise ReleaseValidationError(f"Duplicate public event identity in {name}")
    for name, rows in (
        ("event_catalog", catalog),
        ("event_instances", instances),
        ("finalcascade_summary", summary_rows),
        ("event_stages", stages),
    ):
        if any(row["event_id"] != row["public_event_id"] for row in rows):
            raise ReleaseValidationError(f"event_id/public_event_id mismatch in {name}")

    catalog_by_id = {row["public_event_id"]: row for row in catalog}
    instances_by_id = {row["public_event_id"]: row for row in instances}
    for event_id in event_ids:
        catalog_row = catalog_by_id[event_id]
        instance_row = instances_by_id[event_id]
        gallery_row = gallery[int(event_id[-4:]) - 1]
        summary_row = summary_rows[int(event_id[-4:]) - 1]
        for field in ("title", "domain", "category", "event_descriptor"):
            if gallery_row[field] != catalog_row[field]:
                raise ReleaseValidationError(f"Gallery/catalog mismatch: {event_id}:{field}")
        for field in (
            "event_id",
            "title",
            "display_name",
            "event_descriptor",
            "domain",
            "category",
            "keywords",
            "has_gold_reference",
        ):
            if instance_row[field] != catalog_row[field]:
                raise ReleaseValidationError(f"Instance/catalog mismatch: {event_id}:{field}")
        for field in ("event_id", "title", "domain", "category"):
            if summary_row[field] != catalog_row[field]:
                raise ReleaseValidationError(f"Summary/catalog mismatch: {event_id}:{field}")
        if catalog_row["has_gold_reference"] is not True:
            raise ReleaseValidationError(f"Catalog Gold-reference flag is not true: {event_id}")
        access = {
            "finalcascade_access_level": "public_sanitized_full_graph",
            "gold_reference_access_level": "manual_gated_companion",
            "evidence_context_access_level": "not_included_in_this_release",
        }
        if instance_row["has_gold_reference"] is not True or {
            key: instance_row[key] for key in access
        } != access:
            raise ReleaseValidationError(f"Instance access contract mismatch: {event_id}")
        if not isinstance(catalog_row["keywords"], str) or not catalog_row[
            "keywords"
        ].strip():
            raise ReleaseValidationError(f"Catalog keywords are empty: {event_id}")
        if (
            catalog_row["stage_count"] != summaries[event_id]["stage_count"]
            or catalog_row["episode_count"] != summaries[event_id]["episode_count"]
        ):
            raise ReleaseValidationError(f"Catalog graph count mismatch: {event_id}")
        expected_summary = {
            "public_event_id": event_id,
            "event_id": event_id,
            "title": catalog_row["title"],
            "domain": catalog_row["domain"],
            "category": catalog_row["category"],
            **summaries[event_id],
            "schema_version": TABLE_CONTRACTS["finalcascade_summary"]["schema_version"],
        }
        _compare_derived_row(
            summary_row, expected_summary, label=f"finalcascade_summary:{event_id}"
        )

    if len(stages) != len(expected_stage_rows):
        raise ReleaseValidationError("Stage Parquet/wrapper row count does not close")
    for row_number, (actual, expected) in enumerate(
        zip(stages, expected_stage_rows, strict=True), start=1
    ):
        _compare_derived_row(actual, expected, label=f"event_stages:{row_number}")

    graph_totals = {
        column: sum(int(summary[column]) for summary in summaries.values())
        for column in GRAPH_COUNT_COLUMNS
    }
    for count_key, column in COUNT_TO_GRAPH_COLUMN.items():
        if graph_totals[column] != contract["counts"][count_key]:
            raise ReleaseValidationError(f"Release graph total mismatch: {count_key}")
    if len({row["public_event_id"] for row in stages}) != contract["counts"][
        "stage_events"
    ]:
        raise ReleaseValidationError("Stage-event coverage count does not close")
    return graph_totals


def validate_release(
    dataset_root: Path | str,
    contract_path: Path | str = DEFAULT_CONTRACT,
    *,
    require_published: bool = False,
) -> dict[str, Any]:
    """Validate one explicit local public Dataset root and return a stable receipt."""

    supplied_root = Path(dataset_root).expanduser().absolute()
    if supplied_root.is_symlink() or not supplied_root.is_dir():
        raise ReleaseValidationError("Dataset root must be an existing real directory")
    root = supplied_root.resolve()
    contract, published = _load_contract(
        Path(contract_path).expanduser(), require_published=require_published
    )
    event_ids = _expected_event_ids(contract)
    files, checksum_entries, package_checksum_hash = _validate_package_checksums(
        root, contract
    )
    _validate_direct_topology(root, event_ids)
    source_rows = _validate_source_hashes(root, contract, event_ids)
    summaries, expected_stages, draft_ledger = _validate_wrappers(
        root, contract, event_ids, source_rows
    )
    table_rows, table_hashes = _read_tables(root, contract)
    graph_totals = _validate_table_closure(
        table_rows, event_ids, summaries, expected_stages, contract
    )
    return {
        "all_checks_passed": True,
        "contract_version": contract["contract_version"],
        "dataset_repo": contract["dataset_repo"],
        "dataset_revision": contract["dataset_revision"],
        "publication_state": "published" if published else "local_candidate",
        "immutable_revision_bound": published,
        "counts": dict(contract["counts"]),
        "graph_totals": graph_totals,
        "table_sha256": dict(sorted(table_hashes.items())),
        "aggregate_sha256": contract["artifacts"]["aggregate_drafts"]["sha256"],
        "source_hash_manifest_sha256": contract["artifacts"]["draft_source_hashes"][
            "sha256"
        ],
        "package_sha256sums_sha256": package_checksum_hash,
        "package_checksum_entries": len(checksum_entries),
        "package_files_including_sha256sums": len(files),
        "draft_ledger_sha256": draft_ledger,
        "gold_records_accessed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_root", type=Path)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument(
        "--require-published",
        action="store_true",
        help="fail unless dataset_revision is an immutable lowercase 40-hex revision",
    )
    args = parser.parse_args()
    try:
        receipt = validate_release(
            args.dataset_root,
            args.contract,
            require_published=args.require_published,
        )
    except ReleaseValidationError as exc:
        parser.error(str(exc))
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
