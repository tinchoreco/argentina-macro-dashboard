# Argentina Macro Dashboard

Interactive dashboard of Argentine macroeconomic indicators, powered by the
public time series API at [datos.gob.ar](https://apis.datos.gob.ar/series/api/).

<!--
  Once the repo is pushed to GitHub, uncomment and update these badges:

  [![Deploy](https://github.com/<USER>/argentina-macro-dashboard/actions/workflows/deploy.yml/badge.svg)](https://github.com/<USER>/argentina-macro-dashboard/actions/workflows/deploy.yml)
  [![ETL](https://github.com/<USER>/argentina-macro-dashboard/actions/workflows/etl.yml/badge.svg)](https://github.com/<USER>/argentina-macro-dashboard/actions/workflows/etl.yml)

  Live site: https://<USER>.github.io/argentina-macro-dashboard/
-->

**Status:** IPC module live. EMAE, Empleo, Comex planned.

## Quick start

```bash
pip install -r requirements.txt
python -m etl.run --module ipc     # fetch data
python scripts/build_site.py       # assemble _site/
cd _site && python -m http.server 8000
# open http://localhost:8000
```

If you can't hit the API, use the dev fixture instead:

```bash
python scripts/generate_dev_snapshot.py
python scripts/build_site.py
```

Run tests:

```bash
pytest etl/tests/ -v
```

## Architecture

```
etl/                   # Data extraction pipeline (Python)
├── catalog.yaml       # Curated series IDs by module
├── api_client.py      # HTTP client for apis.datos.gob.ar
├── transform.py       # MoM, YoY, summary stats
├── writer.py          # JSON snapshot writer
├── run.py             # CLI entry point
└── tests/             # pytest suite with API mocks

scripts/
├── build_site.py              # Assembles _site/ for deployment
└── generate_dev_snapshot.py   # Builds a snapshot from the test fixture

data/snapshots/        # Generated JSON files (committed to the repo)
dashboard/             # Static HTML + JS source
_site/                 # Build output (gitignored)

.github/workflows/
├── deploy.yml         # On push to main: build and deploy to GitHub Pages
└── etl.yml            # Monthly (+ manual trigger): fetch new data, commit to main
```

Two layers separated by a stable contract (the snapshot JSON):

- **ETL layer** decides *what* data to fetch and how to transform it
- **Frontend layer** only renders what it reads from the snapshot

## Deployment

This project is set up for **GitHub Pages** with automation via GitHub Actions.

### Initial setup

1. Create a public repo on GitHub named `argentina-macro-dashboard` (or any name — update references accordingly).
2. From the project root, initialize git and push:

   ```bash
   git init -b main
   git add .
   git commit -m "feat: initial commit — IPC dashboard (Sprint 1 + 2 + deploy setup)"
   git remote add origin https://github.com/<YOUR_USER>/argentina-macro-dashboard.git
   git push -u origin main
   ```

3. On GitHub, go to **Settings → Pages** and set:
   - **Source:** GitHub Actions (not "Deploy from a branch")
   - Pages will pick up the artifact uploaded by `deploy.yml` automatically.

4. On GitHub, go to **Settings → Actions → General → Workflow permissions** and ensure:
   - **Read and write permissions** is selected (so the ETL workflow can commit data updates back).

5. The first push to `main` triggers `deploy.yml`. After a minute or two, the
   site is live at `https://<YOUR_USER>.github.io/argentina-macro-dashboard/`.

### Data updates

Three ways to refresh data:

- **Manual local push**: `python -m etl.run --module ipc`, commit, push. The deploy workflow fires automatically.
- **Manual trigger in GitHub Actions**: open the "Refresh data (ETL)" workflow, click "Run workflow". The ETL runs on GitHub, commits the new snapshot if changed, which triggers the deploy workflow.
- **Scheduled**: `etl.yml` runs automatically on the 20th of every month at 17:00 UTC (14:00 ART) — a safe margin after INDEC's typical IPC release on the 15th.

### Before trusting the schedule

The series IDs in `etl/catalog.yaml` are tentative (only IPC Nivel General is
confirmed against the official catalog). Run the ETL workflow manually once via
**Actions → Refresh data (ETL) → Run workflow** and check the logs for missing
IDs before relying on the monthly schedule.

## Data source

All series come from the unified time series API operated by the Argentine
government, aggregating data from INDEC, BCRA, Ministerio de Economía and
other agencies. See the
[API documentation](https://datosgobar.github.io/series-tiempo-ar-api/).

Series are mapped to stable internal keys in `etl/catalog.yaml`. If a series
is discontinued or its ID changes upstream, update that file only.

## Frontend design notes

- Aesthetic: dark editorial, inspired by financial press front pages
- Typography: Fraunces (display serif) + JetBrains Mono (data) + Inter (UI)
- Accent: signal red for headline values, gold for level indicators
- No build step, no framework — HTML + CSS + vanilla JS, Chart.js from CDN

## Manual testing checklist

See previous sprint docs. Quick check after any change:

- [ ] Tests pass: `pytest etl/tests/ -v`
- [ ] Build works: `python scripts/build_site.py`
- [ ] Site loads locally: `cd _site && python -m http.server 8000`
- [ ] No console errors in DevTools
- [ ] Headline shows real numbers (not dashes)
- [ ] All three tabs render correctly
- [ ] Responsive works on mobile widths

## Known limitations

- Series IDs tentative — validate on first ETL run
- Only IPC module implemented
- No domain custom yet (using `github.io` subdomain)

## License

Data source: INDEC / datos.gob.ar (Creative Commons Attribution 4.0).
Code: to be defined.
