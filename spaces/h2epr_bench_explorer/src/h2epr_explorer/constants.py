from __future__ import annotations

PUBLIC_DATASET_REPO = "AgenticFinLab/H2EPR-Bench"
GOLD_COMPANION_REPO = "AgenticFinLab/H2EPR-Bench-Gold"

PROJECT_WEBSITE_URL = "https://agenticfinlab.github.io/H2EPR-Bench/"
PUBLIC_DATASET_URL = "https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench"
EXPLORER_URL = "https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer"
FINMYCELIUM_URL = "https://github.com/AgenticFinLab/FinMycelium"
GOLD_COMPANION_URL = "https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold"
SOURCE_REPOSITORY_URL = "https://github.com/AgenticFinLab/H2EPR-Bench"
AGENTICFINLAB_URL = "https://agenticfinlab.github.io/"

DEFAULT_PUBLIC_DATASET_REVISION: str | None = None
PUBLIC_DATASET_REVISION = DEFAULT_PUBLIC_DATASET_REVISION
PUBLIC_DATASET_REVISION_URL = (
    f"{PUBLIC_DATASET_URL}/tree/{PUBLIC_DATASET_REVISION}"
    if PUBLIC_DATASET_REVISION
    else PUBLIC_DATASET_URL
)
LOCAL_DATASET_ENV = "H2EPR_EXPLORER_LOCAL_DATASET_DIR"

EVENT_ID_PATTERN = r"^H2EPR-[0-9]{4}$"
EVENT_ID_MIN = 1
EVENT_ID_MAX = 3000

EVENT_GALLERY_PARQUET = "data/viewer_mirrors/event_gallery.parquet"
CATALOG_PARQUET = "data/viewer_mirrors/event_catalog.parquet"
EVENT_INSTANCES_PARQUET = "data/viewer_mirrors/event_instances.parquet"
FINALCASCADE_SUMMARY_PARQUET = "data/viewer_mirrors/finalcascade_summary.parquet"
STAGES_PARQUET = "data/viewer_mirrors/event_stages.parquet"
DRAFT_SOURCE_HASHES_CSV = "manifests/draft_source_hashes.csv"
DRAFT_EPG_PATH_TEMPLATE = "draft_events/{event_id}/draft_epg.json"

RELEASE_ASSET_SHA256 = {
    EVENT_GALLERY_PARQUET: "be68b57e42cfc0cde97c949b5dcfe14cc4ec80397d428f1f27d88b39e88a9b53",
    CATALOG_PARQUET: "2a478a96aa2713b3b3894a222a511aaaadd06327c90498d03405ad1860a33ac0",
    EVENT_INSTANCES_PARQUET: "ba258780091c10c46508684d90bebd5f34285a61cc4bc4c6600c75fa380817a8",
    STAGES_PARQUET: "eeab17e56ceb14a99ffc6a64e8508f9b98bd5ea9d260b14cbf95a42374dc8db8",
    FINALCASCADE_SUMMARY_PARQUET: "273fedfdc74aba8f00669b7e82d45ec4a312b16aaa98f7c28182a06d9c6f471f",
    DRAFT_SOURCE_HASHES_CSV: "29f8c3af1641b4b7031cb0d21021177e5eda6816b57b82adbd3d4d7952f76d1d",
}

EXPECTED_EVENT_COUNT = 3000
EXPECTED_STAGE_ROW_COUNT = 8843

EVENT_GALLERY_SCHEMA = (
    "public_event_id",
    "title",
    "domain",
    "category",
    "event_descriptor",
    "schema_version",
)

CATALOG_SCHEMA = (
    "public_event_id",
    "event_id",
    "title",
    "display_name",
    "event_descriptor",
    "domain",
    "category",
    "keywords",
    "has_gold_reference",
    "stage_count",
    "episode_count",
    "schema_version",
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
    "has_gold_reference",
    "finalcascade_access_level",
    "gold_reference_access_level",
    "evidence_context_access_level",
    "schema_version",
)

FINALCASCADE_SUMMARY_SCHEMA = (
    "public_event_id",
    "event_id",
    "title",
    "domain",
    "category",
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
    "schema_version",
)

DRAFT_SOURCE_HASHES_SCHEMA = (
    "public_event_id",
    "source_payload_sha256",
    "sanitized_record_sha256",
    "draft_record_index",
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
    "schema_version",
)

TABLE_SCHEMA_VERSIONS = {
    "event_gallery": "h2epr-public-event-gallery-v3",
    "event_catalog": "h2epr-public-event-catalog-v3",
    "event_instances": "h2epr-public-event-instances-v3",
    "event_stages": "h2epr-public-event-stages-v3",
    "finalcascade_summary": "h2epr-public-finalcascade-summary-v3",
}

FINALCASCADE_ACCESS_LEVEL = "public_sanitized_full_graph"
GOLD_REFERENCE_ACCESS_LEVEL = "manual_gated_companion"
EVIDENCE_CONTEXT_ACCESS_LEVEL = "not_included_in_this_release"

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
    }
)

ARROW_BOOL_COLUMNS = frozenset(
    {
        "has_gold_reference",
        "relative_order_available",
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

RELEASE_BOUNDARY_NOTICE = (
    "Public Draft EPGs are FinMycelium construction artifacts. Official benchmark "
    "scoring uses reference EPGs in the manual-gated companion repository; this "
    "Explorer loads neither reference EPGs nor frozen evidence packages."
)
