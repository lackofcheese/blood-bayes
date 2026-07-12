import csv
import json
from pathlib import Path

from bb_stats.analysis.tourplay_resolved import build_views, write_output


def _csv(path: Path, fields: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(fields)
        writer.writerows(rows)


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    normalized, registry = tmp_path / "normalized", tmp_path / "registry"
    base = ("schema_version", "tourplay_event_id", "source_sha256")
    _csv(
        normalized / "tourplay_event_link.csv",
        ("tourplay_event_id", "rule_set"),
        [("e20", "20"), ("e25", "25")],
    )
    _csv(
        normalized / "tier_race.csv",
        base + ("race_id",),
        [("v", "e20", "x", "1"), ("v", "e25", "x", "1"), ("v", "e25", "x", "404")],
    )
    _csv(normalized / "improvement_pack.csv", base + ("cost_type",), [("v", "e25", "x", "2")])
    _csv(
        normalized / "improvement_option.csv",
        base + ("improvement_pack_type",),
        [("v", "e25", "x", "11")],
    )
    _csv(normalized / "tier_inducement.csv", base + ("inducement_id",), [("v", "e25", "x", "9")])
    _csv(normalized / "star_rule.csv", base + ("star_player_id",), [("v", "e25", "x", "7")])
    _csv(normalized / "mercenary_rule.csv", base + ("mercenary_id",), [("v", "e25", "x", "8")])
    fields = (
        "registry",
        "raw_id",
        "enum_key",
        "display_name",
        "roster_master_id",
        "cost",
        "ruleset",
        "status",
    )
    rows = [
        ("race", "1", "Amazon", "Amazon old", "10", "", "20", "resolved"),
        ("race", "1", "Amazon", "Amazon new", "11", "", "25", "resolved"),
        ("pack_cost_type", "2", "GoldPieces", "", "", "", "", "resolved"),
        ("improvement_type", "11", "StarPlayer", "", "", "", "", "resolved"),
        ("inducement_master", "9", "Wizard", "Wizard", "", "150000", "25", "resolved"),
        ("star_master", "7", "", "Same", "", "", "25", "resolved"),
        ("star_master", "7", "", "Different", "", "", "25", "resolved"),
    ]
    _csv(registry / "registry.csv", fields, rows)
    return normalized, registry


def test_resolves_by_event_ruleset_and_preserves_missing_and_ambiguous(tmp_path: Path) -> None:
    normalized, registry = _fixture(tmp_path)
    views, counts = build_views(normalized, registry)
    races = views["resolved_tier_race"]
    assert [row["resolved_display_name"] for row in races] == ["Amazon old", "Amazon new", ""]
    assert [row["resolution_status"] for row in races] == ["resolved", "resolved", "unresolved"]
    assert views["resolved_star_rule"][0]["resolution_status"] == "ambiguous"
    assert views["resolved_mercenary_rule"][0]["resolution_status"] == "unresolved"
    assert counts["resolved_tier_race_input_rows"] == counts["resolved_tier_race_output_rows"] == 3


def test_write_output_is_deterministic_and_reconciled(tmp_path: Path) -> None:
    normalized, registry = _fixture(tmp_path)
    output = tmp_path / "output"
    write_output(normalized, registry, output)
    first = (output / "manifest.json").read_bytes()
    write_output(normalized, registry, output)
    assert (output / "manifest.json").read_bytes() == first
    manifest = json.loads(first)
    assert manifest["tables"]["resolved_tier_race"] == 3
    with (output / "resolved_tier_race.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["race_id"] for row in rows] == ["1", "1", "404"]
