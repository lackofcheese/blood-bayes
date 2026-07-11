# Review of `TECHNICAL.md` against `PRD.md`

Overall, the technical design tracks the PRD well, but there are several
substantive gaps.

## High-priority issues

### 1. The thesis gate does not isolate treatment-vector effects

The baseline is defined as coach + race + matchup, while the challenger also
adds both race×treatment terms and FR8c scoring cutpoints
([TECHNICAL.md:667](TECHNICAL.md#L667),
[TECHNICAL.md:680](TECHNICAL.md#L680)). Because gate success uses overall
log-loss improvement ([TECHNICAL.md:563](TECHNICAL.md#L563)), the global
scoring cutpoint term could make the gate pass even if the race×treatment terms
add no value—contrary to the PRD's stated criterion
([PRD.md:279](PRD.md#L279)).

**Suggestion:** Give baseline and challenger identical nuisance terms,
including the global scoring effect. Make the target treatment block the only
difference, or require a separate ablation demonstrating that it drives the
improvement.

### 2. TD/CAS bonus points cannot currently be included in expected tournament points

The PRD says favorability uses expected points under win/draw and TD/CAS bonus
scoring ([PRD.md:121](PRD.md#L121), [PRD.md:221](PRD.md#L221)). T6.2,
however, calculates expected points solely from W/D/L probabilities
([TECHNICAL.md:517](TECHNICAL.md#L517)). Without a TD/CAS model,
performance-dependent bonus points cannot simply be applied afterwards.

**Suggestion:** Either explicitly limit v1 favorability to base result points,
or add a small conditional bonus-point model before FR9a. Merely encoding bonus
structure in the scoring-incentive scalar does not calculate expected bonuses.

### 3. The static coach latent has a mathematically inconsistent time-varying prior

T5.3 defines one static `theta_i`, but its prior mean is the Glicko value “as of
the match's tournament start” ([TECHNICAL.md:317](TECHNICAL.md#L317)). A
single latent variable cannot have a different prior mean for every match.

**Suggestion:** For v1, choose one lagged snapshot per coach at a defined model
cutoff. Alternatively, make Glicko a time-varying covariate or introduce
coach-period latents. Also distinguish retrospective pack CV—which may
estimate a coach using later matches—from a genuinely prospective evaluation.

### 4. The BB2020 pooling structure required by FR3 is not specified

The PRD requires hierarchical race×era offsets, downweighting sensitivity, and
cross-edition partial pooling ([PRD.md:133](PRD.md#L133)). The technical
design currently provides only roster-version keys and defers the exact
structure ([TECHNICAL.md:97](TECHNICAL.md#L97),
[TECHNICAL.md:717](TECHNICAL.md#L717)). Independent roster-version baselines
would not let BB2020 inform BB2025 as intended.

**Suggestion:** Specify at least the structural contract now, for example
`alpha[r,v] = alpha[r] + delta[r,v]`, with hierarchical version deviations and
an explicit pooling/downweight parameter. Also clarify “sum-to-zero within each
roster-version block” ([TECHNICAL.md:295](TECHNICAL.md#L295)); a roster
version belongs to one race, so the intended contemporaneous comparison block
needs definition.

### 5. Cross-validation preprocessing risks leakage and undefined extrapolation

Treatment scaling is calculated over the annotated corpus
([TECHNICAL.md:175](TECHNICAL.md#L175)), and the budget grid uses all observed
annotated-pack TVs ([TECHNICAL.md:193](TECHNICAL.md#L193)). During
leave-pack-out CV, those must not be derived from the held-out pack. A held-out
extreme TV also has no enclosing training interval under the query rule.

**Suggestion:** Fit centering, scaling, grid pooling, and occupancy decisions
independently inside every fold. Define behavior for values below or above
training support and report an explicit out-of-distribution/support warning for
every forecast.

### 6. The field model needs cross-fitting and broader uncertainty propagation

Historical choice rows are fitted using favorability produced by the match
model ([TECHNICAL.md:495](TECHNICAL.md#L495),
[TECHNICAL.md:511](TECHNICAL.md#L511)), but the design does not require that
historical favorability be out-of-fold. If the match model used the same
event's outcomes, the field model learns from post-choice evidence. In
addition, T6.2 explicitly propagates match-model uncertainty but does not
mention field-choice coefficient uncertainty
([TECHNICAL.md:526](TECHNICAL.md#L526)).

**Suggestion:** Compute training favorability using leave-event- or
leave-pack-out match predictions. At forecast time, jointly sample match-model
and field-model posteriors. Define `choice(fav)` precisely as aggregation
across the supplied coach pool, respecting each event's legal-race set and
cold-start policy.

## Other concrete gaps

### 7. The counter-pick study is scheduled after the feature it is supposed to gate

The PRD says the counter-pick study gates FR9a
([PRD.md:296](PRD.md#L296)). Technical W20 implements FR9a before W23 runs
that study ([TECHNICAL.md:694](TECHNICAL.md#L694),
[TECHNICAL.md:702](TECHNICAL.md#L702)).

**Suggestion:** Move the counter-pick study before W20, or revise the PRD to
say it gates interpretation/adoption rather than implementation.

### 8. Region and event-type confound handling is not fully implemented

The PRD requires within-region identification, a region covariate, and explicit
open/squad segmentation ([PRD.md:324](PRD.md#L324),
[PRD.md:480](PRD.md#L480)). The technical design reinterprets region as
field-model/residual-only ([TECHNICAL.md:293](TECHNICAL.md#L293)). It is
correct that global region and event-type terms cancel from `eta`, but they
could still enter cutpoints, race interactions, or stratified evaluation.

**Suggestion:** State the exact channels and gate diagnostics used to satisfy
PS3. Otherwise the PRD's confound-control requirement is only partially
addressed.

### 9. Fictitious-play convergence is overstated

T6.3 says fictitious play's average converges to a mixed equilibrium
([TECHNICAL.md:534](TECHNICAL.md#L534)). That is not guaranteed for a general
non-constant-sum game. Expected tournament points—especially with 3/1/0
scoring or bonuses—need not create a zero-sum payoff matrix. Multi-start does
not resolve this.

**Suggestion:** First establish whether the chosen utility transformation
produces a constant-sum/zero-sum game. Otherwise report regret/exploitability
and convergence diagnostics, and specify a fallback equilibrium solver. Treat
non-convergence as a valid result.

### 10. FR11 attribution has no defined estimand or algorithm

The PRD asks which treatment features drive favorability
([PRD.md:250](PRD.md#L250)). The technical document schedules a report
generator but does not specify how attribution is calculated
([TECHNICAL.md:695](TECHNICAL.md#L695)). This is nontrivial because changing a
feature can also change the projected field.

**Suggestion:** Define the reference pack, counterfactual operation, and
whether the fixed point is recomputed. For interacting features, use an ordered
decomposition or posterior Shapley-style attribution and avoid causal wording.

### 11. FR9c is a work item rather than a technical design

The PRD requires constrained squad-level assignment
([PRD.md:233](PRD.md#L233)). T6 only says squad events are excluded from the
open-event model ([TECHNICAL.md:495](TECHNICAL.md#L495)); W25 supplies a
success condition but no model contract.

**Suggestion:** Add a short design covering squad membership, no-duplicate
constraints, captain-level utility, coach-to-race assignment, and how EuroBowl
validation differs from open-event validation.

### 12. Milestone-1 Tourplay scope differs between documents

The PRD calls for “NAF + Tourplay ingestion” in milestone 1
([PRD.md:289](PRD.md#L289)), while technical W4 performs only reconnaissance
and delays the importer until W17 ([TECHNICAL.md:663](TECHNICAL.md#L663),
[TECHNICAL.md:686](TECHNICAL.md#L686)).

**Suggestion:** Either change the PRD milestone wording to “Tourplay
reconnaissance/access validation,” or define the minimum milestone-1 ingestion
deliverable.

## Recommended priority

Resolve the first six issues before implementation, especially gate isolation,
the scoring-bonus gap, coach-prior consistency, BB2020 pooling, and fold-local
preprocessing. The remaining findings should be resolved before their
respective milestones are started.
