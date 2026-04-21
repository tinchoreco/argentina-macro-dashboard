"""Assemble the static site for deployment.

Copies the dashboard assets and the latest snapshot JSONs into a single
directory ready to be published by GitHub Pages (or any static host).

Output structure:
    _site/
    ├── index.html
    ├── assets/
    │   ├── styles.css
    │   ├── loader.js
    │   ├── charts.js
    │   └── ui.js
    └── data/
        ├── ipc.json
        └── metadata.json

Usage:
    python scripts/build_site.py [--output _site]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_SRC = PROJECT_ROOT / "dashboard"
SNAPSHOTS_SRC = PROJECT_ROOT / "data" / "snapshots"
DEFAULT_OUTPUT = PROJECT_ROOT / "_site"


def build(output_dir: Path) -> int:
    """Assemble the site in output_dir. Returns exit code."""
    if not DASHBOARD_SRC.exists():
        print(f"ERROR: dashboard source not found at {DASHBOARD_SRC}", file=sys.stderr)
        return 1
    if not SNAPSHOTS_SRC.exists() or not any(SNAPSHOTS_SRC.glob("*.json")):
        print(
            f"ERROR: no snapshots found in {SNAPSHOTS_SRC}. "
            "Run the ETL first (python -m etl.run --module ipc) or "
            "generate a dev snapshot (python scripts/generate_dev_snapshot.py).",
            file=sys.stderr,
        )
        return 1

    # Clean output dir
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    # Copy dashboard (HTML + assets/)
    for item in DASHBOARD_SRC.iterdir():
        if item.is_dir():
            shutil.copytree(item, output_dir / item.name)
        else:
            shutil.copy2(item, output_dir / item.name)

    # Copy snapshots into _site/data/
    site_data = output_dir / "data"
    site_data.mkdir(exist_ok=True)
    for json_file in SNAPSHOTS_SRC.glob("*.json"):
        shutil.copy2(json_file, site_data / json_file.name)

    # Add a .nojekyll marker so GitHub Pages doesn't try to process anything
    # with Jekyll (which can hide files starting with _ or break on some paths).
    (output_dir / ".nojekyll").touch()

    # Report
    n_assets = sum(1 for _ in (output_dir / "assets").rglob("*") if _.is_file())
    n_data = sum(1 for _ in site_data.glob("*.json"))
    print(f"Site built at: {output_dir}")
    print(f"  HTML: {(output_dir / 'index.html').exists()}")
    print(f"  Assets: {n_assets} files")
    print(f"  Data: {n_data} JSON files")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the static site")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output directory (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args(argv)
    return build(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
