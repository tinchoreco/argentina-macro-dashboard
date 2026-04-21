"""ETL entry point.

Usage:
    python -m etl.run --module ipc
    python -m etl.run --all
    python -m etl.run --module ipc --start-date 2018-01-01
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml

from etl.api_client import APIError, SeriesAPIClient
from etl.writer import build_module_snapshot, write_metadata, write_snapshot

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = PROJECT_ROOT / "etl" / "catalog.yaml"
OUTPUT_DIR = PROJECT_ROOT / "data" / "snapshots"
DEFAULT_START_DATE = "2017-01-01"


def load_catalog(path: Path = CATALOG_PATH) -> dict:
    """Load the curated series catalog from YAML."""
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_module(
    module_name: str,
    catalog: dict,
    client: SeriesAPIClient,
    start_date: str,
    output_dir: Path,
) -> bool:
    """Fetch, transform, and write a snapshot for one module.

    Returns True on success, False if the module was skipped or failed.
    """
    if module_name not in catalog:
        logger.error("Module '%s' not found in catalog", module_name)
        return False

    module = catalog[module_name]
    series_entries = module.get("series", [])
    if not series_entries:
        logger.warning("Module '%s' has no series defined", module_name)
        return False

    ids = [entry["id"] for entry in series_entries]
    logger.info("Fetching %d series for module '%s'", len(ids), module_name)

    try:
        fetched = client.fetch(ids, start_date=start_date)
    except APIError as exc:
        logger.error("Failed to fetch module '%s': %s", module_name, exc)
        return False

    snapshot = build_module_snapshot(
        module_name=module_name,
        module_meta={k: v for k, v in module.items() if k != "series"},
        catalog_series=series_entries,
        fetched=fetched,
    )
    output_path = output_dir / f"{module_name}.json"
    write_snapshot(snapshot, output_path)

    got = len(snapshot["series"])
    missing = len(snapshot["missing_series"])
    logger.info(
        "Wrote %s: %d series OK, %d missing", output_path.name, got, missing
    )
    if missing:
        logger.warning(
            "Missing IDs for '%s': %s", module_name, snapshot["missing_series"]
        )
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Argentina macro ETL")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--module", help="Module name from catalog (e.g. 'ipc')")
    group.add_argument("--all", action="store_true", help="Run all modules")
    parser.add_argument(
        "--start-date",
        default=DEFAULT_START_DATE,
        help=f"ISO start date (default: {DEFAULT_START_DATE})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    catalog = load_catalog()
    client = SeriesAPIClient()

    modules_to_run = list(catalog.keys()) if args.all else [args.module]

    successes: list[str] = []
    failures: list[str] = []
    for module_name in modules_to_run:
        ok = run_module(
            module_name=module_name,
            catalog=catalog,
            client=client,
            start_date=args.start_date,
            output_dir=args.output_dir,
        )
        (successes if ok else failures).append(module_name)

    if successes:
        write_metadata(args.output_dir / "metadata.json", successes)

    if failures:
        logger.error("Failed modules: %s", failures)
        return 1
    logger.info("All modules processed successfully: %s", successes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
