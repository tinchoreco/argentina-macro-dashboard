"""Snapshot writer.

Serializes processed series into JSON files that the frontend dashboard reads.
The output shape is the stable contract between the ETL and the frontend:
changes here require frontend changes too.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from etl.api_client import SeriesData
from etl.transform import (
    monthly_percent_change,
    summary_stats,
    yoy_percent_change,
)


def build_module_snapshot(
    module_name: str,
    module_meta: dict[str, Any],
    catalog_series: list[dict[str, Any]],
    fetched: dict[str, SeriesData],
) -> dict[str, Any]:
    """Assemble a snapshot dict for a single module (e.g. 'ipc').

    Args:
        module_name: Internal module key (e.g. "ipc").
        module_meta: Module-level metadata from catalog (name, source, description).
        catalog_series: List of series entries from catalog (with id/key/label/category).
        fetched: Dict of SeriesData returned by the API client, keyed by API ID.

    Returns:
        A JSON-serializable dict ready to be written to disk. Shape:
            {
                "module": "ipc",
                "name": "Índice de Precios al Consumidor",
                "source": "INDEC",
                "description": "...",
                "generated_at": "2026-04-20T12:34:56Z",
                "series": [
                    {
                        "key": "nivel_general",
                        "label": "Nivel general",
                        "category": "agregado",
                        "api_id": "148.3_INIVELNAL_DICI_M_26",
                        "observations": [["2020-01-01", 100.5], ...],
                        "mom_pct": [["2020-01-01", null], ["2020-02-01", 2.3], ...],
                        "yoy_pct": [...],
                        "summary": {"last_value": 8234.5, "last_date": "2026-03-01", ...}
                    },
                    ...
                ],
                "missing_series": ["<id1>", ...]
            }
    """
    serialized_series: list[dict[str, Any]] = []
    missing: list[str] = []

    for entry in catalog_series:
        api_id = entry["id"]
        series_data = fetched.get(api_id)
        if series_data is None or not series_data.observations:
            missing.append(api_id)
            continue

        obs = series_data.observations
        serialized_series.append(
            {
                "key": entry["key"],
                "label": entry["label"],
                "category": entry.get("category"),
                "api_id": api_id,
                "observations": [[d, v] for d, v in obs],
                "mom_pct": [[d, v] for d, v in monthly_percent_change(obs)],
                "yoy_pct": [[d, v] for d, v in yoy_percent_change(obs)],
                "summary": summary_stats(obs),
            }
        )

    return {
        "module": module_name,
        "name": module_meta.get("name", module_name),
        "source": module_meta.get("source"),
        "description": module_meta.get("description"),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "series": serialized_series,
        "missing_series": missing,
    }


def write_snapshot(snapshot: dict[str, Any], output_path: Path) -> None:
    """Write a snapshot dict to a JSON file, pretty-printed."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)


def write_metadata(
    output_path: Path,
    modules_generated: list[str],
) -> None:
    """Write a top-level metadata.json with info about the last ETL run."""
    meta = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "modules": modules_generated,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
