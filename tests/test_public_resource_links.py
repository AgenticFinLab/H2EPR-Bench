import unittest

from scripts.validate_public_resource_links import (
    SURFACE_PATHS,
    load_manifest,
    validate_card_sources,
    validate_manifest,
    validate_surfaces,
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

    def test_hugging_face_card_sources_pin_current_remote_baselines(self):
        validate_card_sources(self.manifest)
        cards = self.manifest["hugging_face_card_sources"]
        self.assertEqual(
            cards["public_dataset_card"]["baseline_revision"],
            "1d01f3649ace0301ac3bbe9ee875eea660347a29",
        )
        self.assertEqual(
            cards["gold_card"]["baseline_revision"],
            "48041e35e000e036b85dfd0d8f1273a85d027159",
        )
        self.assertEqual(
            cards["explorer_card"]["baseline_revision"],
            "a1cf81783396bb52328ed0ebe7a43da32a447f46",
        )

    def test_finmycelium_role_preserves_draft_gold_boundary(self):
        role = self.resources["finmycelium"]["role"]
        self.assertIn("public drafts", role)
        self.assertNotIn("Gold", role)


if __name__ == "__main__":
    unittest.main()
