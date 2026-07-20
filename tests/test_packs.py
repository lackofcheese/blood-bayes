from datetime import date
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from bb_stats.packs import (
    EventPackApplication,
    FieldReview,
    PackAnnotation,
    ReviewStatus,
    lint_pack,
    load_pack,
    required_review_paths,
)

ROOT = Path(__file__).parents[1]
DRAFTS = ROOT / "packs" / "drafts"


def test_schema_v0_trials_load_strictly_and_remain_unreviewed() -> None:
    for path in sorted(DRAFTS.glob("*.yaml")):
        pack = load_pack(path)
        assert pack.schema_version == 0
        assert pack.annotation_status.value == "draft"
        assert pack.clause_coverage.status.value == "not_started"
        findings = lint_pack(pack)
        assert not [finding for finding in findings if finding.level == "error"]
        assert {finding.path for finding in findings} == set(required_review_paths(pack))
        assert all("unreviewed" in finding.message for finding in findings)


def test_eucalyptus_trial_has_exact_race_group_coverage() -> None:
    pack = load_pack(DRAFTS / "eucalyptus-bowl-2026-v0.4.yaml")
    assert len(pack.legal_races) == 31
    assert set(pack.legal_races) == set(pack.race_groups)
    assert set(pack.race_groups.values()) == {"all"}
    assert pack.groups["all"].skill_funding.mode.value == "shared_team_gold"


def test_eurobowl_trial_preserves_tiers_packages_and_tournament_gap() -> None:
    pack = load_pack(DRAFTS / "eurobowl-2026-final.yaml")
    assert len(pack.legal_races) == 31
    assert len(pack.groups) == 7
    assert pack.race_groups["ogre"] == "tier_7"
    assert len(pack.groups["tier_1"].skill_rules.packages) == 7
    assert pack.groups["tier_6"].stars.classes[1].fee == 80_000
    assert pack.groups["tier_6"].stars.classes[1].fee_resource == "skill_funding"
    assert len(pack.groups["tier_6"].stars.classes[0].star_ids) == 33
    assert pack.global_rules.event_structure is None


def test_schema_rejects_unknown_fields_and_incomplete_race_mapping() -> None:
    with (DRAFTS / "eucalyptus-bowl-2026-v0.4.yaml").open() as handle:
        raw = yaml.safe_load(handle)
    raw["typo"] = True
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PackAnnotation.model_validate(raw)

    del raw["typo"]
    del raw["race_groups"]["amazon"]
    with pytest.raises(ValidationError, match="race-group coverage mismatch"):
        PackAnnotation.model_validate(raw)


def test_non_unreviewed_status_requires_a_named_human_and_date() -> None:
    with pytest.raises(ValidationError, match="require reviewer and review date"):
        FieldReview(status=ReviewStatus.CONFIRMED, evidence_ids=["evidence"])
    confirmed = FieldReview(
        status=ReviewStatus.CONFIRMED,
        evidence_ids=["evidence"],
        reviewer="Pack reviewer",
        reviewed_on=date(2026, 7, 20),
    )
    assert confirmed.status is ReviewStatus.CONFIRMED


def test_model_ready_requires_complete_global_rules_and_every_confirmation() -> None:
    pack = load_pack(DRAFTS / "eucalyptus-bowl-2026-v0.4.yaml")
    raw = pack.model_dump(mode="json")
    raw["annotation_status"] = "model_ready"
    raw["clause_coverage"] = {
        "status": "complete",
        "normative_source_id": "eucalyptus_pdf",
        "reviewer": "Pack reviewer",
        "reviewed_on": "2026-07-20",
    }
    raw["global_rules"] = {
        "games": 6,
        "progression": "resurrection",
        "scoring": {"win_points": 3, "draw_points": 1, "loss_points": 0},
        "event_structure": {"event_type": "open", "scoring_level": "individual"},
    }
    for rule in raw["other_rules"]:
        if rule["materiality"] == "needs_review":
            rule["materiality"] = "not_modelled"
    raw["evidence"].append(
        {
            "evidence_id": "human_pdf_review",
            "source_id": "eucalyptus_pdf",
            "extraction_method": "manual",
            "locator": "whole-document review fixture",
            "quote": "Reviewed normative evidence for the test fixture.",
        }
    )
    for path in required_review_paths(pack):
        raw["field_reviews"][path] = {
            "status": "confirmed",
            "evidence_ids": [
                *raw["field_reviews"][path]["evidence_ids"],
                "human_pdf_review",
            ],
            "reviewer": "Pack reviewer",
            "reviewed_on": "2026-07-20",
        }
    ready = PackAnnotation.model_validate(raw)
    assert ready.annotation_status.value == "model_ready"

    raw["field_reviews"]["global_rules.games"]["status"] = "unclear"
    raw["field_reviews"]["global_rules.games"]["reason"] = "Source is silent."
    with pytest.raises(ValidationError, match="field is not confirmed"):
        PackAnnotation.model_validate(raw)


def test_lint_rejects_incoherent_base_scoring_order() -> None:
    pack = load_pack(DRAFTS / "eucalyptus-bowl-2026-v0.4.yaml")
    raw = pack.model_dump(mode="json")
    raw["global_rules"]["scoring"] = {
        "win_points": 1,
        "draw_points": 2,
        "loss_points": 0,
    }
    incoherent = PackAnnotation.model_validate(raw)
    errors = [finding for finding in lint_pack(incoherent) if finding.level == "error"]
    assert len(errors) == 1
    assert errors[0].path == "global_rules.scoring"


def test_lint_rejects_unknown_race_ids() -> None:
    pack = load_pack(DRAFTS / "eucalyptus-bowl-2026-v0.4.yaml")
    raw = pack.model_dump(mode="json")
    raw["legal_races"].append("invented_race")
    raw["race_groups"]["invented_race"] = "all"
    unknown = PackAnnotation.model_validate(raw)
    errors = [finding for finding in lint_pack(unknown) if finding.level == "error"]
    assert errors[0].path == "legal_races"
    assert "invented_race" in errors[0].message


def test_event_application_requires_confirmed_organizer_amendment() -> None:
    raw = {
        "schema_version": 0,
        "annotation_status": "model_ready",
        "application_id": "event_123_pack_patch",
        "event_id": "123",
        "pack_id": "example-pack",
        "base_pack_sha256": "a" * 64,
        "sources": [
            {
                "source_id": "organizer_amendment",
                "kind": "organizer_amendment",
                "authority": "amendment",
                "sha256": "b" * 64,
                "url": "https://example.test/amendment.pdf",
                "version": "final correction",
                "retrieved_on": "2026-07-20",
            }
        ],
        "evidence": [
            {
                "evidence_id": "amendment_scoring",
                "source_id": "organizer_amendment",
                "extraction_method": "manual",
                "locator": "page 1",
                "quote": "Wins score four points.",
            }
        ],
        "patches": [
            {
                "path": "global_rules.scoring.win_points",
                "value": 4,
                "review": {
                    "status": "confirmed",
                    "evidence_ids": ["amendment_scoring"],
                    "reviewer": "Pack reviewer",
                    "reviewed_on": "2026-07-20",
                },
            }
        ],
    }
    application = EventPackApplication.model_validate(raw)
    assert application.patches[0].value == 4

    raw["sources"][0]["authority"] = "non_normative_observation"
    raw["sources"][0]["kind"] = "other"
    with pytest.raises(ValidationError, match="requires normative evidence"):
        EventPackApplication.model_validate(raw)
