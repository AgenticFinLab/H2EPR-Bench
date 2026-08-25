import ast
import hashlib
import inspect
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SPACE_ROOT = REPO_ROOT / "spaces" / "h2epr_bench_explorer"
EXPECTED_DATASET_REVISION = "6156a6bb3b838143401cb3e5709f708e5d6e802c"
if os.environ.get("H2EPR_TEST_DATASET_DIR"):
    DATASET_ROOT = Path(os.environ["H2EPR_TEST_DATASET_DIR"]).expanduser().resolve()
else:
    candidates = (
        REPO_ROOT / "build" / "hf_unified3000_v2_rc_v2" / "H2EPR-Bench",
        REPO_ROOT.parents[1]
        / "build"
        / "hf_unified3000_v2_rc_v2"
        / "H2EPR-Bench",
    )
    DATASET_ROOT = next((candidate for candidate in candidates if candidate.is_dir()), candidates[0])
sys.path.insert(0, str(SPACE_ROOT / "src"))


def _read_contract_inputs():
    root = DATASET_ROOT / "data" / "viewer_mirrors"
    gallery = pd.read_parquet(root / "event_gallery.parquet")
    catalog = pd.read_parquet(root / "event_catalog.parquet")
    instances = pd.read_parquet(root / "event_instances.parquet")
    summary = pd.read_parquet(root / "finalcascade_summary.parquet")
    source_hashes = pd.read_csv(DATASET_ROOT / "manifests" / "draft_source_hashes.csv")
    return gallery, catalog, instances, summary, source_hashes


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class H2EPRExplorerSpaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from h2epr_explorer.data_loader import clear_caches, load_release

        if not DATASET_ROOT.is_dir():
            raise RuntimeError(f"Unified-3000 release candidate is missing: {DATASET_ROOT}")
        clear_caches()
        cls.release = load_release(DATASET_ROOT)

    def test_space_readme_declares_uniform_release_and_boundary(self):
        readme = (SPACE_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("sdk: docker", readme)
        self.assertIn("license: apache-2.0", readme)
        self.assertIn("Streamlit", readme)
        self.assertIn("Unified-3000", readme)
        self.assertIn("3,000", readme)
        self.assertIn("Draft EPG", readme)
        self.assertIn("reference EPG", readme)
        self.assertIn("manual-gated companion", readme)
        self.assertIn("draft_events/<H2EPR-ID>/draft_epg.json", readme)
        self.assertIn("manifests/draft_source_hashes.csv", readme)
        self.assertIn("fail closed", readme)
        for forbidden in (
            "2," + "876",
            "1" + "24 catalog",
            "draft_" + "availability",
            "1d01f364" + "9ace0301",
        ):
            self.assertNotIn(forbidden, readme)

    def test_space_container_files_remain_compatible(self):
        dockerfile = (SPACE_ROOT / "Dockerfile").read_text(encoding="utf-8")
        requirements = (SPACE_ROOT / "requirements.txt").read_text(encoding="utf-8")

        self.assertIn("streamlit run app.py", dockerfile)
        self.assertIn("--server.port=7860", dockerfile)
        self.assertIn("--server.address=0.0.0.0", dockerfile)
        for dependency in ("streamlit", "pandas", "pyarrow", "plotly", "huggingface_hub"):
            self.assertIn(dependency, requirements)

    def test_constants_bind_exact_published_assets_and_uniform_counts(self):
        from h2epr_explorer.constants import (
            CATALOG_PARQUET,
            DEFAULT_PUBLIC_DATASET_REVISION,
            DRAFT_SOURCE_HASHES_CSV,
            EVENT_GALLERY_PARQUET,
            EVENT_INSTANCES_PARQUET,
            EXPECTED_EVENT_COUNT,
            EXPECTED_STAGE_ROW_COUNT,
            FINALCASCADE_SUMMARY_PARQUET,
            PUBLIC_DATASET_REVISION,
            RELEASE_ASSET_SHA256,
            STAGES_PARQUET,
        )

        self.assertEqual(DEFAULT_PUBLIC_DATASET_REVISION, EXPECTED_DATASET_REVISION)
        self.assertEqual(PUBLIC_DATASET_REVISION, EXPECTED_DATASET_REVISION)
        self.assertEqual(EXPECTED_EVENT_COUNT, 3000)
        self.assertEqual(EXPECTED_STAGE_ROW_COUNT, 8843)
        expected_assets = (
            EVENT_GALLERY_PARQUET,
            CATALOG_PARQUET,
            EVENT_INSTANCES_PARQUET,
            STAGES_PARQUET,
            FINALCASCADE_SUMMARY_PARQUET,
            DRAFT_SOURCE_HASHES_CSV,
        )
        self.assertEqual(set(RELEASE_ASSET_SHA256), set(expected_assets))
        for relative_path in expected_assets:
            with self.subTest(relative_path=relative_path):
                self.assertEqual(_sha256(DATASET_ROOT / relative_path), RELEASE_ASSET_SHA256[relative_path])

    def test_constants_expose_canonical_project_links_and_columns(self):
        from h2epr_explorer.constants import (
            CATALOG_COLUMNS,
            DRAFT_EPG_PATH_TEMPLATE,
            FINMYCELIUM_URL,
            GOLD_COMPANION_REPO,
            GOLD_COMPANION_URL,
            PROJECT_WEBSITE_URL,
            PUBLIC_DATASET_REPO,
            PUBLIC_DATASET_URL,
            RELEASE_BOUNDARY_NOTICE,
            SOURCE_REPOSITORY_URL,
        )

        self.assertEqual(PUBLIC_DATASET_REPO, "AgenticFinLab/H2EPR-Bench")
        self.assertEqual(GOLD_COMPANION_REPO, "AgenticFinLab/H2EPR-Bench-Gold")
        self.assertEqual(PROJECT_WEBSITE_URL, "https://agenticfinlab.github.io/H2EPR-Bench/")
        self.assertEqual(SOURCE_REPOSITORY_URL, "https://github.com/AgenticFinLab/H2EPR-Bench")
        self.assertEqual(PUBLIC_DATASET_URL, "https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench")
        self.assertEqual(FINMYCELIUM_URL, "https://github.com/AgenticFinLab/FinMycelium")
        self.assertEqual(GOLD_COMPANION_URL, "https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold")
        self.assertEqual(DRAFT_EPG_PATH_TEMPLATE, "draft_events/{event_id}/draft_epg.json")
        self.assertEqual(
            CATALOG_COLUMNS,
            (
                "event_id",
                "display_name",
                "domain",
                "category",
                "event_descriptor",
                "keywords",
                "stage_count",
            ),
        )
        self.assertIn("Draft EPGs", RELEASE_BOUNDARY_NOTICE)
        self.assertIn("reference EPGs", RELEASE_BOUNDARY_NOTICE)

    def test_explorer_exposes_canonical_project_links(self):
        app = (SPACE_ROOT / "app.py").read_text(encoding="utf-8")
        expected_labels = (
            "Project Website",
            "Public Dataset",
            "FinMycelium System",
            "Reference EPGs (Gated)",
            "Release Repository",
        )
        positions = [app.index(f'"{label}"') for label in expected_labels]
        self.assertEqual(positions, sorted(positions))
        for constant in (
            "PROJECT_WEBSITE_URL",
            "SOURCE_REPOSITORY_URL",
            "PUBLIC_DATASET_REVISION_URL",
            "FINMYCELIUM_URL",
            "GOLD_COMPANION_URL",
        ):
            self.assertIn(constant, app)

    def test_full_local_release_is_uniform_and_complete(self):
        from h2epr_explorer.constants import (
            EVIDENCE_CONTEXT_ACCESS_LEVEL,
            FINALCASCADE_ACCESS_LEVEL,
            GOLD_REFERENCE_ACCESS_LEVEL,
            GRAPH_COUNT_COLUMNS,
        )

        events = self.release.events
        stages = self.release.stages
        self.assertEqual(len(events), 3000)
        self.assertEqual(events["event_id"].tolist(), [f"H2EPR-{i:04d}" for i in range(1, 3001)])
        self.assertTrue(events["event_id"].equals(events["public_event_id"]))
        self.assertEqual(len(stages), 8843)
        self.assertEqual(stages["event_id"].nunique(), 3000)
        self.assertEqual(set(stages["event_id"]), set(events["event_id"]))
        self.assertFalse(events[list(GRAPH_COUNT_COLUMNS)].isna().any().any())
        self.assertTrue(events["finalcascade_access_level"].eq(FINALCASCADE_ACCESS_LEVEL).all())
        self.assertTrue(events["gold_reference_access_level"].eq(GOLD_REFERENCE_ACCESS_LEVEL).all())
        self.assertTrue(events["evidence_context_access_level"].eq(EVIDENCE_CONTEXT_ACCESS_LEVEL).all())
        self.assertTrue(events["source_payload_sha256"].str.fullmatch(r"[0-9a-f]{64}").all())
        self.assertTrue(events["sanitized_record_sha256"].str.fullmatch(r"[0-9a-f]{64}").all())
        self.assertEqual(events["draft_record_index"].tolist(), list(range(1, 3001)))
        self.assertGreater(len(self.release.stage_frame("H2EPR-0001")), 0)
        self.assertGreater(len(self.release.stage_frame("H2EPR-1000")), 0)
        self.assertGreater(len(self.release.stage_frame("H2EPR-3000")), 0)

    def test_loaded_release_contains_no_retired_per_event_fields(self):
        retired_fields = {
            "draft_" + "status",
            "has_" + "finalcascade",
            "unavailable_" + "reason",
            "release_" + "split",
            "version",
        }
        self.assertTrue(retired_fields.isdisjoint(self.release.events.columns))
        self.assertTrue(retired_fields.isdisjoint(self.release.stages.columns))

    def test_stage_contract_closes_identity_order_and_event_summary(self):
        import h2epr_explorer.data_loader as loader

        stages = self.release.stages.copy(deep=True)
        events = self.release.events.copy(deep=True)
        loader._validate_stages(stages, events)
        event_indices = stages.index[stages["event_id"].eq("H2EPR-0001")].tolist()
        self.assertGreater(len(event_indices), 1)

        duplicate_index = stages.copy(deep=True)
        duplicate_index.loc[event_indices[1], "stage_index"] = duplicate_index.loc[
            event_indices[0], "stage_index"
        ]
        with self.assertRaisesRegex(loader.ReleaseContractError, "duplicate stage_index"):
            loader._validate_stages(duplicate_index, events)

        stage_gap = stages.copy(deep=True)
        stage_gap.loc[event_indices[-1], "stage_index"] = len(event_indices) + 1
        with self.assertRaisesRegex(loader.ReleaseContractError, "Non-contiguous"):
            loader._validate_stages(stage_gap, events)

        stage_count_mismatch = events.copy(deep=True)
        selected_event = stage_count_mismatch["event_id"].eq("H2EPR-0001")
        stage_count_mismatch.loc[selected_event, "stage_count"] += 1
        with self.assertRaisesRegex(loader.ReleaseContractError, "stage_count closure"):
            loader._validate_stages(stages, stage_count_mismatch)

        for column in (
            "episode_count",
            "participant_count",
            "action_count",
            "transaction_count",
            "relation_count",
        ):
            with self.subTest(column=column):
                component_mismatch = events.copy(deep=True)
                component_mismatch.loc[selected_event, column] += 1
                with self.assertRaisesRegex(loader.ReleaseContractError, f"{column} closure"):
                    loader._validate_stages(stages, component_mismatch)

    def test_release_load_is_deterministic_after_cache_clear(self):
        from h2epr_explorer.data_loader import clear_caches, load_release

        first_events = self.release.events.copy(deep=True)
        first_stages = self.release.stages.copy(deep=True)
        clear_caches()
        second = load_release(DATASET_ROOT)
        pd.testing.assert_frame_equal(first_events, second.events, check_exact=True)
        pd.testing.assert_frame_equal(first_stages, second.stages, check_exact=True)

    def test_contract_rejects_schema_drift_duplicate_identity_and_order_drift(self):
        from h2epr_explorer.data_loader import ReleaseContractError, build_explorer_view

        gallery, catalog, instances, summary, source_hashes = _read_contract_inputs()
        with self.assertRaisesRegex(ReleaseContractError, "Schema mismatch"):
            build_explorer_view(
                gallery,
                catalog.drop(columns=["category"]),
                instances,
                summary,
                source_hashes,
            )

        duplicated_instances = pd.concat(
            [instances.iloc[:-1], instances.iloc[[0]]], ignore_index=True
        )
        with self.assertRaisesRegex(ReleaseContractError, "duplicate identity"):
            build_explorer_view(gallery, catalog, duplicated_instances, summary, source_hashes)

        reordered_catalog = pd.concat([catalog.iloc[[1]], catalog.iloc[[0]], catalog.iloc[2:]])
        with self.assertRaisesRegex(ReleaseContractError, "exact numeric"):
            build_explorer_view(gallery, reordered_catalog, instances, summary, source_hashes)

    def test_contract_rejects_semantic_access_and_hash_registry_drift(self):
        from h2epr_explorer.data_loader import ReleaseContractError, build_explorer_view

        gallery, catalog, instances, summary, source_hashes = _read_contract_inputs()
        bad_summary = summary.copy()
        bad_summary.loc[0, "category"] = "contract-drift"
        with self.assertRaisesRegex(ReleaseContractError, "category disagrees"):
            build_explorer_view(gallery, catalog, instances, bad_summary, source_hashes)

        bad_access = instances.copy()
        bad_access.loc[0, "finalcascade_access_level"] = "contract-drift"
        with self.assertRaisesRegex(ReleaseContractError, "finalcascade_access_level"):
            build_explorer_view(gallery, catalog, bad_access, summary, source_hashes)

        bad_hashes = source_hashes.copy()
        bad_hashes.loc[0, "sanitized_record_sha256"] = "0" * 63
        with self.assertRaisesRegex(ReleaseContractError, "malformed sanitized_record_sha256"):
            build_explorer_view(gallery, catalog, instances, summary, bad_hashes)

    def test_release_asset_digest_is_checked_before_parquet_parse(self):
        import h2epr_explorer.data_loader as loader
        from h2epr_explorer.constants import CATALOG_PARQUET, CATALOG_SCHEMA

        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            altered = Path(tmp) / "event_catalog.parquet"
            payload = bytearray((DATASET_ROOT / CATALOG_PARQUET).read_bytes())
            payload[-1] ^= 1
            altered.write_bytes(payload)
            with mock.patch.object(loader, "resolve_dataset_file", return_value=altered):
                with self.assertRaisesRegex(loader.ReleaseContractError, "digest mismatch"):
                    loader._read_required_parquet(CATALOG_PARQUET, CATALOG_SCHEMA, DATASET_ROOT)

    def test_filters_search_current_fields_and_uniform_stage_counts(self):
        from h2epr_explorer.filters import filter_catalog

        rows = [
            {
                "public_event_id": "H2EPR-0001",
                "event_id": "H2EPR-0001",
                "title": "Northern market event",
                "display_name": "Northern market event",
                "event_descriptor": "A liquidity event.",
                "domain": "Finance",
                "category": "Market Events",
                "keywords": "bank; liquidity",
                "stage_count": 4,
            },
            {
                "public_event_id": "H2EPR-3000",
                "event_id": "H2EPR-3000",
                "title": "Policy event",
                "display_name": "Policy event",
                "event_descriptor": "An exchange-rate policy process.",
                "domain": "Finance",
                "category": "Policy Events",
                "keywords": "policy; exchange rate",
                "stage_count": 3,
            },
        ]
        for query in ("H2EPR-0001", "Northern", "liquidity", "Market Events"):
            with self.subTest(query=query):
                self.assertEqual(
                    [row["event_id"] for row in filter_catalog(rows, query=query)],
                    ["H2EPR-0001"],
                )
        self.assertEqual(len(filter_catalog(rows, min_stage_count=0)), 2)
        self.assertEqual(
            [row["event_id"] for row in filter_catalog(rows, min_stage_count=4)],
            ["H2EPR-0001"],
        )
        removed_parameter = "min_" + "source_" + "count"
        self.assertNotIn(removed_parameter, inspect.signature(filter_catalog).parameters)

    def test_non_navigation_modules_reject_legacy_identity(self):
        from h2epr_explorer.data_loader import InvalidEventId, load_event_graph
        from h2epr_explorer.filters import filter_catalog
        from h2epr_explorer.render_gantt import prepare_gantt_rows

        legacy_id = "P1000-0001"
        with self.assertRaises(ValueError):
            filter_catalog([{"event_id": legacy_id}])
        with self.assertRaises(ValueError):
            prepare_gantt_rows([{"event_id": legacy_id, "stage_id": "S1", "stage_index": 1}])
        with self.assertRaises(InvalidEventId):
            load_event_graph(legacy_id, release=self.release, local_dataset_dir=DATASET_ROOT)

    def test_display_helpers_use_current_catalog_fields(self):
        from h2epr_explorer.filters import event_description, event_display_label

        row = {
            "event_id": "H2EPR-0001",
            "display_name": "Market event",
            "event_descriptor": "A liquidity process.",
        }
        self.assertEqual(event_display_label(row), "H2EPR-0001 · Market event")
        self.assertEqual(event_description(row), "A liquidity process.")

    def test_cached_graph_samples_use_the_fixed_direct_path(self):
        event_root = DATASET_ROOT / "draft_events"
        for event_id in ("H2EPR-0001", "H2EPR-1000"):
            with self.subTest(event_id=event_id):
                files = list((event_root / event_id).iterdir())
                self.assertEqual([path.name for path in files], ["draft_epg.json"])
                self.assertTrue(files[0].is_file())

    def test_graph_uses_derived_direct_path_and_registry_integrity(self):
        import h2epr_explorer.data_loader as loader

        loader.clear_caches()
        original_resolver = loader.resolve_dataset_file
        with mock.patch.object(loader, "resolve_dataset_file", wraps=original_resolver) as resolver:
            graph = loader.load_event_graph(
                "H2EPR-0001", release=self.release, local_dataset_dir=DATASET_ROOT
            )

        self.assertEqual(graph["event_id"], "H2EPR-0001")
        self.assertEqual(graph["public_event_id"], "H2EPR-0001")
        self.assertEqual(graph["event"]["event_id"], "H2EPR-0001")
        requested_path = resolver.call_args.args[0]
        self.assertEqual(requested_path, "draft_events/H2EPR-0001/draft_epg.json")
        event_row = self.release.event_row("H2EPR-0001")
        self.assertEqual(graph["source_payload_sha256"], event_row["source_payload_sha256"])
        self.assertEqual(loader._canonical_graph_sha256(graph), event_row["sanitized_record_sha256"])

    def test_graph_validator_requires_exact_nested_event_identity(self):
        import h2epr_explorer.data_loader as loader

        source = DATASET_ROOT / "draft_events" / "H2EPR-0001" / "draft_epg.json"
        valid_payload = json.loads(source.read_text(encoding="utf-8"))
        event_row = self.release.event_row("H2EPR-0001")
        self.assertIs(loader._validate_graph(valid_payload, "H2EPR-0001", event_row), valid_payload)

        invalid_nested_events = {
            "missing": None,
            "non_object": ["H2EPR-0001"],
            "missing_id": {},
            "wrong_id": {"event_id": "H2EPR-0002"},
        }
        for case, nested_event in invalid_nested_events.items():
            with self.subTest(case=case):
                payload = valid_payload.copy()
                if case == "missing":
                    payload.pop("event")
                else:
                    payload["event"] = nested_event
                with self.assertRaisesRegex(loader.DraftIntegrityError, "Nested Draft EPG"):
                    loader._validate_graph(payload, "H2EPR-0001", event_row)

    def test_graph_loader_treats_every_event_uniformly(self):
        import h2epr_explorer.data_loader as loader

        loader.clear_caches()
        original_resolver = loader.resolve_dataset_file
        with mock.patch.object(loader, "resolve_dataset_file", wraps=original_resolver) as resolver:
            graph = loader.load_event_graph(
                "H2EPR-1000", release=self.release, local_dataset_dir=DATASET_ROOT
            )
        self.assertEqual(graph["event_id"], "H2EPR-1000")
        self.assertEqual(resolver.call_args.args[0], "draft_events/H2EPR-1000/draft_epg.json")

    def test_graph_loader_rejects_malformed_and_traversal_ids(self):
        from h2epr_explorer.data_loader import InvalidEventId, load_event_graph

        invalid_ids = (
            "H2EPR-0000",
            "H2EPR-3001",
            "H2EPR-0001/../../outside",
            "../H2EPR-0001",
            "H2EPR-1",
            "",
        )
        for event_id in invalid_ids:
            with self.subTest(event_id=event_id), self.assertRaises(InvalidEventId):
                load_event_graph(event_id, release=self.release, local_dataset_dir=DATASET_ROOT)

    def test_local_resolver_rejects_path_escape(self):
        from h2epr_explorer.data_loader import resolve_dataset_file

        with self.assertRaises(ValueError):
            resolve_dataset_file("../outside", DATASET_ROOT)
        with self.assertRaises(ValueError):
            resolve_dataset_file("/etc/passwd", DATASET_ROOT)

    def _assert_graph_mutation_rejected(self, mutation, message):
        import h2epr_explorer.data_loader as loader

        source = DATASET_ROOT / "draft_events" / "H2EPR-0001" / "draft_epg.json"
        payload = json.loads(source.read_text(encoding="utf-8"))
        mutation(payload)
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            path = Path(tmp) / "mutated.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            loader.clear_caches()
            with mock.patch.object(loader, "resolve_dataset_file", return_value=path):
                with self.assertRaisesRegex(loader.DraftIntegrityError, message):
                    loader.load_event_graph("H2EPR-0001", release=self.release)

    def test_graph_loader_rejects_wrong_identity(self):
        self._assert_graph_mutation_rejected(
            lambda payload: payload.__setitem__("event_id", "H2EPR-0002"),
            "identity mismatch",
        )

    def test_graph_loader_rejects_wrong_sanitized_hash(self):
        self._assert_graph_mutation_rejected(
            lambda payload: payload.__setitem__("redaction_level", "tampered"),
            "sanitized record digest",
        )

    def test_graph_loader_rejects_wrong_source_hash(self):
        self._assert_graph_mutation_rejected(
            lambda payload: payload.__setitem__("source_payload_sha256", "0" * 64),
            "source payload digest",
        )

    def test_graph_loader_reports_missing_required_asset(self):
        import h2epr_explorer.data_loader as loader

        loader.clear_caches()
        with mock.patch.object(
            loader, "resolve_dataset_file", side_effect=FileNotFoundError("missing")
        ):
            with self.assertRaises(loader.DraftAssetMissing):
                loader.load_event_graph("H2EPR-0001", release=self.release)

    def test_unbound_remote_reads_fail_closed_before_hugging_face_call(self):
        import h2epr_explorer.data_loader as loader
        from h2epr_explorer.constants import CATALOG_PARQUET, LOCAL_DATASET_ENV

        with mock.patch.dict(os.environ, {LOCAL_DATASET_ENV: ""}):
            with mock.patch.object(loader, "PUBLIC_DATASET_REVISION", None):
                with mock.patch.object(loader, "hf_hub_download") as download:
                    with self.assertRaises(loader.DatasetRevisionUnavailable):
                        loader.resolve_dataset_file(CATALOG_PARQUET)
                    with self.assertRaises(loader.DatasetRevisionUnavailable):
                        loader.load_event_graph("H2EPR-0001", release=self.release)
            download.assert_not_called()

    def test_navigation_translates_only_inbound_legacy_links(self):
        from h2epr_explorer.navigation import normalize_query_event_id

        expected = {
            "P1000-0001": "H2EPR-0001",
            "P1000-0359": "H2EPR-0359",
            "P1000-0360": "H2EPR-0087",
            "P1000-0361": "H2EPR-0360",
            "P1000-1000": "H2EPR-0999",
        }
        for legacy_id, canonical_id in expected.items():
            with self.subTest(legacy_id=legacy_id):
                result = normalize_query_event_id(legacy_id)
                self.assertEqual(result.canonical_id, canonical_id)
                self.assertTrue(result.used_legacy_mapping)

    def test_navigation_canonicalizes_query_state_and_rejects_unknown_ids(self):
        from h2epr_explorer.navigation import query_param_event_id

        current = query_param_event_id({"event_id": ["H2EPR-3000"]})
        self.assertEqual(current.canonical_id, "H2EPR-3000")
        self.assertFalse(current.used_legacy_mapping)
        translated = query_param_event_id({"event_id": ["P1000-0361"]})
        self.assertEqual(translated.canonical_id, "H2EPR-0360")
        self.assertTrue(translated.used_legacy_mapping)
        for value in ("H2EPR-3001", "P1000-1001", "../../event", "unknown"):
            with self.subTest(value=value):
                self.assertTrue(query_param_event_id({"event_id": value}).unresolved)

    def test_published_navigation_uses_the_pinned_dataset_revision(self):
        import h2epr_explorer.navigation as navigation

        links = navigation.build_event_links("H2EPR-0001")
        self.assertEqual(
            links["explorer"],
            "https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer?event_id=H2EPR-0001",
        )
        self.assertEqual(
            links["public_dataset"],
            f"{navigation.PUBLIC_DATASET_URL}/tree/{EXPECTED_DATASET_REVISION}",
        )
        self.assertEqual(
            links["draft_epg"],
            f"{navigation.PUBLIC_DATASET_URL}/blob/{EXPECTED_DATASET_REVISION}/draft_events/H2EPR-0001/draft_epg.json",
        )
        with self.assertRaises(ValueError):
            navigation.build_event_links("P1000-0001")

    def test_unbound_navigation_still_fails_closed(self):
        import h2epr_explorer.navigation as navigation

        with mock.patch.object(navigation, "PUBLIC_DATASET_REVISION", None):
            links = navigation.build_event_links("H2EPR-0001")
            self.assertEqual(links["public_dataset"], navigation.PUBLIC_DATASET_URL)
            self.assertNotIn("draft_epg", links)
            self.assertNotIn("/tree/None", json.dumps(links))
            self.assertNotIn("/blob/None", json.dumps(links))
            with self.assertRaises(navigation.ImmutableDatasetLinkUnavailable):
                navigation.build_immutable_dataset_link()
            with self.assertRaises(navigation.ImmutableDatasetLinkUnavailable):
                navigation.build_immutable_dataset_link(
                    "draft_events/H2EPR-0001/draft_epg.json"
                )

    def test_published_navigation_uses_one_immutable_revision_for_all_events(self):
        import h2epr_explorer.navigation as navigation

        revision = "a" * 40
        with mock.patch.object(navigation, "PUBLIC_DATASET_REVISION", revision):
            for event_id in ("H2EPR-0001", "H2EPR-1000", "H2EPR-3000"):
                links = navigation.build_event_links(event_id)
                self.assertEqual(
                    links["public_dataset"],
                    f"{navigation.PUBLIC_DATASET_URL}/tree/{revision}",
                )
                self.assertEqual(
                    links["draft_epg"],
                    f"{navigation.PUBLIC_DATASET_URL}/blob/{revision}/draft_events/{event_id}/draft_epg.json",
                )

    def test_timeline_handles_relative_and_calendar_modes_for_any_event(self):
        from h2epr_explorer.render_gantt import prepare_gantt_rows

        cases = {
            "H2EPR-0001": "relative_order",
            "H2EPR-0427": "calendar",
            "H2EPR-1000": "calendar",
            "H2EPR-3000": "calendar",
        }
        for event_id, expected_mode in cases.items():
            with self.subTest(event_id=event_id):
                rows = self.release.stage_frame(event_id).to_dict(orient="records")
                prepared = prepare_gantt_rows(rows)
                self.assertTrue(prepared)
                self.assertEqual({row["axis_mode"] for row in prepared}, {expected_mode})
                self.assertEqual(
                    [row["stage_index"] for row in prepared],
                    sorted(row["stage_index"] for row in prepared),
                )

    def test_timeline_uses_current_action_anchor_field(self):
        from h2epr_explorer.render_gantt import prepare_gantt_rows

        rows = [
            {
                "event_id": "H2EPR-0001",
                "stage_id": "S1",
                "stage_index": 1,
                "stage_title": "Build-up",
                "stage_start_time": "unknown",
                "stage_end_time": "unknown",
                "known_action_time_anchors": '["2008-09-15", "2008-09-16"]',
            }
        ]
        prepared = prepare_gantt_rows(rows)
        self.assertEqual(prepared[0]["axis_mode"], "relative_order")
        self.assertEqual(prepared[0]["time_note"], "2008-09-15; 2008-09-16")

    def test_calendar_timeline_normalizes_mixed_iso_precision(self):
        from h2epr_explorer.render_gantt import _calendar_datetime_values

        parsed = _calendar_datetime_values(["2017", "2017-11", "2017-11-30"])
        self.assertEqual(
            [value.strftime("%Y-%m-%d") for value in parsed],
            ["2017-01-01", "2017-11-01", "2017-11-30"],
        )

    def test_app_uses_uniform_graph_path_and_canonical_query_writeback(self):
        app_source = (SPACE_ROOT / "app.py").read_text(encoding="utf-8")

        self.assertIn("Draft EPG JSON", app_source)
        self.assertIn("Download selected Draft EPG JSON", app_source)
        self.assertIn('st.query_params["event_id"] = selected_event', app_source)
        self.assertIn("load_event_graph(selected_event, release=release)", app_source)
        self.assertNotIn("Final" + "Cascade JSON", app_source)
        for retired in (
            "DRAFT_" + "UNAVAILABLE_MESSAGE",
            "Draft" + "Unavailable",
            "draft_" + "available",
            "draft_" + "status",
            "has_" + "finalcascade",
        ):
            self.assertNotIn(retired, app_source)

    def test_app_filter_reset_has_stable_keys_and_preserves_deep_link_state(self):
        app_path = SPACE_ROOT / "app.py"
        app_source = app_path.read_text(encoding="utf-8")
        tree = ast.parse(app_source, filename=str(app_path))
        contract_names = {
            "FILTER_SEARCH_KEY",
            "FILTER_DOMAIN_KEY",
            "FILTER_CATEGORY_KEY",
            "FILTER_MIN_STAGE_KEY",
            "FILTER_RESET_KEY",
            "FILTER_DEFAULTS",
        }
        contract_nodes = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id in contract_names
                for target in node.targets
            ):
                contract_nodes.append(node)
            elif isinstance(node, ast.FunctionDef) and node.name == "_reset_filters":
                contract_nodes.append(node)

        namespace = {}
        reset_contract = ast.Module(body=contract_nodes, type_ignores=[])
        exec(compile(reset_contract, str(app_path), "exec"), namespace)
        state = {
            namespace["FILTER_SEARCH_KEY"]: "bank run",
            namespace["FILTER_DOMAIN_KEY"]: ["Finance"],
            namespace["FILTER_CATEGORY_KEY"]: ["Institutional Crises"],
            namespace["FILTER_MIN_STAGE_KEY"]: 4,
            "event_id": "H2EPR-0427",
        }
        namespace["_reset_filters"](state)
        self.assertEqual(state[namespace["FILTER_SEARCH_KEY"]], "")
        self.assertEqual(state[namespace["FILTER_DOMAIN_KEY"]], [])
        self.assertEqual(state[namespace["FILTER_CATEGORY_KEY"]], [])
        self.assertEqual(state[namespace["FILTER_MIN_STAGE_KEY"]], 0)
        self.assertEqual(state["event_id"], "H2EPR-0427")
        for key_name in (
            "FILTER_SEARCH_KEY",
            "FILTER_DOMAIN_KEY",
            "FILTER_CATEGORY_KEY",
            "FILTER_MIN_STAGE_KEY",
        ):
            self.assertIn(f"key={key_name}", app_source)

    def test_runtime_has_no_retired_release_split_logic(self):
        runtime_files = [
            SPACE_ROOT / "app.py",
            *sorted((SPACE_ROOT / "src" / "h2epr_explorer").glob("*.py")),
        ]
        retired_tokens = (
            "draft_" + "availability",
            "draft_" + "status",
            "has_" + "finalcascade",
            "Draft" + "Unavailable",
            "DRAFT_" + "UNAVAILABLE",
            "EXPECTED_" + "AVAILABLE_DRAFT_COUNT",
            "EXPECTED_" + "UNAVAILABLE_DRAFT_COUNT",
        )
        for path in runtime_files:
            source = path.read_text(encoding="utf-8")
            for token in retired_tokens:
                self.assertNotIn(token, source, msg=f"{token} remains in {path}")

        legacy_prefix = "P" + "1000-"
        allowed_legacy_file = SPACE_ROOT / "src" / "h2epr_explorer" / "navigation.py"
        for path in runtime_files:
            if path == allowed_legacy_file:
                continue
            self.assertNotIn(legacy_prefix, path.read_text(encoding="utf-8"), msg=str(path))

        loader_source = (
            SPACE_ROOT / "src" / "h2epr_explorer" / "data_loader.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("H2EPR-Bench-Gold", loader_source)
        self.assertNotIn("finmycelium_" + "finalcascade_public.jsonl", loader_source)


if __name__ == "__main__":
    unittest.main()
