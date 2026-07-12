"""Offline NAF-to-Tourplay candidate linker over cached public listing pages."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
COUNTRY_CODES = {
    "Australia": "AU",
    "Austria": "AT",
    "Belgium": "BE",
    "Bulgaria": "BG",
    "Canada": "CA",
    "Croatia": "HR",
    "Cyprus": "CY",
    "Czech Republic": "CZ",
    "Denmark": "DK",
    "England": "GB",
    "Finland": "FI",
    "France": "FR",
    "Germany": "DE",
    "Hungary": "HU",
    "Ireland": "IE",
    "Italy": "IT",
    "Lithuania": "LT",
    "Luxembourg": "LU",
    "New Zealand": "NZ",
    "Northern Ireland": "GB",
    "Poland": "PL",
    "Portugal": "PT",
    "Russia": "RU",
    "Scotland": "GB",
    "Singapore": "SG",
    "Slovak Republic": "SK",
    "Spain": "ES",
    "Sweden": "SE",
    "United States": "US",
    "Wales": "GB",
}


def normalize(value: str, remove_year: bool = False) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    if remove_year:
        text = YEAR_RE.sub(" ", text)
    return " ".join(NON_ALNUM_RE.sub(" ", text).split())


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _iso_day(value: str) -> date:
    return date.fromisoformat(value[:10])


@dataclass(frozen=True)
class Candidate:
    slug: str
    name: str
    score: float
    name_score: float
    date_distance: int
    country_match: bool
    locality_score: float


def load_tourplay_pages(directory: Path) -> list[dict[str, object]]:
    tournaments = {}
    for path in sorted(directory.glob("tourplay-page-*.json")):
        for item in json.loads(path.read_text(encoding="utf-8")):
            tournaments[item["nameNormalized"]] = item
    return list(tournaments.values())


def name_similarity(left: str, right: str) -> float:
    exact_left, exact_right = normalize(left), normalize(right)
    series_left, series_right = normalize(left, True), normalize(right, True)
    exact = SequenceMatcher(None, exact_left, exact_right).ratio()
    series = SequenceMatcher(None, series_left, series_right).ratio()
    left_tokens, right_tokens = set(exact_left.split()), set(exact_right.split())
    union = left_tokens | right_tokens
    token = len(left_tokens & right_tokens) / len(union) if union else 0.0
    return max(exact, 0.92 * series, token)


def learn_country_codes(
    events: dict[str, dict[str, str]],
    exact_links: dict[str, str],
    tournaments: dict[str, dict[str, object]],
) -> dict[str, str]:
    votes: dict[str, Counter[str]] = defaultdict(Counter)
    for event_id, slug in exact_links.items():
        event, tournament = events.get(event_id), tournaments.get(slug)
        if event and tournament and tournament.get("country"):
            votes[event["nation"]][str(tournament["country"])] += 1
    return {nation: counts.most_common(1)[0][0] for nation, counts in votes.items()}


def candidates_for_event(
    event: dict[str, str],
    tournaments: list[dict[str, object]],
    country_codes: dict[str, str],
) -> list[Candidate]:
    event_day = _iso_day(event["start_date"])
    expected_country = country_codes.get(event["nation"])
    result = []
    for tournament in tournaments:
        if not tournament.get("initDate") or int(tournament.get("ruleSet", 0)) != 25:
            continue
        distance = abs((_iso_day(str(tournament["initDate"])) - event_day).days)
        if distance > 2:
            continue
        name_score = name_similarity(event["name"], str(tournament["name"]))
        if name_score < 0.45:
            continue
        country_match = bool(expected_country and expected_country == tournament.get("country"))
        location = " ".join(
            str(tournament.get(field) or "") for field in ("locality", "region")
        )
        locality_score = name_similarity(event["city"], location) if event["city"] else 0.0
        date_score = {0: 1.0, 1: 0.75, 2: 0.4}[distance]
        score = (
            0.62 * name_score
            + 0.2 * date_score
            + 0.1 * float(country_match)
            + 0.08 * locality_score
        )
        result.append(
            Candidate(
                slug=str(tournament["nameNormalized"]),
                name=str(tournament["name"]),
                score=score,
                name_score=name_score,
                date_distance=distance,
                country_match=country_match,
                locality_score=locality_score,
            )
        )
    return sorted(result, key=lambda item: (-item.score, item.slug))


def run(
    naf_dir: Path, link_csv: Path, page_dir: Path, output: Path
) -> dict[str, object]:
    events = {
        row["event_id"]: row
        for row in _rows(naf_dir / "event.csv")
        if row["variant_id"] == "15"
    }
    played_events = {
        row["event_id"]
        for row in _rows(naf_dir / "match.csv")
        if row["variant_id"] == "15"
    }
    events = {event_id: event for event_id, event in events.items() if event_id in played_events}
    exact_links = {
        row["naf_tournament_id"]: row["tourplay_slug"] for row in _rows(link_csv)
    }
    tournament_rows = load_tourplay_pages(page_dir)
    tournaments = {str(row["nameNormalized"]): row for row in tournament_rows}
    learned_country_codes = learn_country_codes(events, exact_links, tournaments)
    country_codes = COUNTRY_CODES
    output_rows = []
    exact_found = 0
    exact_top = 0
    exact_confident = 0
    exact_confident_wrong_slug = 0
    recovered = []
    for event_id, event in sorted(events.items(), key=lambda item: int(item[0])):
        candidates = candidates_for_event(event, tournament_rows, country_codes)
        expected = exact_links.get(event_id, "")
        rank = next(
            (index + 1 for index, candidate in enumerate(candidates) if candidate.slug == expected),
            0,
        )
        if expected and expected in tournaments:
            exact_found += 1
            exact_top += rank == 1
        top = candidates[0] if candidates else None
        runner_up = candidates[1].score if len(candidates) > 1 else 0.0
        margin = top.score - runner_up if top else 0.0
        confident = bool(
            top and top.score >= 0.82 and top.name_score >= 0.8 and margin >= 0.08
        )
        if expected and expected in tournaments and confident and top and top.slug == expected:
            exact_confident += 1
        if expected and confident and top and top.slug != expected:
            exact_confident_wrong_slug += 1
        if not expected and confident and top:
            recovered.append(event_id)
        output_rows.append(
            {
                "naf_event_id": event_id,
                "naf_name": event["name"],
                "start_date": event["start_date"],
                "nation": event["nation"],
                "city": event["city"],
                "known_exact_slug": expected,
                "known_exact_rank": rank,
                "candidate_count": len(candidates),
                "top_slug": top.slug if top else "",
                "top_name": top.name if top else "",
                "top_score": round(top.score, 6) if top else "",
                "top_name_score": round(top.name_score, 6) if top else "",
                "top_date_distance": top.date_distance if top else "",
                "top_country_match": top.country_match if top else "",
                "top_locality_score": round(top.locality_score, 6) if top else "",
                "runner_up_margin": round(margin, 6) if top else "",
                "linker_confident": confident,
                "review_status": (
                    "known_exact" if expected else ("candidate" if confident else "none")
                ),
            }
        )
    output.mkdir(parents=True, exist_ok=True)
    with (output / "candidates.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    summary = {
        "tourplay_listing_records": len(tournament_rows),
        "naf_bb2025_events": len(events),
        "known_exact_links": len(exact_links),
        "known_exact_present_in_pages": exact_found,
        "known_exact_top_1": exact_top,
        "known_exact_confident_top_1": exact_confident,
        "known_exact_confident_wrong_slug": exact_confident_wrong_slug,
        "unlinked_confident_candidates": len(recovered),
        "unlinked_candidate_event_ids": recovered,
        "static_country_codes": country_codes,
        "validation_learned_country_codes": learned_country_codes,
        "thresholds": {
            "top_score": 0.82,
            "name_score": 0.8,
            "runner_up_margin": 0.08,
        },
        "status": "candidates_require_review",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("naf", type=Path)
    parser.add_argument("links", type=Path)
    parser.add_argument("pages", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.naf, args.links, args.pages, args.output), indent=2))


if __name__ == "__main__":
    main()
