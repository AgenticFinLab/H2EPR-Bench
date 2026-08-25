from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd


APP_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_ROOT / "src"))

import streamlit as st

from h2epr_explorer.constants import (
    CATALOG_COLUMNS,
    FINMYCELIUM_URL,
    GOLD_COMPANION_REPO,
    GOLD_COMPANION_URL,
    PROFILE_COLUMNS,
    PUBLIC_DATASET_REPO,
    PUBLIC_DATASET_REVISION_URL,
    PROJECT_WEBSITE_URL,
    RELEASE_BOUNDARY_NOTICE,
    SOURCE_REPOSITORY_URL,
)
from h2epr_explorer.data_loader import (
    DatasetTransportError,
    DraftAssetMissing,
    DraftIntegrityError,
    ReleaseContractError,
    load_event_graph,
    load_release,
)
from h2epr_explorer.filters import event_description, event_display_label, event_name, filter_catalog
from h2epr_explorer.navigation import (
    build_event_links,
    filter_summary_text,
    query_param_event_id,
    resolve_selected_event_index,
)
from h2epr_explorer.render_gantt import build_timeline_figure


FILTER_SEARCH_KEY = "h2epr_filter_search"
FILTER_DOMAIN_KEY = "h2epr_filter_domains"
FILTER_CATEGORY_KEY = "h2epr_filter_categories"
FILTER_MIN_STAGE_KEY = "h2epr_filter_min_stage_count"
FILTER_RESET_KEY = "h2epr_filter_reset"
FILTER_DEFAULTS = {
    FILTER_SEARCH_KEY: "",
    FILTER_DOMAIN_KEY: (),
    FILTER_CATEGORY_KEY: (),
    FILTER_MIN_STAGE_KEY: 0,
}


def _as_records(frame: pd.DataFrame) -> list[dict]:
    return frame.to_dict(orient="records")


def _select_columns(frame: pd.DataFrame, columns: tuple[str, ...] | list[str]) -> pd.DataFrame:
    return frame.loc[:, list(columns)]


def _metric_value(value) -> str:
    if value is None or bool(pd.isna(value)):
        return "—"
    return f"{int(value):,}"


def _reset_filters(state=None) -> None:
    target = st.session_state if state is None else state
    for key, value in FILTER_DEFAULTS.items():
        target[key] = list(value) if isinstance(value, tuple) else value


st.set_page_config(page_title="H2EPR-Bench Explorer", layout="wide")

st.markdown(
    """
<style>
div[data-testid="stMetric"] {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 0.35rem 0.6rem;
    background: #fbfbf8;
}
.h2epr-kicker {
    color: #4b5563;
    font-size: 0.92rem;
    letter-spacing: 0;
    margin-bottom: 0.25rem;
}
.h2epr-title {
    font-size: 2.15rem;
    font-weight: 760;
    line-height: 1.12;
    margin-bottom: 0.25rem;
}
.h2epr-subtitle {
    color: #374151;
    max-width: 920px;
    margin-bottom: 0.75rem;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="h2epr-kicker">H²EPR-Bench · public release explorer</div>', unsafe_allow_html=True)
st.markdown('<div class="h2epr-title">Event-process graph browser</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="h2epr-subtitle">Browse 3,000 public event records, Draft EPG summaries, and stage timelines from one validated Unified-3000 release.</div>',
    unsafe_allow_html=True,
)
st.info(RELEASE_BOUNDARY_NOTICE)

try:
    release = load_release()
except DatasetTransportError as exc:
    st.error(f"The pinned public dataset could not be retrieved. Please retry. Details: {exc}")
    st.stop()
except ReleaseContractError as exc:
    st.error(f"The public release failed Explorer contract validation: {exc}")
    st.stop()

catalog = release.events
catalog_rows = _as_records(catalog)
query_resolution = query_param_event_id(st.query_params)

with st.sidebar:
    st.header("Filter events")
    query = st.text_input(
        "Search",
        placeholder="event name, ID, category, keyword",
        key=FILTER_SEARCH_KEY,
    )
    domains = st.multiselect(
        "Domain",
        sorted(catalog["domain"].dropna().unique().tolist()),
        key=FILTER_DOMAIN_KEY,
    )
    categories = st.multiselect(
        "Category",
        sorted(catalog["category"].dropna().unique().tolist()),
        key=FILTER_CATEGORY_KEY,
    )
    max_stage_count = int(catalog["stage_count"].dropna().max())
    min_stage_count = st.slider(
        "Minimum stages",
        0,
        max_stage_count,
        key=FILTER_MIN_STAGE_KEY,
    )
    st.button(
        "Reset filters",
        key=FILTER_RESET_KEY,
        on_click=_reset_filters,
        width="stretch",
    )
    st.divider()
    st.subheader("Public resources")
    st.link_button(
        "Project Website",
        PROJECT_WEBSITE_URL,
        width="stretch",
    )
    st.link_button(
        "Public Dataset",
        PUBLIC_DATASET_REVISION_URL,
        width="stretch",
    )
    st.link_button(
        "FinMycelium System",
        FINMYCELIUM_URL,
        width="stretch",
    )
    st.link_button(
        "Reference EPGs (Gated)",
        GOLD_COMPANION_URL,
        width="stretch",
    )
    st.link_button(
        "Release Repository",
        SOURCE_REPOSITORY_URL,
        width="stretch",
    )

filtered_rows = filter_catalog(
    catalog_rows,
    query=query,
    domains=domains,
    categories=categories,
    min_stage_count=min_stage_count,
)

if not filtered_rows:
    st.warning("No event matches the current filters.")
    st.stop()

if query_resolution.used_legacy_mapping:
    st.caption(f"Historical event link resolved to canonical ID {query_resolution.canonical_id}.")
elif query_resolution.unresolved:
    st.warning("The requested event link is malformed or outside this release; showing a valid event instead.")

event_labels = {row["event_id"]: event_display_label(row) for row in catalog_rows}
selected_index = resolve_selected_event_index(filtered_rows, query_resolution.canonical_id)
selected_event = st.selectbox(
    "Selected event",
    [row["event_id"] for row in filtered_rows],
    index=selected_index,
    format_func=lambda event_id: event_labels.get(event_id, event_id),
)
if st.query_params.get("event_id") != selected_event:
    st.query_params["event_id"] = selected_event

event_row = release.event_row(selected_event)
event_record = event_row.to_dict()
event_stages = release.stage_frame(selected_event)
stage_records = _as_records(event_stages)
event_links = build_event_links(selected_event)

st.caption(filter_summary_text(len(filtered_rows), len(catalog_rows)))

tabs = st.tabs(
    ["Catalog", "Event detail", "Timeline", "Stages", "Draft EPG JSON", "Access and boundary"]
)

with tabs[0]:
    st.subheader("Event catalog")
    filtered_ids = [row["event_id"] for row in filtered_rows]
    table = catalog.loc[catalog["event_id"].isin(filtered_ids)]
    st.dataframe(_select_columns(table, CATALOG_COLUMNS), width="stretch", height=520)

with tabs[1]:
    st.subheader(event_name(event_record))
    st.write(event_description(event_record))
    metric_columns = st.columns(5)
    for column, label, widget in zip(
        ("stage_count", "episode_count", "participant_count", "action_count", "relation_count"),
        ("Stages", "Episodes", "Participants", "Actions", "Relations"),
        metric_columns,
    ):
        widget.metric(label, _metric_value(event_record.get(column)))

    st.markdown("#### Event profile")
    selected_frame = catalog.loc[catalog["event_id"].eq(selected_event)]
    st.dataframe(
        _select_columns(selected_frame, PROFILE_COLUMNS),
        width="stretch",
    )

    link_columns = st.columns(3 if "draft_epg" in event_links else 2)
    link_columns[0].link_button("Open Public Dataset", event_links["public_dataset"], width="stretch")
    link_columns[1].link_button(
        "Reference EPGs (Gated)", event_links["reference_access"], width="stretch"
    )
    if "draft_epg" in event_links:
        link_columns[2].link_button(
            "Open Draft EPG file", event_links["draft_epg"], width="stretch"
        )

    st.markdown("#### Draft EPG summary")
    summary_columns = [
        "event_id",
        "stage_count",
        "episode_count",
        "participant_count",
        "action_count",
        "transaction_count",
        "relation_count",
        "event_boundary_time_status",
        "known_action_time_anchor_count",
    ]
    st.dataframe(selected_frame.loc[:, summary_columns], width="stretch")

with tabs[2]:
    figure = build_timeline_figure(stage_records, selected_event)
    if figure is None:
        st.error("The validated stage rows could not be rendered as a timeline.")
    else:
        st.plotly_chart(figure, width="stretch")

with tabs[3]:
    st.dataframe(event_stages, width="stretch", height=520)

with tabs[4]:
    try:
        graph_result = load_event_graph(selected_event, release=release)
    except DatasetTransportError as exc:
        st.error(f"The selected Draft EPG could not be retrieved. Please retry. Details: {exc}")
    except DraftAssetMissing as exc:
        st.error(f"The selected Draft EPG file is missing: {exc}")
    except DraftIntegrityError as exc:
        st.error(f"The selected Draft EPG failed integrity validation and was not shown: {exc}")
    else:
        graph_json = json.dumps(graph_result, ensure_ascii=False, indent=2)
        st.download_button(
            "Download selected Draft EPG JSON",
            data=graph_json,
            file_name=f"{selected_event}_draft_epg.json",
            mime="application/json",
        )
        if "draft_epg" in event_links:
            st.link_button("Open exact public file", event_links["draft_epg"])
        st.json(graph_result, expanded=False)

with tabs[5]:
    st.markdown(
        f"""
### Release boundary

- Project Website: [H²EPR-Bench]({PROJECT_WEBSITE_URL}).
- Public Dataset: [`{PUBLIC_DATASET_REPO}`]({PUBLIC_DATASET_REVISION_URL}).
- FinMycelium System: [multi-agent event reconstruction system]({FINMYCELIUM_URL}).
- Reference EPGs (Gated): [`{GOLD_COMPANION_REPO}`]({GOLD_COMPANION_URL}).
- Release Repository: [`AgenticFinLab/H2EPR-Bench`]({SOURCE_REPOSITORY_URL}).
- Public Draft EPGs are sanitized FinMycelium construction artifacts, not scoring references.
- Official benchmark scoring uses expert-adjudicated reference EPGs in the gated companion.
- This Explorer loads neither reference EPGs nor frozen evidence packages.
"""
    )
