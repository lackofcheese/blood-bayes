from bb_stats.contracts import COACH_FIELDS, MATCH_FIELDS, PACK_SOURCE_LINK_FIELDS


def test_derived_contracts_do_not_expose_direct_identity_fields() -> None:
    forbidden = {"name", "email", "address", "postcode", "zip", "contact"}
    assert forbidden.isdisjoint(COACH_FIELDS)
    assert forbidden.isdisjoint(MATCH_FIELDS)


def test_match_contract_has_both_sides() -> None:
    assert "home_coach_id" in MATCH_FIELDS
    assert "away_coach_id" in MATCH_FIELDS
    assert "home_result" in MATCH_FIELDS
    assert "away_result" in MATCH_FIELDS


def test_pack_source_links_keep_event_and_pack_identity_separate() -> None:
    assert "event_id" in PACK_SOURCE_LINK_FIELDS
    assert "pack_id" in PACK_SOURCE_LINK_FIELDS
    assert "review_status" in PACK_SOURCE_LINK_FIELDS
    assert "evidence" in PACK_SOURCE_LINK_FIELDS
