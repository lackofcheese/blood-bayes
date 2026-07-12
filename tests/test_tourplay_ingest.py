import csv
import json
from pathlib import Path

from bb_stats.ingest.tourplay import normalize, write_output


def _coverage(path: Path, *slugs: str) -> None:
    events = [
        {
            "naf_tournament_id": str(index),
            "tourplay_slug": slug,
            "fetch_state": "cached",
            "http_status": 200,
            "evidence_field": "tournamenturl",
            "confidence": "exact_url",
        }
        for index, slug in enumerate(slugs, 1)
    ]
    path.write_text(json.dumps({"events": events}), encoding="utf-8")


def _event() -> dict[str, object]:
    return {
        "id": 99,
        "ruleSet": 7,
        "isNaf": True,
        "administrators": [{"email": "secret@example.test"}],
        "address": "private",
        "categories": [
            {
                "id": 8,
                "type": 2,
                "tiers": [
                    {
                        "id": 10,
                        "level": 1,
                        "treasuryBudget": 1150,
                        "teamRaces": [3001, 3002],
                        "inducements": [],
                        "improvementPacks": [
                            {"id": 20, "name": "Standard", "order": 1, "options": []},
                            {
                                "id": 21,
                                "name": "Legends",
                                "order": 2,
                                "maxStackedPlayers": 1,
                                "options": [
                                    {
                                        "id": 30,
                                        "improvementPackType": 11,
                                        "maxQuantity": 1,
                                        "sppRepeatCost": 2.25,
                                        "sppStackCost": 3.25,
                                        "maxCtv": 1250,
                                        "allowExtraGoldForPackBudget": False,
                                        "bannedStarPlayers": [100],
                                        "megaStarPlayers": [101],
                                        "customSppStarPlayers": [{"id": 102, "sppCost": 4.5}],
                                        "bannedMercenaries": [200],
                                        "customSppMercenaries": [{"id": 201, "sppCost": 6.5}],
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "id": 11,
                        "level": 2,
                        "teamRaces": [],
                        "inducements": [],
                        "improvementPacks": [],
                    },
                ],
            }
        ],
    }


def test_normalizes_multiple_legal_choices_and_star_rows(tmp_path: Path) -> None:
    coverage, cache = tmp_path / "coverage.json", tmp_path / "cache"
    cache.mkdir()
    _coverage(coverage, "event", "missing")
    (cache / "event.json").write_text(json.dumps(_event()), encoding="utf-8")
    tables, counts = normalize(coverage, cache)
    assert counts == {
        "coverage_rows": 2,
        "normalized_events": 1,
        "missing_cache": 1,
        "malformed_cache": 0,
    }
    assert [row["pack_id"] for row in tables["improvement_pack"]] == [20, 21]
    assert [row["race_id"] for row in tables["tier_race"]] == [3001, 3002]
    assert {row["rule_kind"] for row in tables["star_rule"]} == {
        "banned",
        "mega",
        "custom_spp_cost",
    }
    assert len(tables["tier"]) == 2
    option = tables["improvement_option"][0]
    assert (option["spp_repeat_cost"], option["spp_stack_cost"]) == (2.25, 3.25)
    assert option["max_ctv"] == 1250
    assert option["allow_extra_gold_for_pack_budget"] is False
    assert {row["rule_kind"] for row in tables["mercenary_rule"]} == {
        "banned",
        "custom_spp_cost",
    }
    assert tables["quarantine"][0]["reason"] == "missing_cache"


def test_writes_deterministic_privacy_safe_tables_and_quarantines_bad_json(tmp_path: Path) -> None:
    coverage, cache, output = tmp_path / "coverage.json", tmp_path / "cache", tmp_path / "out"
    cache.mkdir()
    _coverage(coverage, "event", "bad")
    (cache / "event.json").write_text(json.dumps(_event()), encoding="utf-8")
    (cache / "bad.json").write_text("not json", encoding="utf-8")
    write_output(coverage, cache, output)
    first = {path.name: path.read_bytes() for path in output.iterdir()}
    write_output(coverage, cache, output)
    assert first == {path.name: path.read_bytes() for path in output.iterdir()}
    all_text = "\n".join(path.read_text(encoding="utf-8") for path in output.iterdir())
    assert "secret@example.test" not in all_text
    assert "private" not in all_text
    with (output / "improvement_pack.csv").open(newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 2
    quarantine = (output / "quarantine.csv").read_text(encoding="utf-8")
    assert "bad.json" in quarantine and "Expecting value" in quarantine


def test_quarantines_non_list_races_or_inducements(tmp_path: Path) -> None:
    coverage, cache = tmp_path / "coverage.json", tmp_path / "cache"
    cache.mkdir()
    _coverage(coverage, "bad-races", "bad-inducements")
    for slug, field in (("bad-races", "teamRaces"), ("bad-inducements", "inducements")):
        event = _event()
        event["categories"][0]["tiers"][0][field] = "3001"
        (cache / f"{slug}.json").write_text(json.dumps(event), encoding="utf-8")
    tables, counts = normalize(coverage, cache)
    assert counts["malformed_cache"] == 2
    assert {row["reason"] for row in tables["quarantine"]} == {
        "teamRaces must be a list",
        "inducements must be a list",
    }
