"""Generate a dev snapshot from the test fixture.

This produces a realistic `data/snapshots/ipc.json` using mocked API data,
useful for developing the frontend (Sprint 2) before verifying live API IDs.
Not part of the production ETL — for local development only.

Usage:
    python scripts/generate_dev_snapshot.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = PROJECT_ROOT / "etl" / "tests" / "fixtures" / "api_response_ipc.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "snapshots" / "ipc.json"


def main() -> int:
    # Import here so the script works standalone.
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    from etl.api_client import SeriesAPIClient, SeriesData
    from etl.writer import build_module_snapshot, write_metadata, write_snapshot

    with FIXTURE_PATH.open(encoding="utf-8") as f:
        api_payload: dict[str, Any] = json.load(f)

    # Use the parser directly to convert the payload to SeriesData objects.
    requested_ids = [
        "148.3_INIVELNAL_DICI_M_26",
        "148.3_INUCLEONAL_DICI_M_22",
    ]
    # Access the static parser method.
    fetched: dict[str, SeriesData] = SeriesAPIClient._parse_response(
        api_payload, requested_ids=requested_ids
    )

    # Build a minimal catalog slice matching fixture IDs.
    catalog_series = [
        {
            "id": "148.3_INIVELNAL_DICI_M_26",
            "key": "nivel_general",
            "label": "Nivel general",
            "category": "agregado",
        },
        {
            "id": "148.3_INUCLEONAL_DICI_M_22",
            "key": "nucleo",
            "label": "IPC Núcleo",
            "category": "clasificacion",
        },
    ]

    snapshot = build_module_snapshot(
        module_name="ipc",
        module_meta={
            "name": "Índice de Precios al Consumidor (DEV DATA)",
            "source": "INDEC (fixture)",
            "description": "Development snapshot from test fixture. Not real data.",
        },
        catalog_series=catalog_series,
        fetched=fetched,
    )

    write_snapshot(snapshot, OUTPUT_PATH)
    write_metadata(OUTPUT_PATH.parent / "metadata.json", ["ipc"])
    print(f"Wrote dev snapshot: {OUTPUT_PATH}")
    print(f"Series: {len(snapshot['series'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
