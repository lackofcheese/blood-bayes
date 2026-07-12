import csv
import json
from pathlib import Path

from bb_stats.ingest.tourplay_registry import build_registry, parse_bundle_enums


def test_parse_minified_numeric_enums() -> None:
    source = (
        "var TeamRace;!function(e){e[e.Human=3001]='Human',e[e.Orc=3002]='Orc'}"
        "(TeamRace||(TeamRace={}));"
        "var ImprovementPackType;!function(e){e[e.Primary=0]='Primary',e[e.Star=14]='Star'}"
        "(ImprovementPackType||(ImprovementPackType={}));"
        "var PackCostType;!function(e){e[e.Spp=0]='Spp',e[e.Gold=1]='Gold'}"
        "(PackCostType||(PackCostType={}));"
        "var InducementType;!function(e){e[e.Bribe=3]='Bribe'}"
        "(InducementType||(InducementType={}));"
    )
    result = parse_bundle_enums(source)
    assert result["race"] == {3001: "Human", 3002: "Orc"}
    assert result["improvement_type"] == {0: "Primary", 14: "Star"}
    assert result["pack_cost_type"] == {0: "Spp", 1: "Gold"}
    assert result["inducement_type"] == {3: "Bribe"}


def test_parse_current_function_return_shape() -> None:
    source = (
        'var r=function(i){return i[i.Amazon=1]="Amazon",'
        'i[i.Amazon_BB2025=3001]="Amazon_BB2025",i}(r||{});'
        'var p=function(t){return t[t.Primary=0]="Primary",t[t.Secondary=2]="Secondary",'
        't[t.StarPlayer=11]="StarPlayer",t[t.Elite=14]="Elite",t}(p||{});'
    )
    result = parse_bundle_enums(source)
    assert result["race"][3001] == "Amazon_BB2025"
    assert result["improvement_type"][11] == "StarPlayer"


def _csv(path: Path, field: str, value: object) -> None:
    path.write_text(f"{field}\n{value}\n", encoding="utf-8")


def test_build_registry_reports_observed_unknowns(tmp_path: Path) -> None:
    bundle = tmp_path / "app.js"
    bundle.write_text(
        "var TeamRace;!function(e){e[e.Human=3001]='Human'}(TeamRace||(TeamRace={}));"
        # Keep the production minification shape intact.
        "var ImprovementPackType;!function(e){e[e.Primary=0]='Primary'}(ImprovementPackType||(ImprovementPackType={}));",  # noqa: E501
        encoding="utf-8",
    )
    master = tmp_path / "master.json"
    master.write_text(
        json.dumps({"ruleSet": 25, "rosters": [{"id": 88, "name": "Human", "rosterMasterId": 88}]}),
        encoding="utf-8",
    )
    normalized = tmp_path / "normalized"
    normalized.mkdir()
    _csv(normalized / "tier_race.csv", "race_id", 9999)
    _csv(normalized / "improvement_option.csv", "improvement_pack_type", 0)
    _csv(normalized / "tier_inducement.csv", "inducement_id", 77)
    output = tmp_path / "out"

    counts = build_registry(bundle, [master], normalized, output)

    assert counts["unresolved_observed"] == 2
    unresolved = list(csv.DictReader((output / "unresolved_observed.csv").open()))
    assert {(row["registry"], row["raw_id"]) for row in unresolved} == {
        ("race", "9999"),
        ("inducement_master", "77"),
    }
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["schema_version"] == "tourplay-registry-v1"
    assert len(manifest["bundle"]["sha256"]) == 64


def test_duplicate_master_meanings_are_ambiguous(tmp_path: Path) -> None:
    bundle = tmp_path / "app.js"
    bundle.write_text("", encoding="utf-8")
    master = tmp_path / "master.json"
    master.write_text(
        json.dumps(
            {
                "rosters": [
                    {"id": 1, "name": "One", "rosterMasterId": 1},
                    {"id": 1, "name": "Two", "rosterMasterId": 1},
                ]
            }
        ),
        encoding="utf-8",
    )
    normalized = tmp_path / "normalized"
    normalized.mkdir()
    output = tmp_path / "out"
    build_registry(bundle, [master], normalized, output)
    rows = list(csv.DictReader((output / "registry.csv").open()))
    assert [row["status"] for row in rows] == ["ambiguous", "ambiguous"]
