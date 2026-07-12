"""Audit a NAF statistics export without extracting it.

The report deliberately contains aggregates and opaque numeric identifiers only.
Coach names and tournament contact/location details are never read into outputs.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any
from zipfile import ZipFile


def _member(zf: ZipFile, basename: str) -> str:
    matches = [n for n in zf.namelist() if n.rsplit("/", 1)[-1].lower() == basename.lower()]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {basename} in archive, found {len(matches)}")
    return matches[0]


@contextmanager
def _rows(zf: ZipFile, basename: str) -> Iterator[csv.DictReader]:
    import io

    with (
        zf.open(_member(zf, basename)) as raw,
        io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="") as text,
    ):
        yield csv.DictReader(text, delimiter=";")


def _int(value: str | None) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except ValueError:
        return None


def _ratio(n: int, d: int) -> float | None:
    return round(n / d, 6) if d else None


def _sorted_counts(counter: Counter[str]) -> list[dict[str, Any]]:
    return [{"value": key or "(missing)", "count": value} for key, value in sorted(counter.items())]


def _history_counts(source_games: list[dict[str, Any]], target_variant: int) -> dict[str, int]:
    """Count target-side support using pre-event snapshots from source games."""
    overall_prior: Counter[int] = Counter()
    race_prior: Counter[tuple[int, int]] = Counter()
    history: Counter[str] = Counter()
    by_event: dict[tuple[int, int | None], list[dict[str, Any]]] = defaultdict(list)
    for game in source_games:
        by_event[(game["variant"], game["tid"])].append(game)
    ordered = sorted(
        by_event,
        key=lambda event: (
            min((g["date"] for g in by_event[event] if g["date"]), default=date.max),
            event,
        ),
    )
    for event in ordered:
        sides = [side for game in by_event[event] for side in game["sides"]]
        if event[0] == target_variant:
            for coach, race in sides:
                if coach is None or race is None:
                    continue
                overall, with_race = overall_prior[coach], race_prior[(coach, race)]
                history["eligible_sides"] += 1
                history["first_observed_race_use_sides"] += with_race == 0
                history["established_overall_5_sides"] += overall >= 5
                history["established_race_3_sides"] += with_race >= 3
                history["established_both_sides"] += overall >= 5 and with_race >= 3
        for coach, race in sides:
            if coach is not None and race is not None:
                overall_prior[coach] += 1
                race_prior[(coach, race)] += 1
    return dict(history)


def audit_naf_zip(zip_path: str | Path, variant_id: int = 15) -> dict[str, Any]:
    """Return a JSON-compatible aggregate audit for one NAF rules variant."""
    with ZipFile(zip_path) as zf:
        race_names: dict[int, str] = {}
        wildcard_race_ids: set[int] = set()
        with _rows(zf, "naf_race.csv") as rows:
            for row in rows:
                rid = _int(row.get("raceid"))
                if rid is not None:
                    name = row.get("name") or f"race-{rid}"
                    race_names[rid] = name
                    if rid == 99 or name.casefold() == "multiple races":
                        wildcard_race_ids.add(rid)

        tournaments: dict[int, dict[str, str]] = {}
        duplicate_tournament_ids = 0
        with _rows(zf, "naf_tournament.csv") as rows:
            for row in rows:
                tid = _int(row.get("tournamentid"))
                if tid is None:
                    continue
                if tid in tournaments:
                    duplicate_tournament_ids += 1
                if _int(row.get("naf_variantsid")) == variant_id:
                    tournaments[tid] = {
                        "country": row.get("tournamentnation") or "(missing)",
                        "type": row.get("tournamenttype") or "(missing)",
                    }

        entrant_races: dict[tuple[int, int], set[int]] = defaultdict(set)
        entrant_duplicate_rows = 0
        entrant_seen: set[tuple[int, int, int | None]] = set()
        with _rows(zf, "naf_tournamentcoach.csv") as rows:
            for row in rows:
                tid, coach, race = (_int(row.get(k)) for k in ("naftournament", "nafcoach", "race"))
                if tid not in tournaments or coach is None:
                    continue
                key = (tid, coach, race)
                entrant_duplicate_rows += key in entrant_seen
                entrant_seen.add(key)
                if race is not None:
                    entrant_races[(tid, coach)].add(race)

        games: list[dict[str, Any]] = []
        standard_history_games: list[dict[str, Any]] = []
        game_ids: set[int] = set()
        duplicate_game_ids = invalid_game_ids = 0
        orphan_tournaments: Counter[int] = Counter()
        td_present = cas_present = cas_all_zero = 0
        cas_field_present: Counter[str] = Counter()
        cas_field_zero: Counter[str] = Counter()
        side_mismatches = missing_entrant_sides = wildcard_entrant_sides = 0
        with _rows(zf, "naf_game.csv") as rows:
            for row in rows:
                variant = _int(row.get("naf_variantsid"))
                gid, tid = _int(row.get("gameid")), _int(row.get("tournamentid"))
                sides = [
                    (_int(row.get(coach_key)), _int(row.get(race_key)))
                    for coach_key, race_key in (
                        ("homecoachid", "racehome"),
                        ("awaycoachid", "raceaway"),
                    )
                ]
                raw_date = (row.get("date") or row.get("newdate") or "")[:10]
                try:
                    played = date.fromisoformat(raw_date)
                except ValueError:
                    played = None
                history_game = {
                    "gid": gid,
                    "tid": tid,
                    "date": played,
                    "sides": sides,
                    "variant": variant,
                }
                if variant in {13, 15}:
                    standard_history_games.append(history_game)
                if variant != variant_id:
                    continue
                if gid is None:
                    invalid_game_ids += 1
                elif gid in game_ids:
                    duplicate_game_ids += 1
                else:
                    game_ids.add(gid)
                if tid not in tournaments and tid is not None:
                    orphan_tournaments[tid] += 1
                td = [_int(row.get("goalshome")), _int(row.get("goalsaway"))]
                cas_keys = (
                    "badlyhurthome",
                    "badlyhurtaway",
                    "serioushome",
                    "seriousaway",
                    "killshome",
                    "killsaway",
                )
                cas = [_int(row.get(k)) for k in cas_keys]
                for key, value in zip(cas_keys, cas, strict=True):
                    cas_field_present[key] += value is not None
                    cas_field_zero[key] += value == 0
                td_present += all(v is not None for v in td)
                cas_present += all(v is not None for v in cas)
                cas_all_zero += all(v == 0 for v in cas)
                for coach, race in sides:
                    registered = entrant_races.get((tid, coach))
                    if not registered:
                        missing_entrant_sides += 1
                    elif registered & wildcard_race_ids:
                        wildcard_entrant_sides += 1
                    elif race not in registered:
                        side_mismatches += 1
                games.append(history_game | {"td": td})

    coaches: set[int] = set()
    races: Counter[int] = Counter()
    pairs: Counter[tuple[int, int]] = Counter()
    draws = valid_outcomes = 0
    dates: list[date] = []
    for game in games:
        if game["date"]:
            dates.append(game["date"])
        for coach, race in game["sides"]:
            if coach is not None:
                coaches.add(coach)
            if race is not None:
                races[race] += 1
        r1, r2 = (side[1] for side in game["sides"])
        if r1 is not None and r2 is not None:
            pairs[tuple(sorted((r1, r2)))] += 1
        if all(v is not None for v in game["td"]):
            valid_outcomes += 1
            draws += game["td"][0] == game["td"][1]

    variant_history = _history_counts(games, variant_id)
    standard_history = _history_counts(standard_history_games, variant_id)

    race_support = [
        {"race_id": rid, "race": race_names.get(rid, f"race-{rid}"), "game_sides": n}
        for rid, n in sorted(races.items())
    ]
    pair_support = [
        {
            "race_a_id": a,
            "race_a": race_names.get(a, f"race-{a}"),
            "race_b_id": b,
            "race_b": race_names.get(b, f"race-{b}"),
            "games": n,
        }
        for (a, b), n in sorted(pairs.items())
    ]
    observed_event_ids = {game["tid"] for game in games if game["tid"] in tournaments}
    countries = Counter(tournaments[tid]["country"] for tid in observed_event_ids)
    event_types = Counter(tournaments[tid]["type"] for tid in observed_event_ids)
    cas_by_field = {
        key: {
            "complete_games": cas_field_present[key],
            "complete_rate": _ratio(cas_field_present[key], len(games)),
            "zero_games": cas_field_zero[key],
            "zero_rate_among_complete": _ratio(cas_field_zero[key], cas_field_present[key]),
        }
        for key in cas_field_present
    }
    return {
        "schema_version": 1,
        "variant_id": variant_id,
        "volume": {
            "games": len(games),
            "events": len(observed_event_ids),
            "coaches": len(coaches),
            "races": len(races),
            "date_min": min(dates).isoformat() if dates else None,
            "date_max": max(dates).isoformat() if dates else None,
        },
        "coverage": {
            "countries": _sorted_counts(countries),
            "event_types": _sorted_counts(event_types),
            "race_support": race_support,
            "race_pair_support": pair_support,
        },
        "outcomes": {
            "games_with_td": valid_outcomes,
            "draws": draws,
            "draw_rate": _ratio(draws, valid_outcomes),
        },
        "fields": {
            "td_complete_games": td_present,
            "td_complete_rate": _ratio(td_present, len(games)),
            "cas_complete_games": cas_present,
            "cas_complete_rate": _ratio(cas_present, len(games)),
            "cas_all_zero_games": cas_all_zero,
            "cas_all_zero_rate": _ratio(cas_all_zero, cas_present),
            "cas_by_field": cas_by_field,
        },
        "integrity": {
            "duplicate_game_ids": duplicate_game_ids,
            "invalid_game_ids": invalid_game_ids,
            "duplicate_tournament_ids": duplicate_tournament_ids,
            "duplicate_entrant_rows": entrant_duplicate_rows,
            "orphan_tournament_ids": len(orphan_tournaments),
            "orphan_tournament_games": sum(orphan_tournaments.values()),
            "missing_entrant_game_sides": missing_entrant_sides,
            "multiple_race_wildcard_game_sides": wildcard_entrant_sides,
            "entrant_race_mismatch_game_sides": side_mismatches,
        },
        "history_sensitivity": {
            "definitions": {
                "first_observed_race_use": (
                    "zero games in earlier events by this coach with this race"
                ),
                "established_overall_5": "at least 5 games in earlier events by this coach",
                "established_race_3": (
                    "at least 3 games in earlier events by this coach with this race"
                ),
                "ordering": (
                    "events by earliest game date, then tournament ID; all games in an event "
                    "use the pre-event snapshot"
                ),
                "target_variant_only_scope": (
                    f"history from variant {variant_id} only; evaluated on variant "
                    f"{variant_id} sides"
                ),
                "standard_editions_scope": (
                    f"history from standard variants 13 and 15; evaluated on variant {variant_id} "
                    "sides; nonstandard and online variants excluded"
                ),
            },
            "scopes": {
                "target_variant_only": variant_history,
                "standard_editions_13_15": standard_history,
            },
            # Compatibility aliases use the broader, preferred history scope.
            **standard_history,
        },
        "privacy": (
            "Aggregate report only; coach names and tournament contact/location details are "
            "excluded."
        ),
    }


def report_markdown(report: dict[str, Any]) -> str:
    v, o, f, i, h = (
        report[k] for k in ("volume", "outcomes", "fields", "integrity", "history_sensitivity")
    )
    lines = [
        f"# NAF variant {report['variant_id']} audit",
        "",
        "## Volume",
        "",
        f"- Games: {v['games']:,}",
        f"- Events: {v['events']:,}",
        f"- Coaches: {v['coaches']:,}",
        f"- Races: {v['races']:,}",
        f"- Date span: {v['date_min']} to {v['date_max']}",
        "",
        "## Outcome and field coverage",
        "",
        f"- Draw rate: {o['draw_rate']} ({o['draws']:,}/{o['games_with_td']:,})",
        f"- Complete TD: {f['td_complete_games']:,} ({f['td_complete_rate']})",
        f"- Complete CAS: {f['cas_complete_games']:,} ({f['cas_complete_rate']})",
        (
            f"- All-zero CAS among complete rows: {f['cas_all_zero_games']:,} "
            f"({f['cas_all_zero_rate']})"
        ),
        "",
        "## Integrity",
        "",
    ]
    lines += [f"- {key.replace('_', ' ').capitalize()}: {value:,}" for key, value in i.items()]
    lines += [
        "",
        "## History sensitivity",
        "",
        f"- Eligible game sides: {h['eligible_sides']:,}",
        f"- First observed race use: {h['first_observed_race_use_sides']:,}",
        f"- At least 5 prior coach games: {h['established_overall_5_sides']:,}",
        f"- At least 3 prior coach/race games: {h['established_race_3_sides']:,}",
        f"- Both established thresholds: {h['established_both_sides']:,}",
        "",
        "Displayed history counts use standard variants 13 and 15 and evaluate target-variant "
        "sides only; the JSON also includes target-variant-only counts.",
        "",
        (
            "Counts use pre-event history snapshots. Full country, event-type, race, and "
            "race-pair aggregates are in the JSON report."
        ),
        "",
        report["privacy"],
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip", type=Path)
    parser.add_argument("output", type=Path, help="output stem or .json path")
    parser.add_argument("--variant", type=int, default=15)
    args = parser.parse_args(argv)
    report = audit_naf_zip(args.zip, args.variant)
    stem = args.output.with_suffix("")
    stem.parent.mkdir(parents=True, exist_ok=True)
    stem.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    stem.with_suffix(".md").write_text(report_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
