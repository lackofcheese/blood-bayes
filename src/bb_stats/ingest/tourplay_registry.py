"""Build offline, provenance-rich registries for Tourplay identifiers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "tourplay-registry-v1"

REGISTRY_FIELDS = (
    "schema_version",
    "registry",
    "raw_id",
    "enum_key",
    "display_name",
    "roster_master_id",
    "cost",
    "ruleset",
    "source_file",
    "source_sha256",
    "status",
)

_ENUM_ALIASES = {
    "race": ("teamrace", "team race"),
    "improvement_type": ("improvementpacktype", "improvement pack type"),
    "pack_cost_type": ("packcosttype", "improvementpackcosttype", "cost type"),
    "inducement_type": ("inducementtype", "inducement type"),
}
_ASSIGNMENT = re.compile(
    r"(?:[A-Za-z_$][\w$]*\s*\[\s*)?[A-Za-z_$][\w$]*\.([A-Za-z_$][\w$]*)\s*=\s*(\d+)"
)
_IIFE = re.compile(
    r"(?:function\s*\(\s*([A-Za-z_$][\w$]*)\s*\)|\(\s*([A-Za-z_$][\w$]*)\s*\)\s*=>)\s*\{(.{1,30000}?)\}\s*\((.{1,300}?)\)",
    re.DOTALL,
)
_FUNCTION_ENUM = re.compile(
    r"function\s*\(\s*([A-Za-z_$][\w$]*)\s*\)\s*\{\s*return\s+(.{1,30000}?)\}\s*\(",
    re.DOTALL,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_bundle_enums(text: str) -> dict[str, dict[int, str]]:
    """Parse TypeScript numeric enums from readable or minified application code.

    Classification uses the enum's surrounding symbol, never member-name guesses.
    This deliberately leaves unidentified numeric enums unresolved.
    """
    found: dict[str, dict[int, str]] = {key: {} for key in _ENUM_ALIASES}
    for match in _IIFE.finditer(text):
        body, invocation = match.group(3), match.group(4)
        # The invocation normally contains the enum variable and is far safer than
        # a broad minified-code window containing several adjacent enum modules.
        context = invocation.lower()
        kinds = [
            kind
            for kind, aliases in _ENUM_ALIASES.items()
            if any(alias in context for alias in aliases)
        ]
        if len(kinds) != 1:
            continue
        parsed = {int(value): key for key, value in _ASSIGNMENT.findall(body)}
        if parsed:
            found[kinds[0]].update(parsed)

    # Production chunks use ``function(t){return ...}(e||{})`` and minify away
    # descriptive variables. Complete enum signatures identify these modules
    # without relying on overlapping numeric ranges.
    for match in _FUNCTION_ENUM.finditer(text):
        parsed = {int(value): key for key, value in _ASSIGNMENT.findall(match.group(2))}
        signature = set(parsed.items())
        kind = None
        if (3001, "Amazon_BB2025") in signature:
            kind = "race"
        elif {
            (0, "Primary"),
            (2, "Secondary"),
            (11, "StarPlayer"),
            (14, "Elite"),
        } <= signature:
            kind = "improvement_type"
        elif {(0, "None"), (1, "Spp"), (2, "GoldPieces")} <= signature:
            kind = "pack_cost_type"
        elif {
            (7, "TempAgencyCheerleaders"),
            (11, "Mercenary"),
            (12, "StarPlayer"),
        } <= signature:
            kind = "inducement_type"
        if kind:
            found[kind].update(parsed)

    return found


def _walk(value: object) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _first(row: Mapping[str, Any], keys: Sequence[str]) -> object:
    for key in keys:
        if row.get(key) not in (None, ""):
            return row[key]
    return None


def parse_master(path: Path) -> list[dict[str, object]]:
    """Extract explicitly named master objects without assuming one API envelope."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    digest = sha256(path)
    explicit: list[tuple[str, Mapping[str, Any]]] = []
    if isinstance(payload, Mapping):
        for key, registry in (
            ("rosterMasters", "race_master"),
            ("starplayerMasters", "star_master"),
            ("inducementsMasters", "inducement_master"),
        ):
            values = payload.get(key)
            if isinstance(values, list):
                explicit.extend((registry, item) for item in values if isinstance(item, Mapping))
    candidates = explicit or [("", item) for item in _walk(payload)]
    for explicit_registry, item in candidates:
        raw_id = _first(item, ("id", "masterId", "rosterMasterId", "positionId"))
        name = _first(item, ("name", "position", "displayName", "label"))
        if raw_id is None or name is None:
            continue
        keys = {str(key).lower() for key in item}
        registry = explicit_registry or None
        if "rostermasterid" in keys or "teamrace" in keys or "rerollcost" in keys:
            registry = "race_master"
        elif (
            "starplayer" in keys
            or "isstarplayer" in keys
            or "positionid" in keys
            and "cost" in keys
        ):
            registry = "star_master"
        elif (
            "inducementtype" in keys
            or "inducement" in keys
            or "maxquantity" in keys
            and "cost" in keys
        ):
            registry = "inducement_master"
        if registry:
            rows.append(
                {
                    "registry": registry,
                    "raw_id": str(raw_id),
                    "enum_key": str(item.get("teamRace", "")),
                    "display_name": str(name),
                    "roster_master_id": str(raw_id) if registry == "race_master" else "",
                    "cost": item.get("cost", ""),
                    "ruleset": str(
                        _first(item, ("ruleSet", "ruleset", "version"))
                        or (
                            _first(payload, ("ruleSet", "ruleset", "version"))
                            if isinstance(payload, Mapping)
                            else ""
                        )
                        or ""
                    ),
                    "source_file": path.name,
                    "source_sha256": digest,
                }
            )
    return rows


def _read_observed(directory: Path) -> dict[str, set[str]]:
    specs = {
        "race": ("tier_race.csv", "race_id"),
        "improvement_type": ("improvement_option.csv", "improvement_pack_type"),
        "pack_cost_type": ("improvement_pack.csv", "cost_type"),
        "inducement_master": ("tier_inducement.csv", "inducement_id"),
        "star_master": ("star_rule.csv", "star_player_id"),
        "mercenary_master": ("mercenary_rule.csv", "mercenary_id"),
    }
    result: dict[str, set[str]] = defaultdict(set)
    for registry, (filename, field) in specs.items():
        path = directory / filename
        if not path.is_file():
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get(field):
                    result[registry].add(row[field])
    return result


def _write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def build_registry(
    bundle: Path, masters: Sequence[Path], normalized: Path, output: Path
) -> dict[str, int]:
    bundle_digest = sha256(bundle)
    enums = parse_bundle_enums(bundle.read_text(encoding="utf-8", errors="replace"))
    rows: list[dict[str, object]] = []
    for registry, values in enums.items():
        for raw_id, key in sorted(values.items()):
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "registry": registry,
                    "raw_id": raw_id,
                    "enum_key": key,
                    "display_name": "",
                    "ruleset": "",
                    "source_file": bundle.name,
                    "source_sha256": bundle_digest,
                    "status": "resolved",
                }
            )
    for master in masters:
        for row in parse_master(master):
            if row["registry"] == "race_master" and row.get("enum_key"):
                reverse_races = {key: raw_id for raw_id, key in enums["race"].items()}
                race_id = reverse_races.get(str(row["enum_key"]))
                if race_id is not None:
                    row["registry"] = "race"
                    row["raw_id"] = str(race_id)
            rows.append({"schema_version": SCHEMA_VERSION, "status": "resolved", **row})

    # Preserve duplicate IDs/names as ambiguous rather than selecting an arbitrary row.
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["registry"]), str(row["raw_id"]), str(row["ruleset"]))].append(row)
    for group in grouped.values():
        meanings = {
            (str(row.get("enum_key", "")), str(row.get("display_name", ""))) for row in group
        }
        if len(meanings) > 1:
            for row in group:
                row["status"] = "ambiguous"

    observed = _read_observed(normalized)
    known = defaultdict(set)
    for row in rows:
        known[str(row["registry"])].add(str(row["raw_id"]))
    unresolved = [
        {
            "schema_version": SCHEMA_VERSION,
            "registry": registry,
            "raw_id": raw_id,
            "reason": "no authoritative registry row",
        }
        for registry, ids in sorted(observed.items())
        for raw_id in sorted(ids)
        if raw_id not in known[registry]
    ]
    rows.sort(
        key=lambda row: (
            str(row["registry"]),
            str(row["ruleset"]),
            str(row["raw_id"]),
            str(row.get("display_name", "")),
        )
    )
    counts = {
        "registry_rows": len(rows),
        "unresolved_observed": len(unresolved),
        **{f"{key}_enum_rows": len(value) for key, value in enums.items()},
    }
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".registry-stage-", dir=output.parent) as temporary:
        stage = Path(temporary)
        _write_csv(stage / "registry.csv", REGISTRY_FIELDS, rows)
        for registry in (
            "race",
            "improvement_type",
            "pack_cost_type",
            "inducement_type",
            "inducement_master",
            "star_master",
        ):
            _write_csv(
                stage / f"{registry}_registry.csv",
                REGISTRY_FIELDS,
                (row for row in rows if row["registry"] == registry),
            )
        _write_csv(
            stage / "unresolved_observed.csv",
            ("schema_version", "registry", "raw_id", "reason"),
            unresolved,
        )
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "bundle": {"file": bundle.name, "sha256": bundle_digest},
            "masters": [{"file": path.name, "sha256": sha256(path)} for path in masters],
            "counts": counts,
        }
        (stage / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (stage / "reconciliation.json").write_text(
            json.dumps(counts, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        for path in sorted(stage.iterdir()):
            os.replace(path, output / path.name)
    return counts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("normalized_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("master", type=Path, nargs="*")
    args = parser.parse_args(argv)
    print(
        json.dumps(
            build_registry(args.bundle, args.master, args.normalized_dir, args.output_dir),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
