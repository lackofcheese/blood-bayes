import csv
import json
from pathlib import Path
from zipfile import ZipFile

from bb_stats.analysis.naf_audit import audit_naf_zip, main, report_markdown


def _csv(rows):
    fields = list(rows[0])
    from io import StringIO

    out = StringIO()
    writer = csv.DictWriter(out, fields, delimiter=";", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def _archive(path: Path):
    races = [
        {"raceid": "1", "name": "Orc"},
        {"raceid": "2", "name": "Elf"},
        {"raceid": "99", "name": "Multiple Races"},
    ]
    tournaments = [
        {
            "tournamentid": "10",
            "naf_variantsid": "15",
            "tournamentnation": "AU",
            "tournamenttype": "OPEN",
        },
        {
            "tournamentid": "20",
            "naf_variantsid": "13",
            "tournamentnation": "GB",
            "tournamenttype": "OPEN",
        },
    ]
    entrants = [
        {"naftournament": "10", "nafcoach": "101", "race": "1"},
        {"naftournament": "10", "nafcoach": "102", "race": "99"},
    ]
    base = {
        "seasonid": "0",
        "trhome": "",
        "traway": "",
        "serioushome": "0",
        "seriousaway": "0",
        "killshome": "0",
        "killsaway": "0",
    }
    games = [
        base
        | {
            "gameid": "1",
            "tournamentid": "10",
            "homecoachid": "101",
            "awaycoachid": "102",
            "racehome": "1",
            "raceaway": "2",
            "goalshome": "1",
            "goalsaway": "1",
            "badlyhurthome": "0",
            "badlyhurtaway": "0",
            "date": "2025-01-01",
            "naf_variantsid": "15",
        },
        base
        | {
            "gameid": "2",
            "tournamentid": "10",
            "homecoachid": "101",
            "awaycoachid": "103",
            "racehome": "1",
            "raceaway": "1",
            "goalshome": "2",
            "goalsaway": "0",
            "badlyhurthome": "1",
            "badlyhurtaway": "0",
            "date": "2025-01-02",
            "naf_variantsid": "15",
        },
        base
        | {
            "gameid": "3",
            "tournamentid": "20",
            "homecoachid": "101",
            "awaycoachid": "2",
            "racehome": "1",
            "raceaway": "2",
            "goalshome": "0",
            "goalsaway": "0",
            "badlyhurthome": "0",
            "badlyhurtaway": "0",
            "date": "2024-01-01",
            "naf_variantsid": "13",
        },
    ]
    with ZipFile(path, "w") as zf:
        zf.writestr("dump/naf_race.csv", _csv(races))
        zf.writestr("dump/naf_tournament.csv", _csv(tournaments))
        zf.writestr("dump/naf_tournamentcoach.csv", _csv(entrants))
        zf.writestr("dump/naf_game.csv", _csv(games))


def test_audit_aggregates_variant_and_integrity(tmp_path):
    source = tmp_path / "naf.zip"
    _archive(source)
    report = audit_naf_zip(source)
    assert report["volume"] == {
        "games": 2,
        "events": 1,
        "coaches": 3,
        "races": 2,
        "date_min": "2025-01-01",
        "date_max": "2025-01-02",
    }
    assert report["outcomes"] == {"games_with_td": 2, "draws": 1, "draw_rate": 0.5}
    assert report["fields"]["cas_all_zero_games"] == 1
    assert report["integrity"]["missing_entrant_game_sides"] == 1
    assert report["integrity"]["multiple_race_wildcard_game_sides"] == 1
    assert report["integrity"]["entrant_race_mismatch_game_sides"] == 0
    history = report["history_sensitivity"]
    assert history["scopes"]["target_variant_only"]["first_observed_race_use_sides"] == 4
    assert history["scopes"]["standard_editions_13_15"]["first_observed_race_use_sides"] == 2
    assert history["first_observed_race_use_sides"] == 2
    assert "101" not in report_markdown(report)


def test_cli_writes_json_and_markdown(tmp_path):
    source = tmp_path / "naf.zip"
    _archive(source)
    output = tmp_path / "reports" / "audit"
    assert main([str(source), str(output)]) == 0
    assert json.loads(output.with_suffix(".json").read_text())["variant_id"] == 15
    assert output.with_suffix(".md").read_text().startswith("# NAF variant 15 audit")


def test_archive_requires_unique_table_names(tmp_path):
    source = tmp_path / "bad.zip"
    with ZipFile(source, "w") as zf:
        zf.writestr("a/naf_race.csv", "raceid;name\n")
        zf.writestr("b/naf_race.csv", "raceid;name\n")
    import pytest

    with pytest.raises(ValueError, match="exactly one"):
        audit_naf_zip(source)
