# bb-stats

Reproducible analysis of NAF Blood Bowl tournament results and, later, linked
tournament-pack treatments. The current implementation establishes the privacy-safe
NAF data foundation and pack-source discovery inventory described in `TECHNICAL.md`.

## Setup and verification

```bash
uv sync --extra dev
.venv/bin/pytest
.venv/bin/ruff check .
```

## Local pipeline

The source ZIP and generated outputs are ignored by Git. With the current export in
the repository root:

```bash
.venv/bin/bb-stats-naf nafstat-tmp-name.zip data/derived/naf
.venv/bin/bb-stats-naf-audit \
  nafstat-tmp-name.zip reports/generated/naf_bb2025_audit.json --variant 15
.venv/bin/bb-stats-event-catalog \
  nafstat-tmp-name.zip reports/generated/event_catalog --variant 15
.venv/bin/bb-stats-tourplay-coverage \
  nafstat-tmp-name.zip reports/generated/tourplay_coverage_dry
.venv/bin/bb-stats-tourplay-normalize \
  reports/generated/tourplay_coverage/tourplay_coverage.json \
  data/raw/tourplay data/derived/tourplay
.venv/bin/bb-stats-tourplay-registry \
  data/raw/tourplay/app-main.89d015cbe0605b58.js \
  data/derived/tourplay data/derived/tourplay_registry \
  data/raw/tourplay/master-rosters-bb2025.json \
  data/raw/tourplay/master-rosters-bb2020.json
.venv/bin/bb-stats-tourplay-resolve \
  data/derived/tourplay data/derived/tourplay_registry \
  data/derived/tourplay_resolved
```

The event catalogue is a discovery and connectivity report. Source hints are not
verified event-to-pack links. Read `DATA.md` before working with row-level exports.

Tourplay coverage is a dry run unless `--fetch` is explicitly supplied. Fetch mode
reads only `GET /api/tournament/{slug}`, caches successful raw JSON under ignored
`data/raw/tourplay/`, applies a delay and hard request cap, never retries, and stops
after a configurable run of blocked requests. It never reads inscriptions or rosters.

The Tourplay normalizer is fully offline. It converts cached event metadata into
source-faithful event/category/tier/race/pack/option/inducement/star/mercenary tables,
preserving raw IDs and every legal pack alternative without inferring a coach's selected
build.

The registry step resolves versioned Tourplay race, improvement, cost, inducement, and
star identifiers from cached application and master-data artifacts. Unknown IDs remain
in `unresolved_observed.csv`; the pipeline never guesses their meaning.

The resolver joins those registries back onto the normalized rule rows while retaining
every raw ID and an explicit resolution status. It is also fully offline and checks
that every source row is represented exactly once.
