#!/usr/bin/env python3
"""Validate the canonical H2EPR-Bench public-resource link contract."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "manifests" / "public_resource_links.json"
EXPLORER_SOURCE_MANIFEST_PATH = ROOT / "manifests" / "explorer_space_source.json"
RELEASE_CONTRACT_PATH = (
    ROOT / "datasets" / "h2epr_bench" / "manifests" / "unified3000_release_contract.json"
)
EXPECTED_RELEASE_ID = "h2epr-unified3000-v2"
EXPECTED_RC_TREE_SHA256 = "24f19b2eda8af998fa6e755c6dac8db62c40ad865815e6040cd83f6679cdbdb3"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
GATES = {"local", "deployment", "published"}
PUBLIC_VERSION_LABEL = re.compile(
    r"\bUnified[- ]?3000\b|(?<![-_\w])v(?:0\.)?\d+(?:\.\d+)*\b",
    re.IGNORECASE,
)

SURFACE_PATHS: dict[str, tuple[Path, ...]] = {
    "website": (ROOT / "index.html",),
    "github_readme": (ROOT / "README.md",),
    "public_dataset_card": (ROOT / "datasets" / "h2epr_bench" / "huggingface" / "README.md",),
    "gold_card": (ROOT / "datasets" / "h2epr_bench_gold" / "huggingface" / "README.md",),
    "explorer_card": (ROOT / "spaces" / "h2epr_bench_explorer" / "README.md",),
    "explorer_app": (
        ROOT / "spaces" / "h2epr_bench_explorer" / "app.py",
        ROOT / "spaces" / "h2epr_bench_explorer" / "src" / "h2epr_explorer" / "constants.py",
    ),
}

README_BADGE_SURFACES = {
    "github_readme",
    "public_dataset_card",
    "gold_card",
    "explorer_card",
}

EXPECTED_SURFACE_ORDER = {
    "website": ["explorer", "public_dataset", "finmycelium", "gated_gold", "release_repository"],
    "github_readme": ["website", "public_dataset", "explorer", "finmycelium", "gated_gold"],
    "public_dataset_card": ["website", "explorer", "finmycelium", "gated_gold", "release_repository"],
    "gold_card": ["website", "public_dataset", "explorer", "finmycelium", "release_repository"],
    "explorer_card": ["website", "public_dataset", "finmycelium", "gated_gold", "release_repository"],
    "explorer_app": ["website", "public_dataset", "finmycelium", "gated_gold", "release_repository"],
}

EXPECTED_RESOURCE_LABELS = {
    "website": "Project Website",
    "release_repository": "Release Repository",
    "public_dataset": "Public Dataset",
    "explorer": "Event Explorer",
    "finmycelium": "FinMycelium System",
    "gated_gold": "Reference EPGs (Gated)",
}

EXPECTED_CARD_SCOPES = {
    "public_dataset_card": "public_presentation_polish",
    "gold_card": "reference_presentation_polish",
    "explorer_card": "dataset_pinned_explorer_presentation",
}
EXPECTED_CARD_TARGET_REPOS = {
    "public_dataset_card": "AgenticFinLab/H2EPR-Bench",
    "gold_card": "AgenticFinLab/H2EPR-Bench-Gold",
    "explorer_card": "AgenticFinLab/H2EPR-Bench-Explorer",
}
EXPECTED_PUBLIC_DATASET_CARD_IMAGES = (
    "assets/card/h2epr-benchmark-overview.svg",
    "assets/card/h2epr-overview.svg",
)


class _AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._active: list[str] | None = None
        self.anchors: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._active = [dict(attrs).get("href") or "", ""]

    def handle_data(self, data: str) -> None:
        if self._active is not None:
            self._active[1] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._active is not None:
            self.anchors.append((self._active[0], " ".join(self._active[1].split())))
            self._active = None


def load_manifest() -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("manifest_version") != 2:
        raise SystemExit("unexpected public-resource manifest version")
    return manifest


def validate_release_identity(manifest: dict, gate: str = "local") -> None:
    if gate not in GATES:
        raise SystemExit(f"invalid public-resource gate: {gate!r}")
    identity = manifest.get("release_identity")
    if not isinstance(identity, dict) or identity.get("release_id") != EXPECTED_RELEASE_ID:
        raise SystemExit("public-resource manifest is not bound to Unified-3000 v2")
    state = identity.get("release_state")
    if state not in {"candidate", "dataset_published", "published"}:
        raise SystemExit(f"invalid public-resource release_state: {state!r}")
    revision = identity.get("dataset_revision")
    if revision is not None and not HEX40.fullmatch(revision):
        raise SystemExit("public-resource dataset_revision must be null or lowercase 40-hex")
    if state == "candidate" and revision is not None:
        raise SystemExit("candidate public resources must not claim a published dataset revision")
    if state != "candidate" and revision is None:
        raise SystemExit("post-candidate public resources must pin a dataset revision")
    for key in ("sha256sums_sha256", "tree_sha256"):
        value = identity.get(key)
        if not isinstance(value, str) or not HEX64.fullmatch(value):
            raise SystemExit(f"release_identity.{key} must be lowercase 64-hex")
        if value != EXPECTED_RC_TREE_SHA256:
            raise SystemExit(f"release_identity.{key} is not the audited release candidate")
    if identity["sha256sums_sha256"] != identity["tree_sha256"]:
        raise SystemExit("public-resource RC SHA256SUMS and package tree differ")

    explorer = json.loads(EXPLORER_SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    contract = json.loads(RELEASE_CONTRACT_PATH.read_text(encoding="utf-8"))
    if any(
        (
            explorer.get("manifest_version") != 2,
            explorer.get("release_id") != identity["release_id"],
            explorer.get("release_state") != state,
            explorer.get("dataset_revision") != revision,
            explorer.get("release_candidate", {}).get("sha256sums_sha256")
            != identity["sha256sums_sha256"],
            explorer.get("release_candidate", {}).get("tree_sha256") != identity["tree_sha256"],
            contract.get("contract_version") != "h2epr-unified3000-public-release-v2",
            contract.get("dataset_repo") != "AgenticFinLab/H2EPR-Bench",
            contract.get("dataset_revision") != revision,
            contract.get("artifacts", {}).get("package_checksums", {}).get("sha256")
            != identity["tree_sha256"],
        )
    ):
        raise SystemExit("public-resource, contract, and Explorer release identities differ")

    if gate in {"deployment", "published"} and state not in {"dataset_published", "published"}:
        raise SystemExit(f"{gate} gate rejects an unpublished release candidate")
    if gate == "published" and state != "published":
        raise SystemExit("published gate requires release_state=published")
    if gate == "published" and not isinstance(explorer.get("published_deployment"), dict):
        raise SystemExit("published gate requires a bound Explorer Space deployment identity")


def validate_manifest(manifest: dict) -> dict[str, dict]:
    resources = manifest.get("resources", [])
    by_id = {resource.get("id"): resource for resource in resources}
    if len(by_id) != len(resources) or None in by_id:
        raise SystemExit("public-resource IDs must be present and unique")
    if set(by_id) != set(EXPECTED_RESOURCE_LABELS):
        raise SystemExit("public-resource IDs do not match the reader-facing contract")
    labels = {resource_id: resource["label"] for resource_id, resource in by_id.items()}
    if labels != EXPECTED_RESOURCE_LABELS:
        raise SystemExit("public-resource labels do not match the reader-facing contract")

    urls = [resource.get("url") for resource in resources]
    if len(set(urls)) != len(urls):
        raise SystemExit("public-resource URLs must be unique")
    for resource in resources:
        parsed = urlparse(resource["url"])
        if parsed.scheme != "https" or not parsed.netloc:
            raise SystemExit(f"resource {resource['id']} is not an absolute HTTPS URL")

    paper = manifest.get("paper", {})
    if paper.get("status") != "forthcoming" or paper.get("url") is not None:
        raise SystemExit("paper must remain non-interactive until a public URL is verified")
    return by_id


def _url_position(text: str, url: str) -> int:
    candidates = [
        text.find(f'href="{url}"'),
        text.find(f"]({url})"),
        text.find(f'"{url}"'),
    ]
    present = [position for position in candidates if position >= 0]
    return min(present, default=-1)


def validate_surfaces(manifest: dict, resources: dict[str, dict]) -> None:
    expected_surfaces = set(SURFACE_PATHS)
    configured_surfaces = set(manifest.get("surface_order", {}))
    if configured_surfaces != expected_surfaces:
        raise SystemExit("surface_order keys do not match the validated public surfaces")
    if manifest["surface_order"] != EXPECTED_SURFACE_ORDER:
        raise SystemExit("surface_order does not match the task-first, self-link-free contract")
    if set(manifest.get("surface_labels", {})) != expected_surfaces:
        raise SystemExit("surface_labels keys do not match the validated public surfaces")

    for surface, paths in SURFACE_PATHS.items():
        missing = [path.relative_to(ROOT) for path in paths if not path.is_file()]
        if missing:
            raise SystemExit(f"missing public-resource surface files: {missing}")
        text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        if match := PUBLIC_VERSION_LABEL.search(text):
            raise SystemExit(
                f"{surface} contains a public-facing release-version label: {match.group(0)!r}"
            )
        if "FinMycelium_O1" in text:
            raise SystemExit(f"non-canonical FinMycelium_O1 link found in {surface}")
        labels = manifest["surface_labels"][surface]
        if list(labels) != manifest["surface_order"][surface]:
            raise SystemExit(f"{surface} labels do not follow its canonical resource order")
        positions: list[int] = []
        for resource_id in manifest["surface_order"][surface]:
            if resource_id not in resources:
                raise SystemExit(f"unknown resource {resource_id!r} configured for {surface}")
            url = resources[resource_id]["url"]
            position = _url_position(text, url)
            if position < 0:
                raise SystemExit(f"{surface} is missing {resource_id}: {url}")
            positions.append(position)
            if labels[resource_id] not in text:
                raise SystemExit(f"{surface} is missing visible label {labels[resource_id]!r}")
        if positions != sorted(positions):
            raise SystemExit(f"{surface} resource links do not follow the canonical order")
        if "Paper-forthcoming" in text or "Lab-AgenticFinLab" in text:
            raise SystemExit(f"{surface} contains a non-resource status or lab badge")

        if surface in README_BADGE_SURFACES:
            badges = re.findall(
                r"\[!\[([^\]]+)\]\((https://img\.shields\.io/badge/[^)]+)\)\]\((https://[^)]+)\)",
                text,
            )
            expected_ids = manifest["surface_order"][surface]
            expected_labels = [labels[resource_id] for resource_id in expected_ids]
            expected_urls = [resources[resource_id]["url"] for resource_id in expected_ids]
            if [badge[0] for badge in badges] != expected_labels:
                raise SystemExit(f"{surface} badge labels do not match its public-resource contract")
            if [badge[2] for badge in badges] != expected_urls:
                raise SystemExit(f"{surface} badge targets do not match its public-resource contract")
            if any("-176B70?style=flat-square" not in badge[1] for badge in badges):
                raise SystemExit(f"{surface} badges do not use the uniform public-resource style")

    website = SURFACE_PATHS["website"][0].read_text(encoding="utf-8")
    parser = _AnchorCollector()
    parser.feed(website)
    release_url = resources["release_repository"]["url"]
    mislabeled = [
        label
        for href, label in parser.anchors
        if href == release_url and label in {"Code", "GitHub", "Source", "Source code", "Website"}
    ]
    if mislabeled:
        raise SystemExit("the release monorepo has a misleading generic label")
    for resource_id, label in manifest["surface_labels"]["website"].items():
        target = resources[resource_id]["url"]
        if (target, label) not in parser.anchors:
            raise SystemExit(f"website does not pair {label!r} with its canonical URL")


def validate_card_sources(manifest: dict) -> None:
    cards = manifest.get("hugging_face_card_sources", {})
    if set(cards) != set(EXPECTED_CARD_SCOPES):
        raise SystemExit("Hugging Face card source set does not match the release contract")
    for surface, card in cards.items():
        source = ROOT / card["source_path"]
        if (
            source != SURFACE_PATHS[surface][0]
            or card.get("target_repo") != EXPECTED_CARD_TARGET_REPOS[surface]
            or card.get("target_path") != "README.md"
        ):
            raise SystemExit(f"invalid Hugging Face card source mapping for {surface}")
        rollback = card.get("rollback_baseline")
        if not isinstance(rollback, dict) or rollback.get("role") != "rollback_only":
            raise SystemExit(f"card baseline must be explicitly rollback_only for {surface}")
        revision = rollback.get("revision", "")
        baseline_hash = rollback.get("readme_sha256", "")
        if not HEX40.fullmatch(revision):
            raise SystemExit(f"invalid rollback revision for {surface}")
        if not HEX64.fullmatch(baseline_hash):
            raise SystemExit(f"invalid rollback README SHA-256 for {surface}")
        if (
            surface == "public_dataset_card"
            and manifest["release_identity"]["dataset_revision"] is not None
            and revision == manifest["release_identity"]["dataset_revision"]
        ):
            raise SystemExit(
                "rollback-only Dataset revision cannot identify Unified-3000 v2"
            )
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        if source_hash != card.get("source_readme_sha256"):
            raise SystemExit(f"Hugging Face card source hash mismatch for {surface}")
        if card.get("change_scope") != EXPECTED_CARD_SCOPES[surface]:
            raise SystemExit(f"unexpected reviewed change_scope for {surface}")
        if surface == "public_dataset_card":
            text = source.read_text(encoding="utf-8")
            images = tuple(re.findall(r'<img src="([^"]+)"', text))
            if images != EXPECTED_PUBLIC_DATASET_CARD_IMAGES:
                raise SystemExit(
                    "public Dataset Card must use the two approved visuals in narrative order"
                )
            missing = [
                relative
                for relative in images
                if not (source.parent / relative).is_file()
            ]
            if missing:
                raise SystemExit(f"public Dataset Card images are missing: {missing}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gate",
        choices=("local", "deployment", "published"),
        default="local",
        help="local accepts candidate links; deployment/published require a pinned dataset revision",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_manifest()
    validate_release_identity(manifest, args.gate)
    resources = validate_manifest(manifest)
    validate_surfaces(manifest, resources)
    validate_card_sources(manifest)
    print(
        json.dumps(
            {
                "resources": len(resources),
                "surfaces": len(SURFACE_PATHS),
                "paper_status": manifest["paper"]["status"],
                "gate": args.gate,
                "release_state": manifest["release_identity"]["release_state"],
                "status": "pass",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
