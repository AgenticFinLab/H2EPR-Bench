#!/usr/bin/env python3
"""Verify the exact deployable Explorer source subtree and its hash ledger."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "manifests" / "explorer_space_source.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    deployment_root = ROOT / manifest["deployment_root"]
    observed_files = sorted(
        path.relative_to(deployment_root).as_posix()
        for path in deployment_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )
    expected_files = sorted(manifest["files"])
    if observed_files != expected_files:
        raise SystemExit(
            f"Explorer source path set mismatch: expected {expected_files}, observed {observed_files}"
        )

    ledger = hashlib.sha256()
    for relative in expected_files:
        observed_hash = sha256(deployment_root / relative)
        expected_hash = manifest["files"][relative]
        if observed_hash != expected_hash:
            raise SystemExit(f"Explorer source SHA-256 mismatch: {relative}")
        ledger.update(f"{observed_hash}  {relative}\n".encode("utf-8"))
    if ledger.hexdigest() != manifest["ledger_sha256"]:
        raise SystemExit("Explorer source ledger SHA-256 mismatch")
    print(
        json.dumps(
            {
                "dataset_revision": manifest["dataset_revision"],
                "files": len(expected_files),
                "ledger_sha256": ledger.hexdigest(),
                "status": "pass",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
