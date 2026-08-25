import copy
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
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
CACHE_PREPARER_PATH = REPO_ROOT / "scripts" / "prepare_public_dataset_test_cache.py"
RETIRED_AVAILABILITY_SCHEMA = (
    REPO_ROOT
    / "datasets"
    / "h2epr_bench"
    / "schema"
    / "draft_availability.schema.json"
)
ACTUAL_RC = (
    REPO_ROOT.parent.parent
    / "build"
    / "hf_unified3000_v2_rc_v2"
    / "H2EPR-Bench"
)

SPEC = importlib.util.spec_from_file_location("h2epr_public_release_validator", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)

CACHE_SPEC = importlib.util.spec_from_file_location(
    "h2epr_public_dataset_cache_preparer", CACHE_PREPARER_PATH
)
cache_preparer = importlib.util.module_from_spec(CACHE_SPEC)
assert CACHE_SPEC.loader is not None
CACHE_SPEC.loader.exec_module(cache_preparer)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


class SyntheticPublicRelease:
    """A complete two-event release, including its package checksum closure."""

    def __init__(self, base: Path):
        self.root = base / "dataset"
        self.root.mkdir()
        self.contract_path = base / "contract.json"
        self.contract = copy.deepcopy(json.loads(CONTRACT_PATH.read_text(encoding="utf-8")))
        self.contract["dataset_revision"] = None
        self.contract["event_identity"].update({"first": 1, "last": 2})
        self.contract["counts"].update(
            {
                "events": 2,
                "draft_epgs": 2,
                "stage_rows": 2,
                "stage_events": 2,
                "episodes": 2,
                "participants": 2,
                "actions": 2,
                "transactions": 2,
                "relations": 2,
            }
        )
        for table in self.contract["tables"].values():
            table["rows"] = 2
        self.contract["artifacts"]["aggregate_drafts"]["rows"] = 2
        self.contract["artifacts"]["draft_source_hashes"]["rows"] = 2

        self.wrappers = [self._wrapper(index) for index in (1, 2)]
        self.source_rows = []
        for index, wrapper in enumerate(self.wrappers, start=1):
            event_id = f"H2EPR-{index:04d}"
            payload = _canonical_bytes(wrapper) + b"\n"
            directory = self.root / "draft_events" / event_id
            directory.mkdir(parents=True)
            (directory / "draft_epg.json").write_bytes(payload)
            self.source_rows.append(
                {
                    "public_event_id": event_id,
                    "source_payload_sha256": wrapper["source_payload_sha256"],
                    "sanitized_record_sha256": hashlib.sha256(payload[:-1]).hexdigest(),
                    "draft_record_index": str(index),
                }
            )
        aggregate = self.root / self.contract["artifacts"]["aggregate_drafts"]["path"]
        aggregate.parent.mkdir(parents=True)
        aggregate.write_bytes(b"".join(_canonical_bytes(row) + b"\n" for row in self.wrappers))
        self._write_source_csv()
        self.rows = self._viewer_rows()
        for name in self.contract["tables"]:
            self.write_table(name)
        self.refresh_integrity()

    @staticmethod
    def _source_hash(index: int) -> str:
        return hashlib.sha256(f"synthetic-source-{index}".encode("ascii")).hexdigest()

    def _wrapper(self, index: int) -> dict[str, object]:
        event_id = f"H2EPR-{index:04d}"
        return {
            "artifact_role": "reference_construction_artifact",
            "artifact_type": "finmycelium_finalcascade_public",
            "event": {
                "end_time": {"value": "unknown"},
                "event_id": event_id,
                "event_type": {"value": "Synthetic"},
                "stages": [
                    {
                        "end_time": {"value": "unknown"},
                        "episodes": [
                            {
                                "episode_id": "E1",
                                "participants": [
                                    {
                                        "actions": [
                                            {
                                                "action_id": "A1",
                                                "timestamp": {"value": "unknown"},
                                            }
                                        ],
                                        "participant_id": "P1",
                                        "participant_relations": [{"relation_id": "R1"}],
                                        "transactions": [{"transaction_id": "T1"}],
                                    }
                                ],
                            }
                        ],
                        "stage_id": "S1",
                        "start_time": {"value": "unknown"},
                        "title": {"value": f"Synthetic stage {index}"},
                    }
                ],
                "start_time": {"value": "unknown"},
                "title": {"value": f"Synthetic event {index}"},
            },
            "event_id": event_id,
            "not_gold_warning": (
                "This FinMycelium FinalCascade draft is a construction artifact, "
                "not the Gold reference or scoring target."
            ),
            "public_event_id": event_id,
            "quality_flags_public": [],
            "redaction_counts": {"reasons": 1},
            "redaction_level": "public_sanitized_full_graph",
            "schema_version": "h2epr-finmycelium-finalcascade-public-v2",
            "source_artifact_name": "FinalEventCascade.json",
            "source_event_label": f"synthetic_event_{index}",
            "source_payload_sha256": self._source_hash(index),
            "workflow_family": "FinMycelium",
        }

    def _viewer_rows(self) -> dict[str, list[dict[str, object]]]:
        gallery = []
        catalog = []
        instances = []
        stages = []
        summaries = []
        for index in (1, 2):
            event_id = f"H2EPR-{index:04d}"
            title = f"Synthetic event {index}"
            common = {
                "public_event_id": event_id,
                "event_id": event_id,
                "title": title,
                "display_name": title,
                "event_descriptor": f"Synthetic descriptor {index}.",
                "domain": "Synthetic domain",
                "category": "Synthetic category",
                "keywords": "synthetic",
                "has_gold_reference": True,
            }
            gallery.append(
                {
                    "public_event_id": event_id,
                    "title": title,
                    "domain": common["domain"],
                    "category": common["category"],
                    "event_descriptor": common["event_descriptor"],
                    "schema_version": validator.TABLE_CONTRACTS["event_gallery"][
                        "schema_version"
                    ],
                }
            )
            catalog.append(
                {
                    **common,
                    "stage_count": 1,
                    "episode_count": 1,
                    "schema_version": validator.TABLE_CONTRACTS["event_catalog"][
                        "schema_version"
                    ],
                }
            )
            instances.append(
                {
                    **common,
                    "finalcascade_access_level": "public_sanitized_full_graph",
                    "gold_reference_access_level": "manual_gated_companion",
                    "evidence_context_access_level": "not_included_in_this_release",
                    "schema_version": validator.TABLE_CONTRACTS["event_instances"][
                        "schema_version"
                    ],
                }
            )
            stages.append(
                {
                    "public_event_id": event_id,
                    "event_id": event_id,
                    "stage_id": "S1",
                    "stage_index": 1,
                    "stage_title": f"Synthetic stage {index}",
                    "stage_start_time": "unknown",
                    "stage_end_time": "unknown",
                    "stage_boundary_time_status": "unknown_boundary_no_action_anchors",
                    "episode_count": 1,
                    "participant_count": 1,
                    "action_count": 1,
                    "transaction_count": 1,
                    "relation_count": 1,
                    "known_action_time_anchor_count": 0,
                    "known_action_time_anchors": "",
                    "relative_order_available": False,
                    "schema_version": validator.TABLE_CONTRACTS["event_stages"][
                        "schema_version"
                    ],
                }
            )
            summaries.append(
                {
                    "public_event_id": event_id,
                    "event_id": event_id,
                    "title": title,
                    "domain": common["domain"],
                    "category": common["category"],
                    "stage_count": 1,
                    "episode_count": 1,
                    "participant_count": 1,
                    "action_count": 1,
                    "transaction_count": 1,
                    "relation_count": 1,
                    "event_start_time": "unknown",
                    "event_end_time": "unknown",
                    "event_boundary_time_status": "unknown_boundary_no_action_anchors",
                    "known_action_time_anchor_count": 0,
                    "known_action_time_anchors": "",
                    "relative_order_available": False,
                    "schema_version": validator.TABLE_CONTRACTS[
                        "finalcascade_summary"
                    ]["schema_version"],
                }
            )
        return {
            "event_gallery": gallery,
            "event_catalog": catalog,
            "event_instances": instances,
            "event_stages": stages,
            "finalcascade_summary": summaries,
        }

    def _write_source_csv(self) -> None:
        path = self.root / self.contract["artifacts"]["draft_source_hashes"]["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=validator.SOURCE_HASH_FIELDS, lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(self.source_rows)

    def write_table(self, name: str) -> None:
        declared = self.contract["tables"][name]
        path = self.root / declared["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        fields = []
        for column in declared["columns"]:
            if column in validator.BOOL_COLUMNS:
                field_type = pa.bool_()
            elif column in validator.INT64_COLUMNS:
                field_type = pa.int64()
            else:
                field_type = pa.string()
            fields.append(pa.field(column, field_type))
        table = pa.Table.from_pylist(self.rows[name], schema=pa.schema(fields))
        pq.write_table(table, path)
        declared["sha256"] = _sha256(path)

    def rewrite_wrapper(
        self,
        index: int,
        wrapper: dict[str, object],
        *,
        update_sanitized_hash: bool = True,
    ) -> None:
        self.wrappers[index - 1] = wrapper
        event_id = f"H2EPR-{index:04d}"
        payload = _canonical_bytes(wrapper) + b"\n"
        (self.root / "draft_events" / event_id / "draft_epg.json").write_bytes(payload)
        aggregate = self.root / self.contract["artifacts"]["aggregate_drafts"]["path"]
        aggregate.write_bytes(b"".join(_canonical_bytes(row) + b"\n" for row in self.wrappers))
        if update_sanitized_hash:
            self.source_rows[index - 1]["sanitized_record_sha256"] = hashlib.sha256(
                payload[:-1]
            ).hexdigest()
            self._write_source_csv()
        self.refresh_integrity()

    def write_checksums(self) -> None:
        checksum = self.root / "SHA256SUMS"
        files = sorted(
            path
            for path in self.root.rglob("*")
            if path.is_file() and path != checksum
        )
        checksum.write_text(
            "".join(
                f"{_sha256(path)}  {path.relative_to(self.root).as_posix()}\n"
                for path in files
            ),
            encoding="ascii",
        )
        declared = self.contract["artifacts"]["package_checksums"]
        declared["entries"] = len(files)
        declared["sha256"] = _sha256(checksum)

    def refresh_integrity(self) -> None:
        for name in ("aggregate_drafts", "draft_source_hashes"):
            declared = self.contract["artifacts"][name]
            declared["sha256"] = _sha256(self.root / declared["path"])
        for name, declared in self.contract["tables"].items():
            declared["sha256"] = _sha256(self.root / declared["path"])
        self.write_checksums()
        self.write_contract()

    def write_contract(self) -> None:
        self.contract_path.write_text(
            json.dumps(self.contract, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )


class PublicDatasetReleaseTests(unittest.TestCase):
    def test_frozen_unified3000_candidate_contract(self):
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(contract["contract_version"], validator.CONTRACT_VERSION)
        self.assertIsNone(contract["dataset_revision"])
        self.assertEqual(
            contract["counts"],
            {
                "events": 3000,
                "draft_epgs": 3000,
                "stage_rows": 8843,
                "stage_events": 3000,
                "episodes": 16108,
                "participants": 42205,
                "actions": 46418,
                "transactions": 4748,
                "relations": 21337,
            },
        )
        self.assertEqual(tuple(contract["tables"]), tuple(validator.TABLE_CONTRACTS))
        self.assertEqual(
            {name: row["sha256"] for name, row in contract["tables"].items()},
            {
                "event_gallery": "be68b57e42cfc0cde97c949b5dcfe14cc4ec80397d428f1f27d88b39e88a9b53",
                "event_catalog": "2a478a96aa2713b3b3894a222a511aaaadd06327c90498d03405ad1860a33ac0",
                "event_instances": "ba258780091c10c46508684d90bebd5f34285a61cc4bc4c6600c75fa380817a8",
                "event_stages": "eeab17e56ceb14a99ffc6a64e8508f9b98bd5ea9d260b14cbf95a42374dc8db8",
                "finalcascade_summary": "273fedfdc74aba8f00669b7e82d45ec4a312b16aaa98f7c28182a06d9c6f471f",
            },
        )
        self.assertEqual(
            contract["artifacts"]["package_checksums"],
            {
                "path": "SHA256SUMS",
                "sha256": "9b30d71eacbfa0e07539a5805a3cf05065e76199dfcf0272ef1d135c1098960e",
                "entries": 3072,
            },
        )
        self.assertFalse(RETIRED_AVAILABILITY_SCHEMA.exists())

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

    def test_cache_preparer_uses_five_tables_and_fails_closed_before_publish(self):
        self.assertEqual(
            {
                path
                for path in cache_preparer.TEST_FILES
                if path.endswith(".parquet")
            },
            {
                spec["path"] for spec in validator.TABLE_CONTRACTS.values()
            },
        )
        self.assertFalse(
            any("availability" in path for path in cache_preparer.TEST_FILES)
        )
        self.assertIn(
            "manifests/draft_source_hashes.csv", cache_preparer.TEST_FILES
        )
        self.assertEqual(
            {
                path
                for path in cache_preparer.TEST_FILES
                if path.startswith("draft_events/")
            },
            {
                "draft_events/H2EPR-0001/draft_epg.json",
                "draft_events/H2EPR-1000/draft_epg.json",
            },
        )
        with self.assertRaisesRegex(SystemExit, "not pinned to an immutable 40-hex"):
            cache_preparer.load_published_identity(CONTRACT_PATH)
        with tempfile.TemporaryDirectory() as directory:
            contract = copy.deepcopy(
                json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
            )
            contract["dataset_revision"] = "a" * 40
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(contract), encoding="utf-8")
            self.assertEqual(
                cache_preparer.load_published_identity(path),
                ("AgenticFinLab/H2EPR-Bench", "a" * 40),
            )

    def test_complete_synthetic_candidate_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            receipt = validator.validate_release(release.root, release.contract_path)
        self.assertTrue(receipt["all_checks_passed"])
        self.assertEqual(receipt["publication_state"], "local_candidate")
        self.assertFalse(receipt["immutable_revision_bound"])
        self.assertEqual(receipt["counts"]["events"], 2)
        self.assertEqual(receipt["counts"]["draft_epgs"], 2)
        self.assertEqual(receipt["graph_totals"]["stage_count"], 2)
        self.assertFalse(receipt["gold_records_accessed"])
        self.assertRegex(receipt["draft_ledger_sha256"], r"^[a-f0-9]{64}$")

    def test_published_gate_fails_closed_and_accepts_only_immutable_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "immutable 40-hex"
            ):
                validator.validate_release(
                    release.root, release.contract_path, require_published=True
                )
            process = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR_PATH),
                    str(release.root),
                    "--contract",
                    str(release.contract_path),
                    "--require-published",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(process.returncode, 0)
            self.assertIn("immutable 40-hex", process.stderr)

            release.contract["dataset_revision"] = "g" * 40
            release.write_contract()
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "must be null or an immutable"
            ):
                validator.validate_release(release.root, release.contract_path)

            release.contract["dataset_revision"] = "1" * 40
            release.write_contract()
            receipt = validator.validate_release(
                release.root, release.contract_path, require_published=True
            )
            self.assertEqual(receipt["publication_state"], "published")
            self.assertTrue(receipt["immutable_revision_bound"])

    def test_rejects_extra_direct_file_and_hard_link(self):
        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            extra = release.root / "draft_events" / "H2EPR-0001" / "extra.json"
            extra.write_text("{}\n", encoding="utf-8")
            release.refresh_integrity()
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "exactly draft_epg.json"
            ):
                validator.validate_release(release.root, release.contract_path)

        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            source = release.root / "draft_events" / "H2EPR-0001" / "draft_epg.json"
            hard_link = release.root / "hard-linked-copy.json"
            os.link(source, hard_link)
            release.refresh_integrity()
            with self.assertRaisesRegex(validator.ReleaseValidationError, "hard link"):
                validator.validate_release(release.root, release.contract_path)

    def test_rejects_aggregate_direct_byte_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            direct = release.root / "draft_events" / "H2EPR-0001" / "draft_epg.json"
            direct.write_bytes(b"{}\n")
            release.refresh_integrity()
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "Aggregate/direct Draft byte mismatch"
            ):
                validator.validate_release(release.root, release.contract_path)

    def test_rejects_source_manifest_order_and_wrapper_bindings(self):
        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            release.source_rows[0]["draft_record_index"] = "2"
            release._write_source_csv()
            release.refresh_integrity()
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "draft_record_index"
            ):
                validator.validate_release(release.root, release.contract_path)

        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            wrapper = copy.deepcopy(release.wrappers[0])
            wrapper["event"]["event_id"] = "H2EPR-0002"
            release.rewrite_wrapper(1, wrapper)
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "nested event identity"
            ):
                validator.validate_release(release.root, release.contract_path)

        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            wrapper = copy.deepcopy(release.wrappers[0])
            wrapper["source_payload_sha256"] = "f" * 64
            release.rewrite_wrapper(1, wrapper)
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "source hash mismatch"
            ):
                validator.validate_release(release.root, release.contract_path)

    def test_rejects_noncanonical_wrapper_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            reversed_wrapper = dict(reversed(list(release.wrappers[0].items())))
            pretty = json.dumps(
                reversed_wrapper, ensure_ascii=False, separators=(",", ":")
            ).encode() + b"\n"
            direct = release.root / "draft_events" / "H2EPR-0001" / "draft_epg.json"
            direct.write_bytes(pretty)
            aggregate = release.root / release.contract["artifacts"]["aggregate_drafts"]["path"]
            lines = aggregate.read_bytes().splitlines(keepends=True)
            lines[0] = pretty
            aggregate.write_bytes(b"".join(lines))
            release.source_rows[0]["sanitized_record_sha256"] = hashlib.sha256(
                pretty[:-1]
            ).hexdigest()
            release._write_source_csv()
            release.refresh_integrity()
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "not canonical JSON"
            ):
                validator.validate_release(release.root, release.contract_path)

    def test_rejects_exact_parquet_set_hash_and_graph_closure_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            extra = release.root / "data" / "viewer_mirrors" / "extra.parquet"
            extra.write_bytes(
                (release.root / release.contract["tables"]["event_gallery"]["path"]).read_bytes()
            )
            release.refresh_integrity()
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "exactly five declared Parquet"
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

        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            release.rows["event_stages"][0]["stage_index"] = 2
            release.write_table("event_stages")
            release.refresh_integrity()
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "Derived graph row mismatch"
            ):
                validator.validate_release(release.root, release.contract_path)

        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            release.rows["finalcascade_summary"][0]["action_count"] = 2
            release.write_table("finalcascade_summary")
            release.refresh_integrity()
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "Derived graph row mismatch"
            ):
                validator.validate_release(release.root, release.contract_path)

        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            release.rows["event_catalog"][0]["stage_count"] = 2
            release.write_table("event_catalog")
            release.refresh_integrity()
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "Catalog graph count mismatch"
            ):
                validator.validate_release(release.root, release.contract_path)

    def test_rejects_package_sha256sums_file_closure_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            release = SyntheticPublicRelease(Path(directory))
            # Deliberately do not regenerate SHA256SUMS.
            (release.root / "unbound-file.txt").write_text("unbound\n", encoding="utf-8")
            with self.assertRaisesRegex(
                validator.ReleaseValidationError, "file closure mismatch"
            ):
                validator.validate_release(release.root, release.contract_path)

    @unittest.skipUnless(ACTUAL_RC.is_dir(), "local Unified-3000 v2 RC is not present")
    def test_actual_unified3000_v2_release_candidate_passes(self):
        receipt = validator.validate_release(ACTUAL_RC, CONTRACT_PATH)
        self.assertTrue(receipt["all_checks_passed"])
        self.assertEqual(receipt["publication_state"], "local_candidate")
        self.assertEqual(receipt["counts"]["events"], 3000)
        self.assertEqual(receipt["counts"]["draft_epgs"], 3000)
        self.assertEqual(receipt["graph_totals"]["stage_count"], 8843)
        self.assertEqual(receipt["package_checksum_entries"], 3072)


if __name__ == "__main__":
    unittest.main()
