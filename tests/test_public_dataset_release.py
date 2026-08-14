import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import pyarrow as pa
import pyarrow.parquet as pq


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = (
    REPO_ROOT / "datasets" / "h2epr_bench" / "scripts" / "validate_release.py"
)
CONTRACT_PATH = (
    REPO_ROOT
    / "datasets"
    / "h2epr_bench"
    / "manifests"
    / "unified3000_release_contract.json"
)
AVAILABILITY_SCHEMA_PATH = (
    REPO_ROOT
    / "datasets"
    / "h2epr_bench"
    / "schema"
    / "draft_availability.schema.json"
)

SPEC = importlib.util.spec_from_file_location("h2epr_public_release_validator", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(payload):
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class SyntheticPublicRelease:
    def __init__(self, base):
        self.root = base / "dataset"
        self.root.mkdir()
        self.contract_path = base / "contract.json"
        self.contract = copy.deepcopy(json.loads(CONTRACT_PATH.read_text(encoding="utf-8")))
        self.contract["dataset_revision"] = "synthetic-test-revision"
        self.contract["event_identity"].update({"first": 1, "last": 2})
        self.contract["counts"].update(
            {
                "events": 2,
                "draft_available": 1,
                "draft_unavailable": 1,
                "stage_rows": 1,
                "stage_events": 1,
            }
        )
        for table in self.contract["tables"].values():
            table["rows"] = 1 if table["path"].endswith("event_stages.parquet") else 2

        source_hash = "a" * 64
        self.graph = {
            "artifact_role": "synthetic_test_fixture",
            "artifact_type": "finmycelium_finalcascade_public",
            "event": {"event_id": "H2EPR-0001", "title": {"value": "Synthetic event"}},
            "event_id": "H2EPR-0001",
            "not_gold_warning": "Synthetic Draft fixture; not Gold.",
            "public_event_id": "H2EPR-0001",
            "source_payload_sha256": source_hash,
        }
        draft_hash = _canonical_hash(self.graph)
        self.rows = self._rows(draft_hash, source_hash)
        for name in self.contract["tables"]:
            self.write_table(name)

        draft_dir = self.root / "draft_events" / "H2EPR-0001"
        draft_dir.mkdir(parents=True)
        (draft_dir / "draft_epg.json").write_text(
            json.dumps(self.graph, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        unavailable_dir = self.root / "draft_events" / "H2EPR-0002"
        unavailable_dir.mkdir(parents=True)
        marker = {
            "draft_asset": None,
            "draft_record_index": None,
            "draft_schema": None,
            "draft_sha256": None,
            "draft_source_kind": None,
            "draft_status": "draft_unavailable",
            "has_reference_epg": True,
            "public_event_id": "H2EPR-0002",
            "source_payload_sha256": None,
            "unavailable_reason": "synthetic_unavailable",
        }
        (unavailable_dir / "draft_unavailable.json").write_text(
            json.dumps(marker, sort_keys=True, separators=(",", ":")), encoding="utf-8"
        )
        self.write_contract()

    def _rows(self, draft_hash, source_hash):
        common = {
            "title": "Synthetic event",
            "display_name": "Synthetic event",
            "event_descriptor": "Synthetic content only.",
            "domain": "Synthetic domain",
            "category": "Synthetic category",
            "keywords": "synthetic",
            "release_split": "synthetic",
            "version": "test",
            "schema_version": "test",
            "has_gold_reference": True,
        }
        catalog = []
        instances = []
        gallery = []
        summary = []
        availability = []
        for index, status in ((1, "draft_available"), (2, "draft_unavailable")):
            event_id = f"H2EPR-{index:04d}"
            row = {"public_event_id": event_id, "event_id": event_id, **common}
            row["draft_status"] = status
            catalog.append(row)
            instances.append(
                {
                    **row,
                    "has_finalcascade": index == 1,
                    "finalcascade_access_level": "public" if index == 1 else "unavailable",
                    "gold_reference_access_level": "manual_gated",
                    "evidence_context_access_level": "manual_gated",
                }
            )
            gallery.append(
                {
                    "public_event_id": event_id,
                    "title": common["title"],
                    "domain": common["domain"],
                    "category": common["category"],
                    "event_descriptor": common["event_descriptor"],
                    "draft_status": status,
                }
            )
            counts = {
                name: 1 if index == 1 else None for name in validator.GRAPH_COUNT_COLUMNS
            }
            summary.append(
                {
                    "public_event_id": event_id,
                    "event_id": event_id,
                    "title": common["title"],
                    "domain": common["domain"],
                    "category": common["category"],
                    "draft_status": status,
                    **counts,
                    "event_start_time": "unknown" if index == 1 else None,
                    "event_end_time": "unknown" if index == 1 else None,
                    "event_boundary_time_status": "unknown" if index == 1 else "unavailable",
                    "known_action_time_anchor_count": 0,
                    "known_action_time_anchors": "[]",
                    "relative_order_available": False,
                }
            )
            availability.append(
                {
                    "public_event_id": event_id,
                    "draft_status": status,
                    "draft_source_kind": "synthetic" if index == 1 else None,
                    "draft_schema": "synthetic" if index == 1 else None,
                    # Deliberately unsafe-looking provenance: the validator must ignore it.
                    "draft_asset": "../../must-not-be-resolved.json" if index == 1 else None,
                    "draft_record_index": 1 if index == 1 else None,
                    "draft_sha256": draft_hash if index == 1 else None,
                    "source_payload_sha256": source_hash if index == 1 else None,
                    "has_reference_epg": True,
                }
            )
        stages = [
            {
                "public_event_id": "H2EPR-0001",
                "event_id": "H2EPR-0001",
                "stage_id": "S1",
                "stage_index": 1,
                "stage_title": "Synthetic stage",
                "stage_start_time": "unknown",
                "stage_end_time": "unknown",
                "stage_boundary_time_status": "unknown",
                "episode_count": 1,
                "participant_count": 1,
                "action_count": 1,
                "transaction_count": 1,
                "relation_count": 1,
                "known_action_time_anchor_count": 0,
                "known_action_time_anchors": "[]",
                "relative_order_available": False,
                "release_split": "synthetic",
                "version": "test",
                "schema_version": "test",
            }
        ]
        return {
            "event_gallery": gallery,
            "event_catalog": catalog,
            "event_instances": instances,
            "event_stages": stages,
            "finalcascade_summary": summary,
            "draft_availability": availability,
        }

    def write_table(self, name):
        declared = self.contract["tables"][name]
        path = self.root / declared["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        types = self.contract["arrow_types"]
        fields = []
        for column in declared["columns"]:
            if column in types["bool"]:
                field_type = pa.bool_()
            elif column in types["int64"]:
                field_type = pa.int64()
            else:
                field_type = pa.string()
            fields.append(pa.field(column, field_type))
        table = pa.Table.from_pylist(self.rows[name], schema=pa.schema(fields))
        pq.write_table(table, path)
        declared["sha256"] = _sha256(path)

    def write_contract(self):
        self.contract_path.write_text(
            json.dumps(self.contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


class PublicDatasetReleaseTests(unittest.TestCase):
    def test_frozen_contract_and_public_schema_identity(self):
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            contract["dataset_revision"],
            "1d01f3649ace0301ac3bbe9ee875eea660347a29",
        )
        self.assertEqual(contract["counts"]["events"], 3000)
        self.assertEqual(contract["counts"]["draft_available"], 2876)
        self.assertEqual(contract["counts"]["draft_unavailable"], 124)
        self.assertEqual(contract["counts"]["stage_rows"], 8500)
        self.assertEqual(
            _sha256(AVAILABILITY_SCHEMA_PATH),
            "53e9dcae1d8ed296ed619d690eb022bfc51c2f5c9055748236b60a6a6c36a815",
        )

    def test_repository_contains_contracts_but_no_dataset_records(self):
        root = REPO_ROOT / "datasets" / "h2epr_bench"
        forbidden_suffixes = {".parquet", ".jsonl", ".csv"}
        forbidden_names = {"draft_epg.json", "draft_unavailable.json"}
        found = [
            path.relative_to(REPO_ROOT).as_posix()
            for path in root.rglob("*")
            if path.is_file()
            and (path.suffix in forbidden_suffixes or path.name in forbidden_names)
        ]
        self.assertEqual(found, [])

    def test_synthetic_release_passes_and_draft_asset_is_not_resolved(self):
        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            receipt = validator.validate_release(release.root, release.contract_path)
        self.assertEqual(
            receipt["counts"],
            {
                "events": 2,
                "draft_available": 1,
                "draft_unavailable": 1,
                "stage_rows": 1,
                "stage_events": 1,
            },
        )
        self.assertFalse(receipt["gold_records_accessed"])
        self.assertRegex(receipt["draft_ledger_sha256"], r"^[a-f0-9]{64}$")

    def test_rejects_draft_identity_mismatch_at_derived_path(self):
        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            path = release.root / "draft_events" / "H2EPR-0001" / "draft_epg.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["event"]["event_id"] = "H2EPR-0002"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "Draft EPG identity mismatch"
            ):
                validator.validate_release(release.root, release.contract_path)

    def test_rejects_missing_direct_draft_and_table_digest_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            path = release.root / "draft_events" / "H2EPR-0001" / "draft_epg.json"
            path.unlink()
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "Missing direct Draft EPG"
            ):
                validator.validate_release(release.root, release.contract_path)

        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            release.contract["tables"]["event_catalog"]["sha256"] = "0" * 64
            release.write_contract()
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "SHA-256 mismatch for event_catalog"
            ):
                validator.validate_release(release.root, release.contract_path)

    def test_rejects_stage_index_and_summary_closure_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            release.rows["event_stages"][0]["stage_index"] = 2
            release.write_table("event_stages")
            release.write_contract()
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "Non-contiguous stage_index"
            ):
                validator.validate_release(release.root, release.contract_path)

        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            release.rows["finalcascade_summary"][0]["action_count"] = 2
            release.write_table("finalcascade_summary")
            release.write_contract()
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "action_count closure mismatch"
            ):
                validator.validate_release(release.root, release.contract_path)


if __name__ == "__main__":
    unittest.main()
