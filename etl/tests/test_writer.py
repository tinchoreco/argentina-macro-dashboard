"""Tests for etl.writer."""

from __future__ import annotations

import json
from pathlib import Path

from etl.api_client import SeriesData
from etl.writer import build_module_snapshot, write_snapshot


def test_build_module_snapshot_shape() -> None:
    catalog_series = [
        {
            "id": "FAKE_ID_1",
            "key": "nivel_general",
            "label": "Nivel general",
            "category": "agregado",
        },
        {
            "id": "FAKE_ID_2",
            "key": "nucleo",
            "label": "Núcleo",
            "category": "clasificacion",
        },
    ]
    fetched = {
        "FAKE_ID_1": SeriesData(
            series_id="FAKE_ID_1",
            observations=[("2024-01-01", 100.0), ("2024-02-01", 110.0)],
        ),
        # FAKE_ID_2 not fetched — should land in missing_series
    }

    snapshot = build_module_snapshot(
        module_name="ipc",
        module_meta={"name": "IPC", "source": "INDEC", "description": "desc"},
        catalog_series=catalog_series,
        fetched=fetched,
    )

    assert snapshot["module"] == "ipc"
    assert snapshot["name"] == "IPC"
    assert snapshot["source"] == "INDEC"
    assert "generated_at" in snapshot
    assert len(snapshot["series"]) == 1
    assert snapshot["missing_series"] == ["FAKE_ID_2"]

    s = snapshot["series"][0]
    assert s["key"] == "nivel_general"
    assert s["label"] == "Nivel general"
    assert s["observations"] == [["2024-01-01", 100.0], ["2024-02-01", 110.0]]
    assert s["mom_pct"][0] == ["2024-01-01", None]
    assert s["mom_pct"][1][0] == "2024-02-01"
    assert "summary" in s


def test_write_snapshot_creates_valid_json(tmp_path: Path) -> None:
    snapshot = {"module": "test", "series": [], "missing_series": []}
    output = tmp_path / "nested" / "test.json"

    write_snapshot(snapshot, output)

    assert output.exists()
    with output.open(encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == snapshot


def test_build_snapshot_handles_empty_observations() -> None:
    catalog_series = [{"id": "X", "key": "x", "label": "X", "category": "c"}]
    fetched = {"X": SeriesData(series_id="X", observations=[])}

    snapshot = build_module_snapshot(
        module_name="m", module_meta={}, catalog_series=catalog_series, fetched=fetched
    )

    assert snapshot["missing_series"] == ["X"]
    assert snapshot["series"] == []
