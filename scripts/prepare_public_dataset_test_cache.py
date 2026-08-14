#!/usr/bin/env python3
"""Download the minimal pinned public Dataset files needed by Explorer tests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from huggingface_hub import snapshot_download


PUBLIC_DATASET_REPO = "AgenticFinLab/H2EPR-Bench"
PUBLIC_DATASET_REVISION = "1d01f3649ace0301ac3bbe9ee875eea660347a29"
TEST_FILES = (
    "data/viewer_mirrors/event_catalog.parquet",
    "data/viewer_mirrors/event_instances.parquet",
    "data/viewer_mirrors/finalcascade_summary.parquet",
    "data/viewer_mirrors/draft_availability.parquet",
    "data/viewer_mirrors/event_stages.parquet",
    "draft_events/H2EPR-0001/draft_epg.json",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--local-files-only", action="store_true")
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=PUBLIC_DATASET_REPO,
        repo_type="dataset",
        revision=PUBLIC_DATASET_REVISION,
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
                "dataset_repo": PUBLIC_DATASET_REPO,
                "dataset_revision": PUBLIC_DATASET_REVISION,
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
