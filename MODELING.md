# Modeling rationale: bb-stats

Status: draft · Companion to PRD.md and TECHNICAL.md. The PRD says *what*,
TECHNICAL.md says *how*; this document records *why* — the reasoning that
connects each modeling choice to the realities of tournament Blood Bowl and
of this dataset, so future revisions can argue against the actual rationale
instead of guessing at it. Nothing here overrides the other two documents.
Section references: § and FR/PS point into the PRD, T into TECHNICAL.md,
M into this document.

It also holds the register of **considered-and-deferred features** (M11):
ideas judged plausibly real but out of scope for v1, each with the
condition that would revive it.

---

## M1. Notation

Symbols used in T5–T6, defined once. TECHNICAL.md carries a compact inline
version; this is the authoritative table.

| Symbol | Meaning | Introduced |
|---|---|---|
| A, B | the two sides of a match; assignment is arbitrary (T5.6) | T5.1 |
| σ(x) | the logistic function 1/(1+e^(−x)) | T5.1 |
| η | latent advantage of side A on the log-odds scale; antisymmetric under side swap | T5.1 |
| c | draw half-width; the ordinal cutpoints are (−c, +c); symmetric under side swap | T5.1, T5.4 |
| s(side) | one side's strength contribution to η = s(A) − s(B) + m(r_A, r_B) | T5.2 |
| θ_i | latent ability of coach i | T5.3 |
| μ_i, σ_θ | prior mean of θ_i (Glicko-derived where available) and pooled SD | T5.3 |
| δ | loading of the standardized, strictly-lagged Glicko mu on μ_i | T5.3 |
| α_{r,v} | baseline of race r at roster version v; sum-to-zero within each version block | T5.2 |
| z_{p,r} | treatment vector of pack p for race r, derived per T4.2 (centered, standardized) | T5.2 |
| γ_r, γ̄, Σ_γ | race r's treatment-response coefficients; hierarchical mean and covariance | T5.2 |
| f, ψ, n_{i,r} | familiarity f = ψ·log(1 + n_{i,r}); n = coach i's strictly-prior games with race r | T5.3 |
| m(r_A, r_B) | matchup term x_A′ M x_B | T5.5 |
| x_r | descriptor vector of race r at its roster version (FR8a) | T5.5 |
| M, τ | skew-symmetric matchup matrix (M = −M′); shrinkage scale of its entries | T5.5 |
| c0, κ, λ | cutpoint base level; draw-propensity shift; flexibility interaction | T5.4 |
| s_p | win-incentive scalar of pack p's scoring system, standardized | T5.4 |
| flex_r | strategic-flexibility descriptor of race r (FR8a) | T5.4 |
| U(n, r) | field-model choice utility of coach n for race r | T6.1 |
| β_loy, β_pop, β_fav | choice-model coefficients: loyalty, popularity, favorability | T6.1 |
| fav_r, field^k, ρ | favorability of race r; k-th field iterate; fixed-point damping factor | T6.2 |

Note the scope split: everything through T5 lives on the match-outcome
scale; T6 symbols live on the choice-utility scale. The two meet only
through E[points] in T6.2.

## M2. Why an ordinal paired-comparison model at all

**The outcome scale.** A tournament game resolves to W/D/L on the table,
and draws are genuinely frequent — Blood Bowl is clock-limited (16 turns a
side), grinding game plans deliberately play for 1–0 or 0–0, and pack
scoring visibly shifts how hard players push to break ties. Binarizing
(or coding D as half a win) destroys exactly the phenomenon FR8c studies.
Modeling touchdown margins instead is attractive but deferred (FR7): the
ordinal model is robust to margin noise, and margins may not even arrive
in the data. W/D/L as a three-level ordered outcome is the minimal scale
that keeps draws first-class.

A subtler reason to model the *outcome* rather than tournament *points*:
packs score outcomes differently (2/1/0, 3/1/0, bonus points). Fitting on
outcomes and applying the pack's scoring afterwards (as T6.2 does for
expected points) lets one fitted model serve every scoring system; fitting
on points would bake each pack's scoring into the response and destroy
cross-pack comparability — the same mistake as trusting tier labels (§6).

**The latent-difference structure.** Match outcome depends on *relative*
strength, so the model is built on a scalar advantage η = s(A) − s(B) +
m(r_A, r_B). This is the paired-comparison tradition (Thurstone,
Bradley–Terry, Elo/Glicko), and its defining consequence — anything common
to both sides cancels — is a feature, not a bug: the shared context (pack,
era, region, event type) *cannot* confound a within-match comparison, and
the algebra forces those covariates into the two places they can actually
act, race-interactions in η or the cutpoints (T5.2, T5.4). A direct
multinomial regression on three categories would ignore the W>D>L ordering,
double the parameter count, and lose the automatic side-swap symmetry that
the difference structure gives for free.

## M3. Why the logistic link

The likelihood in T5.1 — ordered logistic with symmetric cutpoints on an
antisymmetric location — is exactly the Rao–Kupper (1967) ties extension
of Bradley–Terry: P(A wins) = π_A/(π_A + ν·π_B) with η = log(π_A/π_B) and
c = log ν. So "why logistic" has a lineage answer: it *is* the canonical
paired-comparison-with-draws model, the same family chess and go rating
systems (Elo in its logistic form, Glicko) live in. That matters
practically here: the FR8b prior maps a (standardized) Glicko mu onto μ_i,
and keeping θ on a logistic log-odds scale makes that mapping a single
scale factor δ rather than a link-function mismatch.

Substantive fit: the logistic has heavier tails than the probit's normal.
Blood Bowl outcomes are dice-dominated — even a huge skill gap leaves a
real upset probability (every veteran has lost to Nuffle) — and the
heavier tail encodes exactly that reluctance to assign extreme
probabilities from large |η|. Honestly, this is a mild bonus rather than a
decisive argument: at the moderate |η| this data produces, logit and
probit are near-indistinguishable after rescaling (~1.6). The remaining
reasons are pragmatic: closed-form CDF, log-odds interpretability (η = 1
is ~73/27 in the no-draw limit), and a native `OrderedLogistic` in
NumPyro. The link choice is weakly load-bearing; no sensitivity analysis
is planned because no conclusion of this project could plausibly hinge
on it.

## M4. The symmetry structure is fully general, not a restriction

Two facts worth having on record, because they settle several "is this
form too restrictive?" questions at once (M6 is an instance).

**(a) Antisymmetric location + symmetric cutpoints is the general
side-swap-invariant form.** Take any three-category cumulative-logit
model: cutpoints κ₁ < κ₂ and location η′, with P(L) = σ(κ₁ − η′) and
P(L or D) = σ(κ₂ − η′). Reparameterize with midpoint d = (κ₁ + κ₂)/2 and
half-width c = (κ₂ − κ₁)/2. Side-swap invariance (relabeling A↔B and W↔L
must give the same distribution) requires (d − η′) to flip sign and c to
be unchanged under the swap. But a cutpoint midpoint d is
indistinguishable from a location shift — only η = η′ − d is identified.
So the general invariant model *is* "antisymmetric η, symmetric cutpoints
±c with c symmetric in (A, B)": T5.1 is not one convenient
parameterization among several, it is the whole family. Free asymmetric
cutpoints (T8.3) don't add expressiveness — they add one unidentified
degree of freedom that the arbitrary side-labeling turns into noise.

**(b) Per-match, (η, c) is saturated.** A three-outcome distribution has
two degrees of freedom, and the map is exactly invertible: given any
target (p_W, p_D, p_L) with p_D > 0,

```
c = ( logit(1 − p_W) − logit(p_L) ) / 2
η = −( logit(1 − p_W) + logit(p_L) ) / 2
```

and c > 0 iff p_D > 0. So the likelihood *shape* excludes nothing: any
pattern of W/D/L probabilities is reachable. All restrictiveness in the
model lives in one place — **which covariates enter η and which enter
c** — and that is where design debates should be aimed. η is the "who is
favored" channel; c is the "how often does it end even" channel; every
effect is a claim about one, the other, or both.

## M5. Why softplus for the cutpoint

c must be positive (the cutpoints −c < +c must stay ordered). The two
standard positivity transforms are exp and softplus; T5.4 uses softplus
and both are acceptable. Reasons for the default:

- Away from zero, softplus is approximately linear, so the κ and λ
  covariate effects read as roughly *additive* changes to the draw
  half-width. Under exp they become multiplicative and interact with each
  other and with c0 — an effect size that means one thing for a low-draw
  pack and another for a high-draw pack, which is harder to prior and
  harder to report (FR11-style attribution wants "this scoring rule
  removes about this much draw mass").
- exp's explosive right tail is a known source of bad HMC geometry when a
  cutpoint scale interacts with hierarchical terms; softplus has bounded
  gradient (σ) and no comparable failure mode. With ~20 packs identifying
  κ and λ, sampler robustness is worth more than elegance.
- Near zero, softplus behaves like exp — a soft floor rather than a hard
  boundary, so a pack that genuinely crushes draw probability can be
  represented without a constraint wall.

## M6. Draw agency: what the symmetric-c channel does and doesn't capture

The question: a team's agency to convert draws into decisive results is
not necessarily *even* between W and L — is modeling it only through
cutpoints a simplification?

**What the cutpoint channel already does.** Shrinking c vacates draw mass,
but the split of that mass is not fixed at 50/50 — it follows the current
η. Marginally, ∂P(W)/∂(−c) = σ′(c − η) and ∂P(L)/∂(−c) = σ′(c + η), and
since σ′ falls with distance from zero, the *favored* side receives the
larger share of the vacated mass (in the c → 0 limit the model degenerates
to Bradley–Terry and the draw mass has been split at the win odds). So
"a flexible team that is ahead on strength converts draws mostly into
wins" is already the model's behavior with zero extra parameters — the
FR8c signature (mass moving from D to both W *and* L) is about the pooled
population of matches, not a claim that each match splits evenly.

**What it cannot do.** By M4, c is symmetric, so the cutpoint channel
cannot give the *more flexible side* a directional edge beyond what η
already says — e.g. "the team that can manufacture a late scoring chance
wins the close game against the team that can't, independent of who was
favored". That is a location effect, and M4 says exactly where it
belongs: an antisymmetric η term,

```
λ₂ · s_p · (flex_A − flex_B)
```

which composes with the existing λ term (shared draw reduction in c;
directional drift in η) without breaking any invariance property.

**Why it is deferred rather than included.** Two reasons. First,
identification: within a single pack, s_p is constant, so the term reduces
to a per-race scalar entering as a difference — precisely the shape the
free race baselines α absorb. λ₂ is identified only by how the
flex-difference effect *varies with s_p across packs*, i.e. at pack-level
N ≈ 20, the same weakness T5.5 already flags for λ (where the prior is
expected to dominate). Second, sign: theory doesn't fix it. Gambling for
the win buys losses too; the net η drift is positive only if flexible
teams gamble *selectively* — plausible, since selectivity is close to what
the descriptor means, but not certain enough to spend one of ~20 packs'
worth of identification on in v1. So: yes, cutpoints-only is a
simplification; the expectation that the data can't support more is
correct at gate-stage volume; and the fix is a registered one-term
extension (M11), not a rework.

## M7. Why the matchup term looks like that

**Why a matchup term exists.** Race interactions in Blood Bowl are
genuinely intransitive — the folklore triangle (bash grinds fragile
speed, speed dances around slow bash, and specific tools like Tackle
invert specific matchups) is real, and no single strength scale α can
represent "X beats Y, Y beats Z, Z beats X". A paired-comparison model
without an interaction term structurally *cannot* express the
rock-paper-scissors component of the game; m(·,·) is that component.

**Why skew-symmetric, and zero for mirrors.** Forced, not chosen: A's
matchup advantage over B is exactly B's disadvantage (side-swap
invariance, M4), and a race cannot beat itself on average. The
parameterization M = −M′ builds both in algebraically instead of hoping
the sampler finds them.

**Why bilinear in hand-authored descriptors.** ~25 races give ~300
unordered pairs, most thinly observed; free per-pair effects or learned
embeddings are unidentifiable at this volume (FR8a). Descriptors put the
structure where the knowledge already is — the community's mechanistic
understanding of *why* matchups tilt (armour, mobility, strength access,
stunty) — and reduce the matchup space to K(K−1)/2 interpretable
"descriptor k beats descriptor l" terms. This is a bias-variance trade
made deliberately: v1 accepts the bias of a low-dimensional mechanistic
model to get estimable, interpretable structure; the milestone-4 low-rank
residual (T5.5) is the variance side, added only if data volume earns it.

**Why no descriptor main effects.** They are already inside α — races
have free baselines, so a w·(x_A − x_B) term is a reparameterization of
nothing, and fitting both just makes two posteriors fight (T8.5). The
matchup term carries only what α cannot: interactions.

**Pack-invariance of M is a v1 simplification.** In reality the matchup
geometry itself is pack-dependent: rule levers reshape specific pairings
through the builds they enable — skill stacking produces Tackle/Mighty
Blow stacks whose EV concentrates against dodge-reliant, low-armour
opponents. v1's γ carries the field-average of such effects; the
matchup-specific remainder is a registered extension with a design
sketch in M11.1.

## M8. Coach terms, and the deferred opponent-experience variant

**Why a jointly-fit latent, not NAF Glicko as a covariate.** FR8b's three
reasons, restated causally: NAF mu is per coach×race, so it has already
absorbed race strength and historical pack treatment — using it as a
feature re-imports the effects this model exists to isolate; it is
unadjusted for ruleset; and current ratings encode the very outcomes
being predicted (leakage). As a strictly-lagged, within-race-standardized
*prior mean* it contributes only what is safe: a head start on ranking
coaches relative to peers on the same race.

**Why the familiarity curve is ψ·log(1+n).** The mechanism is a learning
curve: the first few games with a race teach the most (what the pieces
do, the opening plans), and returns diminish. log(1+n) is the simplest
concave curve with f(0) = 0, and one shared ψ keeps it estimable. The
alternative — a free coach×race random effect — is enormous, nearly
empty, and would soak up genuine matchup signal (T5.3); the parametric
curve is the honest amount of structure for the data.

**The deferred variant: experience against the opponent's race.** One
could add f_vs = ψ₂·log(1 + games against r_B) to s(side), or even a full
matchup-experience term (games playing r_A against r_B). The mechanism is
plausibly real and concentrated in gimmick races: Vampires (Hypnotic
Gaze), Slann (a leaping game with no conventional defensive playbook),
stunty lists (secret weapons, mass fouling, Chef) punish opponents who
haven't learned the specific counters, and that edge should decay with
exposure. Deferred from v1 on three grounds:

- **Collinearity.** A coach's exposure to race r is roughly total games ×
  field share of r. Under that proportionality, log(1 + games vs r) ≈
  log(total games) + log(share_r): the first part is a coach covariate
  (absorbed by θ), and the second is a per-race constant entering η as a
  difference (absorbed by α). The identifying signal is only each coach's
  *deviation* from field-share exposure — real (regional metas differ)
  but far smaller than the raw feature suggests.
- **It needs an interaction to have teeth.** The effect is claimed to be
  large for gimmick races and negligible for Humans; a uniform ψ₂ would
  mostly blur it away. Doing it properly means an "opponent-knowledge
  tax" descriptor or per-race ψ₂,r — more hand-authored input and more
  parameters exactly at the sparsity margin.
- **The matchup-experience version is sparser still** (~600 ordered pairs
  per coach) and shouldn't be attempted before the vs-race version has
  shown signal.

**The cheap gate before ever adding it:** a residual probe on the fitted
baseline — among matches against high-gimmick races, do the model's
residuals correlate with the opponent's prior exposure count to that
race? This costs a group-by on quantities the leakage-safe data layer
already computes (T5.3), needs no refit, and slots naturally into the
milestone-2 residual analysis (§9a's null-interpretation pass). Signal
there revives the feature (M11); silence retires it cheaply.

## M9. Treatment responses and the budget structure

**Why hierarchical race×treatment coefficients.** The reality being
encoded: more resources help everyone, but not equally — extra skills do
more for a skill-poor roster, gold thresholds unlock race-specific
configurations. γ_r ~ N(γ̄, Σ_γ) says exactly that: a shared generic
response, with per-race deviations shrunk toward it. The deviations *are*
the thesis (§8); the shrinkage is what makes them estimable at ~20 packs,
where free race×pack cells would be pure noise (T8.8). Partial pooling is
also the honest epistemic position: absent much data on a race, the best
guess for its response is the generic one, not zero and not a free
parameter.

**Why budget is monotone-discrete** (full specification T4.3, motivation
§6). Two structural facts about the game, not modeling conveniences:
roster math is threshold-like — at a specific TV a race can afford a
specific positional or rerolls configuration, and nothing changes between
thresholds — and tournament TVs are quantized in practice. Monotonicity
itself is close to a free-disposal argument: holding the rest of the pack
fixed, extra budget cannot hurt, because a coach may simply not spend it.
(Packs that couple TV to other rules — tier reassignment by TV — express
that through the other treatment features, not by breaking monotonicity
here.) Encoding monotone steps as scale × cumulative simplex weights makes
the constraint algebraic rather than prior-enforced, and the hand-authored
breakpoint tables inject the deterministic roster math as priors — the
data's job is to say how *big* each unlock is, not to rediscover where
the unlocks sit.

## M10. Field model choices, briefly

Per-coach multinomial logit (T6.1) is the standard discrete-choice tool,
and the utility terms mirror the actual decision: loyalty first (largely
material — miniatures owned and painted; FR9 warns against reading it as
pure preference), popularity (metas are social), favorability last.
Favorability is field-conditional (FR9a) because a race's expected
tournament points depend on what it will actually face — hence the fixed
point, damped because loyalty genuinely damps real-world best-response.
E[points] rather than winrate because coaches optimize what the pack
scores, and draws are frequent enough for the difference to matter. The
equilibrium diagnostic (FR12) removes loyalty and must switch to
fictitious play precisely because the payoff matrix is intransitive by
construction (M7): raw best-response cycles, and averaging turns the
cycle into the mixed equilibrium it orbits — which is the honest object
to report.

## M11. Register of considered-and-deferred features

Candidates judged plausibly real but excluded from v1. Distinct from the
*scheduled* milestone-4 upgrades (low-rank matchup residual W27, TD/CAS
margins W30, meta-pressure W24, Swiss pairing W28, time-varying θ W29 —
see T9): items here have no milestone and are revived only by their
stated condition.

| Feature | Mechanism | Why deferred | Revival condition |
|---|---|---|---|
| Opponent-race experience: ψ₂·log(1 + coach's prior games *against* r_opp), likely interacted with a gimmickiness descriptor | Gimmick races (Vampires, Slann, stunties) tax opponent knowledge; the edge decays with exposure | Near-collinear with θ and α under proportional exposure; needs an extra descriptor or per-race ψ₂ to have teeth (M8) | The M8 residual probe (run with milestone-2 residual analysis) shows exposure-correlated residuals vs gimmick races |
| Coach×matchup experience (games playing r_A vs r_B) | As above, plus own-race-specific counterplay knowledge | Strictly sparser than the vs-race version (~600 ordered pairs per coach) | vs-race term adopted and materially improving, with structured residual remaining |
| Flexibility-difference scoring term in η: λ₂·s_p·(flex_A − flex_B) | Uneven draw agency — the side that can manufacture a late chance converts close games directionally (M6) | Identified only via cross-pack s_p variation (N≈20, same weakness as λ); theoretical sign not certain | Corpus growth past milestone 3 *and* the power rehearsal showing pack-level scoring terms identified |
| Pack-modulated matchups M(p) — design sketch in M11.1 | Pack levers reshape specific matchups through the builds they enable (stacking → Tackle/Mighty Blow stacks preying on dodge-reliant teams) | v1's γ already carries the field-average of the effect; the matchup-specific remainder needs within-pack contrasts ~20 packs can't spare, and must be centered against γ to be separable (M11.1) | Build-response study (W23) passes + milestone-3 corpus, alongside W27; earlier if gate residuals show pack-dependent matchup misses |
| Coach-style descriptors × opponent descriptors (labeled or latent) | Coaches have persistent playstyles and style-specific weaknesses (e.g. struggles against fast agile teams) | No labeling source at corpus scale; the latent version is a per-coach embedding — data is thin for all but the most active coaches, and shrinkage would zero it exactly where it can't be checked | Residual probe on high-volume coaches (per-coach baseline residuals vs. opponent descriptor vector) shows heterogeneous structure |
| Coach×coach terms | Style or psychological matchups between specific coach pairs | Hopeless sparsity — most coach pairs ever meet a handful of times; any real signal is better routed through coach-style descriptors (row above) | None as a direct term; subsumed by the coach-style row |
| Standings-conditional incentives | Late-round standings shape per-match W/D incentives (a draw can lock a placing); the symmetric part is a c effect, any one-sided need-to-win an η effect (M4) | Needs per-round standings reconstruction; largely washes out of the race-level aggregates this project targets | Swiss-pairing simulator work (W28), where round-level realism starts to matter |

Anything added here should state mechanism, deferral reason, and revival
condition in the same shape — the register only works if a null result
can retire an idea as cheaply as a positive one revives it.

### M11.1 Pack-modulated matchups: design sketch

The register entry judged most likely to matter, so it gets more than a
table row.

**What v1 already captures.** Levers like stacking permissiveness are
mostly pack-global, so z_{p,r} carries them for every race, and the
response difference (γ_A − γ_B)·z is identified from shared-environment
variation. This means γ_r reads as *response to the environment*, not
merely response to the race's own grants — "Amazons suffer in
stack-permissive packs" is a v1 challenger effect, not a missing one.
What γ encodes is the field-averaged consequence: how the environment
moved a race's results against the mix of opponents it actually met in
the training data.

**What is missing.** The mechanism is matchup-specific: a Tackle/Mighty
Blow stack extracts its EV from dodge-reliant, low-armour opponents and
far less from, say, Khemri. Averaging that into γ has two costs. (a)
Forecasts against non-average fields misweight it — an elf-heavy
projected field under a stack-permissive pack should hurt Amazons more
than the training-average effect says (FR10). (b) The counter-pick and
equilibrium machinery (FR9a, FR12) runs on the matchup matrix
E[points r vs o | pack] — today a pack moves that matrix only through
per-race strength, when in reality it also *twists* it.

**Parameterization.** Make the matchup matrix pack-dependent:

```
m(A, B; p) = x_A′ M(p) x_B,    M(p) = M0 + Σ_j u_{p,j} · ΔM_j
```

with u_{p,j} a small set of pre-declared pack-level scalars (stacking
permissiveness first) and each ΔM_j skew-symmetric — which makes every
invariance property (antisymmetry, mirror-zero, side-swap) inherited
automatically. Two variants: hand-declared sparse cells (only the
mechanism-known entries, e.g. u_stack on the bash-beats-dodge cell — a
handful of scalars with shrinkage), or full ΔM_j matrices under tight
shrinkage (milestone-4 volume).

**Identification, and the centering trap.** The term varies at match
level through the descriptors, so it is better identified than
pack-global cutpoint terms like λ — but its field-average,
u_{p,j} · x_A′ ΔM_j x̄_field, is a race×u_j main effect: exactly γ-shaped.
Fitted naively, ΔM_j and γ fight over the same signal — the same failure
mode T5.5 avoids by keeping descriptor main effects out of M. The fix is
the same discipline applied once more: center the modulation so γ keeps
the field-average and ΔM_j carries only the deviation around it.

**The mediator becomes observable later.** The causal path is
pack → builds (Tackle/MB density) → matchup EV. The build-response study
(W23) tests the first arrow; Tourplay roster features (W26) would expose
the mediator directly — and observed skill counts entering the matchup
term likely beat inferring latent modulation. Hence the revival
condition: after a W23 pass, alongside W27, sparse hand-declared cells
first. FR9b's meta-pressure features are the complementary conditioning
of the same mediator (field → builds rather than pack → builds); if both
are ever active they should share the build-feature definitions.
