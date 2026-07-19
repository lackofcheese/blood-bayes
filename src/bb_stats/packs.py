"""Versioned, source-independent tournament-pack annotations.

Schema v0 separates source-faithful pack facts from their evidence and review state.
Imports are allowed to create drafts, but only a completed human review can make an
annotation model-ready.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

ID_PATTERN = r"^[a-z0-9][a-z0-9_-]*$"
SHA256_PATTERN = r"^[a-f0-9]{64}$"
COMMIT_PATTERN = r"^[a-f0-9]{7,40}$"

BB2025_RACE_IDS = frozenset(
    {
        "amazon",
        "black_orc",
        "bretonnian",
        "chaos_chosen",
        "chaos_dwarf",
        "chaos_renegades",
        "dark_elf",
        "dwarf",
        "elven_union",
        "gnome",
        "goblin",
        "halfling",
        "high_elf",
        "human",
        "imperial_nobility",
        "khorne",
        "lizardmen",
        "necromantic_horror",
        "norse",
        "nurgle",
        "ogre",
        "old_world_alliance",
        "orc",
        "shambling_undead",
        "skaven",
        "slann",
        "snotling",
        "tomb_kings",
        "underworld_denizens",
        "vampire",
        "wood_elf",
    }
)


class StrictModel(BaseModel):
    """Base model that makes annotation typos fail loudly."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SourceKind(StrEnum):
    ORGANIZER_DOCUMENT = "organizer_document"
    ORGANIZER_AMENDMENT = "organizer_amendment"
    ROSTER_BUILDER_MANIFEST = "roster_builder_manifest"
    ROSTER_BUILDER_FORMAT = "roster_builder_format"
    TOURPLAY_OBSERVATION = "tourplay_observation"
    OTHER = "other"


class SourceAuthority(StrEnum):
    NORMATIVE = "normative"
    AMENDMENT = "amendment"
    DERIVED_TRANSCRIPTION = "derived_transcription"
    NON_NORMATIVE_OBSERVATION = "non_normative_observation"


class ExtractionMethod(StrEnum):
    MANUAL = "manual"
    ROSTER_BUILDER_IMPORT = "roster_builder_import"
    TOURPLAY_IMPORT = "tourplay_import"
    LLM_PDF = "llm_pdf"


class ReviewStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    UNCLEAR = "unclear"


class AnnotationStatus(StrEnum):
    DRAFT = "draft"
    MODEL_READY = "model_ready"


class CoverageStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


class SourceArtifact(StrictModel):
    source_id: str = Field(pattern=ID_PATTERN)
    kind: SourceKind
    authority: SourceAuthority
    sha256: str = Field(pattern=SHA256_PATTERN)
    url: str | None = None
    version: str | None = None
    retrieved_on: date | None = None
    repository: str | None = None
    repository_commit: str | None = Field(default=None, pattern=COMMIT_PATTERN)
    artifact_path: str | None = None
    derived_from: list[str] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_source_boundary(self) -> Self:
        allowed_kinds = {
            SourceAuthority.NORMATIVE: {SourceKind.ORGANIZER_DOCUMENT},
            SourceAuthority.AMENDMENT: {SourceKind.ORGANIZER_AMENDMENT},
            SourceAuthority.DERIVED_TRANSCRIPTION: {
                SourceKind.ROSTER_BUILDER_MANIFEST,
                SourceKind.ROSTER_BUILDER_FORMAT,
                SourceKind.OTHER,
            },
            SourceAuthority.NON_NORMATIVE_OBSERVATION: {
                SourceKind.TOURPLAY_OBSERVATION,
                SourceKind.OTHER,
            },
        }
        if self.kind not in allowed_kinds[self.authority]:
            raise ValueError(
                f"source kind {self.kind.value} is incompatible with {self.authority.value}"
            )
        if self.authority in {SourceAuthority.NORMATIVE, SourceAuthority.AMENDMENT} and (
            not self.url or not self.version or not self.retrieved_on
        ):
            raise ValueError("normative sources and amendments require URL, version, and date")
        if self.url and not self.url.startswith("https://"):
            raise ValueError("source URLs must use HTTPS")
        if self.authority is SourceAuthority.DERIVED_TRANSCRIPTION:
            if not self.derived_from:
                raise ValueError("derived transcriptions must name their upstream sources")
            if not self.repository or not self.repository_commit or not self.artifact_path:
                raise ValueError(
                    "derived transcriptions require a repository, commit, and artifact path"
                )
            artifact = PurePosixPath(self.artifact_path)
            if artifact.is_absolute() or ".." in artifact.parts:
                raise ValueError("derived artifact paths must be repository-relative")
        return self


class Evidence(StrictModel):
    evidence_id: str = Field(pattern=ID_PATTERN)
    source_id: str = Field(pattern=ID_PATTERN)
    extraction_method: ExtractionMethod
    locator: str
    quote: str | None = None
    structured_reference: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def require_evidence_content(self) -> Self:
        if not self.quote and not self.structured_reference:
            raise ValueError("evidence requires a quote or structured reference")
        return self


class FieldReview(StrictModel):
    status: ReviewStatus
    evidence_ids: list[str] = Field(min_length=1)
    reviewer: str | None = None
    reviewed_on: date | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def require_human_review_metadata(self) -> Self:
        if self.status is ReviewStatus.UNREVIEWED:
            if self.reviewer or self.reviewed_on:
                raise ValueError("unreviewed fields cannot name a reviewer or review date")
            return self
        if not self.reviewer or not self.reviewed_on:
            raise ValueError(f"{self.status.value} fields require reviewer and review date")
        if self.status in {ReviewStatus.DISPUTED, ReviewStatus.UNCLEAR} and not self.reason:
            raise ValueError(f"{self.status.value} fields require a reason")
        return self


class ClauseCoverage(StrictModel):
    status: CoverageStatus
    normative_source_id: str = Field(pattern=ID_PATTERN)
    reviewer: str | None = None
    reviewed_on: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def require_completed_review_metadata(self) -> Self:
        if self.status is CoverageStatus.COMPLETE and (not self.reviewer or not self.reviewed_on):
            raise ValueError("complete clause coverage requires reviewer and review date")
        if self.status is CoverageStatus.IN_PROGRESS and (
            not self.reviewer or self.reviewed_on is not None
        ):
            raise ValueError(
                "in-progress clause coverage requires a reviewer but no completion date"
            )
        if self.status is CoverageStatus.NOT_STARTED and (self.reviewer or self.reviewed_on):
            raise ValueError("not-started clause coverage cannot name review metadata")
        return self


class ResourceUnit(StrEnum):
    GOLD = "gold"
    SPP = "spp"
    SKILL_POINTS = "skill_points"
    SELECTIONS = "selections"


class SkillFundingMode(StrEnum):
    NONE = "none"
    SHARED_TEAM_GOLD = "shared_team_gold"
    SEPARATE_BUDGET = "separate_budget"
    PACKAGE_BUDGET = "package_budget"
    POINT_BUDGET = "point_budget"


class SkillAccess(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    CHARACTERISTIC = "characteristic"


class ProgressionMode(StrEnum):
    RESURRECTION = "resurrection"
    PROGRESSION = "progression"
    MIXED = "mixed"


class EventType(StrEnum):
    OPEN = "open"
    SQUAD = "squad"
    TEAM = "team"
    OTHER = "other"


class ScoringLevel(StrEnum):
    INDIVIDUAL = "individual"
    SQUAD = "squad"
    BOTH = "both"


class Policy(StrEnum):
    BANNED = "banned"
    RESTRICTED = "restricted"
    ALLOWED = "allowed"


class FlowingFunds(StrictModel):
    amount: int = Field(ge=0)
    step: int = Field(gt=0)
    destinations: list[Literal["team_gold", "skill_funding"]] = Field(min_length=1)


class SkillFunding(StrictModel):
    mode: SkillFundingMode
    unit: ResourceUnit
    amount: int | None = Field(default=None, ge=0)
    flowing_funds: FlowingFunds | None = None

    @model_validator(mode="after")
    def validate_amount(self) -> Self:
        needs_amount = self.mode in {
            SkillFundingMode.SEPARATE_BUDGET,
            SkillFundingMode.PACKAGE_BUDGET,
            SkillFundingMode.POINT_BUDGET,
        }
        if needs_amount and self.amount is None:
            raise ValueError(f"{self.mode.value} requires an amount")
        if (
            self.mode in {SkillFundingMode.NONE, SkillFundingMode.SHARED_TEAM_GOLD}
            and self.amount is not None
        ):
            raise ValueError(f"{self.mode.value} cannot declare a separate amount")
        return self


class ImprovementSlot(StrictModel):
    access: SkillAccess
    elite: bool = False


class ImprovementPackage(StrictModel):
    package_id: str = Field(pattern=ID_PATTERN)
    cost: int = Field(ge=0)
    cost_unit: ResourceUnit
    cost_resource: Literal["team_gold", "skill_funding"]
    slots: list[ImprovementSlot] = Field(min_length=1, max_length=2)


class SkillRules(StrictModel):
    primary_cost: int | None = Field(default=None, ge=0)
    secondary_cost: int | None = Field(default=None, ge=0)
    elite_primary_cost: int | None = Field(default=None, ge=0)
    elite_secondary_cost: int | None = Field(default=None, ge=0)
    elite_skills: list[str] = Field(default_factory=list)
    packages: list[ImprovementPackage] = Field(default_factory=list)
    max_packages_per_player: int | None = Field(default=None, ge=0)
    max_added_skills_per_player: int | None = Field(default=None, ge=0)
    secondary_skill_cap: int | None = Field(default=None, ge=0)
    stacked_player_cap: int | None = Field(default=None, ge=0)
    per_skill_caps: dict[str, int] = Field(default_factory=dict)
    secondary_allowed: bool | None = None
    characteristic_improvements_allowed: bool | None = None
    random_skills_allowed: bool | None = None

    @model_validator(mode="after")
    def validate_skill_rules(self) -> Self:
        package_ids = [package.package_id for package in self.packages]
        if len(package_ids) != len(set(package_ids)):
            raise ValueError("improvement package IDs must be unique")
        if any(limit < 0 for limit in self.per_skill_caps.values()):
            raise ValueError("per-skill caps must be non-negative")
        return self


class StarClassRule(StrictModel):
    class_id: str = Field(pattern=ID_PATTERN)
    minimum: int = Field(default=0, ge=0)
    maximum: int = Field(ge=0)
    star_ids: list[str] = Field(default_factory=list)
    fee: int | None = Field(default=None, ge=0)
    fee_unit: ResourceUnit | None = None
    fee_resource: Literal["team_gold", "skill_funding"] | None = None

    @model_validator(mode="after")
    def validate_class_rule(self) -> Self:
        if self.minimum > self.maximum:
            raise ValueError("star class minimum cannot exceed maximum")
        fee_fields = (self.fee, self.fee_unit, self.fee_resource)
        if any(value is None for value in fee_fields) != all(
            value is None for value in fee_fields
        ):
            raise ValueError("star class fee, unit, and resource must be declared together")
        return self


class StarRules(StrictModel):
    policy: Policy
    max_count: int | None = Field(default=None, ge=0)
    classes: list[StarClassRule] = Field(default_factory=list)
    banned_star_ids: list[str] = Field(default_factory=list)
    unavailable_star_ids: list[str] = Field(default_factory=list)
    advancement_tags_banned_when_used: list[str] = Field(default_factory=list)
    combination_notes: list[str] = Field(default_factory=list)


class InducementOverride(StrictModel):
    inducement_id: str
    cost: int | None = Field(default=None, ge=0)
    max_count: int | None = Field(default=None, ge=0)
    eligible_races: list[str] = Field(default_factory=list)
    notes: str | None = None


class InducementRules(StrictModel):
    policy: Policy
    allowed_ids: list[str] = Field(default_factory=list)
    banned_ids: list[str] = Field(default_factory=list)
    overrides: list[InducementOverride] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class TreatmentGroup(StrictModel):
    label: str
    team_gold: int | None = Field(default=None, ge=0)
    skill_funding: SkillFunding
    skill_rules: SkillRules
    stars: StarRules
    inducements: InducementRules


class ScoringBonus(StrictModel):
    bonus_id: str = Field(pattern=ID_PATTERN)
    points: float
    condition: str
    cap: float | None = Field(default=None, ge=0)


class ScoringRules(StrictModel):
    win_points: float
    draw_points: float
    loss_points: float
    bonuses: list[ScoringBonus] = Field(default_factory=list)
    tiebreakers: list[str] = Field(default_factory=list)


class EventStructure(StrictModel):
    event_type: EventType
    squad_size: int | None = Field(default=None, ge=2)
    duplicate_races_allowed: bool | None = None
    duplicate_stars_allowed: bool | None = None
    scoring_level: ScoringLevel | None = None
    matchup_constraints: list[str] = Field(default_factory=list)


class GlobalRules(StrictModel):
    games: int | None = Field(default=None, gt=0)
    progression: ProgressionMode | None = None
    scoring: ScoringRules | None = None
    event_structure: EventStructure | None = None


class RuleMateriality(StrEnum):
    MODELLED = "modelled"
    NOT_MODELLED = "not_modelled"
    NEEDS_REVIEW = "needs_review"
    ADMIN_ONLY = "admin_only"


class OtherRule(StrictModel):
    rule_id: str = Field(pattern=ID_PATTERN)
    summary: str
    source_clause_id: str | None = None
    materiality: RuleMateriality


class PackAnnotation(StrictModel):
    schema_version: Literal[0]
    annotation_status: AnnotationStatus
    pack_id: str = Field(pattern=ID_PATTERN)
    name: str
    rules_edition: Literal["BB2025"]
    sources: list[SourceArtifact] = Field(min_length=1)
    evidence: list[Evidence] = Field(min_length=1)
    field_reviews: dict[str, FieldReview]
    clause_coverage: ClauseCoverage
    legal_races: list[str] = Field(min_length=1)
    race_groups: dict[str, str]
    groups: dict[str, TreatmentGroup]
    global_rules: GlobalRules
    other_rules: list[OtherRule]

    @model_validator(mode="after")
    def validate_references_and_readiness(self) -> Self:
        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source IDs must be unique")
        source_id_set = set(source_ids)
        for source in self.sources:
            missing = set(source.derived_from) - source_id_set
            if missing:
                raise ValueError(
                    f"source {source.source_id} derives from unknown sources: {missing}"
                )
            if source.source_id in source.derived_from:
                raise ValueError(f"source {source.source_id} cannot derive from itself")
        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence IDs must be unique")
        evidence_id_set = set(evidence_ids)
        evidence_by_id = {item.evidence_id: item for item in self.evidence}
        source_by_id = {source.source_id: source for source in self.sources}
        for item in self.evidence:
            if item.source_id not in source_id_set:
                raise ValueError(f"evidence {item.evidence_id} references unknown source")
        for path, review in self.field_reviews.items():
            missing = set(review.evidence_ids) - evidence_id_set
            if missing:
                raise ValueError(f"field review {path} references unknown evidence: {missing}")
            if review.status is not ReviewStatus.UNREVIEWED and not any(
                source_by_id[evidence_by_id[evidence_id].source_id].authority
                in {SourceAuthority.NORMATIVE, SourceAuthority.AMENDMENT}
                for evidence_id in review.evidence_ids
            ):
                raise ValueError(
                    f"human-reviewed field {path} requires normative or amendment evidence"
                )
        if self.clause_coverage.normative_source_id not in source_id_set:
            raise ValueError("clause coverage references unknown normative source")
        if (
            source_by_id[self.clause_coverage.normative_source_id].authority
            is not SourceAuthority.NORMATIVE
        ):
            raise ValueError("clause coverage source must be normative")
        if len(self.legal_races) != len(set(self.legal_races)):
            raise ValueError("legal races must be unique")
        legal_race_set = set(self.legal_races)
        if set(self.race_groups) != legal_race_set:
            missing = legal_race_set - set(self.race_groups)
            extra = set(self.race_groups) - legal_race_set
            raise ValueError(f"race-group coverage mismatch; missing={missing}, extra={extra}")
        unknown_groups = set(self.race_groups.values()) - set(self.groups)
        if unknown_groups:
            raise ValueError(f"race mappings reference unknown groups: {unknown_groups}")
        unused_groups = set(self.groups) - set(self.race_groups.values())
        if unused_groups:
            raise ValueError(f"treatment groups are unused: {unused_groups}")
        if self.annotation_status is AnnotationStatus.MODEL_READY:
            if self.clause_coverage.status is not CoverageStatus.COMPLETE:
                raise ValueError("model-ready packs require complete clause coverage")
            for path in required_review_paths(self):
                review = self.field_reviews.get(path)
                if review is None or review.status is not ReviewStatus.CONFIRMED:
                    raise ValueError(f"model-ready pack field is not confirmed: {path}")
            if (
                self.global_rules.games is None
                or self.global_rules.progression is None
                or self.global_rules.scoring is None
                or self.global_rules.event_structure is None
            ):
                raise ValueError("model-ready packs require complete global rules")
            if any(rule.materiality is RuleMateriality.NEEDS_REVIEW for rule in self.other_rules):
                raise ValueError("model-ready packs cannot retain other rules needing review")
        return self


class EventPatch(StrictModel):
    path: str
    value: JsonValue
    review: FieldReview

    @model_validator(mode="after")
    def validate_patch_path(self) -> Self:
        roots = ("legal_races", "race_groups", "groups", "global_rules", "other_rules")
        if not any(self.path == root or self.path.startswith(f"{root}.") for root in roots):
            raise ValueError("event patch path is outside the pack schema")
        return self


class EventPackApplication(StrictModel):
    schema_version: Literal[0]
    annotation_status: AnnotationStatus
    application_id: str = Field(pattern=ID_PATTERN)
    event_id: str
    pack_id: str = Field(pattern=ID_PATTERN)
    base_pack_sha256: str = Field(pattern=SHA256_PATTERN)
    sources: list[SourceArtifact] = Field(min_length=1)
    evidence: list[Evidence] = Field(min_length=1)
    patches: list[EventPatch] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_application(self) -> Self:
        source_by_id = {source.source_id: source for source in self.sources}
        if len(source_by_id) != len(self.sources):
            raise ValueError("event-application source IDs must be unique")
        evidence_by_id = {item.evidence_id: item for item in self.evidence}
        if len(evidence_by_id) != len(self.evidence):
            raise ValueError("event-application evidence IDs must be unique")
        for item in self.evidence:
            if item.source_id not in source_by_id:
                raise ValueError(f"evidence {item.evidence_id} references unknown source")
        patch_paths = [patch.path for patch in self.patches]
        if len(patch_paths) != len(set(patch_paths)):
            raise ValueError("event-application patch paths must be unique")
        for patch in self.patches:
            missing = set(patch.review.evidence_ids) - set(evidence_by_id)
            if missing:
                raise ValueError(f"event patch {patch.path} references unknown evidence: {missing}")
            if patch.review.status is not ReviewStatus.UNREVIEWED and not any(
                source_by_id[evidence_by_id[evidence_id].source_id].authority
                in {SourceAuthority.NORMATIVE, SourceAuthority.AMENDMENT}
                for evidence_id in patch.review.evidence_ids
            ):
                raise ValueError(
                    f"human-reviewed event patch {patch.path} requires normative evidence"
                )
        if self.annotation_status is AnnotationStatus.MODEL_READY:
            if not any(
                source.authority is SourceAuthority.AMENDMENT for source in self.sources
            ):
                raise ValueError("model-ready event patches require an organizer amendment")
            for patch in self.patches:
                if patch.review.status is not ReviewStatus.CONFIRMED:
                    raise ValueError(f"model-ready event patch is not confirmed: {patch.path}")
        return self


def required_review_paths(pack: PackAnnotation) -> tuple[str, ...]:
    """Return the block-level facts that must be human-confirmed for modeling."""

    return (
        "legal_races",
        "race_groups",
        *(f"groups.{group_id}" for group_id in sorted(pack.groups)),
        "global_rules.games",
        "global_rules.progression",
        "global_rules.scoring",
        "global_rules.event_structure",
        "other_rules",
    )


@dataclass(frozen=True)
class PackFinding:
    level: Literal["error", "warning"]
    path: str
    message: str


def lint_pack(pack: PackAnnotation) -> list[PackFinding]:
    """Run semantic and review-readiness checks beyond Pydantic shape validation."""

    findings: list[PackFinding] = []
    unknown_races = set(pack.legal_races) - BB2025_RACE_IDS
    if unknown_races:
        findings.append(
            PackFinding("error", "legal_races", f"unknown BB2025 race IDs: {unknown_races}")
        )
    if pack.global_rules.scoring is not None:
        scoring = pack.global_rules.scoring
        if not scoring.win_points >= scoring.draw_points >= scoring.loss_points:
            findings.append(
                PackFinding(
                    "error",
                    "global_rules.scoring",
                    "base result points must satisfy win >= draw >= loss",
                )
            )
    for path in required_review_paths(pack):
        review = pack.field_reviews.get(path)
        if review is None:
            findings.append(PackFinding("warning", path, "required field has no review record"))
        elif review.status is not ReviewStatus.CONFIRMED:
            findings.append(
                PackFinding("warning", path, f"required field is {review.status.value}")
            )
    known_paths = set(required_review_paths(pack))
    for path in sorted(set(pack.field_reviews) - known_paths):
        findings.append(PackFinding("warning", path, "review path is not a schema-v0 block"))
    return findings


def load_pack(path: str | Path) -> PackAnnotation:
    """Load and strictly validate a pack annotation from YAML."""

    source = Path(path)
    with source.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return PackAnnotation.model_validate(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate bb-stats pack schema v0 YAML")
    parser.add_argument("packs", nargs="+", type=Path)
    args = parser.parse_args(argv)
    has_errors = False
    for path in args.packs:
        try:
            pack = load_pack(path)
        except (OSError, yaml.YAMLError, ValueError) as exc:
            print(f"ERROR {path}: {exc}")
            has_errors = True
            continue
        findings = lint_pack(pack)
        print(f"{path}: {pack.pack_id} ({pack.annotation_status.value})")
        for finding in findings:
            print(f"  {finding.level.upper()} {finding.path}: {finding.message}")
            has_errors |= finding.level == "error"
    return int(has_errors)


if __name__ == "__main__":
    raise SystemExit(main())
