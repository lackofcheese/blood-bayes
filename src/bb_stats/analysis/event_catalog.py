"""Build a privacy-safe NAF candidate-event discovery inventory.

This module deliberately reports source *availability*, not pack contents or a
verified NAF-to-pack linkage. Coach identifiers are used transiently to calculate
event overlap and are never written to an output artifact.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict, deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO, cast

from bb_stats.contracts import BB2025_VARIANT_ID

YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")

CATALOG_FIELDS = (
    "candidate_rank",
    "candidate_score",
    "event_id",
    "event_name",
    "start_date",
    "end_date",
    "country",
    "city",
    "event_type",
    "is_open",
    "is_squad",
    "match_count",
    "coach_count",
    "race_count",
    "registered_entry_count",
    "registered_coach_count",
    "registered_race_count",
    "repeat_series_key_heuristic",
    "repeat_series_event_count_heuristic",
    "has_source_url",
    "has_notes_url",
    "has_ruleset_file_reference",
    "has_information_text",
    "has_scoring_text",
    "source_availability_count",
    "overlap_event_degree",
    "shared_coach_memberships",
    "max_shared_coaches_with_one_event",
    "connectivity_component",
    "connectivity_component_size",
)


@dataclass
class Event:
    event_id: str
    name: str
    start_date: str
    end_date: str
    country: str
    city: str
    event_type: str
    is_squad: bool
    has_source_url: bool
    has_notes_url: bool
    has_ruleset_file_reference: bool
    has_information_text: bool
    has_scoring_text: bool
    match_count: int = 0
    registered_entry_count: int = 0
    registered_coaches: set[str] = field(default_factory=set)
    registered_races: set[str] = field(default_factory=set)
    coaches: set[str] = field(default_factory=set)
    races: set[str] = field(default_factory=set)


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _present(value: str | None) -> bool:
    return bool((value or "").strip())


def _is_true(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def repeat_series_key(name: str) -> str:
    """Return a deliberately conservative, name-only repeat-series heuristic."""

    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    text = YEAR_RE.sub(" ", text.lower())
    return NON_ALNUM_RE.sub(" ", text).strip()


def _member(zip_file: zipfile.ZipFile, basename: str) -> str:
    matches = [name for name in zip_file.namelist() if Path(name).name == basename]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {basename!r} in ZIP, found {len(matches)}")
    return matches[0]


def _rows(zip_file: zipfile.ZipFile, basename: str) -> Iterable[dict[str, str]]:
    with (
        zip_file.open(_member(zip_file, basename)) as raw,
        io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text,
    ):
        yield from csv.DictReader(text, delimiter=";")


def _load_events(zip_file: zipfile.ZipFile, variant_id: str) -> dict[str, Event]:
    events: dict[str, Event] = {}
    for row in _rows(zip_file, "naf_tournament.csv"):
        if row.get("naf_variantsid", "").strip() != variant_id:
            continue
        event_id = row["tournamentid"].strip()
        events[event_id] = Event(
            event_id=event_id,
            name=row.get("tournamentname", "").strip(),
            start_date=row.get("tournamentstartdate", "").strip(),
            end_date=row.get("tournamentenddate", "").strip(),
            country=row.get("tournamentnation", "").strip(),
            city=row.get("tournamentcity", "").strip(),
            event_type=row.get("tournamenttype", "").strip(),
            is_squad=_is_true(row.get("tournament_squad")),
            has_source_url=_present(row.get("tournamenturl")),
            has_notes_url=_present(row.get("tournamentnotesurl")),
            has_ruleset_file_reference=_present(row.get("tournament_ruleset_file")),
            has_information_text=_present(row.get("tournamentinformation")),
            has_scoring_text=_present(row.get("tournamentscoring")),
        )
    return events


def _add_entries(zip_file: zipfile.ZipFile, events: dict[str, Event]) -> None:
    for row in _rows(zip_file, "naf_tournamentcoach.csv"):
        event = events.get(row.get("naftournament", "").strip())
        if event is None:
            continue
        coach = row.get("nafcoach", "").strip()
        race = row.get("race", "").strip()
        event.registered_entry_count += 1
        if coach:
            event.registered_coaches.add(coach)
        if race:
            event.registered_races.add(race)


def _add_matches(zip_file: zipfile.ZipFile, events: dict[str, Event], variant_id: str) -> None:
    for row in _rows(zip_file, "naf_game.csv"):
        if row.get("naf_variantsid", "").strip() != variant_id:
            continue
        event = events.get(row.get("tournamentid", "").strip())
        if event is not None:
            event.match_count += 1
            for field_name in ("homecoachid", "awaycoachid"):
                coach = row.get(field_name, "").strip()
                if coach:
                    event.coaches.add(coach)
            for field_name in ("racehome", "raceaway"):
                race = row.get(field_name, "").strip()
                if race:
                    event.races.add(race)


def _overlap_metrics(events: dict[str, Event]) -> tuple[dict[str, dict[str, int]], int]:
    coach_events: dict[str, set[str]] = defaultdict(set)
    for event in events.values():
        for coach in event.coaches:
            coach_events[coach].add(event.event_id)

    pair_overlap: Counter[tuple[str, str]] = Counter()
    for event_ids in coach_events.values():
        ordered = sorted(event_ids)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1 :]:
                pair_overlap[(left, right)] += 1

    adjacency: dict[str, dict[str, int]] = {event_id: {} for event_id in events}
    for (left, right), count in pair_overlap.items():
        adjacency[left][right] = count
        adjacency[right][left] = count

    component_number = 0
    components: dict[str, tuple[int, int]] = {}
    unseen = set(events)
    while unseen:
        component_number += 1
        seed = min(unseen, key=lambda value: (int(value) if value.isdigit() else math.inf, value))
        queue = deque([seed])
        members: list[str] = []
        unseen.remove(seed)
        while queue:
            current = queue.popleft()
            members.append(current)
            for neighbour in sorted(adjacency[current]):
                if neighbour in unseen:
                    unseen.remove(neighbour)
                    queue.append(neighbour)
        for event_id in members:
            components[event_id] = (component_number, len(members))

    result: dict[str, dict[str, int]] = {}
    for event_id, neighbours in adjacency.items():
        component, component_size = components[event_id]
        result[event_id] = {
            "overlap_event_degree": len(neighbours),
            "shared_coach_memberships": sum(neighbours.values()),
            "max_shared_coaches_with_one_event": max(neighbours.values(), default=0),
            "connectivity_component": component,
            "connectivity_component_size": component_size,
        }
    return result, component_number


def _score(event: Event, metrics: dict[str, int], repeat_count: int) -> float:
    """Transparent triage score; it is not a scientific pack-quality measure."""

    source_count = sum(
        (
            event.has_source_url,
            event.has_notes_url,
            event.has_ruleset_file_reference,
            event.has_information_text,
            event.has_scoring_text,
        )
    )
    return (
        25 * math.log1p(event.match_count)
        + 20 * math.log1p(len(event.coaches))
        + 10 * math.log1p(len(event.races))
        + min(metrics["overlap_event_degree"], 25)
        + min(metrics["connectivity_component_size"], 100) / 5
        + 3 * source_count
        + (5 if repeat_count > 1 else 0)
    )


def build_catalog(
    zip_path: Path | str, variant_id: str = BB2025_VARIANT_ID
) -> tuple[list[dict[str, str]], dict[str, object]]:
    """Read a NAF ZIP and return safe catalog rows plus aggregate summary."""

    with zipfile.ZipFile(zip_path) as zip_file:
        events = _load_events(zip_file, str(variant_id))
        _add_entries(zip_file, events)
        _add_matches(zip_file, events, str(variant_id))

    # A candidate pack corpus is anchored to observed results. Registered/future
    # tournaments without recorded games remain in the raw source, not this inventory.
    events = {event_id: event for event_id, event in events.items() if event.match_count > 0}

    metrics, component_count = _overlap_metrics(events)
    series_counts = Counter(repeat_series_key(event.name) for event in events.values())
    series_counts.pop("", None)
    ranked = sorted(
        events.values(),
        key=lambda event: (
            -_score(event, metrics[event.event_id], series_counts[repeat_series_key(event.name)]),
            event.start_date,
            event.event_id,
        ),
    )

    rows: list[dict[str, str]] = []
    for rank, event in enumerate(ranked, 1):
        key = repeat_series_key(event.name)
        repeat_count = series_counts[key] if key else 1
        event_metrics = metrics[event.event_id]
        source_count = sum(
            (
                event.has_source_url,
                event.has_notes_url,
                event.has_ruleset_file_reference,
                event.has_information_text,
                event.has_scoring_text,
            )
        )
        rows.append(
            {
                "candidate_rank": str(rank),
                "candidate_score": f"{_score(event, event_metrics, repeat_count):.3f}",
                "event_id": event.event_id,
                "event_name": event.name,
                "start_date": event.start_date,
                "end_date": event.end_date,
                "country": event.country,
                "city": event.city,
                "event_type": event.event_type,
                "is_open": _bool_text(event.event_type.strip().upper() == "OPEN"),
                "is_squad": _bool_text(event.is_squad),
                "match_count": str(event.match_count),
                "coach_count": str(len(event.coaches)),
                "race_count": str(len(event.races)),
                "registered_entry_count": str(event.registered_entry_count),
                "registered_coach_count": str(len(event.registered_coaches)),
                "registered_race_count": str(len(event.registered_races)),
                "repeat_series_key_heuristic": key,
                "repeat_series_event_count_heuristic": str(repeat_count),
                "has_source_url": _bool_text(event.has_source_url),
                "has_notes_url": _bool_text(event.has_notes_url),
                "has_ruleset_file_reference": _bool_text(event.has_ruleset_file_reference),
                "has_information_text": _bool_text(event.has_information_text),
                "has_scoring_text": _bool_text(event.has_scoring_text),
                "source_availability_count": str(source_count),
                **{field: str(value) for field, value in event_metrics.items()},
            }
        )

    nonempty_series = Counter(repeat_series_key(event.name) for event in events.values())
    nonempty_series.pop("", None)
    summary: dict[str, object] = {
        "variant_id": str(variant_id),
        "event_count": len(events),
        "match_count": sum(event.match_count for event in events.values()),
        "unique_coach_count": (
            len(set().union(*(event.coaches for event in events.values()))) if events else 0
        ),
        "race_count": (
            len(set().union(*(event.races for event in events.values()))) if events else 0
        ),
        "registered_entry_count": sum(event.registered_entry_count for event in events.values()),
        "unique_registered_coach_count": (
            len(set().union(*(event.registered_coaches for event in events.values())))
            if events
            else 0
        ),
        "registered_race_count": (
            len(set().union(*(event.registered_races for event in events.values())))
            if events
            else 0
        ),
        "country_count": len({event.country for event in events.values() if event.country}),
        "squad_event_count": sum(event.is_squad for event in events.values()),
        "open_event_count": sum(
            event.event_type.strip().upper() == "OPEN" for event in events.values()
        ),
        "connectivity_component_count": component_count,
        "largest_connectivity_component": max(
            (item["connectivity_component_size"] for item in metrics.values()), default=0
        ),
        "events_with_any_source_hint": sum(
            any(
                (
                    event.has_source_url,
                    event.has_notes_url,
                    event.has_ruleset_file_reference,
                    event.has_information_text,
                    event.has_scoring_text,
                )
            )
            for event in events.values()
        ),
        "events_with_source_url": sum(event.has_source_url for event in events.values()),
        "events_with_notes_url": sum(event.has_notes_url for event in events.values()),
        "events_with_ruleset_file_reference": sum(
            event.has_ruleset_file_reference for event in events.values()
        ),
        "events_with_information_text": sum(
            event.has_information_text for event in events.values()
        ),
        "events_with_scoring_text": sum(event.has_scoring_text for event in events.values()),
        "repeat_series_groups_heuristic": sum(count > 1 for count in nonempty_series.values()),
        "method_notes": {
            "scope": (
                "Events with at least one recorded match; discovery inventory only; no source "
                "hint is treated as verified pack linkage."
            ),
            "privacy": "Coach identifiers are used in memory for aggregates and are never output.",
            "participation": (
                "Coach/race coverage, overlap, and ranking use participants observed in "
                "target-variant games; registration counts are separately labeled and may include "
                "no-shows."
            ),
            "repeat_series": (
                "Heuristic groups normalized event names after removing four-digit years; "
                "review required."
            ),
            "connectivity": (
                "Events are adjacent when at least one game-observed coach appears in both events."
            ),
            "ranking": (
                "25*ln(1+matches) + 20*ln(1+coaches) + 10*ln(1+races) + capped "
                "overlap degree + capped component-size/5 + 3 per source hint + 5 for a "
                "heuristic repeat series."
            ),
        },
    }
    return rows, summary


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CATALOG_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(handle: TextIO, summary: dict[str, object]) -> None:
    handle.write(f"# NAF event discovery summary: variant {summary['variant_id']}\n\n")
    handle.write("This is a source-discovery inventory, not verified tournament-pack linkage.\n\n")
    labels = (
        ("Events", "event_count"),
        ("Matches", "match_count"),
        ("Unique coaches (aggregate only)", "unique_coach_count"),
        ("Races", "race_count"),
        ("Registered entries", "registered_entry_count"),
        ("Unique registered coaches (aggregate only)", "unique_registered_coach_count"),
        ("Registered race IDs", "registered_race_count"),
        ("Countries", "country_count"),
        ("Open events", "open_event_count"),
        ("Squad events", "squad_event_count"),
        ("Connectivity components", "connectivity_component_count"),
        ("Largest connectivity component", "largest_connectivity_component"),
        ("Events with any source hint", "events_with_any_source_hint"),
        ("Events with source URL", "events_with_source_url"),
        ("Events with notes URL", "events_with_notes_url"),
        ("Events with ruleset-file reference", "events_with_ruleset_file_reference"),
        ("Events with information text", "events_with_information_text"),
        ("Events with scoring text", "events_with_scoring_text"),
        ("Repeat-series groups (heuristic)", "repeat_series_groups_heuristic"),
    )
    handle.write("| Measure | Count |\n|---|---:|\n")
    for label, key in labels:
        handle.write(f"| {label} | {summary[key]} |\n")
    handle.write("\n## Method notes\n\n")
    method_notes = cast(Mapping[str, object], summary["method_notes"])
    for label, note in method_notes.items():
        handle.write(f"- **{label.replace('_', ' ').title()}:** {note}\n")


def write_catalog(
    zip_path: Path | str,
    output_dir: Path | str,
    variant_id: str = BB2025_VARIANT_ID,
) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rows, summary = build_catalog(zip_path, variant_id)
    _write_csv(output / "candidate_events.csv", rows)
    (output / "connectivity_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (output / "connectivity_summary.md").open("w", encoding="utf-8") as handle:
        _write_markdown(handle, summary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", type=Path, help="NAF statistics ZIP")
    parser.add_argument("output_dir", type=Path, help="directory for safe aggregate outputs")
    parser.add_argument("--variant", default=BB2025_VARIANT_ID, help="NAF variant ID (default: 15)")
    args = parser.parse_args(argv)
    write_catalog(args.zip_path, args.output_dir, args.variant)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
