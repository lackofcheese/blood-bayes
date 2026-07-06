# Technical design: bb-stats

Status: draft · Companion to PRD.md (PRD is the source of truth for *what*;
this document specifies *how*). Section references (§, FR, PS) point into the
PRD unless prefixed with T (this document).

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
- `naf_rating_snapshot` (optional, FR8b): per coach × race × month, mu/phi —
  only ever joined **as of tournament start date** (T5.7).

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
  NAF numbers (not names only), tournament metadata, and whether historical
  monthly Glicko snapshots exist — the FR8b lagged prior is contingent on
  snapshots; if only current ratings exist, the prior is dropped (T5.3),
  not approximated.
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
- Continuous features are standardized (z-scored over the annotated pack
  corpus) before entering the model; store the standardization constants
  with the fitted model so new-pack queries use the same scaling.
- **Centering for identifiability**: the race baseline α_r absorbs any
  constant shift in that race's treatment across packs. Either center each
  race's treatment features over the pack corpus, or document that α_r means
  "baseline at corpus-average treatment for this race". Pick the first — it
  makes attribution outputs (FR11) read cleanly as deviations.

## T5. Match model (FR7, FR8, FR8a–c)

This section is the heart of the document. The model is an ordinal
(W/D/L) regression with an **antisymmetric** linear predictor and
**symmetric** cutpoints. Getting the symmetry structure right is not
optional polish — it is what makes the model coherent under side-swapping
and what prevents several silent double-counting bugs.

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
(T5.6) will fail.

### T5.2 Linear predictor

```
η = s(A) − s(B) + m(r_A, r_B)

s(side) = θ_coach                      # latent coach ability (T5.3)
        + α_{race, roster_version}     # race baseline
        + γ_race · z_{pack, race}      # race × treatment response (challenger only)
        + f(experience_coach,race)     # coach×race familiarity
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
  constraint on α within each roster-version block (or pin a reference
  race). Prefer sum-to-zero: it keeps priors interpretable and doesn't make
  one race's posterior artificially exact.
- **Treatment effects are identified by within-race variation across
  packs** (hence PS1) and enter η as the difference
  γ_{r_A}·z_{p,r_A} − γ_{r_B}·z_{p,r_B}. Hierarchical pooling across races:
  γ_r ~ N(γ̄, Σ_γ), non-centered. γ̄ is the "generic race" response (e.g.
  "more skills helps everyone"); the per-race deviations are what the thesis
  gate is really testing.
- **Mirror matches** (r_A = r_B): race and treatment terms cancel and the
  matchup term is exactly zero. Keep these matches — they are pure signal
  for coach abilities and cutpoints. Dropping them biases coach estimates
  toward races that mirror often.

### T5.3 Coach ability (FR8b)

- v1: static latent θ_i ~ N(μ_i, σ_θ), non-centered, with σ_θ hierarchical.
- Optional prior mean from NAF Glicko: μ_i = δ · standardized(mu_i as of the
  match's tournament start). **Leakage rule**: any Glicko value used for a
  match must be computed from ratings published strictly before that
  tournament. If snapshot history isn't available, set μ_i = 0 and rely on
  pooling — do not substitute current ratings "just for initialization";
  they encode the outcomes being predicted.
- Familiarity: do **not** fit a free coach×race random effect in v1 — it is
  enormous, sparse, and will soak up matchup signal. Use a parametric
  experience curve: f = ψ · log(1 + prior games of this coach with this
  race), where "prior" is computed strictly from earlier matches (another
  leakage point: compute it in the data layer with an as-of join, and test
  it).
- Milestone-4 upgrade (per FR8b): piecewise-constant θ per calendar year
  with a random-walk prior between years, pooled innovation variance.
  Structure the code so θ's index set is a parameter (coach vs. coach×year)
  rather than baking "one θ per coach" into the design matrix builder.

### T5.4 Cutpoints and scoring-system effects (FR8c)

Scoring systems are pack-global, so (per T5.2) they cannot enter η. Both
FR8c channels live in the cutpoints:

```
c = softplus( c0
            + κ · s_p                          # (a) global draw-propensity shift
            + λ · s_p · (flex_A + flex_B) )    # (b) flexibility interaction
```

- `s_p`: scalar (or small vector) win-incentive feature of the pack's
  scoring system, standardized. Deriving it is annotation-guide work: e.g.
  (win points − draw points) relative to draw points, plus bonus-point
  structure.
- `flex`: the tempo-control/strategic-flexibility descriptor (FR8a), keyed
  race × roster version.
- The flexibility combination must be **symmetric** in A and B (sum here;
  max is defensible — a draw is broken by whichever side can break it — but
  start with sum for smoothness). An asymmetric form breaks side-swap
  invariance.
- softplus (or exp) keeps c > 0. Expected signature for the gate's sanity
  check (§9a): λ < 0 under win-rewarding scoring — mass moves from D to
  both W and L for flexible races.

### T5.5 Matchup structure (FR8a)

v1 is descriptor-based. Let x_r be the descriptor vector (armour, agility/
mobility, strength access, stunty flag, flexibility, …) for race r at its
roster version.

- Descriptor **main effects are already absorbed** by the free race
  baselines α — a term w·(x_A − x_B) is redundant and will just fight α in
  the posterior. The matchup term must contain only genuine *interactions*.
- Parameterize as a skew-symmetric bilinear form:
  `m(A, B) = x_A' M x_B` with `M = −M'` (free parameters: the strictly
  upper triangle, K(K−1)/2 for K descriptors). This is automatically
  antisymmetric (m(A,B) = −m(B,A)) and zero for mirrors. Each M_kl reads as
  "descriptor k beats descriptor l" (e.g. armour beats low-strength bash;
  agility beats high-armour-low-mobility), which serves FR11-style
  interpretation.
- With ~5–8 descriptors this is 10–30 parameters — fit with a shrinkage
  prior (e.g. M_kl ~ N(0, τ), τ half-normal).
- Milestone-4 upgrade: learned low-rank skew-symmetric residual
  `C = U V' − V U'` per race (this is the standard disc/cyclic decomposition
  for intransitive games) **on top of** the descriptor term — they compose
  (FR8a). Gate it on data volume; ~25 races × sparse pairings will not
  identify it early, which is why v1 is descriptors-only.

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
3. **Pack-global cancellation**: adding a constant to every race's treatment
   vector within a pack leaves all match probabilities unchanged (given the
   centering convention of T4.2, this is a regression test on the design
   matrix builder).
4. **No-leakage**: the experience feature and Glicko prior for a match
   depend only on strictly earlier data (test with a synthetic timeline).
5. **Parameter recovery**: simulate data from known parameters at realistic
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

Per-coach multinomial logit over available races at an event:

```
U(coach n, race r) = a · loyalty(n, r)      # e.g. log(1 + prior events with r), plus last-race indicator
                   + b · pop_r              # recent global/regional pick share
                   + c · fav_r(field)       # field-conditional favorability (T6.2)
                   + intercept_r
```

- Fit on historical (coach, event, chosen race) rows. Only open events in
  the training set; squad events (EuroBowl) are excluded from fitting the
  individual-choice model (§5.1) and handled by the FR9c variant later.
- The popularity feature has the same leakage exposure as Glicko: "recent
  pick share" must be computed strictly from pre-event data via the same
  as-of-join discipline as T5.3, and tested the same way.
- Loyalty is expected to dominate — that is real (miniature ownership, per
  FR9) and not a modeling failure. Don't interpret the coefficient as pure
  preference in any output text.
- Race intercepts and popularity are near-collinear; if both are included,
  regularize and don't interpret them separately — or drop intercepts and
  let popularity carry it. Decide once, document in code.

### T6.2 Favorability fixed point (FR9a)

```
field⁰   = choice model with fav = isolated race strength
fav^k_r  = Σ_o field^k_o · E[winrate r vs o | pack]     # from the match model, neutral coaches
field^k+1 = (1 − ρ) · field^k + ρ · choice(fav^k)       # damped update, ρ ≈ 0.5
```

Iterate to tolerance; expected 1–2 effective rounds because loyalty damps
best-response (PRD §4). Always cap iterations and log the trajectory —
convergence failure is diagnostic information, not an exception to swallow.

Uncertainty propagation for FR10: run the whole fixed point per posterior
draw (thinned, e.g. 200 draws), not once at the posterior mean. The
favorability→field→favorability loop is nonlinear; the mean of the pipeline
is not the pipeline of the mean, and the headline output's intervals (FR10)
must reflect match-model uncertainty flowing through field projection.

### T6.3 Equilibrium diagnostic (FR12)

Same payoff machinery, loyalty term removed, solved by **fictitious play**
(best-respond to the *running average* field, not the last iterate). Raw
best-response on an intransitive payoff matrix cycles; fictitious play's
average converges to a mixed equilibrium and cycling manifests as mixing —
this is the intended behavior, per the PRD. Multi-start (different initial
fields) to detect non-uniqueness; report all distinct limits found.
Implementation is ~50 lines on top of T6.2 — keep it in `equilibrium.py`,
clearly labeled diagnostic-only, with the PRD's caveats attached to its
output object rather than left to the UI layer to remember.

### T6.4 Swiss pairing (FR10 upgrade, milestone 4)

v1 aggregate forecasts assume random pairing against the projected field.
The upgrade is a Monte Carlo Swiss simulator (sample a field, simulate
rounds with winners-meet-winners pairing, accumulate per-race results).
Design the FR10 report to carry an explicit `pairing_assumption` field from
day one so validation comparisons (§8) are never ambiguous about which
assumption produced a number.

## T7. Evaluation harness and thesis gate (§8, §9a)

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
  sign checks (stunty × skill-grant generosity > 0; λ < 0 per T5.4).
- **Pre-registration is a file**: `eval/GATE.md`, committed before the
  challenger is ever fit to annotated packs, containing the pass criteria
  and the exact metric definitions. The gate report links to the commit
  hash.
- **Power rehearsal precedes pre-registration**: the simulation study
  (T5.6.5) — data generated with known pack effects at realistic size —
  estimates the gate's detection power under candidate criteria. The final
  criteria (CI level, MAE margin) are set in light of that rehearsal, then
  frozen in `eval/GATE.md` along with the estimated power. Deciding this
  after seeing real-data results would make pre-registration theater; the
  rehearsal is the one legitimate input to criteria choice.
- Run order within milestone 2: stunty-vs-generosity scatter first (§9a
  pre-test), then the power rehearsal, then commit `eval/GATE.md`, then the
  gate.
- Confound check (§8): report the coach×pack bipartite connectivity (PS7)
  and per-race switcher counts alongside the gate; sensitivity refit with
  non-switching coaches' race effects examined.

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
5. Descriptor main effects in the matchup term — redundant with race
   baselines; produces unstable, uninterpretable posteriors for both.
6. Using current NAF Glicko ratings (or any not-strictly-lagged feature) —
   future leakage that inflates every validation metric.
7. Random match splits, or splitting a pack's events across train/test —
   leaks pack identity; the gate becomes meaningless.
8. Free race×pack interaction terms instead of race×treatment-vector terms —
   ~20 packs cannot identify them; hierarchical treatment interactions are
   the design (§6, FR8).
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
15. Computing field-model popularity features from data that includes the
    event being predicted — same leakage class as #6.

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
| W6 | Descriptor schema v0 + hand-authored descriptor tables (FR8a) | W2 | YAML validates; one-page rationale per descriptor |
| W7 | Match model core: likelihood, η builder, invariance tests of T5.6 (1–4) | W2 | Property tests pass; parameter recovery on toy data |
| W8 | Baseline model fit (coach + race[roster_version] + descriptor matchup) | W3, W6, W7 | Convergence gates pass on full data |
| W9 | Eval harness with leave-event-out policy; baseline yardstick report | W8 | Yardstick metrics published in a report notebook |

### Milestone 2 — thesis gate

| ID | Task | Depends on | Done when |
|---|---|---|---|
| W10 | Annotation guide (one page) + pack schema v0 + lints (T4.1) | W2 | A trial pack annotates in ≤60 min; lints catch seeded errors |
| W11 | Pack selection: apply PS1–PS7; connectivity script for PS7. PS4 applied as: prefer 60+ coaches, hard floor ~25–30 for regional-coverage (PS3) slots | W3 | ~20-pack list with per-criterion justification; owner approves |
| W12 | Annotate packs; double-annotate 3–4 (LLM second pass w/ quoted evidence) | W10, W11 | All YAML validates; disagreement review written up |
| W13 | Treatment-vector derivation + centering/standardization (T4.2) | W12 | Derivation unit-tested; pack-global cancellation test (T5.6.3) passes |
| W14 | Pre-register `eval/GATE.md`; criteria finalized using W15's power rehearsal (T7) | W10, W15 | Committed before W16 begins; estimated power documented alongside criteria |
| W15 | Stunty scatter pre-test; simulation-based power rehearsal (T5.6.5); descriptor table frozen (T5.5) | W13 | Both written up before the gate fit |
| W16 | Challenger model (race×treatment, FR8c cutpoints) + leave-pack-out CV + gate report | W9, W13, W14 | Gate verdict + confound/connectivity appendix (T7) |

### Milestone 3 — automated parsing (conditional on gate pass)

| ID | Task | Depends on | Done when |
|---|---|---|---|
| W17 | Tourplay importer (rulesets → pack schema) | W4, W16 | Imported packs pass the same lints as hand annotations |
| W18 | LLM PDF extraction: strict schema, verbatim evidence, lint pass, `unclear` routing (FR6) | W10, W16 | On held-back hand-annotated packs, extraction matches human annotation; `unclear` rate reported |

### Field model and outputs (start after W16; not gated on milestone 3)

| ID | Task | Depends on | Done when |
|---|---|---|---|
| W19 | Field choice model v1 (loyalty + popularity + favorability) | W3, W16 | Held-out event field prediction beats popularity-only baseline |
| W20 | Favorability fixed point + posterior-draw propagation (T6.2) | W19 | Convergence logged; intervals reflect posterior draws |
| W21 | FR10/FR10a/FR11 report generator (random-pairing assumption, labeled) | W20 | End-to-end run on Eucalyptus Bowl pack |
| W22 | Equilibrium diagnostic (FR12) | W20 | Multi-start non-uniqueness check implemented; caveats embedded in output |

### Milestone 4 — gated refinements

| ID | Task | Depends on | Done when |
|---|---|---|---|
| W23 | Counter-pick study (gates FR9a interpretation) and build-response study (gates FR9b) | W3, W12 | Each a standalone write-up with a go/no-go |
| W24 | Meta-pressure features in match model (FR9b) | W23 (a pass) | Held-out improvement or documented null |
| W25 | Squad-event field model, validated on EuroBowl (FR9c) | W19 | EuroBowl field reproduced better than the open-event model applied naively |
| W26 | Tourplay↔NAF coach linkage + roster-level features | W17 | Linkage precision audited on a labeled sample |
| W27 | Low-rank matchup residual (T5.5 upgrade) | W16 | Held-out improvement over descriptors-only, or documented null |
| W28 | Swiss-pairing simulator for FR10 | W21 | Forecasts labeled with pairing assumption; delta vs. random-pairing reported |
| W29 | Time-varying coach ability + gate-conclusion sensitivity check (FR8b) | W16 | Gate verdict re-checked under upgraded coach term |
| W30 | TD/CAS margin model (FR7 stretch) | data with margins | Only if margin data materializes |

## T10. Open technical decisions (deliberately deferred)

- NAF data format and access path — blocks W3; everything downstream is
  written against the tidy tables, so the blast radius of surprises is
  confined to `ingest/naf.py`.
- Whether BB2020 pooling is invoked and its exact era-adjustment structure —
  decided at W5 per FR3; the roster-version keying (T3.2) is designed so
  either answer slots in without schema change.
- Exact descriptor list and scoring-incentive feature definition — W6/W10
  authoring work, expected to be revised at schema v1 after the gate's
  residual analysis (§9a).
- Web UI stack (FR13) — untouched until milestone-2 outputs exist.
  **Warning for the notebook phase**: no persistent model-artifact/query
  boundary exists yet, which is fine — but notebooks must only call `src/`
  code, and fitted posteriors/fixed-point results must be serializable
  artifacts on disk, not state living in a kernel. The eventual UI will
  need exactly that boundary; don't let notebook-only state accrete.
