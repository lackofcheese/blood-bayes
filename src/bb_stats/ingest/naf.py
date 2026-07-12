"""Privacy-safe ingestion of a NAF statistics ZIP export.

The source archive is read without extraction.  Only the deliberately narrow fields
in :mod:`bb_stats.contracts` are emitted; in particular, coach names and tournament
contact/address fields never reach the derived directory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import tempfile
import zipfile
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path

from bb_stats.contracts import (
    COACH_FIELDS,
    ENTRY_FIELDS,
    EVENT_FIELDS,
    MATCH_FIELDS,
    NAF_SOURCE_FILES,
    RACE_FIELDS,
)

_REQUIRED_HEADERS = {
    "CoachExport.csv": {"NAF Nr", "Country", "Registration Date"},
    "naf_variants.csv": {"variantid", "variantname"},
    "naf_tournament_statistics_group.csv": {"id", "tournamentID"},
    "naf_game.csv": {
        "gameid", "tournamentid", "homecoachid", "awaycoachid", "racehome",
        "raceaway", "goalshome", "goalsaway", "badlyhurthome", "badlyhurtaway",
        "date", "dirty", "naf_variantsid",
    },
    "naf_race.csv": {"raceid", "name", "reroll_cost", "apoth", "race_count"},
    "naf_tournament_statistics_list.csv": {"id", "name"},
    "naf_tournament.csv": {
        "tournamentid", "tournamentname", "tournamentcity", "tournamentnation",
        "tournamenturl", "tournamentnotesurl", "tournamentstartdate",
        "tournamentenddate", "tournamenttype", "tournamentstyle",
        "tournamentscoring", "tournamentinformation", "tournament_squad",
        "naf_rulesetid", "naf_variantsid", "tournament_ruleset_file",
    },
    "naf_coachranking_variant.csv": {"coachID", "raceID", "variantID"},
    "naf_tournamentcoach.csv": {"naftournament", "nafcoach", "race"},
}

_OUTPUTS = {
    "match": ("match.csv", MATCH_FIELDS),
    "event": ("event.csv", EVENT_FIELDS),
    "event_entry": ("event_entry.csv", ENTRY_FIELDS),
    "coach": ("coach.csv", COACH_FIELDS),
    "race": ("race.csv", RACE_FIELDS),
}


class NAFIngestError(ValueError):
    """The archive does not satisfy the expected NAF export contract."""


def _member_map(archive: zipfile.ZipFile) -> dict[str, str]:
    by_base: dict[str, list[str]] = {}
    for member in archive.namelist():
        if member.endswith("/"):
            continue
        by_base.setdefault(Path(member).name, []).append(member)
    missing = [name for name in NAF_SOURCE_FILES if name not in by_base]
    duplicated = [name for name in NAF_SOURCE_FILES if len(by_base.get(name, ())) > 1]
    if missing or duplicated:
        details = []
        if missing:
            details.append(f"missing members: {', '.join(missing)}")
        if duplicated:
            details.append(f"duplicate basenames: {', '.join(duplicated)}")
        raise NAFIngestError("; ".join(details))
    return {name: by_base[name][0] for name in NAF_SOURCE_FILES}


def _rows(archive: zipfile.ZipFile, member: str, basename: str) -> Iterator[dict[str, str]]:
    with (
        archive.open(member) as raw,
        io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text,
    ):
        reader = csv.DictReader(text, delimiter=";")
        headers = set(reader.fieldnames or ())
        missing = _REQUIRED_HEADERS[basename] - headers
        if missing:
            raise NAFIngestError(f"{basename} missing headers: {', '.join(sorted(missing))}")
        for row in reader:
            yield {key: (value or "").strip() for key, value in row.items() if key}


def _validate_header(archive: zipfile.ZipFile, member: str, basename: str) -> None:
    """Validate a member without retaining (or even parsing) its data rows."""
    with (
        archive.open(member) as raw,
        io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text,
    ):
        headers = set(next(csv.reader(text, delimiter=";"), ()))
    missing = _REQUIRED_HEADERS[basename] - headers
    if missing:
        raise NAFIngestError(f"{basename} missing headers: {', '.join(sorted(missing))}")


def _result(home: str, away: str) -> tuple[str, str]:
    home_score, away_score = int(home), int(away)
    if home_score > away_score:
        return "W", "L"
    if home_score < away_score:
        return "L", "W"
    return "D", "D"


def _bool(value: str) -> str:
    return "true" if value.strip().lower() in {"1", "true", "yes", "y"} else "false"


def _write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def _quarantine(
    sink: list[dict[str, str]], table: str, row_id: str, reason: str
) -> None:
    sink.append({"table": table, "row_id": row_id, "reason": reason})


def _tidy_rows(
    basename: str,
    rows: Iterable[dict[str, str]],
    quarantine: list[dict[str, str]],
) -> Iterator[dict[str, str]]:
    for row in rows:
        if basename == "CoachExport.csv":
            row_id = row["NAF Nr"]
            if not row_id:
                _quarantine(quarantine, "coach", row_id, "missing coach_id")
                continue
            yield {
                "coach_id": row_id,
                "country": row["Country"],
                "registration_date": row["Registration Date"],
            }
        elif basename == "naf_race.csv":
            row_id = row["raceid"]
            if not row_id:
                _quarantine(quarantine, "race", row_id, "missing race_id")
                continue
            yield {
                "race_id": row_id,
                "name": row["name"],
                "reroll_cost": row["reroll_cost"],
                "allows_apothecary": _bool(row["apoth"]),
                "is_counted": _bool(row["race_count"]),
            }
        elif basename == "naf_tournament.csv":
            row_id = row["tournamentid"]
            if not row_id:
                _quarantine(quarantine, "event", row_id, "missing event_id")
                continue
            yield {
                "event_id": row_id,
                "name": row["tournamentname"],
                "start_date": row["tournamentstartdate"],
                "end_date": row["tournamentenddate"],
                "nation": row["tournamentnation"],
                "city": row["tournamentcity"],
                "event_type": row["tournamenttype"],
                "style": row["tournamentstyle"],
                "scoring_text": row["tournamentscoring"],
                "is_squad": _bool(row["tournament_squad"]),
                "variant_id": row["naf_variantsid"],
                "ruleset_id": row["naf_rulesetid"],
                "source_url": row["tournamenturl"],
                "notes_url": row["tournamentnotesurl"],
                "ruleset_file_reference": row["tournament_ruleset_file"],
                "has_information_text": "true" if row["tournamentinformation"] else "false",
            }
        elif basename == "naf_tournamentcoach.csv":
            if not row["naftournament"] or not row["nafcoach"]:
                _quarantine(
                    quarantine,
                    "event_entry",
                    row["naftournament"],
                    "missing event or coach ID",
                )
                continue
            yield {
                "event_id": row["naftournament"],
                "coach_id": row["nafcoach"],
                "race_id": row["race"],
            }
        elif basename == "naf_game.csv":
            row_id = row["gameid"]
            required = (
                "gameid", "tournamentid", "homecoachid", "awaycoachid",
                "racehome", "raceaway", "goalshome", "goalsaway",
            )
            if any(not row[field] for field in required):
                _quarantine(quarantine, "match", row_id, "missing required match value")
                continue
            try:
                home_result, away_result = _result(row["goalshome"], row["goalsaway"])
            except ValueError:
                _quarantine(quarantine, "match", row_id, "invalid touchdown score")
                continue
            yield {
                "match_id": row_id,
                "event_id": row["tournamentid"],
                "played_on": row["date"],
                "variant_id": row["naf_variantsid"],
                "home_coach_id": row["homecoachid"],
                "away_coach_id": row["awaycoachid"],
                "home_race_id": row["racehome"],
                "away_race_id": row["raceaway"],
                "home_touchdowns": row["goalshome"],
                "away_touchdowns": row["goalsaway"],
                "home_result": home_result,
                "away_result": away_result,
                "home_badly_hurt": row["badlyhurthome"],
                "away_badly_hurt": row["badlyhurtaway"],
                "source_dirty": row["dirty"],
            }


def ingest(zip_path: str | Path, output_dir: str | Path) -> dict[str, object]:
    """Ingest *zip_path* into privacy-safe CSVs below *output_dir*.

    Files are first built in a sibling temporary directory.  Each completed file is
    then atomically replaced in the destination; an interrupted run therefore never
    leaves a partially written CSV.
    """
    source = Path(zip_path)
    destination = Path(output_dir)
    hasher = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    quarantine: list[dict[str, str]] = []

    try:
        archive_context = zipfile.ZipFile(source)
    except (OSError, zipfile.BadZipFile) as exc:
        raise NAFIngestError(f"cannot read NAF ZIP: {exc}") from exc

    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    try:
        source_for_table = {
            "match": "naf_game.csv",
            "event": "naf_tournament.csv",
            "event_entry": "naf_tournamentcoach.csv",
            "coach": "CoachExport.csv",
            "race": "naf_race.csv",
        }
        with archive_context as archive:
            members = _member_map(archive)
            for base, member in members.items():
                _validate_header(archive, member, base)
            counts = {}
            for name, (filename, fields) in _OUTPUTS.items():
                base = source_for_table[name]
                tidy = _tidy_rows(base, _rows(archive, members[base], base), quarantine)
                counts[name] = _write_csv(stage / filename, fields, tidy)
        quarantine_count = _write_csv(
            stage / "quarantine.csv", ("table", "row_id", "reason"), quarantine
        )
        reconciliation = {"rows_written": counts, "rows_quarantined": quarantine_count}
        manifest = {
            "source_file": source.name,
            "source_sha256": digest,
            "source_members": sorted(members.values()),
            "outputs": {**counts, "quarantine": quarantine_count},
        }
        for filename, payload in (
            ("reconciliation.json", reconciliation), ("manifest.json", manifest)
        ):
            (stage / filename).write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        destination.mkdir(parents=True, exist_ok=True)
        for path in sorted(stage.iterdir()):
            os.replace(path, destination / path.name)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest a NAF statistics ZIP export")
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    ingest(args.zip_path, args.output_dir)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
