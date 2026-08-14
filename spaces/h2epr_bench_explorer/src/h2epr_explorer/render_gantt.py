from __future__ import annotations

import json
import re
from typing import Any

from .constants import EVENT_ID_MAX, EVENT_ID_MIN, EVENT_ID_PATTERN


def _text_value(value: Any) -> str:
    if value is None:
        return ""
    try:
        if value != value:
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _is_known_time(value: Any) -> bool:
    text = _text_value(value).lower()
    return bool(text) and text not in {"unknown", "none", "nan", "nat"}


def _stage_order(row: dict[str, Any], fallback_index: int = 0) -> int:
    value = row.get("stage_index", fallback_index)
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback_index


def _stage_label(row: dict[str, Any]) -> str:
    for field in ("stage_title", "stage_id"):
        value = _text_value(row.get(field))
        if value:
            return value
    return "Unnamed stage"


def _time_note(row: dict[str, Any]) -> str:
    anchors = row.get("known_action_time_anchors")
    if isinstance(anchors, (list, tuple)):
        return "; ".join(_text_value(anchor) for anchor in anchors if _text_value(anchor))
    text = _text_value(anchors)
    if not text:
        return ""
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return text
    if isinstance(parsed, list):
        return "; ".join(_text_value(anchor) for anchor in parsed if _text_value(anchor))
    return text


def _require_current_event_id(row: dict[str, Any]) -> None:
    event_id = _text_value(row.get("event_id"))
    if not re.fullmatch(EVENT_ID_PATTERN, event_id):
        raise ValueError(f"Timeline received a non-canonical event ID: {event_id!r}")
    number = int(event_id.rsplit("-", 1)[1])
    if not EVENT_ID_MIN <= number <= EVENT_ID_MAX:
        raise ValueError(f"Timeline received an out-of-range event ID: {event_id}")


def prepare_gantt_rows(stage_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for row in stage_rows:
        _require_current_event_id(row)
    ordered = sorted(
        stage_rows,
        key=lambda row: (_stage_order(row), str(row.get("stage_id", ""))),
    )
    calendar_axis = bool(ordered) and all(
        _is_known_time(row.get("stage_start_time"))
        and _is_known_time(row.get("stage_end_time"))
        for row in ordered
    )
    prepared: list[dict[str, Any]] = []
    for fallback_index, row in enumerate(ordered, start=1):
        stage_order = _stage_order(row, fallback_index)
        if calendar_axis:
            display_start = row.get("stage_start_time")
            display_end = row.get("stage_end_time")
            axis_mode = "calendar"
        else:
            display_start = stage_order
            display_end = display_start + 0.85
            axis_mode = "relative_order"

        prepared.append(
            {
                **row,
                "stage_label": _stage_label(row),
                "stage_order": stage_order,
                "display_start": display_start,
                "display_end": display_end,
                "axis_mode": axis_mode,
                "time_note": _time_note(row),
            }
        )
    return prepared


def _calendar_datetime_values(values: list[Any]) -> list[Any]:
    import pandas as pd

    return [pd.to_datetime(value, errors="raise") for value in values]


def build_timeline_figure(stage_rows: list[dict[str, Any]], event_id: str):
    import pandas as pd
    import plotly.express as px

    prepared = prepare_gantt_rows(stage_rows)
    if not prepared:
        return None

    frame = pd.DataFrame(prepared)
    if set(frame["axis_mode"]) == {"calendar"}:
        frame["display_start"] = _calendar_datetime_values(frame["display_start"].tolist())
        frame["display_end"] = _calendar_datetime_values(frame["display_end"].tolist())
        fig = px.timeline(
            frame,
            x_start="display_start",
            x_end="display_end",
            y="stage_label",
            color="stage_label",
            hover_data=["stage_id", "stage_order", "time_note"],
            title=f"{event_id}: public stage timeline",
        )
        fig.update_yaxes(autorange="reversed")
        return fig

    fig = px.bar(
        frame,
        x=[row["display_end"] - row["display_start"] for row in prepared],
        y="stage_label",
        base="display_start",
        orientation="h",
        color="stage_label",
        hover_data=["stage_id", "stage_order", "time_note"],
        title=f"{event_id}: relative stage order",
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(xaxis_title="Relative stage order")
    return fig
