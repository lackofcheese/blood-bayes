# Domain and statistical expert review brief

Status: request for review before treatment schema v0, the power rehearsal,
and `eval/GATE.md` are frozen. This brief is self-contained: the reviewer has
not read `TECHNICAL_REVIEW.md`, `MODELING_REVIEW.md`,
`MODELING_PERSPECTIVES.md`, or `REVIEW_ASSESSMENT.md`.

## 1. What the project is trying to establish

The core thesis is that tournament rules packs alter races differently in a
way that can be represented by a structured per-race treatment vector and
generalized to a previously unseen pack.

The match model is an ordinal W/D/L paired-comparison model:

```text
η = side_strength(A) − side_strength(B) + matchup(A,B)
c = positive symmetric draw half-width
```

`η` says who is favored; `c` says how often a game is drawn. The binding gate
uses leave-whole-pack-out validation and asks whether hierarchical
race×treatment responses improve prediction over a baseline that already
contains coach, race, matchup, draw, and scoring effects.

The automated pack parser is built only if that treatment-schema gate passes.

## 2. Decisions made after the reviews

Please challenge any decision below on either statistical or Blood Bowl
grounds. “Approved” means it has owner agreement, not that review is closed.

### 2.1 Strict gate isolation — approved and normative

Baseline and challenger share all nuisance structure, including baseline race
draw propensity, the global scoring cutpoint term `κ·s_p`, and the
scoring×flexibility term `λ·s_p·(flex_A+flex_B)`. The challenger adds only the
hierarchical race×treatment block `γ_r·z_{p,r}`.

Reason: the gate exists to justify automating the treatment schema. It must not
pass because a scoring/draw term unavailable only to the baseline improves
prediction. The expected `λ` sign is advisory model validation, never a
binding treatment-schema criterion.

Review question: is any supposedly shared term actually part of what the
treatment schema/parser must earn, or is this strict ablation the correct
decision boundary?

### 2.2 Matchup-descriptor centering — approved and normative

Race descriptors are centered using uniform weights over the races active in
the relevant rules edition before entering the skew-symmetric bilinear matchup
term. The reference race list, weights, schema version, and means are stored.

Reason: skew-symmetry alone can still reproduce a transitive
`strength(A)−strength(B)` component. Centering guarantees the induced matchup
matrix has zero weighted row mean (`C·w=0`) and leaves general race strength
inside `α`. Popularity weighting was rejected because it would make intrinsic
strength move with the projected field.

Review question: is uniform edition-specific weighting the best reference, or
is there a more defensible fixed distribution?

### 2.3 Coach strength and Glicko — approved and normative

NAF Glicko is not a model input or prior. Coach strength is inferred jointly
from permitted match history as `θ_i ~ N(0,σ_θ)`, reconstructed inside every
mask and propagated as a posterior distribution. Glicko is retained only as an
external benchmark; using otherwise unavailable pre-dataset history would
require a separate decision.

Masks differ by estimand:

- thesis gate: exclude the held-out pack;
- event validation: exclude the held-out event;
- prospective forecast: use strictly pre-cutoff matches.

Reason: Glicko is a coach×race summary of largely the same outcomes,
unadjusted for this model’s pack/matchup structure. Using it alongside the raw
history risks double use, reimported race effects, and leakage.

Review questions: is the zero-centered latent adequate for v1? Should the
prospective mask be the primary validation estimand rather than a separate
report? Is time-varying coach strength important enough to move before the
gate sensitivity milestone?

### 2.4 Race draw propensity — approved and normative

The cutpoint model is:

```text
c = softplus(
      c0
      + d[r_A,v_A] + d[r_B,v_B]
      + κ·s_p
      + λ·s_p·(flex_A+flex_B)
    )

d[r,v] = β_flex·centered_flex[r,v] + u[r,v]
```

`u` is a centered, hierarchical race/roster-version residual. Scoring and
flexibility are centered so `d` describes reference scoring and `λ` describes
the response away from it.

Reason: equal-strength Dwarf and Wood Elf mirrors should not be forced to have
the same draw probability. Strategic agency may plausibly cause both baseline
decisiveness and a response to win-heavy scoring; those are intercept and
slope contrasts rather than duplicate terms. Other mechanisms remain in `u`.

Free race-pair draw effects are not fitted in v1. Held-out residuals test for
symmetric matchup-specific draw structure; if present, the preferred extension
is a regularized symmetric descriptor interaction.

Review questions: is flexibility the right predictor of baseline draw
propensity? Which other race traits belong upstream? Which pairings should be
drawish beyond additive race tendencies, and why?

### 2.5 BB2020 pooling — approved contract, conditional only

BB2025-only remains the primary plan. BB2020 is activated only if milestone W5
finds BB2025 volume insufficient. If activated, BB2025 is the reference with
hierarchical per-race BB2020 deviations; absent races are structurally
missing, and location constraints apply across contemporaneously comparable
races rather than inside a one-race roster-version key.

Exact shrinkage, downweighting, and sensitivity settings remain deferred to
W5. Review is welcome, but this fallback should not drive v1 complexity unless
the volume report activates it.

### 2.6 Bonus-point scope — approved and normative

V1 favorability is expected base W/D/L result points only. TD/CAS and other
performance bonuses are explicitly omitted and flagged in output metadata.
Bonus rules may inform the scoring-incentive covariate but do not create an
expected bonus award without a validated conditional margin model.

Reason: W/D/L probabilities cannot determine the chance of a touchdown-margin
or casualty threshold. Source margin columns are preserved and coverage is
reported for a later upgrade.

Review question: is base-result-only useful enough for bonus-heavy packs, or
is a conditional margin model essential before the field model is credible?

### 2.7 Pack×race heterogeneity diagnostic — approved and normative

Alongside—but never in place of—the binding gate, fit:

```text
baseline   + pooled centered free b[pack,race]  → τ_raw
challenger + pooled centered free b[pack,race]  → τ_residual
```

Report a simulation-calibrated practical threshold, posterior uncertainty,
`P(τ_raw>ε)`, `P(τ_residual<τ_raw)`, and repeat-event checks where possible.

Reason: a failed predictive schema gate is ambiguous between “little pack
heterogeneity” and “heterogeneity exists but schema v0 missed it.” Free effects
cannot predict a new pack, cannot pass the gate, and are described as
pack-associated rather than causal.

Review questions: is this variance-component sequence identifiable and useful
at roughly 20 packs? Is the proposed descriptive variance reduction liable to
mislead despite its caveats? What practical scale should define `ε`?

### 2.8 Field choice, loyalty, and switching — approved direction; expert input requested

All event-legal races remain possible. The proposed soft repertoire model uses:

- exact-race NAF history and last-race loyalty;
- observed repertoire breadth/entropy and switching rate, interacting with a
  new-to-observed-history indicator;
- transferable style experience using a low-dimensional race geometry;
- entry complexity interacting with unfamiliarity;
- the candidate’s favorability advantage over the coach’s best established
  option, allowing sufficiently strong packs to overcome switching friction;
- popularity and cross-fitted field-conditional favorability.

NAF absence is evidence, not proof, of access friction. Miniature cost,
ownership, borrowing, preference, online loyalty, and unrecorded experience are
not separately identified. Long narrow histories are stronger evidence than
short histories, but every legal race retains nonzero probability.

Current candidate geometry is a continuous bash↔agile axis, a separate stunty
dimension, and an entry-complexity descriptor. Vampires should not receive a
race-specific axis by default; a general unusual-mechanics descriptor is
revived only if several races show the same residual pattern.

Review questions:

1. Is bash↔agile plus stunty a useful transfer geometry?
2. How should entry complexity be defined and reviewed? Are Orcs relatively
   easy and Elves/Vampires hard for sufficiently general reasons?
3. Which race families transfer in practice, and where does this geometry
   fail?
4. How strong is miniature/access friction relative to preference and online
   practice?
5. Is favorability advantage the right mechanism for competitive surprise
   switches?

### 2.9 NAF race history as familiarity — approved cautiously

`log(1+prior NAF games with race)` remains only a weak predictive proxy, not a
literal learning curve or total experience. BB3, FUMBBL, leagues, casual play,
and unrecorded tabletop games are missing. Hidden online specialists may adopt
a race precisely when a pack favors it, potentially confounding treatment
effects.

Required gate sensitivities: no history term, `log(1+n)`, coarse buckets,
established-history-only evaluation, and a first-observed-use diagnostic.
Style-transfer is initially used in choice, not match performance; it moves to
the match model only if held-out residuals support it.

Review questions: are these sensitivities sufficient? Is first-observed-use
selection likely large enough to threaten the gate? Are there obtainable
online/league sources with credible coach linkage?

### 2.10 Region and event type — retained as design/diagnostic structure

A global region or event-type term cannot enter the antisymmetric match
location `η`: both sides share it, so it cancels. Region instead enters pack
selection (several contrasting packs within each region), field/popularity
features, residual/confound reporting, and stratified evaluation. Squad events
are excluded from the individual open-event choice model and receive the later
FR9c constrained assignment model.

We have not added region/event interactions to draw cutpoints or free
region×race performance terms by default. Review questions: are there
region-specific playstyle, scoring-behavior, or race effects that require a
predeclared channel beyond within-region pack contrasts? Are the proposed
diagnostics sufficient to prevent regional culture from masquerading as pack
treatment?

## 3. Decisions currently paused for this review

### 3.1 Mechanistic composite treatment features

The additive treatment model may miss combinations whose rules mechanics are
inherently non-additive. We will not generate all pairwise interactions. The
goal is to predeclare at most two or three high-value composites before schema
v0 is frozen.

Candidate mechanisms:

- skill grants × stacking capacity;
- secondary access × usable slots/eligibility;
- star access × affordability;
- inducement discount × remaining treasury;
- gold × skill-point capacity or, preferably, a roster-derived joint-resource
  feature such as skills placeable on an unlocked viable core.

Gold and skill points may be complementary, substitutes, or both at different
roster thresholds. More gold can unlock skilled positionals; separately
granted skills may be more valuable after the right player is affordable, or
less valuable because the positional already carries key skills.

Requested review for each proposed composite:

1. State the game mechanism.
2. Say whether it is complementarity, substitution, or threshold behavior.
3. Identify the races and pack conditions where it matters.
4. Give counterexamples.
5. Prefer a deterministic roster-derived definition where possible.
6. Say whether its direction is strong enough for a prior/sign check.
7. Rank it for inclusion in the two-or-three-feature v0 budget.

Additional resource-pressure concepts to assess:

- cost of a minimally viable core;
- fraction of budget consumed by key positionals;
- starting coverage of essential skills;
- affordability of players carrying those skills;
- remaining roster flexibility at reference budget.

Please flag concepts that are too subjective, too pack-specific, redundant
with the monotone budget breakpoint model, or unlikely to vary independently
in the selected corpus.

### 3.2 Residual treatment-response covariance `Σ_γ`

For treatment feature `j`, the conservative candidate is:

```text
γ[r,j] = γ̄[j] + τ[j]·ε[r,j]
ε[r,j] ~ Normal(0,1)
```

This is diagonal residual covariance: each treatment lever gets its own
between-race scale, but unexplained deviations do not borrow across levers.

A full covariance could learn, for example, that resource-starved races
respond above average to both gold and skills. But with roughly 25 races and
about 20 packs, a K-feature full covariance adds K(K−1)/2 weakly identified
correlations. More importantly, covariance does not express pack-dependent
gold×skills complementarity.

Current inclination: encode known shared mechanisms through resource-pressure
descriptors and a few composites, then use diagonal covariance for what
remains. Full LKJ, low-rank latent factors, or descriptor-informed response
means are alternatives.

Requested review:

1. After the recommended composites, is diagonal residual covariance too
   restrictive?
2. Is there a sufficiently strong domain prior for positive or negative
   cross-lever response correlation?
3. Would descriptor-informed coefficient means be preferable to anonymous
   covariance?
4. Which covariance sensitivity belongs in the power rehearsal?

## 4. Review proposals rejected or deferred

Please challenge these dispositions as well.

### 4.1 Rejected for v1 or as a gate replacement

- **Soften or replace the binary gate:** rejected. Keep the binding,
  pre-registered treatment-schema criterion as the anti-self-deception device;
  publish heterogeneity, power, schema coverage, and engineering context beside
  it rather than weakening it.
- **Free pack×race effects as the predictive model:** rejected. They cannot
  generalize to an unseen pack; permitted only as the diagnostic in §2.7.
- **All pairwise treatment interactions:** rejected at ~20 packs. Only a few
  mechanistically predeclared composites are eligible.
- **Hard ownership/consideration sets inferred from NAF history:** rejected.
  NAF absence is not ownership or true inexperience; all legal races retain
  nonzero probability.
- **Use current or lagged Glicko as the primary coach input:** rejected for
  double-use, race contamination, and masking complexity.
- **High-dimensional learned race embeddings or free pair effects in v1:**
  rejected at current sparsity in favor of frozen descriptors and shrinkage.
- **A race-specific “Vampire axis”:** rejected unless a general mechanism
  shared by several races is established.

### 4.2 Deferred with a revival condition

- **Time-varying coach ability:** milestone W29 sensitivity; move earlier only
  if static-coach residuals or prospective degradation are material.
- **Coach×race ability/loadings:** add only if held-out residuals show stable
  race-complexity-dependent coach effects; free coach×race effects remain too
  sparse.
- **Style-transfer in match performance:** revive when held-out outcome
  residuals show transfer beyond exact NAF history and general coach strength.
- **Linked BB3/FUMBBL/league exposure:** revive only with audited coach linkage
  and useful coverage.
- **Nested or similarity-aware choice substitution:** revive if held-out choice
  residuals show a material IIA failure.
- **Observed ownership/access model:** revive only with direct survey,
  inventory, borrowing, or comparable access data.
- **Symmetric race-pair draw interaction:** revive if held-out draw residuals
  retain descriptor-structured pair signal after additive race effects.
- **Low-rank matchup residual:** remains milestone W27, after the gate and only
  if it improves held-out prediction.
- **Pack-modulated matchup geometry:** revive after the build-response study
  and more packs, or earlier only for strong residual evidence.
- **Directional flexibility scoring effect in `η`:** revive when cross-pack
  scoring variation has enough power; its sign is not theoretically secure.
- **Swiss simulation:** remains W28. Until then aggregate outputs explicitly say
  random pairing.
- **TD/CAS bonus model:** remains W30 and requires margin coverage plus
  validation.
- **BB2020 pooling:** revive only if W5 shows BB2025 data are insufficient.

### 4.3 Proposals considered but not adopted as redesigns

- **Replace the damped field fixed point with a single response update:** not
  adopted. The current iteration is retained with caps, trajectory logging,
  and convergence treated diagnostically; a one-update version remains a
  sensitivity if held-out field prediction favors it.
- **Move Swiss pairing before the field output:** not adopted. The v1 output is
  labeled expected performance under random pairing rather than event winrate.
- **Defer the equilibrium diagnostic entirely:** not adopted because it is a
  small, explicitly exploratory layer on the field machinery. Its convergence
  guarantee is restricted to constant-sum scoring; other utilities require
  regret/exploitability diagnostics and may yield non-convergence.
- **Start with deterministic roster features instead of the monotone budget
  model:** not adopted wholesale. Roster-derived breakpoints already enter as
  priors/placement logic; the monotone structure remains, with fold-local grid
  construction and out-of-support warnings.
- **Add pairwise matchup residuals from the start:** not adopted; descriptors
  remain the v1 bias-variance choice, with W27 as the earned upgrade.
- **Make a canonical neutral field co-equal with the projected-field headline:**
  not yet adopted or rejected. Neutral-coach race-vs-race outputs exist, but
  whether a fixed canonical field deserves product-level prominence remains an
  open presentation/estimand question.

## 5. Mechanical corrections already accepted

These are included for completeness but need review only if their consequences
are non-obvious:

- all preprocessing, grids, occupancy, and scaling are fold-local;
- TVs outside training support use the nearest fitted boundary and emit an
  explicit warning rather than extrapolating;
- historical favorability used by the field model is cross-fitted;
- match- and field-model posterior uncertainty are jointly propagated;
- residual probes use held-out posterior-predictive residuals;
- fictitious-play convergence is not claimed for non-constant-sum utilities;
- attribution is labeled predictive rather than causal;
- the contrast-rich gate corpus is not claimed representative of deployment;
- random-pairing outputs are not labeled event winrate;
- FR11 and FR9c require estimand/design contracts before implementation;
- milestone-1 Tourplay work is reconnaissance, with importer work after the
  gate; the counter-pick study gates interpretation/adoption rather than prior
  implementation.

## 6. Requested review output

Please return:

1. Any accepted decision you would reverse or materially alter, with reason.
2. Any rejected/deferred proposal you would promote, with an activation test.
3. A ranked list of at most three mechanistic composites for schema v0,
   including formulas or derivation rules where possible.
4. Recommended resource-pressure and race-style/complexity descriptors, with
   counterexamples and annotation rubrics.
5. A recommendation for residual `Σ_γ` after those mechanisms are encoded.
6. Any confounding path or validation failure that could make the binding gate
   answer the wrong question.
