import csv
from pathlib import Path

from bb_stats.analysis.pack_signal import _advancement_capacity, schema_informed_feature_map


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_currency_capacity_is_bounded_by_budget_cost_and_quantity() -> None:
    pack = {"cost_type": "2", "spp": "120"}
    options = [
        {"resolved_enum_key": "Primary", "max_quantity": "999", "spp_cost": "20"},
        {"resolved_enum_key": "Primary", "max_quantity": "4", "spp_cost": "10"},
    ]
    assert _advancement_capacity(pack, options, "Primary") == 6
    assert _advancement_capacity(pack, options, "Secondary") == 0


def test_schema_informed_feature_map_preserves_legal_choice_envelope(tmp_path: Path) -> None:
    tourplay = tmp_path / "tourplay"
    resolved = tmp_path / "resolved"
    _write(
        tourplay / "tourplay_event_link.csv",
        [
            {
                "tourplay_event_id": "tp1",
                "naf_tournament_id": "100",
                "fetch_state": "cached",
                "http_status": "200",
            }
        ],
    )
    _write(
        tourplay / "tier.csv",
        [
            {
                "tourplay_event_id": "tp1",
                "category_id": "c1",
                "tier_id": "t1",
                "level": "2",
                "treasury_budget": "1100",
            },
            {
                "tourplay_event_id": "tp1",
                "category_id": "c1",
                "tier_id": "t2",
                "level": "3",
                "treasury_budget": "1150",
            },
        ],
    )
    _write(
        tourplay / "improvement_pack.csv",
        [
            {"tier_id": "t1", "pack_id": "p1", "cost_type": "2", "spp": "120"},
            {"tier_id": "t1", "pack_id": "p2", "cost_type": "0", "spp": "0"},
        ],
    )
    _write(
        resolved / "resolved_improvement_option.csv",
        [
            {
                "pack_id": "p1",
                "resolved_enum_key": "Primary",
                "max_quantity": "999",
                "spp_cost": "20",
                "max_cost": "0",
                "resolution_status": "resolved",
            },
            {
                "pack_id": "p1",
                "resolved_enum_key": "Secondary",
                "max_quantity": "3",
                "spp_cost": "40",
                "max_cost": "0",
                "resolution_status": "resolved",
            },
            {
                "pack_id": "p1",
                "resolved_enum_key": "StarPlayer",
                "max_quantity": "2",
                "spp_cost": "",
                "max_cost": "0",
                "resolution_status": "resolved",
            },
            {
                "pack_id": "p1",
                "resolved_enum_key": "ExtraGold",
                "max_quantity": "5",
                "spp_cost": "",
                "max_cost": "30",
                "resolution_status": "resolved",
            },
            {
                "pack_id": "p2",
                "resolved_enum_key": "Primary",
                "max_quantity": "8",
                "spp_cost": "",
                "max_cost": "0",
                "resolution_status": "resolved",
            },
        ],
    )
    _write(
        resolved / "resolved_tier_race.csv",
        [
            {
                "tourplay_event_id": "tp1",
                "tier_id": "t1",
                "category_id": "c1",
                "resolved_display_name": "Amazon",
                "resolution_status": "resolved",
            }
        ],
    )

    features, links = schema_informed_feature_map(tourplay, resolved)

    assert set(links) == {"100"}
    assert features[("100", "amazon")] == {
        "relative_tier": 0.5,
        "team_gold_k": 1100.0,
        "primary_capacity_max": 8.0,
        "secondary_capacity_max": 3.0,
        "star_quantity_max": 2.0,
        "extra_gold_k_max": 30.0,
    }
