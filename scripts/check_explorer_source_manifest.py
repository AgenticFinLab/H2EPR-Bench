#!/usr/bin/env python3
"""Verify the exact Explorer source subtree and staged publication identity."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "manifests" / "explorer_space_source.json"
CONTRACT_PATH = (
    ROOT / "datasets" / "h2epr_bench" / "manifests" / "unified3000_release_contract.json"
)
CONSTANTS_PATH = (
    ROOT / "spaces" / "h2epr_bench_explorer" / "src" / "h2epr_explorer" / "constants.py"
)
EXPECTED_RELEASE_ID = "h2epr-unified3000-v2"
EXPECTED_DATASET_REPO = "AgenticFinLab/H2EPR-Bench"
EXPECTED_RC_TREE_SHA256 = "9b30d71eacbfa0e07539a5805a3cf05065e76199dfcf0272ef1d135c1098960e"
RELEASE_STATES = {"candidate", "dataset_published", "published"}
GATES = {"local", "deployment", "published"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path.relative_to(ROOT)}")
    return value


def _literal_constant(path: Path, name: str) -> Any:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in module.body:
        target: ast.expr | None = None
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        if isinstance(target, ast.Name) and target.id == name and value is not None:
            try:
                return ast.literal_eval(value)
            except (ValueError, TypeError) as error:
                relative = path.relative_to(ROOT)
                raise ValueError(f"{name} must be assigned a literal in {relative}") from error
    raise ValueError(f"missing constant {name} in {path.relative_to(ROOT)}")


def validate_release_identity(manifest: dict[str, Any], gate: str) -> None:
    if gate not in GATES:
        raise ValueError(f"invalid release gate: {gate!r}")
    if manifest.get("manifest_version") != 2:
        raise ValueError("unexpected Explorer source manifest version")
    if manifest.get("release_id") != EXPECTED_RELEASE_ID:
        raise ValueError("Explorer source manifest release_id is not Unified-3000 v2")
    if manifest.get("dataset_repo") != EXPECTED_DATASET_REPO:
        raise ValueError("Explorer source manifest dataset_repo mismatch")

    state = manifest.get("release_state")
    if state not in RELEASE_STATES:
        raise ValueError(f"invalid Explorer release_state: {state!r}")
    revision = manifest.get("dataset_revision")
    if revision is not None and not HEX40.fullmatch(revision):
        raise ValueError("dataset_revision must be null or a lowercase 40-hex commit")
    if state == "candidate" and revision is not None:
        raise ValueError("candidate Explorer source must not claim a published dataset revision")
    if state != "candidate" and revision is None:
        raise ValueError("a post-candidate Explorer source must pin a dataset revision")
    published_deployment = manifest.get("published_deployment")
    if state != "published" and published_deployment is not None:
        raise ValueError("only a published Explorer source may claim a deployed Space identity")
    if state == "published":
        if not isinstance(published_deployment, dict):
            raise ValueError("published Explorer source must bind its deployed Space identity")
        if published_deployment.get("dataset_revision") != revision:
            raise ValueError("published Space and Explorer source dataset revisions differ")
        if published_deployment.get("source_ledger_sha256") != manifest.get("ledger_sha256"):
            raise ValueError("published Space source ledger does not bind the local source ledger")
        for key in ("space_commit", "space_tree"):
            value = published_deployment.get(key)
            if not isinstance(value, str) or not HEX40.fullmatch(value):
                raise ValueError(f"published_deployment.{key} must be lowercase 40-hex")

    candidate = manifest.get("release_candidate")
    if not isinstance(candidate, dict):
        raise ValueError("missing release_candidate identity")
    for key in ("sha256sums_sha256", "tree_sha256"):
        if not isinstance(candidate.get(key), str) or not HEX64.fullmatch(candidate[key]):
            raise ValueError(f"release_candidate.{key} must be lowercase 64-hex")
        if candidate[key] != EXPECTED_RC_TREE_SHA256:
            raise ValueError(f"release_candidate.{key} is not the audited Unified-3000 v2 RC")
    if candidate["sha256sums_sha256"] != candidate["tree_sha256"]:
        raise ValueError("RC SHA256SUMS and package-tree identities diverge")

    rollback = manifest.get("rollback_baseline")
    if not isinstance(rollback, dict) or rollback.get("role") != "rollback_only":
        raise ValueError("the previous production binding must be explicitly rollback_only")
    rollback_revision = rollback.get("dataset_revision")
    if not isinstance(rollback_revision, str) or not HEX40.fullmatch(rollback_revision):
        raise ValueError("rollback dataset revision must be a lowercase 40-hex commit")
    for key in ("space_commit", "space_tree"):
        value = rollback.get(key)
        if not isinstance(value, str) or not HEX40.fullmatch(value):
            raise ValueError(f"rollback_baseline.{key} must be a lowercase 40-hex identity")
    if revision is not None and revision == rollback_revision:
        raise ValueError("rollback-only dataset revision cannot identify Unified-3000 v2")

    contract = _load_json(CONTRACT_PATH)
    if contract.get("contract_version") != "h2epr-unified3000-public-release-v2":
        raise ValueError("Explorer source is not bound to the Unified-3000 v2 contract")
    if contract.get("dataset_repo") != manifest["dataset_repo"]:
        raise ValueError("contract and Explorer source manifest dataset_repo values differ")
    if contract.get("dataset_revision") != revision:
        raise ValueError("contract and Explorer source manifest dataset_revision values differ")
    contract_tree = (
        contract.get("artifacts", {}).get("package_checksums", {}).get("sha256")
    )
    if contract_tree != candidate["tree_sha256"]:
        raise ValueError("contract package identity and Explorer release candidate differ")

    constants_repo = _literal_constant(CONSTANTS_PATH, "PUBLIC_DATASET_REPO")
    constants_revision = _literal_constant(CONSTANTS_PATH, "DEFAULT_PUBLIC_DATASET_REVISION")
    if constants_repo != manifest["dataset_repo"]:
        raise ValueError("Explorer constant and source manifest dataset repositories differ")
    if constants_revision != revision:
        raise ValueError("contract, Explorer constant, and source manifest revisions differ")

    if gate in {"deployment", "published"} and state not in {"dataset_published", "published"}:
        raise ValueError(f"{gate} gate rejects an unpublished release candidate")
    if gate == "published" and state != "published":
        raise ValueError("published gate requires release_state=published")


def validate_source_ledger(manifest: dict[str, Any]) -> tuple[int, str]:
    deployment_root_value = manifest.get("deployment_root")
    if deployment_root_value != "spaces/h2epr_bench_explorer":
        raise ValueError("deployment_root must be spaces/h2epr_bench_explorer")
    deployment_root = ROOT / deployment_root_value
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Explorer source files ledger must be a non-empty object")
    ledger_sha256 = manifest.get("ledger_sha256")
    if not isinstance(ledger_sha256, str) or not HEX64.fullmatch(ledger_sha256):
        raise ValueError("ledger_sha256 must be lowercase 64-hex")

    source_nodes = list(deployment_root.rglob("*"))
    unsafe_nodes = sorted(
        path.relative_to(deployment_root).as_posix()
        for path in source_nodes
        if path.is_symlink() or (not path.is_file() and not path.is_dir())
    )
    if unsafe_nodes:
        raise ValueError(
            f"Explorer source contains symlink or non-regular nodes: {unsafe_nodes}"
        )
    observed_files = sorted(
        path.relative_to(deployment_root).as_posix()
        for path in source_nodes
        if path.is_file() and "__pycache__" not in path.parts
    )
    expected_files = sorted(files)
    for relative in expected_files:
        path = Path(relative)
        expected_hash = files[relative]
        if path.is_absolute() or ".." in path.parts or "\\" in relative:
            raise ValueError(f"unsafe Explorer source ledger path: {relative!r}")
        if not isinstance(expected_hash, str) or not HEX64.fullmatch(expected_hash):
            raise ValueError(f"invalid Explorer source SHA-256 in ledger: {relative}")
    if observed_files != expected_files:
        raise ValueError(
            f"Explorer source path set mismatch: expected {expected_files}, observed {observed_files}"
        )

    ledger = hashlib.sha256()
    for relative in expected_files:
        observed_hash = sha256(deployment_root / relative)
        expected_hash = files[relative]
        if observed_hash != expected_hash:
            raise ValueError(f"Explorer source SHA-256 mismatch: {relative}")
        ledger.update(f"{observed_hash}  {relative}\n".encode("utf-8"))
    if ledger.hexdigest() != ledger_sha256:
        raise ValueError("Explorer source ledger SHA-256 mismatch")
    return len(expected_files), ledger.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gate",
        choices=("local", "deployment", "published"),
        default="local",
        help="local accepts an audited candidate; deployment/published require a pinned revision",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = _load_json(MANIFEST_PATH)
    try:
        validate_release_identity(manifest, args.gate)
        file_count, ledger_sha256 = validate_source_ledger(manifest)
    except ValueError as error:
        raise SystemExit(f"Explorer source validation failed: {error}") from error
    print(
        json.dumps(
            {
                "dataset_revision": manifest["dataset_revision"],
                "files": file_count,
                "gate": args.gate,
                "ledger_sha256": ledger_sha256,
                "release_state": manifest["release_state"],
                "tree_sha256": manifest["release_candidate"]["tree_sha256"],
                "status": "pass",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
