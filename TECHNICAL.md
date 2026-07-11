# Technical design: bb-stats

Status: draft · Companion to PRD.md (PRD is the source of truth for *what*;
this document specifies *how*). The reasoning behind the modeling choices —
why these structures fit the game and the data — lives in MODELING.md.
Section references (§, FR, PS) point into the PRD, M into MODELING.md,
T into this document.

Audience: anyone (human or model) implementing the PRD. The purpose is to
capture design decisions, model specification details, and known failure
modes so implementation doesn't quietly diverge from the statistical intent.

---

## T1. Stack

| Concern | Choice | Rationale |
|---|---|---|
| Language | Python ≥3.12 | Ecosystem for Bayesian modeling and data wrangling; no other language is in contention. |
| Package/env | `uv` (pyproject-based) | Fast, reproducible, no conda weight. |
| Data storage | Parquet files + DuckDB for queries | Data volume is small (10⁴–10⁵ matches); a database server is overhead. DuckDB gives SQL over parquet with zero infrastructure. |
| Dataframes | Polars (pandas acceptable at boundaries) | Speed is not critical; strictness about types and nulls is. |
| Schemas/validation | Pydantic v2 models; pack annotations as YAML validated against them | Pack YAML is hand-authored — validation must be loud and early. |
| Probabilistic modeling | NumPyro (JAX) | Leave-pack-out CV means ~20+ full refits per experiment; NUTS on JAX is fast enough to keep iteration cheap. PyMC is an acceptable substitute; Stan is fine but makes the CV loop and posterior plumbing clunkier. Do **not** hand-roll MCMC or use point estimates for the hierarchical model — partial pooling with honest uncertainty is the whole point. |
| Testing | pytest; property-based tests (hypothesis) for the symmetry/invariance properties in T5.6 | The model has algebraic invariants that unit tests can check exactly. |
| Notebooks | Allowed for exploration and milestone-2 reports (FR13); all pipeline logic lives in `src/`, notebooks only call it | Prevents the usual notebook rot. |
| Web UI (FR13) | Deliberately unspecified, matching the PRD | Do not scaffold one early. |

## T2. Repository layout

```
bb-stats/
  PRD.md
  TECHNICAL.md
  pyproject.toml
  data/
    raw/            # immutable ingested artifacts (gitignored if large); never edited
    derived/        # parquet outputs of deterministic transforms; regenerable
  registry/         # small hand-maintained reference tables, in git (see T3.2)
  packs/            # one YAML per pack + schema version docs (see T4)
  descriptors/      # race descriptor tables, YAML, keyed race × roster_version (FR8a)
  src/bbstats/
    ingest/         # naf.py, tourplay.py — raw acquisition + normalization to tidy tables
    registry.py     # loaders/validators for registry tables
    packs.py        # pack schema, validation, treatment-vector derivation (T4)
    model/
      match.py      # match model: baseline and challenger (T5)
      field.py      # field-composition model + fixed point (T6)
      equilibrium.py# fictitious-play diagnostic (FR12)
    eval/
      cv.py         # leave-pack-out / leave-event-out harnesses (T7)
      gate.py       # pre-registered gate computation (§9a)
    reports/        # forecast + attribution outputs (FR10–FR12)
  eval/
    GATE.md         # pre-registered protocol, committed before fitting (§9a)
  notebooks/
  tests/
```

Data discipline: `data/raw` is append-only and immutable (keep the original
scrape/dump bytes plus a fetch timestamp); everything in `data/derived` must
be reproducible by rerunning the pipeline. If a source record is wrong, fix
it via an explicit patch table in `registry/`, never by editing raw or
derived files.

## T3. Data layer

### T3.1 Core entities and tables

- `match`: one row per game. Columns: `match_id`, `event_id`, `round`,
  `coach_a`, `coach_b`, `race_a`, `race_b`, `result` (W/D/L from side A's
  perspective), `td_a`, `td_b`, `cas_a`, `cas_b` (nullable — carried from
  day one if the source provides them, since margins would unlock the FR7
  stretch goal early; the v1 model stays ordinal regardless),
  `result_type` (normal / concession / forfeit / bye — byes are dropped
  from modeling; concessions are kept as losses but flagged, with a
  gate sensitivity check excluding them), `date`, source provenance. Side
  assignment (who is A) is arbitrary; the model must be invariant to it
  (T5.6). Store each match **once** — do not emit mirrored duplicate rows;
  duplication silently doubles the effective sample size and breaks every
  uncertainty estimate.
- `event`: `event_id`, name, date, location/region, `pack_id`, event type
  (open/squad), coach count, source ids (NAF tournament id, Tourplay id).
- `pack`: `pack_id`, name, schema version of its annotation, pointer to the
  YAML file. The event→pack mapping lives on `event` and is hand-maintained
  in `registry/` — it is the holdout key (§8) and must not be inferred
  fuzzily.
- `coach`: `coach_id` (NAF number where available), name variants. NAF
  numbers are the canonical coach key; name-based matching is a last resort
  and must be flagged.
- `race` / `roster_version`: see T3.2.
- `naf_rating_snapshot` (optional benchmark artifact): per coach × race ×
  month, mu/phi. Keep outside primary model feature tables; it is used only
  for external comparison or a separately approved prehistory analysis.

### T3.2 Race registry and roster versions

A single hand-maintained registry table maps every source's race naming to a
canonical `race_id`, and defines `roster_version` spans: `(race_id,
roster_version_id, valid_from, valid_to, edition)`. Rationale (FR3, FR8a):
rosters were rewritten between BB2020 and BB2025 and some changed mid-era, so
race baselines and descriptors key on `race_id × roster_version`, not on
`race_id` alone.

Every match row resolves to a roster version via its date. A match that
cannot be resolved (unknown race string, date outside all spans) is an
ingestion **error**, not a row to drop silently — route to a quarantine
table with a reason code, and report quarantine counts in every pipeline run.

Races absent in an era are structurally missing (FR3): they simply have no
roster version in that span and no parameters for it. Never zero-fill.

### T3.3 Ingestion notes

- **NAF** (FR1): format TBD pending data access (§10). Whatever arrives,
  land it verbatim in `data/raw` first; write the normalizer against the raw
  artifact so ingestion is rerunnable. Expect messiness in tournament
  metadata (region, event type) — that's registry curation work, not parser
  work. The data request should explicitly ask for: per-match TD/CAS counts
  (NAF has historically recorded them; see `match` columns above), coach
  NAF numbers (not names only), and tournament metadata. Historical Glicko
  snapshots are optional benchmark data, not a dependency of FR8b.
- **Tourplay** (FR2): check ToS and rate limits **before** writing a scraper
  (§10). Milestone 1 needs only enough Tourplay access to assess ruleset
  availability; the full importer is milestone 3. Cache every response in
  `data/raw` so development doesn't re-hit the site.
- **Volume count for FR3**: milestone 1 must produce a one-page report:
  BB2025 match count, events, distinct coaches, distinct packs-in-principle,
  and the same for BB2020 — this is the input to the pooling decision.

## T4. Pack schema and treatment vectors

### T4.1 Annotation unit (per §9a)

Packs are annotated at the **pack** level: tier definitions (grants in
normalized units), race→tier map, **legal-race list** (the choice set — some
packs ban or restrict races; the field model (FR9) and the race→tier
coverage lint both need it, and it must be in schema v0 because retrofitting
20 annotations is exactly the rework the guide exists to prevent), global
rules (budget, games count, resurrection/progression, stacking bans,
star/inducement policy, scoring system), plus the mandatory
`other: <verbatim>` escape field. Per-race
treatment vectors are **derived mechanically** in `packs.py` — annotators
never author per-race vectors by hand (24+ races × 20 packs by hand is where
transcription errors would live).

Implementation:

- Pydantic models with `extra="forbid"` — an unknown key in the YAML is an
  error, because a typoed field name would otherwise silently vanish.
- Schema is versioned (`schema_version: 0` in every file). Migrations are
  explicit scripts; never edit the meaning of an existing field in place.
- A lint pass beyond type validation: race names must resolve against the
  registry; every race appearing in the pack's events must be covered by the
  race→tier map; grant units must be within sane ranges; scoring rules must
  sum to something coherent. Lints are the same code path FR6's LLM
  extraction will later feed into — write them as functions over the parsed
  model, not as ad-hoc notebook checks.

### T4.2 Treatment vector derivation

`derive_treatment(pack, race_id) -> TreatmentVector` produces the per-race
feature vector of §6 (effective gold, primary/secondary skill counts,
stacking limits, star access, inducement access, games count, resurrection
flag; scoring-system features are pack-global and kept separate — see T5.4
for why they cannot enter as per-race differences).

Normalization decisions to fix once, in code:

- Express skill grants in comparable units across pack styles (some packs
  grant "N skills", some grant budget spendable on skills — convert both to
  counts of primary/secondary equivalents, and record the conversion rule in
  the annotation guide).
- Continuous features are standardized before entering the model. During
  evaluation, fit centering and scaling constants on the training packs in
  each fold only; the held-out pack is transformed with those constants and
  never contributes to them. The final production fit uses the full training
  corpus. Store the applicable constants with every fitted model artifact so
  new-pack queries use the same scaling.
- Effective gold budget is **not** a continuous linear feature — it has its
  own monotone-discrete structure, specified in T4.3.
- **Centering for identifiability**: the race baseline α_r absorbs any
  constant shift in that race's treatment across packs. Either center each
  race's treatment features over the pack corpus, or document that α_r means
  "baseline at corpus-average treatment for this race". Pick the first — it
  makes attribution outputs (FR11) read cleanly as deviations. As with
  scaling, evaluation-fold centering uses training packs only.

### T4.3 Budget: monotone discrete effect (PRD §6)

Budget effects are step-like (thresholds unlock roster configurations per
race) and tournament TVs are quantized, so budget enters as a monotone
discrete effect rather than a linear feature. Two stages sharing one
structure.

Gate stage (~20 packs):

- **Grid**: the observed distinct TVs across the training corpus (in
  practice ~50k quanta). Pool adjacent levels occupied by fewer than ~2
  packs. In leave-pack-out evaluation, construct the grid, occupancy counts,
  and pooling decisions independently inside each fold; the held-out pack
  must not affect them.
- **Effect**: monotone step increments over the grid — scale × cumulative
  simplex weights — with per-race deviations hierarchically shrunk toward
  the global pattern. The race-specific *level* of any step function is
  absorbed by α_r: parameterize increments only; do not add a per-race
  budget intercept.
- **Breakpoint tables**: hand-authored per-race thresholds
  (`race_id × roster_version → TV thresholds + rationale`), computed from
  deterministic roster math. Same QC and freeze discipline as descriptors
  (T5.5): independent second pass, reconciliation, frozen before
  `eval/GATE.md`. They enter twice: (a) informative priors for the
  per-race step deviations; (b) the **query-time placement rule** — a
  draft pack at an unobserved TV takes the enclosing interval's fitted
  increment placed at the race's breakpoint within that interval
  (piecewise-constant jump there), with proportional spread when the race
  has no breakpoint in that interval. Never interpolate linearly between
  grid points — that reintroduces the smooth-budget fiction this section
  removes. If the query lies outside training support, do not extrapolate
  additional increments: use the fitted contribution at the nearest support
  boundary and return `support_status = below_training_support` or
  `above_training_support`. Reports and APIs must surface the warning rather
  than present the boundary value as an in-distribution estimate.
- **Code contract**: the grid spec (cell edges + nesting map) is a
  parameter of the design-matrix/η builder, like θ's index set (T5.3) —
  the full-data upgrade below must be a configuration change, not a
  rewrite.

Full-data stage (W31; activated only when the milestone-3 corpus passes a
TV-cell occupancy check):

- Latent fine level: 10k cells nested in 50k parent buckets, monotone
  throughout, children shrunk toward their parent's increment
  (multi-resolution partial pooling). Where the corpus is dense the data
  localizes steps at 10k; where sparse, the fine level collapses to the
  coarse pattern.
- Breakpoint tables demote to priors only (the placement rule is
  superseded); posterior drift from the roster-math priors is reported as
  a diagnostic — the analogue of T5.5's descriptor-drift report.

## T5. Match model (FR7, FR8, FR8a–c)

This section is the heart of the document. The model is an ordinal
(W/D/L) regression with an **antisymmetric** linear predictor and
**symmetric** cutpoints. Getting the symmetry structure right is not
optional polish — it is what makes the model coherent under side-swapping
and what prevents several silent double-counting bugs. Why this form (and
why it is fully general, not a restriction): MODELING.md M2–M4.

Notation (authoritative table with rationale: M1): σ is the logistic
function 1/(1+e^(−x)); η the antisymmetric advantage of side A; c > 0 the
draw half-width (cutpoints ±c); θ_i latent coach ability; α_{r,v} the
baseline of race r at roster version v; z_{p,r} the derived treatment
vector of pack p for race r; γ_r race r's treatment-response coefficients;
f the observed NAF coach×race history proxy; m(r_A, r_B) = x̃_A′ M x̃_B the matchup
term over centered race descriptor vectors x̃_r with skew-symmetric M;
c0, κ, λ the
cutpoint intercept/scoring parameters; d_{r,v} the baseline race draw effect,
decomposed into β_flex·flex_{r,v} + u_{r,v}; s_p the pack's
scoring-incentive scalar; flex_r the strategic-flexibility descriptor.

### T5.1 Likelihood

For a match between side A and side B, define a scalar advantage η (positive
favors A) and a draw half-width c > 0. Ordered logistic with cutpoints
(−c, +c):

```
P(L) = σ(−c − η)
P(D) = σ(+c − η) − σ(−c − η)
P(W) = 1 − σ(+c − η)
```

Swapping sides maps η → −η and must map (W, D, L) → (L, D, W). With
cutpoints symmetric around zero this holds exactly. Do **not** use free
asymmetric cutpoints: side assignment is arbitrary in the data, so any
asymmetry the sampler finds is noise, and the swap-invariance property test
(T5.6) will fail. This form loses no generality — any side-swap-invariant
three-category cumulative model reduces to it, and per match (η, c) can
reach any W/D/L distribution exactly (M4). Why the logistic link
specifically (Rao–Kupper/Bradley–Terry lineage, tail behavior): M3.

### T5.2 Linear predictor

```
η = s(A) − s(B) + m(r_A, r_B)

s(side) = θ_coach                      # latent coach ability (T5.3)
        + α_{race, roster_version}     # race baseline
        + γ_race · z_{pack, race}      # race × treatment response (challenger only)
        + f(NAF_history_coach,race)    # weak observed-history proxy
```

Consequences of the difference structure — these are the mistakes waiting to
happen:

- **Anything common to both sides cancels.** Both players face the same
  pack, era, event type, and region. Therefore pack-global covariates, a
  global era offset, event type, and region have *no channel into η*. They
  can act only through (a) interactions with race (race×era = roster-version
  keying; race×treatment), or (b) the cutpoints (T5.4). The PRD's baseline
  "coach + race + matchup + era" (§9a) means race baselines keyed by roster
  version — not a global era coefficient, which would be unidentified.
  Similarly PS3's "region enters as a covariate" is about the *field/choice*
  side and residual diagnostics, not a term in η.
- **Race baselines are only identified relatively.** Impose a sum-to-zero
  constraint across the contemporaneously comparable race-version states
  active in each rules edition (or connected competition environment), not
  within an individual roster-version key. Under the primary BB2025-only
  plan this is simply the active BB2025 race set. If W5 activates BB2020
  pooling, parameterize BB2025 as the reference and add hierarchical
  per-race BB2020 deviations, then center the resulting active race strengths
  within each edition. Races absent from an edition are structurally missing.
- **Treatment effects are identified by within-race variation across
  packs** (hence PS1) and enter η as the difference
  γ_{r_A}·z_{p,r_A} − γ_{r_B}·z_{p,r_B}. Hierarchical pooling across races:
  γ_r ~ N(γ̄, Σ_γ), non-centered. γ̄ is the "generic race" response (e.g.
  "more skills helps everyone"); the per-race deviations are what the thesis
  gate is really testing.
- **Budget enters through the monotone-discrete structure of T4.3**, not as
  a linear z column. It still lives inside s(side) and enters η as a
  difference, so side-swap invariance is unaffected; its per-race
  deviations belong to the challenger's race×treatment block like any
  other treatment response.
- **Mirror matches** (r_A = r_B): race and treatment terms cancel and the
  matchup term is exactly zero. Keep these matches — they are pure signal
  for coach abilities and cutpoints. Dropping them biases coach estimates
  toward races that mirror often.

### T5.3 Coach ability (FR8b)

- v1: static latent `θ_i ~ N(0, σ_θ)`, non-centered, with a pooled prior on
  `σ_θ`. Infer it jointly from the permitted match history alongside race,
  matchup, treatment, and familiarity effects. New coaches receive the
  population prior; sparse coaches shrink toward it rather than receiving a
  fixed fallback score.
- Reconstruct coach posteriors inside every mask. The thesis gate excludes all
  matches belonging to the held-out pack; event validation excludes the
  held-out event; a prospective forecast uses matches strictly before its
  cutoff. Retrospective leave-pack-out evaluation may use other permitted
  matches on either side of the held-out event date, but must be labeled
  retrospective rather than historical forecasting.
- Preserve and propagate the posterior distribution, not only a point score.
  Any materialized summary carries `coach_id`, `as_of_date`, excluded
  pack/event, model version, posterior mean, and posterior SD.
- NAF Glicko is not a model input, prior, or cold-start value. It summarizes
  largely the same outcomes by coach×race without this model's ruleset and
  matchup adjustment, so using both risks double use and re-importing race
  effects. It may be evaluated as an external benchmark or, by an explicit
  later decision, used for material pre-dataset history unavailable here.
- Observed NAF race history: do **not** fit a free coach×race random effect in
  v1 — it is enormous, sparse, and will soak up matchup signal. Use
  `f = ψ·log(1+n_NAF)` as a weak predictive proxy, where `n_NAF` is computed
  strictly from earlier NAF matches via a tested as-of join. Do not call `ψ`
  a learning effect or treat zero as proof of inexperience: BB3, FUMBBL,
  league, casual, and unrecorded tabletop play are missing. No latent online
  exposure is fitted without linkable data. T7 defines gate sensitivities for
  this measurement error and first-observed-use selection.
- Deferred variant — experience *against* the opponent's race (or full
  matchup experience): plausibly real, concentrated in gimmick races
  (Vampires, Slann, stunties), but near-collinear with θ and α under
  proportional exposure and in need of a gimmickiness interaction to have
  teeth. Out of scope for v1; the mechanism, the collinearity argument,
  and the cheap residual probe that gates it are in M8/M11. The probe runs
  with the milestone-2 residual analysis (T7) — do not add the term before
  it shows signal.
- Milestone-4 upgrade (per FR8b): piecewise-constant θ per calendar year
  with a random-walk prior between years, pooled innovation variance.
  Structure the code so θ's index set is a parameter (coach vs. coach×year)
  rather than baking "one θ per coach" into the design matrix builder.

### T5.4 Draw propensity and scoring-system effects (FR8c)

The cutpoint model separates baseline race draw tendency from the response to
pack-global scoring incentives:

```
c = softplus( c0
            + d[r_A, v_A] + d[r_B, v_B]       # baseline race draw tendency
            + κ · s_p                          # global scoring shift
            + λ · s_p · (flex_A + flex_B) )    # flexibility response

d[r, v] = β_flex · flex[r, v] + u[r, v]
```

- `s_p`: scalar (or small vector) win-incentive feature of the pack's
  scoring system, standardized and centered so zero is the declared
  reference scoring environment. Deriving it is annotation-guide work: e.g.
  (win points − draw points) relative to draw points, plus bonus-point
  structure.
- `flex`: the tempo-control/strategic-flexibility descriptor (FR8a), keyed
  race × roster version and centered over the stored uniform edition
  reference. `β_flex` represents the baseline association between that
  ability and decisiveness; `λ` represents the additional response as scoring
  incentives move away from reference.
- `u[r,v]`: residual race/roster-version draw propensity for mechanisms not
  captured by flexibility. Give it a hierarchical prior and constrain its
  uniform mean across active race-version states in each edition to zero, so
  it cannot duplicate `c0`. Mirror matches, which receive `2d[r,v]`, provide
  especially clean information.
- The flexibility combination must be **symmetric** in A and B (sum here;
  max is defensible — a draw is broken by whichever side can break it — but
  start with sum for smoothness). An asymmetric form breaks side-swap
  invariance.
- softplus (or exp) keeps c > 0 — softplus preferred: near-linear away
  from zero, so the coefficients read as additive changes to the draw
  half-width, and its bounded gradient avoids exp's HMC-geometry failure
  modes (M5). Expected signature: λ < 0 under win-rewarding scoring — mass
  moves from D to both W and L for flexible races. `d`, `κ`, and `λ` are
  shared nuisance terms in the thesis-gate baseline and challenger; only the
  race×treatment block differs. The `λ` sign is advisory model validation,
  not a binding gate criterion.
- Note the symmetric-c channel is not a 50/50 split of vacated draw mass —
  the split follows η, favoring the stronger side (M6). What it *cannot*
  express is a directional edge for the more flexible side per se; that is
  a location effect, λ₂·s_p·(flex_A − flex_B) in η, deliberately deferred
  (identified only at pack-level N; see M6 and the M11 register).
- Do not fit free race-pair draw effects in v1. Use held-out
  posterior-predictive residuals to test whether symmetric pair structure
  remains after `d`; if it does, prefer a tightly regularized symmetric
  descriptor interaction over an unpooled parameter for every pair.

### T5.5 Matchup structure (FR8a)

v1 is descriptor-based. Let x_r be the descriptor vector (armour, agility/
mobility, strength access, stunty flag, flexibility, …) for race r at its
roster version.

- Before constructing matchup terms, center every descriptor column over a
  frozen reference distribution: uniform weights across races active in the
  relevant rules edition. Write `x̃_r = x_r − μ_x,edition` and store the
  edition, race list, descriptor schema version, weights, and means with the
  model artifact. BB2020 gets a separate reference only if W5 activates
  pooling. Never use observed or projected popularity as the weights, and do
  not recompute means for a query pack or new roster.
- Descriptor **main effects are already absorbed** by the free race
  baselines α — a term w·(x_A − x_B) is redundant and will just fight α in
  the posterior. The matchup term must contain only genuine *interactions*.
- Parameterize as a skew-symmetric bilinear form over centered descriptors:
  `m(A, B) = x̃_A' M x̃_B` with `M = −M'` (free parameters: the strictly
  upper triangle, K(K−1)/2 for K descriptors). This is automatically
  antisymmetric (m(A,B) = −m(B,A)) and zero for mirrors. Each M_kl reads as
  "descriptor k beats descriptor l" (e.g. armour beats low-strength bash;
  agility beats high-armour-low-mobility), which serves FR11-style
  interpretation.
- Centering additionally guarantees that the induced matchup matrix has zero
  weighted row mean (`C · w = 0`; `C · 1 = 0` under uniform weights). Thus M
  cannot reproduce a transitive `v_A − v_B` strength scale already carried by
  α. Skew-symmetry alone does not provide this separation.
- With ~5–8 descriptors this is 10–30 parameters — fit with a shrinkage
  prior (e.g. M_kl ~ N(0, τ), τ half-normal).
- Milestone-4 upgrade: learned low-rank skew-symmetric residual
  `C = U V' − V U'` per race (this is the standard disc/cyclic decomposition
  for intransitive games) **on top of** the descriptor term — they compose
  (FR8a). Gate it on data volume; ~25 races × sparse pairings will not
  identify it early, which is why v1 is descriptors-only.
- M is pack-invariant in v1. A registered extension makes it
  pack-dependent — M(p) = M0 + Σ_j u_{p,j}·ΔM_j, e.g. stacking
  permissiveness twisting the bash-vs-dodge cells — capturing matchup
  effects of pack levers beyond the field-average that γ already carries.
  Design sketch, the γ-centering requirement, and revival conditions:
  M11.1. Do not add ΔM terms ad hoc.

Descriptor authoring, QC, and iteration protocol — descriptors are a
hand-authored input that directly shapes the matchup term and the FR8c
flexibility interaction, so they get the same hygiene as pack annotations:

- **Values**: hand-authoring by the owner plus an independent second pass
  (LLM from roster sheets, or a second BB-literate human) with
  reconciliation produces the **prior**, not the final word. Predictive
  accuracy may then inform values through either of two sanctioned routes:
  - *Preferred*: fit descriptor values as latent quantities inside the
    model, with informative priors centered on the hand-authored values and
    a tight scale (e.g. SD ≈ 0.1 on a 0–1 descriptor scale) — a standard
    measurement-error treatment. Data pulls a value only where evidence is
    strong; sparse cases shrink to the prior; posterior drift from hand
    values is reported as a diagnostic of which intuitions the data
    disputes.
  - *Acceptable*: coarse manual iteration evaluated on the milestone-1
    leave-*event*-out splits, with every configuration tried logged.
  What stays out: free/unconstrained value fitting — that is a learned
  embedding, which sparse race pairings cannot identify and which is the
  milestone-4 low-rank residual's job. Note the identification asymmetry:
  matchup-relevant values are informed by match-level data (plentiful),
  but the flexibility value's FR8c role is identified at pack level
  (N≈20) — expect the prior to dominate there and do not chase it.
- **The descriptor set** (which columns, how defined) may be selected by
  predictive performance, but only: from a pre-declared candidate pool,
  evaluated on the milestone-1 leave-*event*-out splits (never the gate's
  leave-pack-out folds), with every configuration tried logged.
- **Freeze** before `eval/GATE.md` is committed — meaning the values (or,
  under the latent treatment, the prior means and scales) are fixed;
  changes after that are schema-v1 work. Iterating anything against the
  gate's leave-pack-out folds is never sanctioned.
- Sensitivity check at the gate: perturb descriptor values (or prior
  scales) and confirm gate conclusions survive.

### T5.6 Invariance and correctness tests (write these first)

Property-based tests, exact up to float tolerance:

1. **Side-swap invariance**: swapping (coach_a, race_a) ↔ (coach_b, race_b)
   and relabeling W↔L leaves the likelihood of the dataset unchanged.
2. **Mirror neutrality**: equal coaches, same race, same pack ⇒
   P(W) = P(L) exactly, for any parameter draw.
3. **Per-race centering invariance**: adding a constant to one race's
   treatment feature across every pack in the corpus leaves all match
   probabilities unchanged after re-derivation — the T4.2 centering absorbs
   it into α_r (a regression test on the design matrix builder). The
   transposed statement is **not** an invariant and must not be tested for:
   shifting every race's treatment within one pack legitimately changes
   predictions, because race-specific γ_r responses are the thesis — a pack
   granting everyone more skills helps some races more.
4. **Descriptor interaction centering**: for each edition reference, the
   induced matchup matrix satisfies `C · w = 0` (`C · 1 = 0` for uniform
   weights), while remaining skew-symmetric and mirror-zero.
5. **No-leakage**: experience and materialized coach-strength summaries use
   only data permitted by the event, pack, or prospective-time mask (test
   with synthetic timelines and split keys).
6. **Parameter recovery**: simulate data from known parameters at realistic
   sparsity (~20 packs, realistic coach/race distribution) and check the
   model recovers them within posterior uncertainty. Do this **before** the
   thesis gate — it also rehearses whether the gate has any power at N≈20
   packs, cheaply.

### T5.7 Fitting practice

- NUTS via NumPyro; non-centered parameterization for every hierarchical
  term (θ, γ_r, M entries under shared τ) — centered versions will funnel.
- Standardize all continuous inputs; keep the constants with the model
  artifact.
- Convergence gates on every fit (R̂ < 1.01, adequate ESS, no divergences)
  enforced in code — the CV harness runs ~20 unattended refits and a silent
  divergence in one fold corrupts the gate statistic.
- Keep a fast path (SVI or MAP with Laplace) for iteration, but every
  reported number (baseline yardstick, gate, forecasts) comes from NUTS.

## T6. Field-composition model (FR9, FR9a–c)

### T6.1 Choice model (FR9)

Per-coach multinomial logit over every race legal at the event. All features
are constructed from history strictly before that event.

```
U(n,r) = β_loy · exact_history(n,r)
       + β_last · last_race(n,r)
       + β_transfer · style_transfer(n,r)
       − β_complex · complexity_r · unfamiliarity(n,r)
       + β_pop · pop_r
       + β_fav · fav_r(field)
       + new_to_NAF(n,r) · (
           β_new
           + β_rep · repertoire_profile(n)
           + β_gain · favorability_advantage(n,r)
         )
       + intercept_r
```

- `exact_history` is a saturating summary of strictly prior NAF games/events
  with r. `new_to_NAF` means absent from the permitted NAF history, not newly
  purchased, newly learned, or unowned.
- `repertoire_profile` is a small vector whose effects exist only through the
  new-race interaction: effective repertoire breadth/entropy, historical
  event-to-event switching rate, and history depth. Many observations over a
  narrow repertoire are stronger friction evidence than a short record;
  sparse coach summaries are hierarchically shrunk.
- `style_transfer` uses a frozen low-dimensional similarity kernel over a
  reviewed bash↔agile coordinate and separate stunty dimension, aggregated
  over the coach's prior races. Do not summarize a broad repertoire only by
  its centroid: experience at both extremes must not look like experience only
  with hybrid races. `unfamiliarity` decreases with exact and transferable
  history.
- `complexity_r` is a reviewed entry-complexity descriptor separate from
  style. It is penalized only through unfamiliarity. Do not add a race-specific
  novelty axis; a general unusual-mechanics descriptor requires a residual
  pattern shared by multiple races.
- `favorability_advantage(n,r)` is r's favorability minus the best
  favorability among n's established legal races, with a documented cold-start
  convention when none exist. It allows a strong pack advantage to overcome
  soft repertoire friction. Every legal race retains nonzero probability.
- Fit on historical (coach, event, chosen race) rows. Only open events in
  the training set; squad events (EuroBowl) are excluded from fitting the
  individual-choice model (§5.1) and handled by the FR9c variant later.
- Popularity, exact history, switching, breadth, transfer, and last-race
  features use the same tested pre-event as-of discipline as T5.3. NAF history
  is a predictive proxy for a mixture of access, preference, online loyalty,
  and missing experience; coefficients are not labeled as any one cause.
- Race intercepts and popularity are near-collinear; if both are included,
  regularize and don't interpret them separately — or drop intercepts and
  let popularity carry it. Decide once, document in code.
- Favorability on historical choice rows must be cross-fitted. At minimum,
  fit the match model without the row's event before calculating that event's
  favorability; use leave-pack-out predictions when measuring generalization
  to unseen packs. Persist the split key with the generated feature so an
  in-sample favorability value cannot be substituted accidentally.
- Benchmark against the simpler exact-loyalty + popularity + favorability
  model. A hard consideration/ownership set is prohibited without direct
  access data. Nested or similarity-aware substitution is deferred until
  held-out residuals show a material IIA failure.

### T6.2 Favorability fixed point (FR9a)

```
field⁰   = choice model with fav = isolated race strength
fav^k_r  = Σ_o field^k_o · E[points r vs o | pack]      # from the match model, neutral coaches
field^k+1 = (1 − ρ) · field^k + ρ · choice(fav^k)       # damped update, ρ ≈ 0.5
```

`E[points]` is expected per-game base result points under the pack's W/D/L
values (the pack's win/draw/loss points weighted by the
match model probabilities), per FR9a — coaches optimize points, not winrate,
and draws are frequent. V1 does not add TD/CAS or other performance bonuses.
For a bonus-bearing pack, return `points_scope = base_result_only`,
`bonus_points_modeled = false`, and `bonus_rules_present = true`; annotating a
bonus rule or encoding its incentive in `s_p` does not calculate its expected
award.

Iterate to tolerance; expected 1–2 effective rounds because empirical
repertoire/history friction damps best-response (PRD §4). Always cap
iterations and log the trajectory —
convergence failure is diagnostic information, not an exception to swallow.

Uncertainty propagation for FR10: run the whole fixed point over joint draws
from both the match-model posterior and the field-choice coefficient
posterior (thinned, e.g. 200 draws), not once at either posterior mean. The
favorability→field→favorability loop is nonlinear; the mean of the pipeline
is not the pipeline of the mean, and the headline output's intervals (FR10)
must reflect uncertainty from both models flowing through field projection.

### T6.3 Equilibrium diagnostic (FR12)

Same payoff machinery, with empirical coach-history, repertoire/access
friction, and popularity terms removed, solved by **fictitious play**
(best-respond to the *running average* field, not the last iterate). Raw
best-response on an intransitive payoff matrix can cycle. Under 2/1/0 result
scoring the two-player payoff is constant-sum, so the running average has the
standard fictitious-play convergence guarantee. Under 3/1/0 scoring, TD/CAS
bonuses, or any other non-constant-sum utility, do not claim that guarantee.
In every case report the payoff convention, convergence trajectory, regret or
exploitability diagnostic, iteration cap, and multi-start results. Treat
non-convergence as a valid diagnostic result; choose and document a fallback
solver before supporting a non-constant-sum equilibrium in user-facing
output.
Implementation is ~50 lines on top of T6.2 — keep it in `equilibrium.py`,
clearly labeled diagnostic-only, with the PRD's caveats attached to its
output object rather than left to the UI layer to remember.

### T6.4 Swiss pairing (FR10 upgrade, milestone 4)

v1 aggregate forecasts assume random pairing against the projected field.
The upgrade is a Monte Carlo Swiss simulator (sample a field, simulate
rounds with winners-meet-winners pairing, accumulate per-race results).
Design the FR10 report to carry an explicit `pairing_assumption` field from
day one so validation comparisons (§8) are never ambiguous about which
assumption produced a number. Until the simulator exists, user-facing copy is
"expected performance against the projected field under random pairing",
not an unqualified "event winrate".

### T6.5 Design-contract gates for FR11 and FR9c

Before implementing FR11 attribution, commit a short estimand contract that
defines the reference pack, the feature-change counterfactual, and whether
the projected field is held fixed or recomputed. Attribution output is a
predictive counterfactual under the fitted model, not a causal estimate.

Before implementing FR9c, commit a short squad-model contract covering squad
membership, no-duplicate constraints, captain-level utility, coach-to-race
assignment, and how EuroBowl validation differs from open-event validation.
These contracts are milestone prerequisites; this document deliberately does
not select their algorithms in advance.

## T7. Evaluation harness and thesis gate (§8, §9a)

- The gate models share coach, race/roster-version, centered-descriptor
  matchup, baseline race draw, global scoring, and scoring×flexibility terms.
  The challenger adds only the hierarchical race×treatment response block.
- One harness, two split policies: leave-whole-**event**-out (milestone 1
  yardstick, predates pack annotation) and leave-whole-**pack**-out
  (milestone 2 gate and everything after). The split key is data, not code:
  a function from match table + registry → fold assignments, unit-tested so
  that no pack's events ever straddle train/test. Never random match splits
  (§8).
- Metrics per held-out fold: mean log-loss over matches; per-race predicted
  vs. actual winrate MAE; calibration (reliability of W/D/L probabilities).
- Gate computation (`eval/gate.py`), exactly as pre-registered: per-held-out
  pack paired log-loss differences (challenger − baseline), bootstrap over
  packs (resample packs, not matches — packs are the exchangeable unit),
  80% CI excluding zero; plus winrate-MAE improvement; plus the coefficient
  sign checks, operationalized as posterior probabilities with thresholds
  fixed in `eval/GATE.md` (stunty × skill-grant generosity > 0). The shared
  λ < 0 signature from T5.4 is reported only as advisory model validation;
  it cannot make the treatment-schema gate pass.
- Known-case anchors (§9a): each anchor compiles to a signed delta —
  challenger minus baseline predicted performance for the named race,
  averaged over held-out packs meeting the anchor's treatment condition —
  reported as a table in the gate report. Advisory, not binding.
- Heterogeneity diagnostic (§9a): fit `b[p,r] ~ N(0, τ_raw)` on top of the
  baseline and `b[p,r] ~ N(0, τ_residual)` on top of the challenger, with a
  sum-to-zero constraint across active races within each pack and non-centered
  parameterization. Predeclare a simulation-calibrated practical threshold
  `ε`; report `P(τ_raw > ε)`, intervals for both scales, and
  `P(τ_residual < τ_raw)`. A descriptive
  `1 − τ_residual²/τ_raw²` may be reported with its posterior uncertainty but
  is not a causal R². Where packs span multiple events, add within-pack
  held-event repeatability checks. These fits are diagnostic only: free
  effects for an unseen pack collapse to zero and cannot change the binding
  gate verdict.
- Training corpus: baseline and challenger must be fit on the same corpus
  for the paired comparison to isolate the pack×race terms — the
  milestone-1 full-corpus baseline is a yardstick only, never the gate
  comparator. Annotated-only vs. full-corpus-with-imputation is an open
  decision (§10 in the PRD, T10 here), made before `eval/GATE.md`.
- **Pre-registration is a file**: `eval/GATE.md`, committed before the
  challenger is ever fit to annotated packs, containing the pass criteria,
  the exact metric definitions, the training-corpus decision, and the
  known-case anchor list (§9a). The gate report links to the commit
  hash.
- **Power rehearsal precedes pre-registration**: the simulation study
  (T5.6.6) — data generated with known pack effects at realistic size —
  estimates the gate's detection power under candidate criteria. The
  simulated generative process includes the monotone budget structure
  (T4.3), including a correlated-levers scenario (budget correlated with
  other generosity features) — a flexible shape can absorb confounded
  signal, and the rehearsal is where that shows up. The final
  criteria (CI level, MAE margin) are set in light of that rehearsal, then
  frozen in `eval/GATE.md` along with the estimated power. Deciding this
  after seeing real-data results would make pre-registration theater; the
  rehearsal is the one legitimate input to criteria choice.
- Run order within milestone 2: known-case anchors drafted, then the
  exploratory correlation pass (§9a — per-race winrate vs. treatment
  features, stunty scatter as headline), then the power rehearsal, then
  commit `eval/GATE.md`, then the gate.
- Confound check (§8): report the coach×pack bipartite connectivity (PS7)
  and per-race switcher counts alongside the gate; sensitivity refit with
  non-switching coaches' race effects examined. The residual analysis also
  carries the advisory deferred-feature probes (M8, M11) — no refits, each
  gates its register entry: opponent-experience (residuals vs. opponent's
  prior exposure, matches against high-gimmick races), coach-style
  (per-coach residuals vs. opponent descriptors, high-volume coaches
  only), pack-dependent matchup misses (M11.1), and residual symmetric
  race-pair draw structure after T5.4's additive race effects. All such
  probes use held-out posterior-predictive residuals from the existing event- or
  pack-level folds, with uncertainty or detectable-effect limits reported.
  In-sample residual silence is not grounds for retiring a registered
  feature.
- NAF-history sensitivity (FR8d): rerun or re-evaluate the gate with no
  history term, `log(1+n_NAF)`, and coarse prior-history buckets; additionally
  report an established-history-only subset and a first-observed-race-use
  diagnostic. Hidden online/league specialists may enter NAF with a race when
  a favorable pack selects for them, so instability here is a treatment-effect
  confounding warning rather than evidence of a literal learning curve.

## T8. Known failure modes (checklist for implementers)

Each of these is a mistake that would produce plausible-looking but wrong
results. Review against this list before trusting any fitted model.

1. Binarizing W/D/L or modeling draws as 0.5 wins (violates FR7; draws are
   frequent and the scoring analysis in FR8c depends on them).
2. Emitting each match twice (once per side) — halves all posterior widths.
3. Asymmetric cutpoints or non-antisymmetric matchup terms — breaks
   side-swap invariance; T5.6 tests catch this.
4. Putting pack-global, era-global, region, or event-type covariates in η —
   they cancel and are unidentified; the sampler will return prior noise
   that downstream code then "interprets".
5. Descriptor main effects or uncentered descriptors in the matchup term —
   either lets M duplicate race baselines and destabilizes both posteriors.
6. Feeding NAF Glicko into the primary model, or materializing coach strength
   outside the applicable evaluation mask — double use or future leakage that
   inflates validation metrics.
7. Random match splits, or splitting a pack's events across train/test —
   leaks pack identity; the gate becomes meaningless.
8. Free race×pack interaction terms used as the predictive challenger — they
   cannot generalize to unseen packs. The only sanctioned free effects are the
   centered, heavily pooled, diagnostic-only variance fits in T7.
9. Zero-coding races absent from an era instead of structural missingness.
10. Dropping mirror matches or quarantined rows silently.
11. Fitting the field model on squad events (EuroBowl) — different choice
    process; it is validation data for FR9c, not training data for FR9.
12. Evaluating the fixed point / equilibrium only at the posterior mean —
    understates FR10 interval widths.
13. Deciding gate pass/fail criteria after seeing results — the reason
    `eval/GATE.md` exists (criteria may be informed by the simulation power
    rehearsal, never by real-data results).
14. Fitting descriptor values without informative priors (learned
    embeddings by another name), or iterating descriptor values/sets on the
    gate's leave-pack-out folds — see the protocol in T5.5. Data-informed
    values are fine; unaccounted-for search against the gate's evaluation
    is not.
15. Computing field-model popularity or loyalty features from data that
    includes the event being predicted — same leakage class as #6.
16. Treating budget as a linear feature, interpolating linearly between
    budget grid points at query time, or fitting free (non-monotone,
    unpooled) per-race breakpoints — the sanctioned structure is T4.3.
17. Calculating centering, scaling, budget grids, occupancy, or pooling from
    a held-out pack — preprocessing leakage that invalidates the fold.
18. Training the field model on in-sample favorability, or retiring a
    deferred feature using in-sample residuals.
19. Giving the challenger cutpoint terms absent from the baseline — the gate
    must differ only by the race×treatment response block.
20. Fitting free race-pair draw effects in v1 rather than first testing the
    held-out residual structure after hierarchical additive race effects.
21. Treating zero prior NAF games as zero total experience, or interpreting
    the NAF-history coefficient as a causal learning curve.
22. Removing an event-legal race from a coach's choice set merely because it
    is absent from NAF history; repertoire friction is soft and predictive,
    not an inferred ownership state.
23. Adding a coach-only repertoire feature equally to every race utility — it
    cancels from multinomial probabilities. Breadth/switching/history-depth
    effects must interact with new-to-observed-history status or another
    race-varying feature.

## T9. Work breakdown

Tasks are sized to be individually completable and reviewable. Dependencies
are listed; anything not listed as a dependency can proceed in parallel.

### Milestone 1 — data foundation and yardstick

| ID | Task | Depends on | Done when |
|---|---|---|---|
| W1 | Repo scaffold: pyproject, layout of T2, CI running pytest/ruff | — | `uv run pytest` green on empty test suite |
| W2 | Race registry + roster-version table + loaders | W1 | Every BB2020/BB2025 race resolvable; spans reviewed by owner |
| W3 | NAF ingestion → raw artifacts + tidy `match`/`event`/`coach` tables | W1, W2, NAF data access | Quarantine report < agreed threshold; row counts reconciled against source |
| W4 | Tourplay reconnaissance: ToS/rate-limit check, ruleset availability survey | W1 | Written go/no-go note on scraping; sample rulesets cached |
| W5 | Volume report → FR3 decision (BB2025-only vs. pooling) | W3 | Owner signs the decision; recorded in PRD or a decision log |
| W6 | Descriptor schema v0 + hand-authored descriptor tables (FR8a); per-race budget breakpoint tables (T4.3) | W2 | YAML validates; one-page rationale per descriptor; breakpoint thresholds carry roster-math rationale |
| W7 | Match model core: likelihood, η/c builders, invariance tests of T5.6 | W2 | Property tests pass; parameter recovery on toy data |
| W8 | Baseline model fit (masked coach + race[roster_version] + centered-descriptor matchup + shared cutpoints) | W3, W6, W7 | Convergence gates pass on full data |
| W9 | Eval harness with leave-event-out policy; baseline yardstick report | W8 | Yardstick metrics published in a report notebook |

### Milestone 2 — thesis gate

| ID | Task | Depends on | Done when |
|---|---|---|---|
| W10 | Annotation guide (one page) + pack schema v0 + lints (T4.1) | W2 | A trial pack annotates in ≤60 min; lints catch seeded errors |
| W11 | Pack selection: apply PS1–PS7; connectivity script for PS7; TV-spread check (PS1/T4.3 — the budget grid is identified only where packs differ). PS4 applied as: prefer 60+ coaches, hard floor ~25–30 for regional-coverage (PS3) slots | W3 | ~20-pack list with per-criterion justification incl. TV spread; owner approves |
| W12 | Annotate packs; double-annotate 3–4 (LLM second pass w/ quoted evidence) | W10, W11 | All YAML validates; disagreement review written up |
| W13 | Treatment-vector derivation + centering/standardization (T4.2) | W12 | Derivation unit-tested; centering-invariance test (T5.6.3) passes |
| W14 | Pre-register `eval/GATE.md`: criteria finalized using W15's power rehearsal, training-corpus decision, known-case anchor list (T7, §9a) | W10, W15 | Committed before W16 begins; estimated power documented alongside criteria |
| W15 | Exploratory correlation pass (§9a; stunty scatter headline); simulation-based power rehearsal (T5.6.6); descriptor table frozen (T5.5) | W13 | Both written up before the gate fit |
| W16 | Challenger model (shared baseline/cutpoints + race×treatment only) + leave-pack-out CV + gate report | W9, W13, W14 | Binding verdict + heterogeneity diagnostic + NAF-history sensitivities + confound/connectivity appendix (T7) |

### Milestone 3 — automated parsing (conditional on gate pass)

| ID | Task | Depends on | Done when |
|---|---|---|---|
| W17 | Tourplay importer (rulesets → pack schema) | W4, W16 | Imported packs pass the same lints as hand annotations |
| W18 | LLM PDF extraction: strict schema, verbatim evidence, lint pass, `unclear` routing (FR6) | W10, W16 | On held-back hand-annotated packs, extraction matches human annotation; `unclear` rate reported |

### Field model and outputs (start after W16; not gated on milestone 3)

| ID | Task | Depends on | Done when |
|---|---|---|---|
| W19 | Field choice model v1 (soft repertoire/switching + style transfer + complexity + popularity + favorability) | W3, W16 | History is as-of masked and favorability cross-fitted; richer model beats exact-loyalty baseline on held-out event field prediction or is simplified with a documented null |
| W20 | Favorability fixed point + posterior-draw propagation (T6.2) | W19 | Convergence logged; intervals reflect joint match- and field-model posterior draws |
| W21 | FR10/FR10a/FR11 report generator (random-pairing assumption, labeled) | W20 | FR11 estimand contract committed before implementation; end-to-end run on Eucalyptus Bowl pack |
| W22 | Equilibrium diagnostic (FR12) | W20 | Multi-start non-uniqueness check implemented; caveats embedded in output |

### Milestone 4 — gated refinements

| ID | Task | Depends on | Done when |
|---|---|---|---|
| W23 | Counter-pick study (gates FR9a interpretation) and build-response study (gates FR9b) | W3, W12 | Each a standalone write-up with a go/no-go |
| W24 | Meta-pressure features in match model (FR9b) | W23 (a pass) | Held-out improvement or documented null |
| W25 | Squad-event field model, validated on EuroBowl (FR9c) | W19 | FR9c squad-model contract committed before implementation; EuroBowl field reproduced better than the open-event model applied naively |
| W26 | Tourplay↔NAF coach linkage + roster-level features | W17 | Linkage precision audited on a labeled sample |
| W27 | Low-rank matchup residual (T5.5 upgrade) | W16 | Held-out improvement over descriptors-only, or documented null |
| W28 | Swiss-pairing simulator for FR10 | W21 | Forecasts labeled with pairing assumption; delta vs. random-pairing reported |
| W29 | Time-varying coach ability + gate-conclusion sensitivity check (FR8b) | W16 | Gate verdict re-checked under upgraded coach term |
| W30 | TD/CAS margin model (FR7 stretch) | data with margins | Only if margin data materializes |
| W31 | Latent fine-resolution budget hierarchy (10k-within-50k, T4.3) | W16, W17 | Activated only if the TV-cell occupancy check passes; posterior drift vs. breakpoint priors reported |

## T10. Open technical decisions (deliberately deferred)

- NAF data format and access path — blocks W3; everything downstream is
  written against the tidy tables, so the blast radius of surprises is
  confined to `ingest/naf.py`.
- Whether BB2020 pooling is invoked is decided at W5 per FR3; BB2025-only
  remains primary. If activated, T5.2 fixes the BB2025-reference structure;
  W5 still chooses shrinkage, old-match downweighting, and sensitivity
  settings. Roster-version keying (T3.2) lets either path use the same schema.
- Gate training corpus — matched annotated-only corpora vs. full corpus
  with treatment terms active only where annotated (PRD §10). Decided at
  W14, before `eval/GATE.md`; the power rehearsal (W15) simulates whichever
  is chosen.
- Treatment composites and residual `Σ_γ` structure — paused for the
  domain/statistical review in `DOMAIN_EXPERT_REVIEW.md`. Freeze at most two
  or three mechanistic composites before schema v0; then choose the residual
  covariance, with diagonal per-feature scales the conservative candidate.
- Exact descriptor list and scoring-incentive feature definition — W6/W10
  authoring work, expected to be revised at schema v1 after the gate's
  residual analysis (§9a).
- Field-choice bash↔agile/stunty geometry and entry-complexity rubric — also
  reviewed in `DOMAIN_EXPERT_REVIEW.md`, but downstream of the treatment gate.
  Freeze before W19 and validate against the simpler exact-loyalty model.
- Unscheduled candidate features (opponent-race/matchup experience,
  flexibility-difference scoring term in η) are deliberately out of scope
  for v1 — registered with mechanisms and revival conditions in M11; they
  are not open decisions and should not be added ad hoc.
- Web UI stack (FR13) — untouched until milestone-2 outputs exist.
  **Warning for the notebook phase**: no persistent model-artifact/query
  boundary exists yet, which is fine — but notebooks must only call `src/`
  code, and fitted posteriors/fixed-point results must be serializable
  artifacts on disk, not state living in a kernel. The eventual UI will
  need exactly that boundary; don't let notebook-only state accrete.
