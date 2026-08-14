import ast
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
DATASET_ROOT = (
    Path(os.environ["H2EPR_TEST_DATASET_DIR"]).expanduser().resolve()
    if os.environ.get("H2EPR_TEST_DATASET_DIR")
    else REPO_ROOT
    / "build"
    / "hf_unified3000_inplace_upgrade_rc_v3_dataset_card"
    / "H2EPR-Bench"
)
sys.path.insert(0, str(SPACE_ROOT / "src"))


def _read_contract_tables():
    root = DATASET_ROOT / "data" / "viewer_mirrors"
    return (
        pd.read_parquet(root / "event_catalog.parquet"),
        pd.read_parquet(root / "event_instances.parquet"),
        pd.read_parquet(root / "finalcascade_summary.parquet"),
        pd.read_parquet(root / "draft_availability.parquet"),
    )


class H2EPRExplorerSpaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from h2epr_explorer.data_loader import clear_caches, load_release

        clear_caches()
        cls.release = load_release(DATASET_ROOT)

    def test_space_readme_declares_unified_release_and_boundary(self):
        readme = (SPACE_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("sdk: docker", readme)
        self.assertIn("license: apache-2.0", readme)
        self.assertIn("Streamlit", readme)
        self.assertIn("Unified-3000", readme)
        self.assertIn("3,000", readme)
        self.assertIn("2,876", readme)
        self.assertIn("124", readme)
        self.assertIn("Draft EPG", readme)
        self.assertIn("reference EPG", readme)
        self.assertIn("manual-gated companion", readme)
        self.assertIn("draft_events/<H2EPR-ID>/draft_epg.json", readme)
        self.assertIn("1d01f3649ace0301ac3bbe9ee875eea660347a29", readme)
        self.assertNotIn("Gantt", readme)

    def test_space_container_files_remain_compatible(self):
        dockerfile = (SPACE_ROOT / "Dockerfile").read_text(encoding="utf-8")
        requirements = (SPACE_ROOT / "requirements.txt").read_text(encoding="utf-8")

        self.assertIn("streamlit run app.py", dockerfile)
        self.assertIn("--server.port=7860", dockerfile)
        self.assertIn("--server.address=0.0.0.0", dockerfile)
        for dependency in ("streamlit", "pandas", "pyarrow", "plotly", "huggingface_hub"):
            self.assertIn(dependency, requirements)

    def test_constants_pin_one_unified_release_contract(self):
        from h2epr_explorer.constants import (
            CATALOG_COLUMNS,
            CATALOG_PARQUET,
            DEFAULT_PUBLIC_DATASET_REVISION,
            DRAFT_AVAILABILITY_PARQUET,
            DRAFT_EPG_PATH_TEMPLATE,
            EVENT_INSTANCES_PARQUET,
            FINALCASCADE_SUMMARY_PARQUET,
            GOLD_COMPANION_REPO,
            PUBLIC_DATASET_REPO,
            PUBLIC_DATASET_REVISION,
            RELEASE_BOUNDARY_NOTICE,
            STAGES_PARQUET,
        )

        expected_revision = "1d01f3649ace0301ac3bbe9ee875eea660347a29"
        self.assertEqual(DEFAULT_PUBLIC_DATASET_REVISION, expected_revision)
        self.assertEqual(PUBLIC_DATASET_REVISION, expected_revision)
        self.assertEqual(PUBLIC_DATASET_REPO, "AgenticFinLab/H2EPR-Bench")
        self.assertEqual(GOLD_COMPANION_REPO, "AgenticFinLab/H2EPR-Bench-Gold")
        self.assertEqual(
            [
                CATALOG_PARQUET,
                EVENT_INSTANCES_PARQUET,
                FINALCASCADE_SUMMARY_PARQUET,
                DRAFT_AVAILABILITY_PARQUET,
                STAGES_PARQUET,
            ],
            [
                "data/viewer_mirrors/event_catalog.parquet",
                "data/viewer_mirrors/event_instances.parquet",
                "data/viewer_mirrors/finalcascade_summary.parquet",
                "data/viewer_mirrors/draft_availability.parquet",
                "data/viewer_mirrors/event_stages.parquet",
            ],
        )
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

    def test_full_local_release_contract_and_join(self):
        from h2epr_explorer.constants import GRAPH_COUNT_COLUMNS

        events = self.release.events
        stages = self.release.stages
        self.assertEqual(len(events), 3000)
        self.assertEqual(events["event_id"].nunique(), 3000)
        self.assertTrue(events["event_id"].equals(events["public_event_id"]))
        self.assertEqual(events.iloc[0]["event_id"], "H2EPR-0001")
        self.assertEqual(events.iloc[-1]["event_id"], "H2EPR-3000")
        self.assertEqual(
            events["draft_status"].value_counts().to_dict(),
            {"draft_available": 2876, "draft_unavailable": 124},
        )
        self.assertEqual(len(stages), 8500)
        self.assertEqual(stages["event_id"].nunique(), 2876)
        available_ids = set(events.loc[events.draft_status.eq("draft_available"), "event_id"])
        self.assertEqual(set(stages["event_id"]), available_ids)

        available = events.loc[events.draft_status.eq("draft_available"), list(GRAPH_COUNT_COLUMNS)]
        unavailable = events.loc[
            events.draft_status.eq("draft_unavailable"), list(GRAPH_COUNT_COLUMNS)
        ]
        self.assertFalse(available.isna().any().any())
        self.assertTrue(unavailable.isna().all().all())
        self.assertEqual(len(self.release.stage_frame("H2EPR-0001")), 4)
        self.assertTrue(self.release.stage_frame("H2EPR-1000").empty)

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

        non_positive_index = stages.copy(deep=True)
        non_positive_index.loc[event_indices[0], "stage_index"] = 0
        with self.assertRaisesRegex(loader.ReleaseContractError, "positive integers"):
            loader._validate_stages(non_positive_index, events)

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
                with self.assertRaisesRegex(
                    loader.ReleaseContractError, f"{column} closure"
                ):
                    loader._validate_stages(stages, component_mismatch)

    def test_release_load_is_deterministic_after_cache_clear(self):
        from h2epr_explorer.data_loader import clear_caches, load_release

        first_events = self.release.events.copy(deep=True)
        first_stages = self.release.stages.copy(deep=True)
        clear_caches()
        second = load_release(DATASET_ROOT)
        pd.testing.assert_frame_equal(first_events, second.events, check_exact=True)
        pd.testing.assert_frame_equal(first_stages, second.stages, check_exact=True)

    def test_contract_rejects_schema_drift_and_duplicate_identity(self):
        from h2epr_explorer.data_loader import ReleaseContractError, build_explorer_view

        catalog, instances, summary, availability = _read_contract_tables()
        with self.assertRaisesRegex(ReleaseContractError, "Schema mismatch"):
            build_explorer_view(
                catalog.drop(columns=["category"]), instances, summary, availability
            )

        duplicated_instances = pd.concat(
            [instances.iloc[:-1], instances.iloc[[0]]], ignore_index=True
        )
        with self.assertRaisesRegex(ReleaseContractError, "duplicate identity"):
            build_explorer_view(catalog, duplicated_instances, summary, availability)

    def test_contract_rejects_semantic_field_disagreement(self):
        from h2epr_explorer.data_loader import ReleaseContractError, build_explorer_view

        catalog, instances, summary, availability = _read_contract_tables()
        summary = summary.copy()
        summary.loc[0, "category"] = "contract-drift"
        with self.assertRaisesRegex(ReleaseContractError, "category disagrees"):
            build_explorer_view(catalog, instances, summary, availability)

    def test_filters_search_current_fields_and_handle_null_stage_counts(self):
        from h2epr_explorer.filters import filter_catalog

        rows = [
            {
                "public_event_id": "H2EPR-0001",
                "event_id": "H2EPR-0001",
                "title": "Northern Rock bank run",
                "display_name": "Northern Rock bank run",
                "event_descriptor": "A liquidity crisis and depositor run.",
                "domain": "Finance",
                "category": "Institutional Crises & Liquidity Runs",
                "keywords": "bank; liquidity; deposits",
                "stage_count": 4,
            },
            {
                "public_event_id": "H2EPR-1000",
                "event_id": "H2EPR-1000",
                "title": "Replacement event",
                "display_name": "Replacement event",
                "event_descriptor": "A current catalog event without a public draft.",
                "domain": "Science & Engineering",
                "category": "Research Events",
                "keywords": "research; replacement",
                "stage_count": None,
            },
        ]
        queries = {
            "H2EPR-0001",
            "Northern Rock",
            "depositor",
            "Finance",
            "Liquidity Runs",
            "deposits",
        }
        for query in queries:
            with self.subTest(query=query):
                result = filter_catalog(rows, query=query)
                self.assertEqual([row["event_id"] for row in result], ["H2EPR-0001"])

        self.assertEqual(len(filter_catalog(rows, min_stage_count=0)), 2)
        self.assertEqual(
            [row["event_id"] for row in filter_catalog(rows, min_stage_count=4)],
            ["H2EPR-0001"],
        )
        self.assertEqual(
            [
                row["event_id"]
                for row in filter_catalog(rows, categories=["Research Events"])
            ],
            ["H2EPR-1000"],
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
            "display_name": "Northern Rock bank run",
            "event_descriptor": "A liquidity crisis and depositor run.",
        }
        self.assertEqual(
            event_display_label(row), "H2EPR-0001 · Northern Rock bank run"
        )
        self.assertEqual(event_description(row), "A liquidity crisis and depositor run.")

    def test_available_graph_uses_derived_direct_path_and_full_integrity(self):
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
        self.assertNotEqual(requested_path, event_row["draft_asset"])
        self.assertEqual(graph["source_payload_sha256"], event_row["source_payload_sha256"])

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

    def test_unavailable_graph_returns_typed_state_without_file_access(self):
        import h2epr_explorer.data_loader as loader

        loader.clear_caches()
        with mock.patch.object(loader, "resolve_dataset_file") as resolver:
            result = loader.load_event_graph(
                "H2EPR-1000", release=self.release, local_dataset_dir=DATASET_ROOT
            )
        self.assertIsInstance(result, loader.DraftUnavailable)
        self.assertEqual(result.event_id, "H2EPR-1000")
        resolver.assert_not_called()

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

    def test_graph_loader_rejects_wrong_identity(self):
        import h2epr_explorer.data_loader as loader

        source = DATASET_ROOT / "draft_events" / "H2EPR-0001" / "draft_epg.json"
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["event_id"] = "H2EPR-0002"
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            path = Path(tmp) / "wrong-identity.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            loader.clear_caches()
            with mock.patch.object(loader, "resolve_dataset_file", return_value=path):
                with self.assertRaises(loader.DraftIntegrityError):
                    loader.load_event_graph("H2EPR-0001", release=self.release)

    def test_graph_loader_rejects_wrong_canonical_hash(self):
        import h2epr_explorer.data_loader as loader

        source = DATASET_ROOT / "draft_events" / "H2EPR-0001" / "draft_epg.json"
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["redaction_level"] = "tampered"
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            path = Path(tmp) / "wrong-hash.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            loader.clear_caches()
            with mock.patch.object(loader, "resolve_dataset_file", return_value=path):
                with self.assertRaisesRegex(loader.DraftIntegrityError, "canonical digest"):
                    loader.load_event_graph("H2EPR-0001", release=self.release)

    def test_graph_loader_reports_missing_available_asset(self):
        import h2epr_explorer.data_loader as loader

        loader.clear_caches()
        with mock.patch.object(
            loader, "resolve_dataset_file", side_effect=FileNotFoundError("missing")
        ):
            with self.assertRaises(loader.DraftAssetMissing):
                loader.load_event_graph("H2EPR-0001", release=self.release)

    def test_graph_loader_distinguishes_remote_missing_asset(self):
        import h2epr_explorer.data_loader as loader
        from huggingface_hub.errors import EntryNotFoundError
        from h2epr_explorer.constants import LOCAL_DATASET_ENV

        loader.clear_caches()
        with mock.patch.dict(os.environ, {LOCAL_DATASET_ENV: ""}):
            with mock.patch.object(
                loader,
                "hf_hub_download",
                side_effect=EntryNotFoundError("missing public asset"),
            ):
                with self.assertRaises(loader.DraftAssetMissing):
                    loader.load_event_graph("H2EPR-0001", release=self.release)

    def test_every_public_download_uses_the_pinned_revision(self):
        import h2epr_explorer.data_loader as loader
        from h2epr_explorer.constants import (
            CATALOG_PARQUET,
            LOCAL_DATASET_ENV,
            PUBLIC_DATASET_REVISION,
        )

        with mock.patch.dict(os.environ, {LOCAL_DATASET_ENV: ""}):
            with mock.patch.object(
                loader, "hf_hub_download", return_value="/tmp/pinned-public-asset"
            ) as download:
                loader.resolve_dataset_file(CATALOG_PARQUET)
                loader.resolve_dataset_file("draft_events/H2EPR-0001/draft_epg.json")

        self.assertEqual(download.call_count, 2)
        self.assertEqual(
            {call.kwargs["revision"] for call in download.call_args_list},
            {PUBLIC_DATASET_REVISION},
        )
        self.assertEqual(
            {call.kwargs["repo_id"] for call in download.call_args_list},
            {"AgenticFinLab/H2EPR-Bench"},
        )

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
                resolution = query_param_event_id({"event_id": value})
                self.assertTrue(resolution.unresolved)

    def test_navigation_generates_only_canonical_current_links(self):
        from h2epr_explorer.constants import PUBLIC_DATASET_REVISION
        from h2epr_explorer.navigation import build_event_links

        links = build_event_links("H2EPR-0001", draft_available=True)
        self.assertEqual(
            links["explorer"],
            "https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer?event_id=H2EPR-0001",
        )
        self.assertIn(PUBLIC_DATASET_REVISION, links["public_dataset"])
        self.assertIn(PUBLIC_DATASET_REVISION, links["draft_epg"])
        self.assertTrue(links["draft_epg"].endswith("draft_events/H2EPR-0001/draft_epg.json"))
        self.assertIn("AgenticFinLab/H2EPR-Bench-Gold", links["reference_access"])
        self.assertNotIn("draft_epg", build_event_links("H2EPR-1000"))
        with self.assertRaises(ValueError):
            build_event_links("P1000-0001", draft_available=True)

    def test_timeline_handles_relative_mixed_calendar_and_empty_states(self):
        from h2epr_explorer.render_gantt import prepare_gantt_rows

        cases = {
            "H2EPR-0001": "relative_order",
            "H2EPR-0005": "relative_order",
            "H2EPR-0427": "calendar",
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
        self.assertEqual(prepare_gantt_rows([]), [])

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

    def test_app_uses_current_labels_and_canonical_query_writeback(self):
        app_source = (SPACE_ROOT / "app.py").read_text(encoding="utf-8")

        self.assertIn("Draft EPG JSON", app_source)
        self.assertIn("Download selected Draft EPG JSON", app_source)
        self.assertIn('st.query_params["event_id"] = selected_event', app_source)
        self.assertIn("DRAFT_UNAVAILABLE_MESSAGE", app_source)
        self.assertNotIn("Final" + "Cascade JSON", app_source)
        self.assertNotIn("Minimum " + "sources", app_source)

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
        self.assertIn('"Reset filters"', app_source)
        self.assertIn("key=FILTER_RESET_KEY", app_source)
        self.assertIn("on_click=_reset_filters", app_source)

    def test_obsolete_schema_and_legacy_identity_boundaries_are_static(self):
        forbidden_fields = (
            "event_" + "category",
            "event_descriptor_" + "en",
            "source_" + "count",
            "gantt_html_" + "path",
            "temporal_anchor_" + "summary",
        )
        runtime_files = [
            SPACE_ROOT / "app.py",
            *sorted((SPACE_ROOT / "src" / "h2epr_explorer").glob("*.py")),
        ]
        for path in runtime_files:
            source = path.read_text(encoding="utf-8")
            for field in forbidden_fields:
                self.assertNotIn(field, source, msg=f"{field} remains in {path}")

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
