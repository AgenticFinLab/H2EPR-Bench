#!/usr/bin/env python3
"""Enforce the public monorepo privacy, payload, and size boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "scripts" / "public_release_size_policy.json"
TEXT_SUFFIXES = {
    "",
    ".css",
    ".csv",
    ".gitattributes",
    ".gitignore",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".svg",
    ".txt",
    ".yaml",
    ".yml",
}
FORBIDDEN_PATH_PARTS = {".local-runtime", "__pycache__", "credentials", "secrets"}
PRIVATE_PATTERNS = {
    "private key": re.compile(r"BEGIN (?:RSA|OPENSSH|EC) PRIVATE KEY"),
    "Hugging Face token": re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    "absolute Linux home": re.compile("/" + "home" + r"/[^/\s]+/"),
    "absolute macOS home": re.compile("/" + "Users" + r"/[^/\s]+/"),
    "absolute Windows path": re.compile(r"\b[A-Za-z]:\\\\(?:[^\s\\]+\\\\)+"),
    "ignored maintenance path": re.compile(re.escape(".local" + "-runtime" + "/")),
    "assigned secret": re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|secret[_-]?key)\b\s*[:=]\s*['\"][^'\"]+"
    ),
}
DATASET_PAYLOAD_SUFFIXES = {".csv", ".jsonl", ".parquet"}
GOLD_ALLOWED_JSON = {
    "datasets/h2epr_bench_gold/schema/reference_epg.schema.json",
    "datasets/h2epr_bench_gold/synthetic_fixtures/reference_epg.synthetic.json",
}


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return sorted(value.decode("utf-8") for value in result.stdout.split(b"\0") if value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_fixture(relative: str) -> bool:
    return any(part in {"fixtures", "synthetic_fixtures"} for part in Path(relative).parts)


def main() -> int:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    tracked = _tracked_files()
    errors: list[str] = []
    total_bytes = 0
    fixture_bytes = 0
    legacy = policy["legacy_oversize_files"]

    required_governance = {
        "LICENSE",
        "LICENSES/Apache-2.0.txt",
        "LICENSES/CC-BY-NC-4.0.md",
        "LICENSES/README.md",
        ".github/pull_request_template.md",
    }
    missing_governance = required_governance - set(tracked)
    if missing_governance:
        errors.append(f"missing governance files: {sorted(missing_governance)}")

    for relative in tracked:
        path = ROOT / relative
        parts = set(Path(relative).parts)
        if parts & FORBIDDEN_PATH_PARTS or Path(relative).name.startswith(".env"):
            errors.append(f"forbidden tracked path: {relative}")
            continue
        if not path.is_file():
            continue
        size = path.stat().st_size
        total_bytes += size
        if _is_fixture(relative):
            fixture_bytes += size
            if size > policy["fixture_file_max_bytes"]:
                errors.append(f"fixture exceeds per-file limit: {relative} ({size})")
        if size > policy["hard_file_max_bytes"]:
            errors.append(f"file exceeds hard 10 MB-class limit: {relative} ({size})")
        elif size > policy["ordinary_file_max_bytes"]:
            exception = legacy.get(relative)
            if (
                not exception
                or exception.get("bytes") != size
                or exception.get("sha256") != _sha256(path)
            ):
                errors.append(f"unapproved file exceeds ordinary limit: {relative} ({size})")

        if relative.startswith("datasets/h2epr_bench/") and (
            path.suffix.lower() in DATASET_PAYLOAD_SUFFIXES
            or path.name in {"draft_epg.json", "draft_unavailable.json"}
        ):
            errors.append(f"released Dataset payload is forbidden in GitHub: {relative}")
        if relative.startswith("datasets/h2epr_bench_gold/"):
            if path.suffix.lower() in DATASET_PAYLOAD_SUFFIXES:
                errors.append(f"Gold payload format is forbidden in GitHub: {relative}")
            if path.suffix.lower() == ".json" and relative not in GOLD_ALLOWED_JSON:
                errors.append(f"unapproved Gold JSON is forbidden in GitHub: {relative}")

        prefix = path.read_bytes()[:200]
        if prefix.startswith(b"version https://git-lfs.github.com/spec/v1"):
            errors.append(f"Git LFS pointer is forbidden in the public source tree: {relative}")
        if path.suffix.lower() in TEXT_SUFFIXES and size <= 2_000_000:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                errors.append(f"declared text file is not UTF-8: {relative}")
                continue
            for label, pattern in PRIVATE_PATTERNS.items():
                if pattern.search(text):
                    errors.append(f"{label} found in {relative}")

    if fixture_bytes > policy["fixture_total_max_bytes"]:
        errors.append(f"fixtures exceed aggregate limit: {fixture_bytes}")
    if total_bytes > policy["tree_max_bytes"]:
        errors.append(f"tracked tree exceeds 100 MB-class limit: {total_bytes}")
    undeclared_legacy = set(legacy) - set(tracked)
    if undeclared_legacy:
        errors.append(f"stale oversized-file exceptions: {sorted(undeclared_legacy)}")

    if errors:
        raise SystemExit("Public release boundary failed:\n- " + "\n- ".join(errors))
    print(
        json.dumps(
            {
                "tracked_files": len(tracked),
                "tracked_bytes": total_bytes,
                "fixture_bytes": fixture_bytes,
                "legacy_oversize_files": len(legacy),
                "real_gold_records": 0,
                "status": "pass",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
