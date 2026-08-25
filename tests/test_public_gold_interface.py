import copy
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD_ROOT = REPO_ROOT / "datasets" / "h2epr_bench_gold"
VALIDATOR_PATH = GOLD_ROOT / "validators" / "validate_reference_epg.py"
SCHEMA_PATH = GOLD_ROOT / "schema" / "reference_epg.schema.json"
FIXTURE_PATH = GOLD_ROOT / "synthetic_fixtures" / "reference_epg.synthetic.json"
PRESENTATION_RELEASE_RECEIPT_PATH = (
    REPO_ROOT / "manifests" / "h2epr_reference_presentation_release.json"
)

SPEC = importlib.util.spec_from_file_location("h2epr_reference_validator", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


class PublicGoldInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_schema_is_the_exact_already_public_interface(self):
        digest = hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest()
        self.assertEqual(
            digest,
            "cac9f55961a238902ad548975aa7b450818faf2b35a713ff0cb32f8dd3207024",
        )
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), validator.TOP_LEVEL_FIELDS)

    def test_synthetic_fixture_validates_without_network(self):
        receipt = validator.load_reference_epg(FIXTURE_PATH)
        self.assertEqual(receipt["public_event_id"], "H2EPR-0001")
        self.assertEqual(receipt["counts"]["stages"], 1)
        self.assertEqual(receipt["counts"]["actions"], 1)
        self.assertEqual(receipt["counts"]["evidence_nodes"], 1)
        self.assertFalse(receipt["network_accessed"])
        self.assertRegex(receipt["document_sha256"], r"^[a-f0-9]{64}$")
        self.assertIn("SYNTHETIC", self.fixture["canonical_event"]["name"])
        self.assertIn("NOT A BENCHMARK RECORD", self.fixture["canonical_event"]["name"])

    def test_loader_requires_an_explicit_local_path_and_has_no_hub_client(self):
        signature = inspect.signature(validator.load_reference_epg)
        self.assertIs(signature.parameters["path"].default, inspect.Parameter.empty)
        source = VALIDATOR_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "huggingface_hub",
            "hf_hub_download",
            "requests",
            "H2EPR-Bench-Gold",
            "snapshot_download",
        ):
            self.assertNotIn(forbidden, source)

    def test_repository_contains_no_real_gold_payload_format(self):
        forbidden_suffixes = {".jsonl", ".parquet", ".csv"}
        found = [
            path.relative_to(REPO_ROOT).as_posix()
            for path in GOLD_ROOT.rglob("*")
            if path.is_file() and path.suffix in forbidden_suffixes
        ]
        self.assertEqual(found, [])
        json_files = sorted(path.name for path in GOLD_ROOT.rglob("*.json"))
        self.assertEqual(
            json_files,
            ["reference_epg.schema.json", "reference_epg.synthetic.json"],
        )

    def test_reference_card_release_receipt_is_readme_only(self):
        receipt = json.loads(
            PRESENTATION_RELEASE_RECEIPT_PATH.read_text(encoding="utf-8")
        )
        self.assertEqual(receipt["status"], "passed")
        self.assertEqual(
            receipt["resulting_revision"],
            "9674f25aa57c8323497d50caa093d19db22f571f",
        )
        self.assertEqual(receipt["source"]["github_pull_request"], 5)
        self.assertEqual(receipt["verification"]["change_scope"], "README.md only")
        self.assertEqual(receipt["verification"]["repository_gated"], "manual")
        self.assertFalse(receipt["promotion"]["force_push_used"])
        self.assertFalse(receipt["rollback"]["triggered"])
        self.assertFalse(receipt["verification"]["gold_records_accessed"])

    def test_rejects_unknown_fields_and_out_of_range_identity(self):
        extra = copy.deepcopy(self.fixture)
        extra["internal_note"] = "must be rejected"
        with self.assertRaisesRegex(
            validator.ReferenceValidationError, "unexpected fields"
        ):
            validator.validate_reference_epg(extra)

        out_of_range = copy.deepcopy(self.fixture)
        out_of_range["public_event_id"] = "H2EPR-9999"
        with self.assertRaisesRegex(
            validator.ReferenceValidationError, "outside H²EPR-Bench"
        ):
            validator.validate_reference_epg(out_of_range)

    def test_rejects_non_contiguous_order_and_dangling_graph_references(self):
        stage_gap = copy.deepcopy(self.fixture)
        stage_gap["stages"][0]["sequence_index"] = 2
        with self.assertRaisesRegex(
            validator.ReferenceValidationError, "unique and contiguous"
        ):
            validator.validate_reference_epg(stage_gap)

        unknown_actor = copy.deepcopy(self.fixture)
        unknown_actor["actions"][0]["actor_ids"] = ["P_UNKNOWN"]
        with self.assertRaisesRegex(
            validator.ReferenceValidationError, "unknown participant"
        ):
            validator.validate_reference_epg(unknown_actor)

        unknown_evidence = copy.deepcopy(self.fixture)
        unknown_evidence["evidence_graph"]["support_edges"][0]["evidence_ids"] = [
            "EV_UNKNOWN"
        ]
        with self.assertRaisesRegex(
            validator.ReferenceValidationError, "unknown evidence node"
        ):
            validator.validate_reference_epg(unknown_evidence)

    def test_rejects_duplicate_node_and_relation_identity(self):
        duplicate_node = copy.deepcopy(self.fixture)
        duplicate_node["participants"][0]["id"] = "S1"
        duplicate_node["actions"][0]["actor_ids"] = ["S1"]
        with self.assertRaisesRegex(
            validator.ReferenceValidationError, "globally unique"
        ):
            validator.validate_reference_epg(duplicate_node)

        duplicate_relation = copy.deepcopy(self.fixture)
        duplicate_relation["temporal_relations"] = [
            {
                "id": "R1",
                "from_id": "A1",
                "to_id": "O1",
                "label": "duplicate synthetic relation",
            }
        ]
        with self.assertRaisesRegex(
            validator.ReferenceValidationError, "Relation IDs must be globally unique"
        ):
            validator.validate_reference_epg(duplicate_relation)


if __name__ == "__main__":
    unittest.main()
