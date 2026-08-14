from __future__ import annotations

PUBLIC_DATASET_REPO = "AgenticFinLab/H2EPR-Bench"
GOLD_COMPANION_REPO = "AgenticFinLab/H2EPR-Bench-Gold"

DEFAULT_PUBLIC_DATASET_REVISION = "1d01f3649ace0301ac3bbe9ee875eea660347a29"
PUBLIC_DATASET_REVISION = DEFAULT_PUBLIC_DATASET_REVISION
LOCAL_DATASET_ENV = "H2EPR_EXPLORER_LOCAL_DATASET_DIR"

EVENT_ID_PATTERN = r"^H2EPR-[0-9]{4}$"
EVENT_ID_MIN = 1
EVENT_ID_MAX = 3000

CATALOG_PARQUET = "data/viewer_mirrors/event_catalog.parquet"
EVENT_INSTANCES_PARQUET = "data/viewer_mirrors/event_instances.parquet"
FINALCASCADE_SUMMARY_PARQUET = "data/viewer_mirrors/finalcascade_summary.parquet"
DRAFT_AVAILABILITY_PARQUET = "data/viewer_mirrors/draft_availability.parquet"
STAGES_PARQUET = "data/viewer_mirrors/event_stages.parquet"
DRAFT_EPG_PATH_TEMPLATE = "draft_events/{event_id}/draft_epg.json"

EXPECTED_EVENT_COUNT = 3000
EXPECTED_AVAILABLE_DRAFT_COUNT = 2876
EXPECTED_UNAVAILABLE_DRAFT_COUNT = 124
EXPECTED_STAGE_ROW_COUNT = 8500

CATALOG_SCHEMA = (
    "public_event_id",
    "event_id",
    "title",
    "display_name",
    "event_descriptor",
    "domain",
    "category",
    "keywords",
    "release_split",
    "version",
    "schema_version",
    "draft_status",
    "has_gold_reference",
)

EVENT_INSTANCES_SCHEMA = (
    "public_event_id",
    "event_id",
    "title",
    "display_name",
    "event_descriptor",
    "domain",
    "category",
    "keywords",
    "release_split",
    "version",
    "schema_version",
    "has_finalcascade",
    "draft_status",
    "has_gold_reference",
    "finalcascade_access_level",
    "gold_reference_access_level",
    "evidence_context_access_level",
)

FINALCASCADE_SUMMARY_SCHEMA = (
    "public_event_id",
    "event_id",
    "title",
    "domain",
    "category",
    "draft_status",
    "stage_count",
    "episode_count",
    "participant_count",
    "action_count",
    "transaction_count",
    "relation_count",
    "event_start_time",
    "event_end_time",
    "event_boundary_time_status",
    "known_action_time_anchor_count",
    "known_action_time_anchors",
    "relative_order_available",
)

DRAFT_AVAILABILITY_SCHEMA = (
    "public_event_id",
    "draft_status",
    "draft_source_kind",
    "draft_schema",
    "draft_asset",
    "draft_record_index",
    "draft_sha256",
    "source_payload_sha256",
    "has_reference_epg",
)

STAGES_SCHEMA = (
    "public_event_id",
    "event_id",
    "stage_id",
    "stage_index",
    "stage_title",
    "stage_start_time",
    "stage_end_time",
    "stage_boundary_time_status",
    "episode_count",
    "participant_count",
    "action_count",
    "transaction_count",
    "relation_count",
    "known_action_time_anchor_count",
    "known_action_time_anchors",
    "relative_order_available",
    "release_split",
    "version",
    "schema_version",
)

GRAPH_COUNT_COLUMNS = (
    "stage_count",
    "episode_count",
    "participant_count",
    "action_count",
    "transaction_count",
    "relation_count",
)

ARROW_INT64_COLUMNS = frozenset(
    {
        *GRAPH_COUNT_COLUMNS,
        "stage_index",
        "known_action_time_anchor_count",
        "draft_record_index",
    }
)

ARROW_BOOL_COLUMNS = frozenset(
    {
        "has_gold_reference",
        "has_finalcascade",
        "relative_order_available",
        "has_reference_epg",
    }
)

CATALOG_COLUMNS = (
    "event_id",
    "display_name",
    "domain",
    "category",
    "event_descriptor",
    "keywords",
    "stage_count",
)

PROFILE_COLUMNS = (
    "event_id",
    "display_name",
    "domain",
    "category",
    "keywords",
    "event_boundary_time_status",
    "known_action_time_anchors",
    "gold_reference_access_level",
    "finalcascade_access_level",
)

DRAFT_UNAVAILABLE_MESSAGE = "No public Draft EPG is available for this event in this release."

RELEASE_BOUNDARY_NOTICE = (
    "Public Draft EPGs are FinMycelium construction artifacts. Official benchmark "
    "scoring uses reference EPGs in the manual-gated companion repository; this "
    "Explorer loads neither reference EPGs nor frozen evidence packages."
)
