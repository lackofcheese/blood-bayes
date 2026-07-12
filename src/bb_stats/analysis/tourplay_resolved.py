"""Create offline, privacy-safe resolved views of normalized Tourplay rows."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

SCHEMA_VERSION = "tourplay-resolved-v1"

SPECS = {
    "resolved_tier_race": (
        "tier_race.csv",
        "race",
        "race_id",
        ("enum_key", "display_name", "roster_master_id"),
    ),
    "resolved_improvement_pack": (
        "improvement_pack.csv",
        "pack_cost_type",
        "cost_type",
        ("enum_key",),
    ),
    "resolved_improvement_option": (
        "improvement_option.csv",
        "improvement_type",
        "improvement_pack_type",
        ("enum_key",),
    ),
    "resolved_tier_inducement": (
        "tier_inducement.csv",
        "inducement_master",
        "inducement_id",
        ("display_name", "cost", "enum_key"),
    ),
    "resolved_star_rule": ("star_rule.csv", "star_master", "star_player_id", ("display_name",)),
    "resolved_mercenary_rule": (
        "mercenary_rule.csv",
        "mercenary_master",
        "mercenary_id",
        ("display_name",),
    ),
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _event_rulesets(normalized: Path) -> dict[str, tuple[str, str]]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for row in _read(normalized / "tourplay_event_link.csv"):
        grouped[row["tourplay_event_id"]].add(row.get("rule_set", ""))
    result = {}
    for event_id, values in grouped.items():
        nonempty = {value for value in values if value}
        if len(nonempty) == 1:
            result[event_id] = (next(iter(nonempty)), "resolved")
        elif len(nonempty) > 1:
            result[event_id] = ("", "ambiguous")
        else:
            result[event_id] = ("", "unresolved")
    return result


def _resolve(
    candidates: list[dict[str, str]], fields: Sequence[str], ruleset: str, rule_status: str
) -> tuple[dict[str, str], str]:
    if rule_status != "resolved" and any(row.get("ruleset") for row in candidates):
        return {field: "" for field in fields}, rule_status
    applicable = [
        row for row in candidates if not row.get("ruleset") or row.get("ruleset") == ruleset
    ]
    if not applicable:
        return {field: "" for field in fields}, "unresolved"
    values: dict[str, str] = {}
    ambiguous = any(row.get("status") == "ambiguous" for row in applicable)
    for field in fields:
        distinct = {row.get(field, "") for row in applicable if row.get(field, "")}
        if len(distinct) > 1:
            ambiguous = True
            values[field] = ""
        else:
            values[field] = next(iter(distinct), "")
    return values, "ambiguous" if ambiguous else "resolved"


def build_views(
    normalized: Path, registry_dir: Path
) -> tuple[dict[str, list[dict[str, str]]], dict[str, int]]:
    """Resolve identifiers, preserving each normalized source row exactly once."""
    registry = _read(registry_dir / "registry.csv")
    index: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in registry:
        index[(row["registry"], row["raw_id"])].append(row)
    rulesets = _event_rulesets(normalized)
    views: dict[str, list[dict[str, str]]] = {}
    counts: dict[str, int] = {}
    for output, (filename, registry_name, id_field, fields) in SPECS.items():
        source = _read(normalized / filename)
        enriched = []
        statuses: dict[str, int] = defaultdict(int)
        for row in source:
            ruleset, rule_status = rulesets.get(row["tourplay_event_id"], ("", "unresolved"))
            values, status = _resolve(
                index.get((registry_name, row.get(id_field, "")), []), fields, ruleset, rule_status
            )
            enriched.append(
                {
                    **row,
                    "resolved_schema_version": SCHEMA_VERSION,
                    "resolved_ruleset": ruleset,
                    **{f"resolved_{key}": value for key, value in values.items()},
                    "resolution_status": status,
                }
            )
            statuses[status] += 1
        views[output] = enriched
        counts[f"{output}_input_rows"] = len(source)
        counts[f"{output}_output_rows"] = len(enriched)
        for status in ("resolved", "unresolved", "ambiguous"):
            counts[f"{output}_{status}"] = statuses[status]
    return views, counts


def _write_csv(path: Path, rows: list[dict[str, str]], source_fields: Sequence[str]) -> None:
    resolved_fields = ["resolved_schema_version", "resolved_ruleset"]
    if rows:
        resolved_fields += [
            key for key in rows[0] if key.startswith("resolved_") and key not in resolved_fields
        ]
    fields = list(source_fields) + resolved_fields + ["resolution_status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def write_output(normalized: Path, registry_dir: Path, output: Path) -> dict[str, int]:
    views, counts = build_views(normalized, registry_dir)
    output.mkdir(parents=True, exist_ok=True)
    input_files = sorted(
        {normalized / spec[0] for spec in SPECS.values()}
        | {normalized / "tourplay_event_link.csv", registry_dir / "registry.csv"}
    )
    with tempfile.TemporaryDirectory(prefix=".resolved-stage-", dir=output.parent) as temporary:
        stage = Path(temporary)
        for name, rows in views.items():
            source_fields = tuple(_read(normalized / SPECS[name][0])[0].keys()) if rows else ()
            if not rows:
                with (normalized / SPECS[name][0]).open(encoding="utf-8", newline="") as handle:
                    source_fields = tuple(csv.DictReader(handle).fieldnames or ())
            _write_csv(stage / f"{name}.csv", rows, source_fields)
        (stage / "reconciliation.json").write_text(
            json.dumps(counts, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "inputs": {str(path): _sha(path) for path in input_files},
            "outputs": {path.name: _sha(path) for path in sorted(stage.glob("resolved_*.csv"))},
            "tables": {name: len(rows) for name, rows in views.items()},
        }
        (stage / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        for path in sorted(stage.iterdir()):
            os.replace(path, output / path.name)
    return counts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("normalized", type=Path)
    parser.add_argument("registry", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(write_output(args.normalized, args.registry, args.output), sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
