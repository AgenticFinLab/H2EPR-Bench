#!/usr/bin/env python3
"""Build a presentation-only H²EPR-Bench Dataset release candidate.

The command starts from a complete validated Dataset tree, refreshes its
reader-facing documents and visual naming, and then regenerates the
presentation asset provenance, package manifest, and SHA256SUMS closure.
Dataset records, tables, schemas, and Draft EPGs are copied without
transformation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CARD_SOURCE_ROOT = ROOT / "datasets" / "h2epr_bench" / "huggingface"
CARD_ASSETS = (
    "h2epr-benchmark-overview.svg",
    "h2epr-overview.svg",
)
PRESENTATION_DOCUMENTS = ("README.md", "LICENSE.md")
RETIRED_CARD_ASSETS = (
    "h2epr_epg_overview.png",
    "unified3000_benchmark_profile.png",
)
PRESENTATION_PATH_RENAMES = {
    "assets/charts/unified3000_category_distribution.png": "assets/charts/category-distribution.png",
    "assets/charts/unified3000_domain_distribution.png": "assets/charts/domain-distribution.png",
    "assets/charts/unified3000_draft_stage_distribution.png": "assets/charts/draft-stage-distribution.png",
    "manifests/redaction_report_unified3000.json": "manifests/redaction_report.json",
}
RELEASE_METADATA_PATHS = (
    "data/statistics/benchmark_totals.json",
    "manifests/redaction_report.json",
    "manifests/source_identities.json",
    "manifests/validation_report.json",
)
CHART_GENERATOR_PATH = "scripts/generate_dataset_card_charts.py"
MANIFEST_PATH = "manifests/package_manifest.json"
PROVENANCE_PATH = "manifests/dataset_card_asset_provenance.json"
CHECKSUM_PATH = "SHA256SUMS"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def replace_exact_text(path: Path, replacements: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    for previous, replacement in replacements.items():
        if previous not in text:
            raise ValueError(f"expected presentation text is missing in {path}: {previous!r}")
        text = text.replace(previous, replacement)
    path.write_text(text, encoding="utf-8")


def inspect_regular_tree(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, directories, names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        for name in [*directories, *names]:
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise ValueError(f"source tree contains a symlink: {relative}")
            if name in directories:
                if not stat.S_ISDIR(info.st_mode):
                    raise ValueError(f"source tree contains a non-directory: {relative}")
                continue
            if not stat.S_ISREG(info.st_mode):
                raise ValueError(f"source tree contains a non-regular file: {relative}")
            files.append(path)
    return sorted(files)


def file_records(root: Path) -> list[dict[str, Any]]:
    excluded = {MANIFEST_PATH, CHECKSUM_PATH}
    return [
        {
            "bytes": path.stat().st_size,
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
        }
        for path in inspect_regular_tree(root)
        if path.relative_to(root).as_posix() not in excluded
    ]


def checksum_payload(root: Path) -> str:
    return "".join(
        f"{sha256_file(path)}  {path.relative_to(root).as_posix()}\n"
        for path in inspect_regular_tree(root)
        if path.relative_to(root).as_posix() != CHECKSUM_PATH
    )


def update_presentation_files(root: Path) -> None:
    for name in PRESENTATION_DOCUMENTS:
        shutil.copy2(CARD_SOURCE_ROOT / name, root / name)

    for previous, replacement in PRESENTATION_PATH_RENAMES.items():
        source = root / previous
        target = root / replacement
        if not source.is_file() or target.exists():
            raise ValueError(f"unsafe presentation path rename: {previous} -> {replacement}")
        source.rename(target)

    replace_exact_text(
        root / CHART_GENERATOR_PATH,
        {
            "classification-free Unified-3000 v2 RC": "H²EPR-Bench Dataset",
            "/tmp/h2epr-unified3000-v2-mplconfig": "/tmp/h2epr-bench-mplconfig",
            "H2EPR-Bench Unified-3000 v2 deterministic charts": "H²EPR-Bench deterministic charts",
            "unified3000_domain_distribution.png": "domain-distribution.png",
            "unified3000_category_distribution.png": "category-distribution.png",
            "unified3000_draft_stage_distribution.png": "draft-stage-distribution.png",
        },
    )
    for relative in RELEASE_METADATA_PATHS:
        replace_exact_text(
            root / relative,
            {'"release": "unified-3000-v2"': '"release": "h2epr-bench"'},
        )

    card_root = root / "assets" / "card"
    for name in RETIRED_CARD_ASSETS:
        path = card_root / name
        if not path.is_file():
            raise ValueError(f"expected predecessor card asset is missing: {name}")
        path.unlink()
    for name in CARD_ASSETS:
        source = CARD_SOURCE_ROOT / "assets" / "card" / name
        if not source.is_file():
            raise ValueError(f"approved card asset is missing: {source}")
        shutil.copy2(source, card_root / name)

    provenance_path = root / PROVENANCE_PATH
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["release"] = "h2epr-bench"
    provenance["card_assets"] = [
        {
            "asset": f"assets/card/{name}",
            "sha256": sha256_file(card_root / name),
        }
        for name in CARD_ASSETS
    ]
    provenance["generated_charts"] = [
        {
            "asset": replacement,
            "sha256": sha256_file(root / replacement),
        }
        for previous, replacement in PRESENTATION_PATH_RENAMES.items()
        if previous.startswith("assets/charts/")
    ]
    generator_sha256 = sha256_file(root / CHART_GENERATOR_PATH)
    provenance["generator_sha256"] = generator_sha256
    write_json(provenance_path, provenance)

    source_identities_path = root / "manifests" / "source_identities.json"
    source_identities = json.loads(source_identities_path.read_text(encoding="utf-8"))
    source_identities["chart_generator_sha256"] = generator_sha256
    write_json(source_identities_path, source_identities)


def refresh_integrity_files(root: Path) -> dict[str, Any]:
    manifest_path = root / MANIFEST_PATH
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["release"] = "h2epr-bench"
    records = file_records(root)
    manifest["file_count_excluding_manifest_and_checksums"] = len(records)
    manifest["files"] = records
    write_json(manifest_path, manifest)

    checksum_path = root / CHECKSUM_PATH
    checksum_path.write_text(checksum_payload(root), encoding="ascii")
    return {
        "checksum_entries": len(checksum_path.read_text(encoding="ascii").splitlines()),
        "sha256sums_sha256": sha256_file(checksum_path),
        "tree_bytes": sum(path.stat().st_size for path in inspect_regular_tree(root)),
        "tree_files": len(inspect_regular_tree(root)),
    }


def build(source: Path, output: Path) -> dict[str, Any]:
    source = source.resolve(strict=True)
    output = output.resolve(strict=False)
    if source.is_symlink() or not source.is_dir():
        raise ValueError("source Dataset root must be a real directory")
    inspect_regular_tree(source)
    if output.exists():
        raise ValueError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent)
    )
    try:
        shutil.copytree(source, staging, dirs_exist_ok=True, copy_function=shutil.copy2)
        update_presentation_files(staging)
        result = refresh_integrity_files(staging)
        os.replace(staging, output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {
        "data_transformations": 0,
        "output_root": str(output),
        "presentation_assets": list(CARD_ASSETS),
        "retired_card_assets": list(RETIRED_CARD_ASSETS),
        "source_root": str(source),
        "status": "materialized",
        **result,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dataset", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(
        json.dumps(
            build(args.source_dataset, args.output_root),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
