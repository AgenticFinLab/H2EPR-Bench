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
            "a1cf81783396bb52328ed0ebe7a43da32a447f46",
        )
        self.assertTrue(
            all(
                card["rollback_baseline"]["role"] == "rollback_only"
                for card in cards.values()
            )
        )

    def test_dataset_published_identity_is_pinned_and_bound_to_rc(self):
        identity = self.manifest["release_identity"]
        self.assertEqual(identity["release_state"], "dataset_published")
        self.assertEqual(identity["dataset_revision"], EXPECTED_DATASET_REVISION)
        self.assertEqual(identity["tree_sha256"], EXPECTED_RC_TREE_SHA256)
        self.assertEqual(identity["sha256sums_sha256"], EXPECTED_RC_TREE_SHA256)
        for gate in ("local", "deployment"):
            with self.subTest(gate=gate):
                validate_release_identity(self.manifest, gate)
        with self.assertRaises(SystemExit):
            validate_release_identity(self.manifest, "published")

    def test_explorer_dataset_published_identity_is_pinned(self):
        # The Explorer validator reads its own manifest; use that authoritative object.
        from scripts.check_explorer_source_manifest import _load_json, MANIFEST_PATH

        source_manifest = _load_json(MANIFEST_PATH)
        self.assertEqual(source_manifest["release_state"], "dataset_published")
        self.assertEqual(source_manifest["dataset_revision"], EXPECTED_DATASET_REVISION)
        self.assertEqual(
            source_manifest["release_candidate"]["tree_sha256"], EXPECTED_RC_TREE_SHA256
        )
        self.assertIsNone(source_manifest["published_deployment"])
        self.assertEqual(source_manifest["rollback_baseline"]["role"], "rollback_only")
        for gate in ("local", "deployment"):
            with self.subTest(gate=gate):
                validate_explorer_release_identity(source_manifest, gate)
        with self.assertRaises(ValueError):
            validate_explorer_release_identity(source_manifest, "published")

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


if __name__ == "__main__":
    unittest.main()
