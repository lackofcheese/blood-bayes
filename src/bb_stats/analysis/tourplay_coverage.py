"""Discover exact NAF-to-Tourplay links and audit public event metadata.

Only ``/api/tournament/{slug}`` is fetched.  This module intentionally never
contacts inscription or roster endpoints.
"""

from __future__ import annotations

import argparse
import csv
import http.client
import io
import json
import re
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bb_stats.contracts import BB2025_VARIANT_ID

TOURPLAY_URL = re.compile(
    r"https?://(?:www\.)?tourplay\.net/"
    r"(?:(?:[a-z]{2})(?:-[a-z]{2})?/)?blood-bowl/"
    r"(?P<slug>[a-z0-9][a-z0-9_-]*)"
    r"(?:/(?:news|settings|awards|classifications))?/?"
    r"(?:[?#][^\s<>\"']*)?",
    re.IGNORECASE,
)
SOURCE_FIELDS = ("tournamenturl", "tournamentnotesurl", "tournamentinformation")
OUTPUT_FIELDS = (
    "naf_tournament_id", "naf_tournament_name", "tourplay_slug", "tourplay_url",
    "evidence_field", "confidence", "fetch_state", "http_status",
    "has_categories", "has_tiers", "has_race_mapping", "has_treasury",
    "has_inducements", "has_improvement_packs", "has_skill_costs",
    "has_stacking", "has_stars", "legal_pack_mapping", "pack_choice_structure",
    "has_multiple_pack_choices", "document_supplement_likely", "tourplay_event_id",
)

Transport = Callable[[str, Mapping[str, str]], tuple[int, bytes]]


@dataclass(frozen=True)
class ExactLink:
    naf_tournament_id: str
    naf_tournament_name: str
    tourplay_slug: str
    tourplay_url: str
    evidence_field: str
    confidence: str = "exact_url"


def _member(archive: zipfile.ZipFile, basename: str) -> str:
    matches = [name for name in archive.namelist() if Path(name).name == basename]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {basename!r} in ZIP, found {len(matches)}")
    return matches[0]


def _rows(archive: zipfile.ZipFile, basename: str) -> Iterable[dict[str, str]]:
    with (
        archive.open(_member(archive, basename)) as raw,
        io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text,
    ):
        yield from csv.DictReader(text, delimiter=";")


def normalize_tourplay_url(value: str) -> list[tuple[str, str]]:
    """Return normalized ``(slug, URL)`` pairs found in arbitrary NAF text."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for match in TOURPLAY_URL.finditer(value or ""):
        # Forum software sometimes stores a visually truncated URL such as
        # ``/ii-c ... owl-girona``.  The captured prefix is not a real slug.
        if re.match(r"\s*\.{3}(?:\s|$)", value[match.end():]):
            continue
        slug = match.group("slug").lower().replace("_", "-").strip("-")
        if slug and slug not in seen:
            seen.add(slug)
            found.append((slug, f"https://tourplay.net/en/blood-bowl/{slug}"))
    return found


def extract_exact_links(
    zip_path: Path,
    *,
    variant_id: str = BB2025_VARIANT_ID,
    recorded_games_only: bool = True,
) -> list[ExactLink]:
    """Extract explicit Tourplay URLs; no fuzzy name matching is attempted."""
    with zipfile.ZipFile(zip_path) as archive:
        recorded: set[str] | None = None
        if recorded_games_only:
            recorded = {
                row.get("tournamentid", "").strip()
                for row in _rows(archive, "naf_game.csv")
                if row.get("naf_variantsid", "").strip() == variant_id
            }
        links: list[ExactLink] = []
        seen: set[tuple[str, str]] = set()
        for row in _rows(archive, "naf_tournament.csv"):
            if row.get("naf_variantsid", "").strip() != variant_id:
                continue
            event_id = row.get("tournamentid", "").strip()
            if recorded is not None and event_id not in recorded:
                continue
            for field in SOURCE_FIELDS:
                for slug, url in normalize_tourplay_url(row.get(field, "")):
                    key = (event_id, slug)
                    if key in seen:
                        continue
                    seen.add(key)
                    links.append(ExactLink(
                        naf_tournament_id=event_id,
                        naf_tournament_name=row.get("tournamentname", "").strip(),
                        tourplay_slug=slug,
                        tourplay_url=url,
                        evidence_field=field,
                    ))
    return sorted(links, key=lambda item: (item.naf_tournament_id, item.tourplay_slug))


def _bool(value: object) -> bool:
    return bool(value)


def classify_metadata(payload: Mapping[str, Any]) -> dict[str, object]:
    """Summarize pack-field coverage without retaining personal event metadata."""
    categories = payload.get("categories")
    categories = categories if isinstance(categories, list) else []
    tiers = [
        tier
        for category in categories if isinstance(category, Mapping)
        for tier in (category.get("tiers") or []) if isinstance(tier, Mapping)
    ]
    packs = [
        pack
        for tier in tiers
        for pack in (tier.get("improvementPacks") or []) if isinstance(pack, Mapping)
    ]
    options = [
        option
        for pack in packs
        for option in (pack.get("options") or []) if isinstance(option, Mapping)
    ]
    pack_counts = [len(tier.get("improvementPacks") or []) for tier in tiers]
    multi_pack = any(count > 1 for count in pack_counts)
    all_tiers_mapped = bool(tiers) and all(count >= 1 for count in pack_counts)
    has_stars = any(
        option.get("improvementPackType") == 11
        or any("star" in str(key).lower() for key in option)
        for option in options
    ) or any(
        any("star" in str(key).lower() for key in tier)
        or any("star" in str(key).lower() for key in pack)
        for tier in tiers
        for pack in (tier.get("improvementPacks") or [{}])
        if isinstance(pack, Mapping)
    )
    has_skill_costs = any(
        option.get("improvementPackType") in {0, 2} and "sppCost" in option
        for option in options
    )
    has_stacking = any(
        "maxStackedPlayers" in pack
        or any("stack" in str(key).lower() for key in option)
        for pack in packs for option in (pack.get("options") or [{}])
        if isinstance(option, Mapping)
    )
    has_tiers = bool(tiers)
    return {
        "has_categories": bool(categories),
        "has_tiers": has_tiers,
        "has_race_mapping": any(_bool(tier.get("teamRaces")) for tier in tiers),
        "has_treasury": bool(tiers) and all("treasuryBudget" in tier for tier in tiers),
        "has_inducements": any(_bool(tier.get("inducements")) for tier in tiers),
        "has_improvement_packs": bool(packs),
        "has_skill_costs": has_skill_costs,
        "has_stacking": has_stacking,
        "has_stars": has_stars,
        # Composition of race→tier and tier→improvementPacks yields the legal
        # choice set. Rosters reveal realized choices, not pack availability.
        "legal_pack_mapping": "direct" if all_tiers_mapped else "unavailable",
        "pack_choice_structure": (
            "choice_set" if all_tiers_mapped and multi_pack
            else ("single_only" if all_tiers_mapped else "unavailable")
        ),
        "has_multiple_pack_choices": multi_pack,
        # Event JSON does not establish normative scoring, schedule, or errata.
        "document_supplement_likely": True,
        "tourplay_event_id": str(payload.get("id", "")),
    }


def _default_transport(url: str, headers: Mapping[str, str]) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers=dict(headers))
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except (
        urllib.error.URLError,
        TimeoutError,
        ConnectionError,
        http.client.RemoteDisconnected,
    ):
        # A bounded audit must record a transport failure without retrying or
        # discarding already cached responses. 599 is an internal sentinel.
        return 599, b""


def fetch_metadata(
    links: Sequence[ExactLink],
    cache_dir: Path,
    *,
    max_requests: int = 70,
    delay_seconds: float = 3.0,
    stop_after_blocked: int = 3,
    transport: Transport = _default_transport,
    sleep: Callable[[float], None] = time.sleep,
) -> list[dict[str, object]]:
    """Fetch each unique slug at most once, honoring cache and hard safety limits."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    requests = 0
    blocked = 0
    by_slug: dict[str, tuple[str, int, Mapping[str, Any] | None]] = {}
    for link in links:
        slug = link.tourplay_slug
        if slug in by_slug:
            continue
        cache_path = cache_dir / f"{slug}.json"
        if cache_path.exists():
            try:
                payload = json.loads(cache_path.read_text(encoding="utf-8"))
                by_slug[slug] = ("cached", 200, payload)
                # A valid cached success lies between blocked slugs in the
                # deterministic sequence, so they are not consecutive.
                blocked = 0
            except (json.JSONDecodeError, OSError):
                by_slug[slug] = ("invalid_cache", 0, None)
            continue
        if requests >= max_requests or blocked >= stop_after_blocked:
            by_slug[slug] = ("not_fetched_limit", 0, None)
            continue
        if requests:
            sleep(delay_seconds)
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "Chrome/138.0 Safari/537.36"
            ),
            "Referer": link.tourplay_url,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        status, body = transport(f"https://tourplay.net/api/tournament/{slug}", headers)
        requests += 1
        if status in {403, 423, 599}:
            blocked += 1
        else:
            blocked = 0
        payload = None
        state = "http_error"
        if status == 200:
            try:
                decoded = json.loads(body)
                if isinstance(decoded, Mapping):
                    payload = decoded
                    cache_path.write_bytes(body)
                    state = "fetched"
                else:
                    state = "invalid_json_shape"
            except json.JSONDecodeError:
                state = "invalid_json"
        by_slug[slug] = (state, status, payload)

    rows: list[dict[str, object]] = []
    for link in links:
        state, status, payload = by_slug[link.tourplay_slug]
        row: dict[str, object] = asdict(link)
        row.update({"fetch_state": state, "http_status": status})
        row.update(classify_metadata(payload) if payload is not None else classify_metadata({}))
        rows.append(row)
    return rows


def _dry_rows(links: Sequence[ExactLink]) -> list[dict[str, object]]:
    rows = []
    for link in links:
        row: dict[str, object] = asdict(link)
        row.update({"fetch_state": "dry_run", "http_status": 0})
        row.update(classify_metadata({}))
        rows.append(row)
    return rows


def write_outputs(rows: Sequence[Mapping[str, object]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "tourplay_coverage.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=OUTPUT_FIELDS,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    counts: dict[str, int] = {}
    statuses: dict[str, int] = {}
    for row in rows:
        state = str(row["fetch_state"])
        counts[state] = counts.get(state, 0) + 1
        status = str(row["http_status"])
        statuses[status] = statuses.get(status, 0) + 1
    coverage_fields = (
        "has_tiers", "has_race_mapping", "has_treasury", "has_improvement_packs",
        "has_skill_costs", "has_stacking", "has_stars",
    )
    coverage = {
        field: sum(bool(row.get(field)) for row in rows) for field in coverage_fields
    }
    mappings = {
        value: sum(row.get("legal_pack_mapping") == value for row in rows)
        for value in ("direct", "unavailable")
    }
    choice_structures = {
        value: sum(row.get("pack_choice_structure") == value for row in rows)
        for value in ("single_only", "choice_set", "unavailable")
    }
    summary = {
        "exact_link_count": len(rows),
        "fetch_states": counts,
        "http_statuses": statuses,
        "coverage_counts": coverage,
        "legal_pack_mapping_counts": mappings,
        "pack_choice_structure_counts": choice_structures,
    }
    (output_dir / "tourplay_coverage.json").write_text(
        json.dumps({"summary": summary, "events": list(rows)}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Tourplay coverage",
        "",
        f"Exact NAF–Tourplay links: {len(rows)}",
        "",
        "## Fetch states",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in sorted(counts.items()))
    lines.extend(["", "## HTTP statuses", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(statuses.items()))
    lines.extend(["", "## Metadata coverage", ""])
    lines.extend(f"- {key}: {value}" for key, value in coverage.items())
    lines.extend(["", "## Legal race-to-pack mapping", ""])
    lines.extend(f"- {key}: {value}" for key, value in mappings.items())
    lines.extend(["", "## Pack choice structure", ""])
    lines.extend(f"- {key}: {value}" for key, value in choice_structures.items())
    lines.extend(["", "No inscription or roster endpoints were contacted.", ""])
    (output_dir / "tourplay_coverage.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--variant-id", default=BB2025_VARIANT_ID)
    parser.add_argument("--include-events-without-games", action="store_true")
    parser.add_argument(
        "--fetch", action="store_true", help="Explicitly enable public metadata GETs"
    )
    parser.add_argument("--cache-dir", type=Path, default=Path("data/raw/tourplay"))
    parser.add_argument("--max-requests", type=int, default=70)
    parser.add_argument("--delay-seconds", type=float, default=3.0)
    parser.add_argument("--stop-after-blocked", type=int, default=3)
    args = parser.parse_args(argv)
    links = extract_exact_links(
        args.zip_path,
        variant_id=args.variant_id,
        recorded_games_only=not args.include_events_without_games,
    )
    rows = fetch_metadata(
        links, args.cache_dir, max_requests=args.max_requests,
        delay_seconds=args.delay_seconds, stop_after_blocked=args.stop_after_blocked,
    ) if args.fetch else _dry_rows(links)
    write_outputs(rows, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
