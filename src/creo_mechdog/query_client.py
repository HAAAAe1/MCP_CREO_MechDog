"""Collect bounded model pages for callers that need a complete saved snapshot."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


async def read_full_model(
    call: Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]],
    model_id: str,
) -> dict[str, Any]:
    page = await call("creo_inspect_model", {"model_id": model_id, "detail": "full"})
    if "data" not in page:
        return page
    result = {
        key: value
        for key, value in page.items()
        if key
        not in (
            "data",
            "next_cursor",
            "offset",
            "returned_count",
            "unavailable_sections",
            "section",
        )
    }
    sections: dict[str, list[Any]] = {}
    unavailable = set(page["unavailable_sections"])
    visited = set()
    while True:
        for name, records in page["data"].items():
            sections.setdefault(name, []).extend(records)
        cursor = page.get("next_cursor")
        if not cursor:
            if not page["complete"]:
                raise ValueError("Incomplete inspection without a continuation cursor")
            break
        if cursor in visited:
            raise ValueError("Repeated inspection cursor")
        visited.add(cursor)
        page = await call(
            "creo_inspect_model",
            {
                "model_id": model_id,
                "detail": "full",
                "cursor": cursor,
            },
        )
    state = result["inspection"]
    for name, records in sections.items():
        if name not in unavailable and name not in (
            "aliases",
            "parameters",
            "dimensions",
            "feature_geometry",
            "sketch_dimensions",
            "metadata",
        ):
            state[name] = records
    for name in ("aliases", "parameters"):
        if name not in unavailable:
            target = result if name == "aliases" else state
            target[name] = {record["name"]: record["value"] for record in sections[name]}
    features = {f["id"]: f for f in state.get("features", [])}
    for record in sections.get("metadata", []):
        state[record["name"]] = record["value"]
    for name, field in (
        ("dimensions", "dimensions"),
        ("feature_geometry", "geometry_items"),
        ("sketch_dimensions", "sketch_dimensions"),
    ):
        if name not in unavailable:
            for f in features.values():
                f[field] = []
            for record in sections.get(name, []):
                features[record["feature_id"]][field].append(
                    {key: value for key, value in record.items() if key != "feature_id"}
                )
    result.update(complete=True, next_cursor=None)
    return result
