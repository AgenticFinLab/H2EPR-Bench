import json
from datetime import datetime
from pathlib import Path
import unittest

from scripts.check_explorer_source_manifest import (
    EXPECTED_RC_TREE_SHA256,
    validate_release_identity as validate_explorer_release_identity,
)
from scripts.check_public_release_boundary import public_wording_violations
from scripts.validate_public_resource_links import (
    SURFACE_PATHS,
    load_manifest,
    validate_card_sources,
    validate_manifest,
    validate_release_identity,
    validate_surfaces,
)


EXPECTED_DATASET_REVISION = "6156a6bb3b838143401cb3e5709f708e5d6e802c"
EXPECTED_SPACE_COMMIT = "2cc85fd27d832d429be72c4531ba832d70648046"
EXPECTED_SPACE_TREE = "88deb297c0ef39dd3324d1786eb4119026103e7c"
EXPECTED_SPACE_LEDGER = "ce47455ce680f59808713895642737ab11d765b136d1905e65a62958efa21f8a"
EXPECTED_SPACE_PRIOR_COMMIT = "0f91d75dbed7f4ceddf185363d43b799b7b611e4"
EXPECTED_SPACE_PRIOR_TREE = "fb795f3ec09da6c858e018dc3ee0f5381d217f40"
EXPECTED_SPACE_PRIOR_LEDGER = "ea11fbb05e7266218cbb34ae934244f33a707be6351e2fca7338979b976d275e"
EXPECTED_SPACE_ROLLBACK_TAG_OBJECT = "5d6e7bc3cc65fa48d30076dc028fd903e47a824b"
REPO_ROOT = Path(__file__).resolve().parents[1]
SPACE_RELEASE_RECEIPT_PATH = (
    REPO_ROOT / "manifests" / "unified3000_v2_space_release.json"
)


class PublicResourceLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_manifest()
        cls.resources = validate_manifest(cls.manifest)

    def test_canonical_public_identities(self):
        expected = {
            "website": "https://agenticfinlab.github.io/H2EPR-Bench/",
            "release_repository": "https://github.com/AgenticFinLab/H2EPR-Bench",
            "public_dataset": "https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench",
            "explorer": "https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer",
            "finmycelium": "https://github.com/AgenticFinLab/FinMycelium",
            "gated_gold": "https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold",
        }
        self.assertEqual(
            {resource_id: resource["url"] for resource_id, resource in self.resources.items()},
            expected,
        )
        self.assertEqual(self.manifest["paper"]["status"], "forthcoming")
        self.assertIsNone(self.manifest["paper"]["url"])
        self.assertEqual(
            {resource_id: resource["label"] for resource_id, resource in self.resources.items()},
            {
                "website": "Project Website",
                "release_repository": "Release Repository",
                "public_dataset": "Public Dataset",
                "explorer": "Event Explorer",
                "finmycelium": "FinMycelium System",
                "gated_gold": "Reference EPGs (Gated)",
            },
        )

    def test_every_public_surface_contains_required_links_in_order(self):
        validate_surfaces(self.manifest, self.resources)
        self.assertEqual(len(SURFACE_PATHS), 6)
        self.assertNotIn("release_repository", self.manifest["surface_order"]["github_readme"])
        self.assertNotIn("public_dataset", self.manifest["surface_order"]["public_dataset_card"])
        self.assertNotIn("gated_gold", self.manifest["surface_order"]["gold_card"])
        self.assertNotIn("explorer", self.manifest["surface_order"]["explorer_card"])

    def test_resource_groups_exclude_lab_and_noninteractive_paper_badges(self):
        self.assertNotIn("agenticfinlab", self.resources)
        for paths in SURFACE_PATHS.values():
            text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
            self.assertNotIn("Lab-AgenticFinLab", text)
            self.assertNotIn("Paper-forthcoming", text)

    def test_hugging_face_card_sources_keep_only_explicit_rollback_baselines(self):
        validate_card_sources(self.manifest)
        cards = self.manifest["hugging_face_card_sources"]
        self.assertEqual(
            cards["public_dataset_card"]["rollback_baseline"]["revision"],
            "f1e90230c7bee782d5037b04ffec778bf1053b94",
        )
        self.assertEqual(
            cards["gold_card"]["rollback_baseline"]["revision"],
            "48041e35e000e036b85dfd0d8f1273a85d027159",
        )
        self.assertEqual(
            cards["explorer_card"]["rollback_baseline"]["revision"],
            EXPECTED_SPACE_PRIOR_COMMIT,
        )
        self.assertEqual(
            cards["explorer_card"]["rollback_baseline"]["readme_sha256"],
            "42770432c3f831f4a7e1977768cf19c7c50e60a48d29e2333c2b05e65df9892c",
        )
        self.assertTrue(
            all(
                card["rollback_baseline"]["role"] == "rollback_only"
                for card in cards.values()
            )
        )

    def test_published_identity_is_pinned_and_bound_to_rc(self):
        identity = self.manifest["release_identity"]
        self.assertEqual(identity["release_state"], "published")
        self.assertEqual(identity["dataset_revision"], EXPECTED_DATASET_REVISION)
        self.assertEqual(identity["tree_sha256"], EXPECTED_RC_TREE_SHA256)
        self.assertEqual(identity["sha256sums_sha256"], EXPECTED_RC_TREE_SHA256)
        for gate in ("local", "deployment", "published"):
            with self.subTest(gate=gate):
                validate_release_identity(self.manifest, gate)

    def test_explorer_published_identity_is_pinned(self):
        # The Explorer validator reads its own manifest; use that authoritative object.
        from scripts.check_explorer_source_manifest import _load_json, MANIFEST_PATH

        source_manifest = _load_json(MANIFEST_PATH)
        self.assertEqual(source_manifest["release_state"], "published")
        self.assertEqual(source_manifest["dataset_revision"], EXPECTED_DATASET_REVISION)
        self.assertEqual(
            source_manifest["release_candidate"]["tree_sha256"], EXPECTED_RC_TREE_SHA256
        )
        self.assertEqual(
            source_manifest["published_deployment"],
            {
                "dataset_revision": EXPECTED_DATASET_REVISION,
                "source_ledger_sha256": EXPECTED_SPACE_LEDGER,
                "space_commit": EXPECTED_SPACE_COMMIT,
                "space_tree": EXPECTED_SPACE_TREE,
            },
        )
        self.assertEqual(source_manifest["rollback_baseline"]["role"], "rollback_only")
        self.assertEqual(
            source_manifest["rollback_baseline"]["space_commit"],
            EXPECTED_SPACE_PRIOR_COMMIT,
        )
        for gate in ("local", "deployment", "published"):
            with self.subTest(gate=gate):
                validate_explorer_release_identity(source_manifest, gate)

    def test_space_release_receipt_closes_the_published_identity(self):
        from scripts.check_explorer_source_manifest import _load_json, MANIFEST_PATH

        receipt = json.loads(SPACE_RELEASE_RECEIPT_PATH.read_text(encoding="utf-8"))
        source_manifest = _load_json(MANIFEST_PATH)
        deployment = source_manifest["published_deployment"]

        self.assertEqual(
            receipt["schema_version"],
            "h2epr-unified3000-v2-space-release-receipt-v1",
        )
        self.assertEqual(receipt["status"], "passed")
        pr_merged_at = datetime.fromisoformat(
            receipt["source_commits"]["github_source_pr_merged_at_utc"]
        )
        published_at = datetime.fromisoformat(receipt["published_at_utc"])
        logs_checked_at = datetime.fromisoformat(
            receipt["verification"]["logs_checked_at_utc"]
        )
        verified_at = datetime.fromisoformat(receipt["verified_at_utc"])
        self.assertLessEqual(pr_merged_at, published_at)
        self.assertLessEqual(published_at, logs_checked_at)
        self.assertLessEqual(logs_checked_at, verified_at)
        self.assertEqual(receipt["resulting_revision"], EXPECTED_SPACE_COMMIT)
        self.assertEqual(receipt["resulting_tree"], EXPECTED_SPACE_TREE)
        self.assertEqual(receipt["resulting_revision"], deployment["space_commit"])
        self.assertEqual(receipt["resulting_tree"], deployment["space_tree"])
        self.assertEqual(
            receipt["release_identity"]["dataset_revision"], EXPECTED_DATASET_REVISION
        )
        self.assertEqual(
            receipt["release_identity"]["source_ledger_sha256"],
            deployment["source_ledger_sha256"],
        )
        self.assertEqual(
            receipt["source_commits"]["payload_space_subtree_tree"],
            EXPECTED_SPACE_TREE,
        )
        self.assertEqual(
            receipt["source_commits"]["payload_repository_tree"],
            receipt["source_commits"]["github_source_merge_tree"],
        )
        self.assertEqual(
            receipt["source_commits"]["payload_commit"],
            "b84c309acbafe7609647a138643e988646becc29",
        )
        self.assertEqual(
            receipt["source_commits"]["github_source_repo"],
            "AgenticFinLab/H2EPR-Bench",
        )
        self.assertEqual(receipt["source_commits"]["github_source_pull_request"], 3)
        self.assertEqual(
            receipt["source_commits"]["github_source_merge_commit"],
            "71ebdaf315a9b18d205204ab9482e2971ac1df7e",
        )
        self.assertEqual(
            receipt["promotion"]["parent_commit_guard"], receipt["prior_revision"]
        )
        self.assertFalse(receipt["promotion"]["force_push_used"])
        self.assertTrue(receipt["promotion"]["clean_git_export_used"])
        self.assertFalse(receipt["promotion"]["worktree_upload_used"])
        self.assertFalse(receipt["promotion"]["pull_request_used"])
        self.assertTrue(receipt["promotion"]["pull_request_disposition"])
        self.assertEqual(receipt["promotion"]["staging_tree"], EXPECTED_SPACE_TREE)
        self.assertEqual(
            sorted(receipt["promotion"]["allow_patterns"]),
            sorted(source_manifest["files"]),
        )
        self.assertEqual(
            receipt["rollback"]["peeled_space_commit"], receipt["prior_revision"]
        )
        self.assertEqual(receipt["prior_tree"], EXPECTED_SPACE_PRIOR_TREE)
        self.assertEqual(
            receipt["prior_source_ledger_sha256"], EXPECTED_SPACE_PRIOR_LEDGER
        )
        self.assertEqual(
            receipt["rollback"]["annotated_tag_object"],
            EXPECTED_SPACE_ROLLBACK_TAG_OBJECT,
        )
        self.assertEqual(
            receipt["rollback"]["tag"],
            "pre-unified-3000-v2-explorer-20260825",
        )
        self.assertEqual(receipt["rollback"]["tree"], EXPECTED_SPACE_PRIOR_TREE)
        self.assertEqual(
            receipt["rollback"]["source_ledger_sha256"],
            EXPECTED_SPACE_PRIOR_LEDGER,
        )
        self.assertEqual(
            source_manifest["rollback_baseline"]["space_commit"],
            receipt["prior_revision"],
        )
        self.assertFalse(receipt["rollback"]["triggered"])
        self.assertEqual(receipt["verification"]["runtime_sha"], EXPECTED_SPACE_COMMIT)
        self.assertEqual(receipt["verification"]["runtime_stage"], "RUNNING")
        self.assertEqual(receipt["verification"]["domain_stage"], "READY")
        self.assertEqual(receipt["verification"]["health_http_status"], 200)
        self.assertEqual(receipt["release_identity"]["source_file_count"], 11)
        self.assertEqual(
            receipt["release_identity"]["space_tree"], EXPECTED_SPACE_TREE
        )
        self.assertEqual(receipt["verification"]["exhaustive_event_count"], 3000)
        self.assertEqual(
            receipt["verification"]["all_event_draft_asset_path_hash_closure"],
            "passed",
        )
        self.assertEqual(
            receipt["verification"]["draft_preview_and_download_smoke"], "passed"
        )
        self.assertEqual(receipt["verification"]["browser_console_error_count"], 0)
        self.assertEqual(receipt["verification"]["browser_page_error_count"], 0)
        self.assertTrue(
            receipt["verification"]["browser_screenshot_capture_api_passed"]
        )
        self.assertFalse(
            receipt["verification"]["browser_screenshot_artifacts_retained"]
        )
        self.assertFalse(receipt["verification"]["gold_records_accessed"])

    def test_finmycelium_role_preserves_draft_gold_boundary(self):
        role = self.resources["finmycelium"]["role"]
        self.assertIn("public drafts", role)
        self.assertNotIn("Gold", role)


class PublicWordingGuardTests(unittest.TestCase):
    def test_rejects_retired_partition_phrases(self):
        phrases = (
            "Only 2,876 public per-event Draft EPG files are present.",
            "The old release was 2,876 + 124.",
            "The other 124 catalog events remain without drafts.",
            "124 events are unavailable.",
            "The historical Core-1000 subset is preserved.",
            "A recovery batch supplied missing drafts.",
            "Rows use draft_unavailable status.",
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertTrue(public_wording_violations("README.md", phrase))

    def test_allows_event_ids_and_unrelated_numbers_or_history(self):
        allowed = (
            "H2EPR-2876 is a valid event identifier.",
            "H2EPR-2876 events are linked by canonical identifier.",
            "Stage 124 contains 2876 weighted tokens.",
            "All 3,000 Draft EPGs are available.",
            "Git history is preserved without rewriting commits.",
            "The method studies historical truth records.",
        )
        for phrase in allowed:
            with self.subTest(phrase=phrase):
                self.assertEqual(public_wording_violations("README.md", phrase), [])

    def test_does_not_apply_prose_policy_to_code(self):
        self.assertEqual(
            public_wording_violations("tests/test_guard.py", 'fixture = "2,876 drafts"'),
            [],
        )

    def test_applies_retired_partition_policy_to_public_json_and_javascript(self):
        for path in ("manifests/release.json", "static/js/site.js"):
            with self.subTest(path=path):
                self.assertTrue(
                    public_wording_violations(path, 'const note = "2,876 + 124";')
                )


if __name__ == "__main__":
    unittest.main()
