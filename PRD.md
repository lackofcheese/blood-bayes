# PRD: Blood Bowl 2025 tournament outcome model ("bb-stats")

Status: draft · Owner: Peter Klimenko · Last updated: 2026-07-07

## 1. Summary

A statistical model of Blood Bowl 2025 tournament results that predicts race
performance as a function of tournament ruleset (tiering, skill budgets,
stacking rules), racial matchups, and coach strength. The primary use case is
evaluating a new or draft rulepack: given its rules, estimate which races are
favored or disfavored and what the field composition is likely to be.

**Terminology.** A *pack* is a ruleset document; an *event* is one tournament
instance. A pack maps to one or more events (reused across years or venues).
The canonical evaluation/holdout unit is the pack: all of a pack's events are
held out together, since same-pack events share rules identity (see §8).

## 2. Background

- Tournament rulesets vary widely in how they compensate weaker races (tiers,
  extra skills, stars, inducements). Tier labels are not comparable across
  tournaments, so results cannot be naively pooled.
- Match-level data exists: the NAF database records results with coach, race,
  and tournament; Tourplay hosts many tournaments with machine-readable rules
  and rosters. Division of roles: NAF is the results source; Tourplay is a
  ruleset source (and, in a later phase, a roster source). The core pipeline
  therefore needs no NAF↔Tourplay record linkage; that only arises for
  roster-level features at milestone 4 (see §10).
- Related project: `~/code/roster-builder` (separate, paid deliverable). Its
  format-overlay schema may later serve as a shared pack representation, but
  this project takes no dependency on it.

## 3. Goals

1. Predict per-race expected performance under a given ruleset, comparable
   across tournaments.
2. Given a new/draft rulepack, output favored/disfavored races with
   uncertainty.
3. Model match outcomes (W/D/L) using race, matchup, coach strength, and
   ruleset features.
4. Secondary: predict field composition (what races coaches will actually
   bring), since matchup exposure depends on it.

## 4. Non-goals

- Roster-level detail (specific skill selections) in v1. Planned as a later
  refinement; the model must not depend on it.
- Single-game prediction accuracy as a headline metric. Blood Bowl variance
  puts a low ceiling on it; the target is aggregate race performance.
- Equilibrium as *predictor*: field prediction is empirical (coach loyalty +
  observed trends + dampened best-response, FR9a) because real fields don't
  sit at Nash. Equilibrium analysis as a *diagnostic* is in scope as an
  exploratory output (FR12) — this is a stance on usage, not a ban on the
  machinery.
- Progression-event modeling (within-tournament team development). Progression
  tournaments are rare; resurrection-vs-progression stays in the treatment
  vector, but no within-tournament development term is planned.
- Live/in-tournament prediction, betting-adjacent use.

## 5. Users and use cases

| User | Use case |
|---|---|
| Tournament organizer | Test a draft pack: projected race performance before publishing; compare tiering options. |
| Coach | Assess how a pack treats their race; anticipate likely field. |
| Analyst / community | Measure which rule levers actually affect race performance across the historical record. |

### 5.1 Key targets / test cases

**Eucalyptus Bowl** — open-tournament test case. Standard individual-entry
structure, so it exercises the default pipeline (per-coach field model with
loyalty + favorability, match model, aggregate forecasts) without the squad
complications below. Regionally relevant (AU/NZ scene).

**EuroBowl** — squad-event test case, explicitly in scope as a primary target
and validation case, with two caveats acknowledged up front:

- **Different structure.** It is a squad event: captains allocate races across
  a national team (~8 coaches), typically under no-duplicate-race constraints.
  Race selection is a constrained squad-level assignment, not independent
  per-coach choice, so it needs its own field-model variant (or exclusion from
  the individual-choice model initially).
- **Unusually competitive.** Nations field their strongest coaches, and race
  allocation is deliberate. Observed dynamic (to be verified in data): elf
  teams (Elven Union, Dark Elf, High Elf) are treated as must-picks, which in
  turn inflates picks of natural elf-predators (e.g. Humans) beyond their
  isolated pack strength, and other lists are built around that meta.

This makes EuroBowl the cleanest validation data for counter-pick and
meta-adaptation mechanisms (strategic reasoning is least diluted by coach
loyalty there), while being unrepresentative of typical open-tournament
fields — so it serves as a test case, not as calibration data for the loyalty
model. Eucalyptus Bowl is the complementary case: representative of the open
tournaments the model will mostly be queried on.

## 6. Key design decision: treatment vectors, not tier labels

Rulepacks are normalized into a **per-race treatment vector**: the concrete
resources a pack grants each race. Candidate features:

- effective gold budget — not a continuous linear feature: budget effects
  are step-like (crossing a threshold unlocks a roster configuration for a
  specific race — the Elven Union anchor in §9a is the motivating case),
  and tournament TVs are quantized in practice, so budget enters as a
  monotone discrete effect. Gate stage (~20 packs): monotone step
  increments over the observed distinct TVs, with per-race deviations
  hierarchically shrunk toward the global pattern; hand-authored per-race
  breakpoint tables (deterministic roster math) serve both as priors for
  the per-race steps and as the query-time rule for placing a step within
  a coarse interval when evaluating a draft pack at an unobserved TV.
  Full-data stage (post-milestone-3 corpus): the fine level becomes
  latent — 10k cells nested in 50k buckets, monotone, children shrunk
  toward parents — gated on TV-cell occupancy, with posterior drift from
  the roster-math priors reported as a diagnostic (milestone 4).
  Specification in TECHNICAL.md T4.3.
- number of primary / secondary skills grantable
- skill stacking limits (incl. specific bans, e.g. Claw + Mighty Blow)
- star player access
- inducement access (e.g. discounted Master Chef)
- games count, resurrection vs. progression
- tournament scoring system (win/draw points, TD/CAS bonus points) —
  pack-global rather than per-race; enters the model per FR8c

This is the comparability layer that lets one model train on all tournaments
and generalize to unseen packs.

## 7. Functional requirements

### 7.1 Data ingestion
- FR1: Ingest NAF match records (coach, race, tournament, result) into a
  match-level table.
- FR2: Ingest Tourplay tournament results and structured ruleset data.
- FR3: **BB2025-only is the primary plan; BB2020 pooling is the fallback** if
  BB2025 volume proves insufficient — decided with actual match counts at
  milestone 1. If pooling is needed: the 2020→2025 change is per-race
  (rosters rewritten; some races exist in only one edition), so a single
  scalar era offset is insufficient. Design: pooled model with hierarchical
  race×era offsets — BB2020 effectively informs the prior for BB2025 race
  baselines, with per-race deviations where the roster changed materially.
  Era-dependence is keyed per race as *roster version* (see FR8a), not as
  global sub-eras; a global era covariate carries only environment-wide
  changes. Sensitivity check: refit with BB2020 downweighted; if conclusions
  shift, weaken pooling. Races absent in an era are simply structurally
  missing, not zero-coded.

### 7.2 Pack parsing
- FR4: Represent any pack as a per-race treatment vector (schema TBD,
  versioned).
- FR5: Manual annotation path (v1): hand-authored treatment vectors for ~20
  packs.
- FR6: Automated path (later): Tourplay importer; LLM extraction for PDF packs
  with (a) strict output schema, (b) verbatim quoted evidence per field,
  (c) deterministic validation/lint pass, (d) explicit `unclear` markers
  routed to human review — never guessed values.

### 7.3 Model
- FR7: Ordinal W/D/L outcome model (draws are frequent; do not binarize).
  TD/CAS margin modeling is a later-phase goal — margins would sharpen
  coach and matchup identification from thin data. NAF match records may
  include per-match TD/CAS counts (to be confirmed via the data request,
  §10); ingestion carries these columns from day one where present, but the
  v1 model remains ordinal W/D/L regardless.
- FR8: Components: race baseline; matchup structure (descriptor-based first,
  optional learned low-rank residual later — see FR8a); coach rating fit
  from match history (see FR8b); coach×race familiarity; race ×
  treatment-vector interactions with hierarchical pooling.
- FR8a: Matchup descriptors are hand-authored continuous race attributes in
  v1 (e.g. armour profile, agility/mobility profile, strength access,
  stunty flag, and a tempo-control/strategic-flexibility descriptor — the
  ability to manufacture a late scoring chance and trade draw probability
  for win-at-risk-of-loss; correlated with agility but distinct, e.g. some
  bash teams with reliable ball retrieval have more late-game agency than
  their agility suggests) — ~25 races × sparse pairings won't identify
  learned embeddings early. Descriptor rows are keyed per race × roster
  version (BB2020 launch, post-rework variants, BB2025), since rosters were
  rewritten between editions and some changed mid-era. The descriptor set is
  a small versioned schema alongside the treatment vector. A learned low-rank residual on top of the descriptor
  main effect is the planned upgrade path if data volume supports it
  (milestone 4); the two compose rather than compete. Descriptor authoring
  follows the same double-annotation discipline as pack annotation
  (independent second pass, reconciliation); values may be data-informed
  under informative priors centered on the hand-authored values — protocol
  in TECHNICAL.md (T5.5), frozen before the milestone-2 gate.
- FR8b: Coach strength — NAF publishes per-coach×race Glicko ratings
  (mu/phi, monthly rating periods, rank displayed as mu − 2.5·phi, inactive
  above phi 100, new-race mu seeded from the coach's other races). Not used
  as-is: (a) per-race mu absorbs race and pack strength, double-counting the
  effects we're trying to isolate; (b) ratings are unadjusted for ruleset;
  (c) using current ratings for past matches leaks future information. Coach
  ability is fit jointly inside the model as a latent skill. NAF Glicko
  mu/phi may serve as a time-lagged prior/initialization (rating as of
  tournament start only) and as the cold-start fallback for sparse coaches.
  Time variation: milestone 1 uses a static per-coach latent; the planned
  upgrade (milestone 4) is piecewise-constant ability per calendar year with
  a random-walk prior between years (pooled innovation variance), which
  collapses to static where a coach's data is thin. The thesis gate is
  fairly robust to this choice — baseline and challenger share the coach
  term, so drift bias largely cancels — but a sensitivity check that gate
  conclusions survive the upgrade is required.
- FR8c: Scoring-system effects. Tournament scoring (win/draw points, TD/CAS
  bonus points) enters the match model through two channels:
  (a) a global effect on draw propensity — a shift in the ordinal model's
  cutpoints (cheap, clearly identified); (b) a race-dependent response via a
  scoring-incentive × strategic-flexibility (FR8a) descriptor interaction —
  not free race×scoring terms, which ~20 packs cannot identify. Mechanism:
  races differ in their *agency* to act on scoring incentives — a team that
  controls tempo can push for a win at the risk of accepting a higher chance
  of a loss, where a grinding team locked into its game plan cannot,
  whatever the incentive. Expected signature: probability mass moves from D
  to both W and L for high-flexibility races under win-rewarding scoring;
  this doubles as a coefficient-sanity check at the gate (§9a).
- FR9: Field-composition model: per-coach discrete choice using coach race
  history (loyalty), race popularity, and pack favorability. Note: "loyalty"
  is partly material, not psychological — many coaches own miniatures for
  only one or two teams — so high observed stickiness is expected and real;
  the model doesn't need to distinguish the mechanisms, but interpretation
  of the loyalty term should not read it as pure preference. Field
  projection for a genuinely new event (no attendee history) is
  de-prioritized; primary use assumes a known or historical coach pool
  (e.g. last edition's attendees).
- FR9a (refinement): favorability input to FR9 is field-conditional —
  matchup-weighted expected per-game tournament points under the pack's
  scoring system vs. the currently projected field, not isolated race
  strength. (Points, not raw winrate: draws are frequent and packs weight
  them differently; the W/D/L model plus the annotated scoring rules give
  expected points directly.) Solved by fixed-point iteration (project field →
  recompute favorability → update picks; expected to converge in 1–2 rounds).
  Captures counter-picking (e.g. Humans rising in elf-heavy metas).
- FR9b (refinement): meta-pressure features — low-dimensional summaries of the
  projected field (dodge/agility share, bash share) fed into the match model
  to proxy field-adapted builds (e.g. Tackle/Mighty Blow density rising with
  elf share). Gated on the build-response study (see §9).
- FR9c (later): squad-event variant of the field model (EuroBowl-type):
  constrained race assignment across a squad rather than independent
  per-coach choice.

### 7.4 Outputs
- FR10: Headline output — for a given pack: per-race expected winrate vs.
  projected field, with uncertainty intervals. Staged with respect to
  pairing structure: v1 assumes random pairing against the projected field;
  a later upgrade simulates Swiss rounds (winners meet winners, so matchup
  exposure correlates with performance — material for mid-table races).
  Validation comparisons against actual per-race winrates (§8) must note
  which assumption is in effect.
- FR10a: Secondary output — race-vs-race matchup predictions at the
  individual-game level: W/D/L probabilities for any pairing under the pack,
  optionally conditioned on coach ratings (neutral-coach by default). These
  fall directly out of the match model; presented with uncertainty and
  without single-game accuracy claims (see non-goals).
- FR11: Attribution: which treatment-vector features drive a race's
  favorability under the pack.
- FR12 (exploratory): equilibrium meta diagnostic — the FR9a machinery with
  the loyalty term removed, solved by fictitious play (averaged
  best-response) rather than raw iteration: loyalty is the damping term, and
  without it best-response on an intransitive payoff matrix can cycle;
  under fictitious play cycling shows up as a mixed equilibrium instead of a
  divergence. The result is read as a mixed-strategy field distribution —
  the idealized fully-metagamed field for a pack — with a multi-start check
  for non-uniqueness. Outputs: (a) the equilibrium field itself
  (a balance target for TOs — tune rules for the attractor, not this year's
  inertia); (b) the gap between predicted and equilibrium field as an
  exploitability measure (where the value picks are). Caveats to surface in
  any UI: equilibria may be mixed and non-unique (the payoff structure is
  intransitive by construction), and the result is an equilibrium of the
  *fitted* payoff matrix, inheriting its estimation uncertainty — a
  diagnostic lens, not a prediction.
- FR13: Delivery: the eventual consumer is a lightweight web UI. Deliberately
  unspecified beyond that at this stage — this is a hobby project, not a
  commercial product; milestone-2 outputs can live in notebooks/reports.

## 8. Validation and success criteria

- Evaluation holdout unit is the **pack** (see Terminology, §1): all of a
  pack's events are held out together — never random match splits, and never
  splitting same-pack events across train/test (they share rules identity).
  Metrics: predicted vs. actual per-race winrates, log-loss, calibration.
  Exception: milestone 1's baseline yardstick predates pack annotation and
  uses whole-*event* holdout as the approximation.
- Gate (go/no-go for the pack thesis): pack × race interaction terms must
  improve held-out predictive performance over the baseline model
  (coach + race + matchup only). If they don't, stop before building the
  automated parser.
- Known confound to check: race choice correlates with coach quality.
  Identification of race effects leans on coaches who switch races; verify
  sensitivity to this.

## 9. Milestones

1. **Data foundation** — NAF + Tourplay ingestion; tidy match table; baseline
   model (coach + race + matchup) as yardstick. Includes the BB2025 volume
   count that decides whether BB2020 pooling is needed (FR3).
2. **Thesis gate** — hand-annotated treatment vectors for ~20 packs; test
   whether pack×race terms add held-out predictive power. Detailed in §9a.
3. **Automated parsing** — Tourplay importer; LLM extraction pipeline for PDF
   packs.
4. **Refinements** — gated by two cheap standalone studies on historical data:
   (a) build-response study — do Tackle/Mighty Blow counts per roster track
   the dodge-share of the actual field? gates FR9b; (b) counter-pick study —
   does Human/Dwarf pick share track elf pick share, controlling for pack
   favorability? gates FR9a. Then: roster-level features from Tourplay
   rosters (requires Tourplay↔NAF coach linkage — see §10); squad-event
   field model validated against EuroBowl (FR9c); learned low-rank matchup
   embeddings if data volume supports them (FR8a); latent fine-resolution
   budget hierarchy (§6), gated on corpus TV-cell occupancy once the
   milestone-3 corpus exists; Swiss-pairing simulation
   for aggregate forecasts (FR10); time-varying coach skill (FR8b); TD/CAS
   margin outcome modeling (FR7 stretch goal).

## 9a. Thesis gate (milestone 2) in detail

### Pack selection requirements (~20 packs; specific packs chosen later)

The concrete pack list is deferred. The criteria below are the agreed
requirements any candidate list must satisfy:

- PS1 (identifiability): the set must span the treatment levers — at minimum
  include flat/untiered, steep stunty-compensation, stack-permissive, and
  star-heavy packs, and span TV levels (the budget grid of §6 is identified
  only where packs differ). A set of near-identical packs makes pack×race
  terms unidentifiable regardless of match count.
- PS2 (natural experiments): include at least 2–3 same-event-across-years
  pairs where the pack changed between editions — field culture held
  constant, rules varied.
- PS3 (confound control): 2–3 deliberately distinct regions (natural picks:
  UK/continental Europe, AU/NZ, North America), with **several packs per
  region** spanning at least some treatment levers internally — so pack
  effects are identified *within* region and region enters as a covariate,
  rather than relying on spread alone. Event type (open vs. squad) recorded
  per pack.
- PS4 (data volume): each pack's event(s) must be linkable to NAF results;
  prefer 60+ coaches per event, with a hard floor of ~25–30 coaches for
  slots needed for regional coverage — PS3 takes precedence over PS4 where
  they conflict, since within-region identification is the more
  load-bearing requirement. Pack-level N (~20) is the binding statistical
  constraint, so no slot should be spent on tiny events.
- PS5 (annotatability): the pack document must be obtainable and complete
  (including errata); packs whose effective rules lived in forum threads
  only qualify if the record is recoverable.
- PS6 (relevance anchors): include the named test cases (§5.1) where data
  permits — Eucalyptus Bowl and EuroBowl — noting EuroBowl enters as a
  squad-event data point (PS3).
- PS7 (connectivity): the coach×pack bipartite graph must be well connected —
  every pack linked to the rest of the corpus through a reasonable number of
  shared coaches (cross-region travelers, e.g. EuroBowl and World Cup
  attendees, are the natural bridges). A pack connected by only a couple of
  coaches contributes almost nothing to coach-adjusted estimates.

### Annotation unit and schema v0
- Annotate **per pack**, not per race×pack: tier definitions (grants in
  normalized units), race→tier map, legal-race list (the choice set — some
  packs ban or restrict races; needed by the field model (FR9) and by
  coverage lints, and must be in schema v0), global rules (budget, games
  count, resurrection, stacking bans, star/inducement policy). Per-race
  treatment vectors are derived mechanically from these. ~30–60 min per
  pack.
- Mandatory `other: <verbatim>` escape field per pack for rules the schema
  can't express — this is the primary input to schema v1.
- Process: one-page annotation guide written first; packs as versioned YAML
  in-repo; 3–4 packs double-annotated (LLM second pass with quoted evidence
  acceptable) to catch systematic misreads.

### Test protocol (pre-registered before fitting)
- Baseline: coach + race + matchup + era. Challenger: + race×treatment
  interactions with hierarchical pooling.
- Evaluation: **leave-whole-pack-out** CV (matches the unseen-pack use case;
  random match splits leak pack identity).
- Pass criteria fixed in advance, with magnitude — a bare "improves" would
  let a lucky +0.001 log-loss delta pass. Final criteria (CI level,
  margins) are set after a simulation-based power rehearsal — synthetic
  data with known pack effects at realistic size (~20 packs) — and then
  frozen before fitting to annotated packs; the rehearsal is the only
  legitimate input to criteria choice, and estimated power is documented
  alongside the frozen criteria. The values below are the working
  defaults. Rule: compute per-held-out-pack
  paired log-loss differences (challenger − baseline); pass requires (a) the
  bootstrap 80% CI of the mean difference excludes zero, (b) per-race
  winrate MAE also improves, and (c) interaction coefficient signs are sane
  (e.g. stunty performance rises with skill-grant generosity; under
  win-rewarding scoring, high-flexibility races shift probability mass from
  D to both W and L — the FR8c signature). Sign checks are operationalized
  as posterior-probability thresholds fixed in `eval/GATE.md` (e.g.
  P(correct sign) ≥ 0.9), not posterior-mean signs. The FR8c λ check is
  binding only if the power rehearsal shows λ is identified at N≈20 packs —
  T5.5 expects the prior to dominate there — otherwise it is reported as
  advisory and the binding sign check is stunty × generosity alone. With
  N≈20 packs this is deliberately a lenient-but-nonzero bar; the point is
  fixing it before fitting so a marginal result can't be argued past.
- Cheap exploratory pass to run first: rough correlations of per-race
  winrate against treatment features across the annotated packs, headlined
  by the stunty winrate vs. skill-grant generosity scatter (stunty
  treatment varies most across packs; if the thesis holds anywhere it is
  visible there). This is a sanity check and schema-v1 input, not evidence —
  with ~20 packs the correlations are noisy and confounded by region and
  field strength. Discipline: the pass is written up and committed; gate
  pass criteria still come only from the power rehearsal; known-case
  anchors drafted before the pass keep their expert-judgement status, and
  any anchor added or changed afterward is labeled data-suggested.

### Known-case anchors (expert judgement)

A short list of race × pack-treatment expectations, fixed from expert
judgement before fitting and frozen in `eval/GATE.md` alongside the
quantitative criteria. Each anchor is a directional statement: the
challenger should move the held-out prediction for the named race in the
stated direction, relative to the baseline, on packs with the stated
treatment. Anchors are advisory diagnostics reported with the gate, not
binding pass criteria — the binding bar stays quantitative (above).

Two roles: (a) face validity — a challenger that clears the quantitative
bar while moving known cases the wrong way is suspect; (b) diagnosing the
gate training-corpus choice (§10): a baseline fit on the broad corpus pulls
pack-sensitive races toward their broad-data average, and the anchors are
exactly where that distortion shows.

Confirmed anchor:

- Elven Union: weak in broad pooled data, strong under packs with specific
  enabling features — e.g. skill-stacking allowances or gold-budget
  breakpoints that unlock key roster configurations — rather than under
  generic generosity. The canonical pack-sensitive race; pinning down the
  exact features is deferred to anchor authoring at the GATE.md freeze.

Candidate anchors (owner to confirm or strike before the GATE.md freeze):

- Stunty races rise with steep compensation (overlaps the pre-test above).
- Dwarf gains less than the generic response from skill-grant generosity
  (skill-dense starting roster; diminishing returns).
- Claw + Mighty Blow stacking bans depress armour-breaking bash lists
  (Chaos Chosen, Nurgle).
- Discounted Master Chef lifts Halflings.
- Broad star-player access lifts low-tier races more than high-tier.

Pack selection must exercise the anchor conditions — this list doubles as
a concrete checklist for PS1's lever-spanning requirement (generous vs.
stingy skill budgets, stacking bans, chef discount, and star access must
all vary within the corpus).

### Interpreting a null
- N=20 packs is the binding constraint (not match count); a null is
  ambiguous between "pack effects don't matter" and "schema v0 missed the
  levers." Disambiguate via residual analysis: which packs does the baseline
  miss worst, and are those misses explainable by un-encoded rules? A failed
  gate still yields the annotated corpus, the baseline model, and schema v1
  requirements.

## 10. Risks and open questions

- BB2025 sample size: measured at milestone 1; determines whether the BB2020
  pooling fallback (FR3) is invoked, and if so with what era-adjustment
  structure.
- Treatment-vector schema completeness: which rule levers matter enough to
  encode? (Resolved empirically at milestone 2.)
- NAF data access: expected via NAF contacts (format TBD). The data request
  should explicitly ask for: per-match TD/CAS counts (see FR7), coach NAF
  numbers (not names only), tournament metadata, and whether historical
  monthly Glicko snapshots exist. Contingency: if no snapshot history is
  available, the FR8b Glicko prior is dropped in favor of pure hierarchical
  pooling — never approximated with current ratings (leakage). Tourplay
  likely requires scraping — check ToS and rate limits before building the
  importer.
- Tourplay↔NAF linkage: not needed for the core pipeline (NAF = results,
  Tourplay = rulesets, per §2). It resurfaces at milestone 4, where
  roster-level features require joining Tourplay rosters to NAF match
  records per coach; most Tourplay accounts carry a usable join key.
- Gate training corpus: the challenger can only be fit on matches whose
  pack is annotated, so the gate comparison must decide between (a) fitting
  baseline and challenger both on the ~20 annotated packs' matches (clean
  pairing, weaker coach identification than the full corpus) or (b) fitting
  both on the full corpus with treatment terms active only where annotated
  (needs an imputation convention for unannotated packs). Either way the
  two models must share a corpus — comparing an all-data baseline against
  an annotated-only challenger would confound the pack×race delta. Decided
  before `eval/GATE.md` is committed; the power rehearsal must simulate the
  chosen corpus, and the known-case anchors (§9a) are the sensitivity
  diagnostic.
- Matchup sparsity: rare race pairs may not support even low-rank structure;
  fall back to descriptor-based interactions.
- Coach rating cold-start for new coaches (mitigation: hierarchical prior;
  NAF Glicko as fallback where available, per FR8b).
- EuroBowl generalization: its field is elite and squad-constrained; models
  validated there may not transfer to open tournaments, and vice versa. Keep
  event type (open vs. squad) as an explicit covariate/segment.
