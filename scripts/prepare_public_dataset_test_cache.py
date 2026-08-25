#!/usr/bin/env python3
"""Download the immutable public Dataset subset needed by Explorer tests.

The revision comes from the Unified-3000 v2 release contract.  A staged
contract with ``dataset_revision: null`` deliberately fails closed; this
script must never turn a mutable branch or an unpublished candidate into an
Explorer test oracle.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from huggingface_hub import snapshot_download


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = (
    REPO_ROOT
    / "datasets"
    / "h2epr_bench"
    / "manifests"
    / "unified3000_release_contract.json"
)
IMMUTABLE_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
TEST_FILES = (
    "data/viewer_mirrors/event_gallery.parquet",
    "data/viewer_mirrors/event_catalog.parquet",
    "data/viewer_mirrors/event_instances.parquet",
    "data/viewer_mirrors/finalcascade_summary.parquet",
    "data/viewer_mirrors/event_stages.parquet",
    "manifests/draft_source_hashes.csv",
    "draft_events/H2EPR-0001/draft_epg.json",
    "draft_events/H2EPR-1000/draft_epg.json",
)


def load_published_identity(contract_path: Path) -> tuple[str, str]:
    try:
        payload = json.loads(contract_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"unable to read Unified-3000 release contract: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("Unified-3000 release contract must be a JSON object")
    repo = payload.get("dataset_repo")
    revision = payload.get("dataset_revision")
    if not isinstance(repo, str) or not repo.strip():
        raise SystemExit("Unified-3000 release contract has no Dataset repository")
    if not isinstance(revision, str) or not IMMUTABLE_REVISION_PATTERN.fullmatch(
        revision
    ):
        raise SystemExit(
            "Unified-3000 public Dataset is not pinned to an immutable 40-hex revision"
        )
    return repo, revision


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--local-files-only", action="store_true")
    args = parser.parse_args()
    dataset_repo, dataset_revision = load_published_identity(
        args.contract.expanduser().resolve()
    )
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=dataset_repo,
        repo_type="dataset",
        revision=dataset_revision,
        allow_patterns=list(TEST_FILES),
        local_dir=output,
        local_files_only=args.local_files_only,
    )
    missing = [relative for relative in TEST_FILES if not (output / relative).is_file()]
    if missing:
        raise SystemExit(f"pinned public Dataset test cache is incomplete: {missing}")
    print(
        json.dumps(
            {
                "dataset_repo": dataset_repo,
                "dataset_revision": dataset_revision,
                "files": list(TEST_FILES),
                "gold_records_accessed": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
