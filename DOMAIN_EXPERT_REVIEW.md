# Domain-expert working brief: decisions still worth expert time

Status: focused review before treatment schema v0, the power rehearsal, race
descriptor priors, known-case anchors, and `eval/GATE.md` are frozen.

This document deliberately excludes questions that are now sufficiently
specified, implementation detail that can be tested later, and statistical
choices that do not require Blood Bowl expertise. Git history retains the
long-form review record.

## 1. Project and decision boundary

The thesis is that tournament packs treat races differently in a way that can
be encoded as a structured per-race treatment vector and generalized to a
previously unseen pack.

The match model predicts W/D/L using:

```text
eta = coach/race strength(A) - coach/race strength(B) + matchup(A,B)
c   = positive symmetric draw half-width
```

The binding test leaves whole packs out. Baseline and challenger share coach,
race, matchup, draw, scoring, and preprocessing structure. The challenger adds
only hierarchical race×treatment responses. If that block does not materially
improve held-out prediction under pre-registered criteria, the automated pack
parser is not built.

The immediate expert task is therefore not to design the largest plausible
model. It is to prevent schema v0 and its frozen race descriptors from omitting
the few mechanisms most likely to make the gate answer the wrong question.

## 2. Settled enough to stop spending session time

Challenge these only for a specific, material Blood Bowl failure mode.

| Area | Current contract |
|---|---|
| Gate isolation | Baseline and challenger share every nuisance term; only race×treatment differs. |
| Matchup separation | Descriptor matchup term is skew-symmetric and centered over the uniformly weighted active races in the edition. |
| Coach strength | Joint zero-centered coach latent from permitted match history; no NAF Glicko input or prior; reconstruct inside each validation mask. |
| Draw baseline | Hierarchical additive race/roster-version draw propensity, initially linked to strategic flexibility, with held-out residual checks for pair-specific draw structure. |
| BB2020 | BB2025-only unless W5 volume forces the hierarchical BB2020 fallback. |
| Bonus points | V1 favorability is expected base W/D/L result points; bonus omissions are explicit; margin columns are preserved for later. |
| Pack heterogeneity | Free pack×race effects are diagnostic only: raw versus residual variance after schema v0; they cannot pass the gate or predict a new pack. |
| Validation hygiene | Fold-local preprocessing, pack holdout, cross-fitted downstream predictors, posterior uncertainty propagation, held-out residual probes. |
| Causal language | Treatment attribution is predictive, not causal. |
| Pairing | V1 aggregate output is explicitly random-pairing performance, not event winrate; Swiss is later. |

### 2.1 Coach race choice, loyalty, and hidden competence

The conceptual space is now sufficiently mapped to implement or simplify
later. Every legal race retains nonzero probability. Prior NAF history is soft
evidence about observed repertoire, not ownership or total experience. The
choice process may depend on practical access, psychological loyalty,
competitive adaptation, perceived personal fit, and pack/field favorability.
Actual coach–race competence may affect performance while beliefs about that
competence affect choice or squad assignment.

Do not attempt to identify ownership, money, borrowing, hidden online play,
learning rate, seriousness, and psychological loyalty as separate NAF-only
latents merely because they exist conceptually. Start small and pull back if
the parameters do not earn themselves.

Working artifacts:

- `PLAYER_RACE_CONCEPT_MAP.md`
- `JOINT_COACH_RACE_MODEL_SCRATCHPAD.md`
- `diagrams/player_race_process_map.svg`
- `diagrams/player_race_proxy_map.svg`

Reopen this area only if it changes the treatment gate, the frozen race
descriptor rubric, or a known-case anchor. Otherwise it belongs to later
field-model implementation and held-out comparison.

## 3. Priority 1: choose at most three mechanistic composites

An additive treatment vector can miss rules whose value is inherently joint.
At roughly 20 packs, all pairwise interactions are impossible. Schema v0 gets
at most three predeclared composites.

### Required decision

Rank no more than three mechanisms. For each selected mechanism provide:

1. the in-game causal story;
2. complementarity, substitution, or threshold behaviour;
3. the races and pack conditions where it matters most;
4. counterexamples and sign reversals;
5. a deterministic derivation from pack and roster data if possible;
6. whether a sign check is defensible; and
7. what selected pack contrast identifies it.

### Candidate mechanisms

| Candidate | Central question |
|---|---|
| Skills × stacking | Does an extra skill become materially more valuable when several skills can be placed on one key player, or does stacking merely relocate a mostly additive grant? |
| Secondary access × usable slots | Is secondary access valuable only when the pack grants enough eligible slots/points and the race has worthwhile recipients? |
| Star access × affordability | Does nominal star permission matter only when treasury and roster constraints leave a viable star build? |
| Inducement discount × remaining treasury | Is a Chef, bribe, wizard-equivalent, or other inducement discount usable only after a viable core is funded? |
| Gold × skill capacity | Does gold unlock positionals that make granted skills useful, or do gold and granted skills substitute once key starting skills are purchased? |
| Viable skilled core | Can the preceding resource interactions be represented better by one deterministic roster-derived feature: the strongest viable core with legal skill placement under the pack? |

### Pressure tests

- Gold and skills may complement below a positional threshold and substitute
  above it. Do not force one global interaction sign when the mechanism is
  piecewise.
- A stack-permissive rule is not beneficial to every race merely because it
  creates strong individual players.
- Nominal access without affordability, eligible recipients, or a viable core
  should not receive full treatment value.
- Avoid composites that simply reproduce the monotone budget breakpoint model.
- Prefer a roster calculation over an expert adjective whenever both encode
  the same mechanism.

## 4. Priority 2: define resource pressure mechanically

The treatment model needs to know not only how many resources a pack grants,
but whether a race can turn them into a viable tournament roster.

### Concepts to accept, reject, or merge

- cost of a minimally viable core;
- fraction of budget consumed by key positionals;
- reroll tax at the relevant roster version;
- starting coverage of essential skills;
- affordability of players carrying those skills;
- legal and useful recipients for granted primary/secondary skills;
- remaining treasury after the core;
- remaining skill-placement flexibility after mandatory choices;
- star/inducement opportunity cost;
- number or quality of viable roster configurations at reference budget;
- distance to the next meaningful roster breakpoint.

### Required output

For each retained descriptor specify:

```text
name
deterministic inputs
calculation or annotation rule
reference budget/pack assumptions
expected direction, if any
races that anchor low / middle / high
counterexamples
overlap with budget breakpoints or another descriptor
```

### Rejection criteria

Reject or postpone a descriptor if it is:

- primarily a subjective judgement about the optimal roster;
- pack-specific rather than stable across the target corpus;
- nearly deterministic from nominal TV alone;
- redundant with a selected composite;
- impossible to calculate without roster selections unavailable in v1; or
- unlikely to vary independently among the selected packs.

## 5. Priority 3: freeze known-case anchors and their exact conditions

Anchors are advisory face-validity checks, not binding gate criteria. They
must be written before fitting and must state the enabling pack condition, not
merely a race stereotype.

### Current candidates requiring confirmation or replacement

| Race/mechanism | Candidate directional anchor | Missing precision |
|---|---|---|
| Elven Union | Improves under specific enabling gold/stacking conditions, not generic generosity. | Which roster breakpoint, positional core, and stack pattern? |
| Stunty teams | Improve under steep compensation. | Which resources distinguish Halfling, Goblin, Ogre, and other stunty responses? |
| Dwarf | Gains less than the generic race from skill-grant generosity. | Is this starting skill coverage, limited useful recipients, TV pressure, or pack-dependent? |
| Chaos Chosen / Nurgle | Suffer when Claw+Mighty Blow stacking is banned. | Does the ban matter at realistic grant counts and recipient access in BB2025? |
| Halfling | Improves with discounted Chef access. | What budget/core conditions make the Chef actually usable? |
| Lower-tier/star-dependent races | Gain disproportionately from broad star access. | Which races, which stars, and what affordability/roster trade-off? |

### Required decision

- Confirm, rewrite, or strike every anchor.
- State the minimum pack condition that activates it.
- Give at least one counterexample.
- Name the treatment/composite column expected to carry it.
- Confirm that the proposed ~20-pack corpus contains both activating and
  non-activating conditions within useful regional contrasts.

## 6. Priority 4: freeze Blood Bowl race descriptors and rubrics

Use Blood Bowl terminology. Avoid replacing Bash and Ag with superficially
formal synonyms. Descriptor values may later be represented statistically,
but their meaning must be intelligible to coaches.

### 6.1 Style transfer

Decide between:

```text
A. one Bash <-> Ag axis + separate Stunty dimension
B. independent Bash and Ag dimensions + separate Stunty dimension
```

Independent Bash and Ag allow both-high, both-low, and hybrid teams; a single
axis is cheaper and may be sufficient. For either choice provide:

- what practical skills transfer along each dimension;
- anchor races at the extremes and middle;
- races the geometry places misleadingly;
- whether Stunty is binary, graded, or a family label rather than a dimension;
- whether unusual mechanics deserves a separate general descriptor shared by
  several races rather than a race-specific exception.

### 6.2 Team difficulty

Separate conceptually:

- **entry difficulty:** friction and expected underperformance when unfamiliar;
- **mastery ceiling:** how much expertise/talent continues to matter at high
  experience.

Decide whether v1 needs one combined rubric or two descriptors. Define the
rubric using game demands, not reputation alone: sequencing burden, positional
interdependence, recovery from failure, resource management, unusual rules,
turn-planning depth, and punishment for small mistakes. Provide anchors and
counterexamples. Explain whether Orcs are generally easy and Elves/Vampires
hard for mechanisms that generalize beyond those names.

### 6.3 Matchup and draw descriptors

Confirm or refine the small frozen descriptor set used for matchup geometry:

- Bash and Ag profile;
- armour/durability;
- movement and scoring reach;
- strength access and pitch control;
- starting skill coverage and reliability;
- Stunty/unusual mechanics;
- strategic flexibility/tempo control.

Prefer roster-derived values where possible. Reserve annotation for strategic
concepts that roster sheets do not determine.

## 7. Priority 5: determine what makes races and pairings drawish

The accepted v1 cutpoint model gives each race an additive baseline draw
tendency and links its prior mean to strategic flexibility. Free race-pair
draw effects are deferred unless held-out residuals demand them.

### Required expert review

1. Is strategic flexibility/tempo control the best upstream predictor of
   baseline decisiveness?
2. Which other stable mechanisms belong upstream rather than in the residual:
   defensive reliability, one-turn threat, recovery speed, removal pressure,
   ball security, stall control, or something else?
3. Which races should anchor high and low draw propensity at equal strength?
4. Which specific pairings are unusually drawish or decisive beyond the sum
   of each race's tendency, and what symmetric mechanism causes that?
5. Can pack treatments change decisiveness as well as latent strength—for
   example defensive skill saturation, stacking, stars, or inducements?
6. Does win-heavy scoring produce the expected mass shift from draws to both
   wins and losses for strategically flexible races, or are there important
   directional/sign exceptions?

Do not propose free pair effects merely because folklore names a matchup.
Prefer a mechanism that could become a regularized symmetric descriptor
interaction if residual evidence supports it.

## 8. Priority 6: choose residual treatment-response covariance

After explicit mechanisms and composites are encoded, decide what unexplained
race responses may borrow across treatment levers.

Conservative candidate:

```text
gamma[r,j] = gamma_bar[j] + tau[j] * epsilon[r,j]
epsilon[r,j] ~ Normal(0,1)
```

This gives each lever its own between-race scale but assumes diagonal residual
covariance.

### Required decision

- Is any residual cross-lever response relationship strong enough to state
  before seeing data?
- Is that relationship better represented by a descriptor-informed mean or a
  mechanistic composite than by anonymous covariance?
- After the chosen composites, is diagonal covariance materially implausible?
- Which single sensitivity belongs in the power rehearsal: strongly
  regularized LKJ, one low-rank factor, or descriptor-informed means?

Default unless expert mechanism says otherwise: encode shared mechanisms in
features/means, use diagonal residual covariance, and test one richer
sensitivity in simulation. Covariance does not represent pack-dependent
gold×skills complementarity.

## 9. Priority 7: identify ways the gate could answer the wrong question

For each path below, say whether it is negligible, diagnostic-only, a required
sensitivity, or a reason to alter the gate design.

### Coach and race selection

- Hidden league/online specialists first appear on NAF with a race when a pack
  favours it.
- Strong coaches self-select into favoured or difficult races.
- Squad captains assign strong coaches deliberately to strategically important
  races.
- Loyalty/access/history influence accumulated competence and current choice.
- Outcomes exist only for selected races; unchosen competence is
  counterfactual, not missing at random.

### Event and attendance selection

- Pack appeal, geography, prestige, time, money, and social ties alter who
  attends.
- Pack rules change the coach pool as well as race choices within that pool.
- EuroBowl/squad fields are generated by constrained assignment, not ordinary
  individual choice.

### Pack-design endogeneity

- Organisers choose tiers/resources in response to previous race performance,
  local meta, organiser goals, expected attendance, or desired field shape.
- Region, event culture, pack design, and coach quality may move together.
- Same-event-across-year changes help but do not make arbitrary feature
  attribution causal.

### Unobserved mediators and tournament mechanics

- Pack → enabled build → matchup performance is partly hidden in v1.
- Aggregate choices create the realised field; anticipated field and realised
  pairing are not the same object.
- Swiss standings select later opponents based on earlier performance.
- Progression, injuries, and SPP alter later-round roster state where relevant.
- Bonus-heavy scoring may change behaviour even though v1 expected points omit
  bonus awards.

### Existing defences to assess

- several contrasting packs within each region;
- same-event-across-year natural contrasts;
- coach×pack connectivity and race-switcher counts;
- pack-level holdout and shared-corpus baseline/challenger comparison;
- no-history/log-history/bucketed-history sensitivities;
- established-history-only and first-observed-use diagnostics;
- squad/open segmentation;
- held-out build/matchup/draw residual probes;
- diagnostic raw/residual pack×race heterogeneity.

## 10. Priority 8: scoring, bonus-heavy packs, and regional play

### 10.1 Scoring-incentive feature

The exact pack scoring-incentive definition is still open. Advise how to map:

- 2/1/0 versus 3/1/0 and other W/D/L values;
- the relative cost of accepting a draw;
- TD/CAS or threshold bonuses as behavioural incentives;
- large-win or margin incentives;
- incentives that change late-round strategy rather than ordinary match play.

The feature may describe incentives without calculating expected bonus awards.
Flag scoring systems that cannot defensibly be compressed to one scalar.

### 10.2 Base-result-only usefulness

For which bonus-heavy packs is expected base W/D/L points still a useful
favorability measure? When would omission of bonus awards make the field model
or headline forecast misleading enough to suppress or downgrade it?

### 10.3 Region and event type

Identify any mechanism strong enough to require a predeclared channel beyond
within-region pack contrasts and stratified diagnostics:

- region-specific race performance;
- region-specific draw/tempo behaviour;
- different response to scoring incentives;
- different roster/build preparation;
- open versus squad selection and assignment.

A global region/event term cannot enter match advantage because both sides
share it. A proposed channel must say whether it acts through race interaction,
draw cutpoints, field choice, build mediation, or validation stratification.

## 11. Statistical decisions that do not need domain-session time

Record relevant intuitions, but do not spend scarce expert time resolving:

- annotated-only versus broader shared gate training corpus;
- exact CI level and improvement margins after the power rehearsal;
- simulation-calibrated practical heterogeneity threshold `epsilon`;
- static versus time-varying coach ability implementation;
- exact shrinkage hyperpriors;
- NUTS/SVI engineering;
- whether Graphviz arrows are pretty.

These remain important, but their decisions come from estimands, simulation,
data volume, diagnostics, and implementation constraints.

## 12. Requested expert output

Return the following, preferably as direct edits or a compact decision table:

1. Ranked mechanistic composites, maximum three, with derivation rules.
2. Accepted/rejected resource-pressure descriptors with annotation formulas.
3. Final known-case anchors and exact activating pack conditions.
4. Bash/Ag/Stunty, entry-difficulty, mastery, flexibility, matchup, and draw
   rubrics with anchor races and counterexamples.
5. Recommendation for residual `Sigma_gamma` after those mechanisms.
6. Gate confounding paths requiring design changes or sensitivities.
7. Scoring-incentive guidance and packs where base-result-only output is not
   credible.
8. Any settled decision in §2 that must be reversed for a concrete Blood Bowl
   reason.

For every proposed addition, distinguish:

```text
belongs in schema/descriptor v0 before the gate
belongs only in the power rehearsal or a sensitivity
belongs in held-out diagnostics
belongs after the gate
conceptually real but not identifiable with planned data
```
