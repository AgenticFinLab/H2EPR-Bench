#!/usr/bin/env python3
"""Validate one explicitly supplied H2EPR reference EPG JSON document."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any


EVENT_ID_PATTERN = re.compile(r"^H2EPR-[0-9]{4}$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
TOP_LEVEL_FIELDS = {
    "public_event_id",
    "canonical_event",
    "scope_boundary",
    "stages",
    "episodes",
    "participants",
    "actions",
    "outcomes",
    "structural_relations",
    "temporal_relations",
    "causal_relations",
    "mechanism_paths",
    "evidence_graph",
}


class ReferenceValidationError(ValueError):
    """A document violates the public reference EPG interface."""


def _object(
    value: Any,
    path: str,
    required: set[str],
    optional: set[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReferenceValidationError(f"{path} must be an object")
    allowed = required | (optional or set())
    missing = required - set(value)
    unexpected = set(value) - allowed
    if missing:
        raise ReferenceValidationError(f"{path} is missing fields: {sorted(missing)}")
    if unexpected:
        raise ReferenceValidationError(f"{path} has unexpected fields: {sorted(unexpected)}")
    return value


def _nonempty(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise ReferenceValidationError(f"{path} must be a non-empty string")
    return value


def _nullable_string(value: Any, path: str) -> None:
    if value is not None and not isinstance(value, str):
        raise ReferenceValidationError(f"{path} must be a string or null")


def _string_list(value: Any, path: str, *, minimum: int = 0) -> list[str]:
    if not isinstance(value, list) or len(value) < minimum:
        raise ReferenceValidationError(f"{path} must be an array with at least {minimum} items")
    result = [_nonempty(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if len(result) != len(set(result)):
        raise ReferenceValidationError(f"{path} must contain unique strings")
    return result


def _time_range(value: Any, path: str) -> None:
    row = _object(value, path, set(), {"start", "end", "precision", "note"})
    for field, item in row.items():
        _nullable_string(item, f"{path}.{field}")


def _optional_common(row: dict[str, Any], path: str, *, summary: bool = False) -> None:
    for field in ("description", "event_type", "summary"):
        if field in row:
            _nullable_string(row[field], f"{path}.{field}")
    if "time_range" in row:
        _time_range(row["time_range"], f"{path}.time_range")


def _unique_rows(rows: Any, path: str) -> tuple[list[dict[str, Any]], set[str]]:
    if not isinstance(rows, list):
        raise ReferenceValidationError(f"{path} must be an array")
    objects = []
    identifiers = []
    for index, value in enumerate(rows):
        if not isinstance(value, dict):
            raise ReferenceValidationError(f"{path}[{index}] must be an object")
        identifiers.append(_nonempty(value.get("id"), f"{path}[{index}].id"))
        objects.append(value)
    if len(identifiers) != len(set(identifiers)):
        raise ReferenceValidationError(f"{path} contains duplicate IDs")
    return objects, set(identifiers)


def _positive_index(value: Any, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ReferenceValidationError(f"{path} must be a positive integer")
    return value


def _validate_canonical_event(value: Any) -> None:
    row = _object(
        value,
        "canonical_event",
        {"name", "domain", "category"},
        {"aliases", "event_type", "summary", "time_range"},
    )
    for field in ("name", "domain", "category"):
        _nonempty(row[field], f"canonical_event.{field}")
    if "aliases" in row:
        _string_list(row["aliases"], "canonical_event.aliases")
    _optional_common(row, "canonical_event")


def _validate_scope(value: Any) -> None:
    row = _object(value, "scope_boundary", {"include", "exclude"})
    _nonempty(row["include"], "scope_boundary.include")
    _nonempty(row["exclude"], "scope_boundary.exclude")


def _validate_stages(value: Any) -> tuple[set[str], dict[str, int]]:
    rows, identifiers = _unique_rows(value, "stages")
    indices: dict[str, int] = {}
    for index, row in enumerate(rows):
        path = f"stages[{index}]"
        _object(row, path, {"id", "label", "sequence_index"}, {"summary", "time_range"})
        _nonempty(row["label"], f"{path}.label")
        indices[row["id"]] = _positive_index(row["sequence_index"], f"{path}.sequence_index")
        _optional_common(row, path)
    if sorted(indices.values()) != list(range(1, len(indices) + 1)):
        raise ReferenceValidationError("stages.sequence_index must be unique and contiguous")
    return identifiers, indices


def _validate_episodes(value: Any, stage_ids: set[str]) -> tuple[set[str], dict[str, str]]:
    rows, identifiers = _unique_rows(value, "episodes")
    stage_members: dict[str, list[int]] = {stage_id: [] for stage_id in stage_ids}
    episode_stage: dict[str, str] = {}
    for index, row in enumerate(rows):
        path = f"episodes[{index}]"
        _object(
            row,
            path,
            {"id", "label", "stage_id", "sequence_index"},
            {"summary", "time_range"},
        )
        _nonempty(row["label"], f"{path}.label")
        stage_id = _nonempty(row["stage_id"], f"{path}.stage_id")
        if stage_id not in stage_ids:
            raise ReferenceValidationError(f"{path}.stage_id is not a declared stage")
        stage_members[stage_id].append(
            _positive_index(row["sequence_index"], f"{path}.sequence_index")
        )
        episode_stage[row["id"]] = stage_id
        _optional_common(row, path)
    for stage_id, indices in stage_members.items():
        if sorted(indices) != list(range(1, len(indices) + 1)):
            raise ReferenceValidationError(
                f"episodes.sequence_index must be contiguous within {stage_id}"
            )
    return identifiers, episode_stage


def _validate_participants(value: Any) -> set[str]:
    rows, identifiers = _unique_rows(value, "participants")
    for index, row in enumerate(rows):
        path = f"participants[{index}]"
        _object(row, path, {"id", "label"}, {"type", "role"})
        _nonempty(row["label"], f"{path}.label")
        for field in ("type", "role"):
            if field in row:
                _nullable_string(row[field], f"{path}.{field}")
    return identifiers


def _validate_actions(
    value: Any, episode_ids: set[str], participant_ids: set[str]
) -> tuple[set[str], dict[str, str]]:
    rows, identifiers = _unique_rows(value, "actions")
    action_episode: dict[str, str] = {}
    for index, row in enumerate(rows):
        path = f"actions[{index}]"
        _object(
            row,
            path,
            {"id", "label", "episode_id", "actor_ids", "target_ids"},
            {"description", "time_range"},
        )
        _nonempty(row["label"], f"{path}.label")
        episode_id = _nonempty(row["episode_id"], f"{path}.episode_id")
        if episode_id not in episode_ids:
            raise ReferenceValidationError(f"{path}.episode_id is not a declared episode")
        for field in ("actor_ids", "target_ids"):
            values = _string_list(row[field], f"{path}.{field}")
            if not set(values) <= participant_ids:
                raise ReferenceValidationError(f"{path}.{field} contains an unknown participant")
        action_episode[row["id"]] = episode_id
        _optional_common(row, path)
    return identifiers, action_episode


def _validate_outcomes(
    value: Any, episode_ids: set[str], action_ids: set[str]
) -> set[str]:
    rows, identifiers = _unique_rows(value, "outcomes")
    for index, row in enumerate(rows):
        path = f"outcomes[{index}]"
        _object(
            row,
            path,
            {"id", "label", "producer_action_ids"},
            {"episode_id", "description"},
        )
        _nonempty(row["label"], f"{path}.label")
        producers = _string_list(row["producer_action_ids"], f"{path}.producer_action_ids")
        if not set(producers) <= action_ids:
            raise ReferenceValidationError(f"{path}.producer_action_ids contains an unknown action")
        episode_id = row.get("episode_id")
        _nullable_string(episode_id, f"{path}.episode_id")
        if episode_id is not None and episode_id not in episode_ids:
            raise ReferenceValidationError(f"{path}.episode_id is not a declared episode")
        if "description" in row:
            _nullable_string(row["description"], f"{path}.description")
    return identifiers


def _validate_relations(value: Any, path: str, node_ids: set[str]) -> set[str]:
    rows, identifiers = _unique_rows(value, path)
    for index, row in enumerate(rows):
        item_path = f"{path}[{index}]"
        _object(
            row,
            item_path,
            {"id", "from_id", "to_id", "label"},
            {"description"},
        )
        _nonempty(row["label"], f"{item_path}.label")
        for field in ("from_id", "to_id"):
            reference = _nonempty(row[field], f"{item_path}.{field}")
            if reference not in node_ids:
                raise ReferenceValidationError(f"{item_path}.{field} is not a declared node")
        if "description" in row:
            _nullable_string(row["description"], f"{item_path}.description")
    return identifiers


def _validate_mechanisms(
    value: Any, node_ids: set[str], relation_ids: set[str]
) -> set[str]:
    rows, identifiers = _unique_rows(value, "mechanism_paths")
    for index, row in enumerate(rows):
        path = f"mechanism_paths[{index}]"
        _object(row, path, {"id", "label", "node_ids", "relation_ids"})
        _nonempty(row["label"], f"{path}.label")
        nodes = _string_list(row["node_ids"], f"{path}.node_ids")
        relations = _string_list(row["relation_ids"], f"{path}.relation_ids")
        if not set(nodes) <= node_ids:
            raise ReferenceValidationError(f"{path}.node_ids contains an unknown node")
        if not set(relations) <= relation_ids:
            raise ReferenceValidationError(f"{path}.relation_ids contains an unknown relation")
    return identifiers


def _validate_evidence(value: Any, target_ids: set[str]) -> tuple[int, int]:
    graph = _object(value, "evidence_graph", {"evidence_nodes", "support_edges"})
    nodes, evidence_ids = _unique_rows(graph["evidence_nodes"], "evidence_graph.evidence_nodes")
    for index, row in enumerate(nodes):
        path = f"evidence_graph.evidence_nodes[{index}]"
        _object(row, path, {"id", "source_id"}, {"passage_id", "passage_sha256"})
        _nonempty(row["source_id"], f"{path}.source_id")
        if "passage_id" in row:
            _nullable_string(row["passage_id"], f"{path}.passage_id")
        if "passage_sha256" in row:
            digest = row["passage_sha256"]
            if digest is not None and (
                not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest)
            ):
                raise ReferenceValidationError(f"{path}.passage_sha256 is invalid")

    edges = graph["support_edges"]
    if not isinstance(edges, list):
        raise ReferenceValidationError("evidence_graph.support_edges must be an array")
    for index, value in enumerate(edges):
        path = f"evidence_graph.support_edges[{index}]"
        row = _object(value, path, {"target_id", "target_type", "evidence_ids"})
        target_id = _nonempty(row["target_id"], f"{path}.target_id")
        _nonempty(row["target_type"], f"{path}.target_type")
        if target_id not in target_ids:
            raise ReferenceValidationError(f"{path}.target_id is not a declared graph target")
        references = _string_list(row["evidence_ids"], f"{path}.evidence_ids", minimum=1)
        if not set(references) <= evidence_ids:
            raise ReferenceValidationError(f"{path}.evidence_ids contains an unknown evidence node")
    return len(nodes), len(edges)


def validate_reference_epg(document: Any) -> dict[str, Any]:
    """Validate one parsed reference EPG and return a content-only receipt."""

    payload = _object(document, "document", TOP_LEVEL_FIELDS)
    event_id = _nonempty(payload["public_event_id"], "public_event_id")
    if not EVENT_ID_PATTERN.fullmatch(event_id):
        raise ReferenceValidationError("public_event_id must match H2EPR-NNNN")
    number = int(event_id.rsplit("-", 1)[1])
    if not 1 <= number <= 3000:
        raise ReferenceValidationError("public_event_id is outside Unified-3000")

    _validate_canonical_event(payload["canonical_event"])
    _validate_scope(payload["scope_boundary"])
    stage_ids, _ = _validate_stages(payload["stages"])
    episode_ids, _ = _validate_episodes(payload["episodes"], stage_ids)
    participant_ids = _validate_participants(payload["participants"])
    action_ids, _ = _validate_actions(payload["actions"], episode_ids, participant_ids)
    outcome_ids = _validate_outcomes(payload["outcomes"], episode_ids, action_ids)

    node_sets = (stage_ids, episode_ids, participant_ids, action_ids, outcome_ids)
    all_node_ids: set[str] = set()
    for identifiers in node_sets:
        if all_node_ids & identifiers:
            raise ReferenceValidationError("Graph node IDs must be globally unique")
        all_node_ids.update(identifiers)

    relation_ids: set[str] = set()
    relation_counts = {}
    for field in ("structural_relations", "temporal_relations", "causal_relations"):
        identifiers = _validate_relations(payload[field], field, all_node_ids)
        if relation_ids & identifiers:
            raise ReferenceValidationError("Relation IDs must be globally unique")
        relation_ids.update(identifiers)
        relation_counts[field] = len(identifiers)
    mechanism_ids = _validate_mechanisms(
        payload["mechanism_paths"], all_node_ids, relation_ids
    )
    evidence_nodes, support_edges = _validate_evidence(
        payload["evidence_graph"], all_node_ids | mechanism_ids
    )

    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "public_event_id": event_id,
        "document_sha256": hashlib.sha256(canonical).hexdigest(),
        "counts": {
            "stages": len(stage_ids),
            "episodes": len(episode_ids),
            "participants": len(participant_ids),
            "actions": len(action_ids),
            "outcomes": len(outcome_ids),
            **relation_counts,
            "mechanism_paths": len(mechanism_ids),
            "evidence_nodes": evidence_nodes,
            "support_edges": support_edges,
        },
        "network_accessed": False,
    }


def load_reference_epg(path: Path | str) -> dict[str, Any]:
    """Load and validate exactly the local JSON document named by the caller."""

    document_path = Path(path).expanduser().resolve()
    if not document_path.is_file():
        raise ReferenceValidationError("Reference EPG path must name an existing local file")
    try:
        with document_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception as exc:
        raise ReferenceValidationError("Unable to parse the supplied reference EPG JSON") from exc
    return validate_reference_epg(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    args = parser.parse_args()
    print(json.dumps(load_reference_epg(args.document), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
