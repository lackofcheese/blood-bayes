from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

import pytest

from bb_stats.contracts import NAF_SOURCE_FILES
from bb_stats.ingest.naf import NAFIngestError, ingest, main  # noqa: I001

HEADERS = {
    "CoachExport.csv": ["NAF Nr", "NAF name", "Country", "Registration Date"],
    "naf_variants.csv": ["variantid", "variantname"],
    "naf_tournament_statistics_group.csv": ["id", "tournamentID"],
    "naf_game.csv": ["gameid", "tournamentid", "homecoachid", "awaycoachid", "racehome",
        "raceaway", "goalshome", "goalsaway", "badlyhurthome", "badlyhurtaway", "date",
        "dirty", "naf_variantsid"],
    "naf_race.csv": ["raceid", "name", "reroll_cost", "apoth", "race_count"],
    "naf_tournament_statistics_list.csv": ["id", "name"],
    "naf_tournament.csv": ["tournamentid", "tournamentname", "tournamentcity",
        "tournamentnation", "tournamenturl", "tournamentnotesurl", "tournamentstartdate",
        "tournamentenddate", "tournamenttype", "tournamentstyle", "tournamentscoring",
        "tournamentinformation", "tournament_squad", "naf_rulesetid", "naf_variantsid",
        "tournament_ruleset_file"],
    "naf_coachranking_variant.csv": ["coachID", "raceID", "variantID"],
    "naf_tournamentcoach.csv": ["naftournament", "nafcoach", "race"],
}


def _zip(path: Path, *, omit: str | None = None, bad_game_header: bool = False) -> None:
    rows = {
        "CoachExport.csv": [
            ["2", "Secret Name", "AU", "2020-01-02"],
            ["1", "Other", "NZ", "2019-01-01"],
        ],
        "naf_variants.csv": [["15", "BB2025"]],
        "naf_tournament_statistics_group.csv": [],
        "naf_game.csv": [
            ["11", "7", "2", "1", "3", "4", "2", "1", "5", "2", "2026-01-03", "TRUE", "15"],
            ["12", "7", "1", "2", "4", "3", "x", "1", "0", "0", "2026-01-03", "FALSE", "15"],
        ],
        "naf_race.csv": [["4", "Orc", "60000", "y", "yes"], ["3", "Elf", "50000", "n", "yes"]],
        "naf_tournament_statistics_list.csv": [],
        "naf_tournament.csv": [[
            "7", "Cup", "Brisbane", "Australia", "https://event.invalid", "notes",
            "2026-01-03", "2026-01-04", "OPEN", "Swiss", "2/1/0", "private prose",
            "0", "11", "15", "pack.pdf",
        ]],
        "naf_coachranking_variant.csv": [],
        "naf_tournamentcoach.csv": [["7", "2", "3"], ["7", "1", "4"]],
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name in NAF_SOURCE_FILES:
            if name == omit:
                continue
            headers = HEADERS[name].copy()
            if name == "naf_game.csv" and bad_game_header:
                headers.remove("gameid")
            buffer = io.StringIO(newline="")
            writer = csv.writer(buffer, delimiter=";", lineterminator="\n")
            writer.writerow(headers)
            for row in rows[name]:
                if len(row) == len(headers):
                    writer.writerow(row)
                elif not bad_game_header:
                    raise AssertionError("fixture does not match headers")
            archive.writestr(f"dump/{name}", buffer.getvalue())


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_ingest_writes_deterministic_privacy_safe_tables(tmp_path: Path) -> None:
    source, output = tmp_path / "naf.zip", tmp_path / "derived"
    _zip(source)

    manifest = ingest(source, output)

    assert [row["coach_id"] for row in _read(output / "coach.csv")] == ["2", "1"]
    assert "Secret Name" not in "".join(path.read_text() for path in output.iterdir())
    match = _read(output / "match.csv")
    assert match[0]["home_result"] == "W"
    assert match[0]["away_result"] == "L"
    assert match[0]["source_dirty"] == "TRUE"
    assert _read(output / "event.csv")[0]["has_information_text"] == "true"
    assert _read(output / "quarantine.csv") == [
        {"table": "match", "row_id": "12", "reason": "invalid touchdown score"}
    ]
    assert manifest["outputs"]["match"] == 1
    assert json.loads((output / "reconciliation.json").read_text())["rows_quarantined"] == 1

    before = {path.name: path.read_bytes() for path in output.iterdir()}
    ingest(source, output)
    assert before == {path.name: path.read_bytes() for path in output.iterdir()}


def test_rejects_missing_member(tmp_path: Path) -> None:
    source = tmp_path / "naf.zip"
    _zip(source, omit="naf_race.csv")
    with pytest.raises(NAFIngestError, match="missing members: naf_race.csv"):
        ingest(source, tmp_path / "out")


def test_rejects_missing_required_header(tmp_path: Path) -> None:
    source = tmp_path / "naf.zip"
    _zip(source, bad_game_header=True)
    with pytest.raises(NAFIngestError, match="naf_game.csv missing headers: gameid"):
        ingest(source, tmp_path / "out")


def test_cli(tmp_path: Path) -> None:
    source, output = tmp_path / "naf.zip", tmp_path / "out"
    _zip(source)
    assert main([str(source), str(output)]) == 0
    assert (output / "manifest.json").is_file()
