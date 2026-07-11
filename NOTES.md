# Decision notes

Working decisions from review discussions. Approved decisions are propagated
into `PRD.md`, `MODELING.md`, and `TECHNICAL.md` unless a section explicitly
says it is paused or awaiting expert refinement. The self-contained review
request is `DOMAIN_EXPERT_REVIEW.md`.

## 2026-07-12 — Upstream model corrections

### Thesis-gate isolation — approved

- Put both scoring cutpoint terms — the global `κ · s_p` term and the
  scoring×flexibility `λ · s_p · (flex_A + flex_B)` term — in the baseline
  and challenger.
- Make the race×treatment response block `γ` the predictive difference
  between the models.
- Keep the `λ` sign check as advisory model validation, not a binding
  treatment-schema gate criterion.

### Matchup-descriptor centering — approved

- Center matchup descriptors over a stored reference race distribution before
  constructing the bilinear matchup term.
- Use uniform weights across the races available in the relevant rules
  edition, with separate stored BB2020 and BB2025 references if both are
  modeled.
- Store the race list, descriptor version, weights, and means with the model.
- Do not recenter using projected field popularity or at query time.

### Coach strength and Glicko — approved direction

- Drop NAF Glicko from the primary match model and retain it as an external
  benchmark. Any later use of material pre-dataset history available only
  through Glicko requires a separate decision.
- Infer coach strength directly and jointly from match history as a
  zero-centered hierarchical latent, alongside race, matchup, pack, and
  familiarity effects.
- Refit or reconstruct coach strength inside every evaluation mask:
  leave-pack-out for the thesis gate, leave-event-out for event validation,
  and strictly pre-cutoff history for prospective forecasts.
- Treat retrospective pack validation and prospective forecasting as distinct
  estimands and label them accordingly.
- Preserve the coach-strength posterior distribution in modeling and propagate
  it through predictions; any displayed scalar rating is a derived summary.
- New coaches receive the population prior, while sparse-history coaches are
  shrunk toward it with appropriately wider uncertainty.
- Store auditable provenance with derived coach-strength summaries, including
  `coach_id`, `as_of_date`, excluded pack/event, model version, posterior mean,
  and posterior standard deviation.
- Defer time-varying coach strength to a later static-versus-dynamic sensitivity
  analysis rather than expressing time variation as multiple priors on one
  static latent.

### Race draw propensity — approved

- Add symmetric, hierarchical race/roster-version draw effects to the
  cutpoint model and include them identically in baseline and challenger.
- Interpret the race contribution at reference scoring as a descriptor-linked
  effect plus a residual, initially centered on strategic flexibility:
  `d_r = β_flex · centered_flex_r + u_r`.
- Retain the scoring×flexibility term as a distinct response slope: the shared
  ability to control tempo or take scoring risks may affect both baseline
  decisiveness and the response to win-heavy scoring without the two terms
  representing the same statistical contrast.
- Center scoring incentive and flexibility so `d_r` describes reference
  scoring and `λ` describes movement away from it.
- Constrain residual race draw effects for identifiability and hierarchically
  shrink sparsely observed races toward the descriptor-based expectation.
- Do not initially add free race-pair draw parameters. Use held-out residual
  diagnostics to test for remaining symmetric matchup-specific draw structure;
  if warranted, prefer a tightly regularized symmetric descriptor interaction
  over a free parameter for every pair.
- Treat these as mechanistically motivated predictive effects, not identified
  causal coefficients.

### BB2020 pooling constraint — approved, conditional only

- Keep BB2025-only as the primary plan. BB2020 remains on the backburner and
  is introduced only if the W5 volume check shows it is necessary.
- Replace the invalid "sum-to-zero within each roster-version block" wording
  with a constraint across the contemporaneously comparable races active in a
  rules edition or connected competition environment.
- If pooling is activated, use BB2025 as the reference and model hierarchical
  per-race BB2020 deviations, with races absent from an edition structurally
  missing.
- Decide exact shrinkage, old-match downweighting, and sensitivity settings at
  W5; this approval does not activate or fully specify the fallback now.

### V1 bonus-point scope — approved

- Define v1 favorability as expected **base result points** from modeled W/D/L
  probabilities and the pack's win/draw/loss point values.
- Do not claim TD/CAS or other performance bonuses are included without a
  validated margin/bonus model.
- Detect bonus rules and return explicit scope metadata, including that bonus
  rules are present but omitted from expected points.
- Bonus structures may still contribute to the scoring-incentive feature as a
  predictive description of player incentives; that does not calculate
  expected bonus awards.
- Preserve TD/CAS source columns and report their coverage. Activate
  bonus-inclusive expected points only after margin data and a conditional
  model pass validation.

### Pack×race heterogeneity diagnostic — approved

- Add a diagnostic-only, heavily pooled free pack×race variance component,
  centered across active races within each pack.
- Fit it first on top of the shared baseline to estimate raw unexplained
  pack-associated race heterogeneity, then on top of the treatment challenger
  to estimate residual heterogeneity after schema v0.
- Predeclare a simulation-calibrated practically negligible threshold rather
  than testing whether the continuous variance is exactly zero.
- Report posterior uncertainty, the probability of material raw
  heterogeneity, and whether residual heterogeneity is smaller; any explained
  fraction is descriptive and non-causal.
- Where a pack spans multiple events, test whether effects estimated from some
  events repeat in the others. Always include connectivity, region, event-type,
  and natural-contrast caveats.
- The free effects cannot predict an unseen pack and cannot pass or soften the
  binding treatment-schema gate. They only distinguish "little heterogeneity"
  from "heterogeneity exists but schema v0 missed it."

### Field choice: loyalty, repertoire friction, and switching — approved

- Keep every event-legal race possible; never infer a hard ownership set or
  assign zero probability solely because a race is absent from NAF history.
- Model exact-race loyalty from strictly prior NAF games/events and the last
  race used.
- Model a soft new-to-observed-history penalty. Let observed repertoire
  breadth/entropy and historical switching rate modify that penalty; long,
  narrow histories are stronger evidence of friction than short histories.
- Add low-dimensional transferable style experience using a frozen
  bash↔agile axis plus a separate stunty dimension.
- Add a reviewed entry-complexity descriptor interacting with unfamiliarity;
  complexity is separate from style.
- Allow a candidate race's favorability advantage over the coach's best
  established option to overcome switching friction.
- Interpret NAF history as predictive evidence of observed repertoire, not
  ownership, purchase, borrowing, poverty, total experience, or causal
  loyalty. Online, league, casual, and unrecorded tabletop play remain known
  missing exposure.
- In the match model, keep prior NAF race games only as a weak predictive
  familiarity proxy. Test the treatment gate with no-history, `log(1+n)`,
  coarse-bucket, established-history-only, and first-observed-use
  sensitivities because hidden online specialists may adopt races selected by
  favorable packs.

#### Promising deferred extensions

- **Linked online/league experience:** incorporate BB3, FUMBBL, or league
  history only if coach linkage and coverage can be audited; then replace the
  NAF-only proxy with an explicitly multi-source exposure measure.
- **Style-transfer in match performance:** extend familiarity beyond the exact
  race only if held-out outcome residuals show that experience on nearby
  bash/agile or stunty styles predicts performance after exact NAF history and
  coach strength are controlled.
- **Nested or similarity-aware substitution:** replace ordinary multinomial
  logit only if held-out choice residuals show a material IIA pattern, such as
  new elf-like alternatives drawing implausibly from unrelated bash races.
- **Observed access/ownership model:** use a richer consideration stage only
  if surveys, roster inventories, borrowing records, or another direct access
  signal becomes available; NAF absence alone is insufficient.
- **Additional unusual-mechanics descriptor:** add a reviewed low-dimensional
  "gimmick/novel mechanics" feature only if complexity plus bash/agile/stunty
  geometry systematically misses first-use choices for multiple races. Do not
  create a race-specific axis for a single outlier.
- **Heterogeneous meta-switching:** add a strongly pooled coach-level random
  switching or favorability-response coefficient only if coaches with enough
  repeated events show stable differences that improve held-out prediction.

Free coach×race choice effects, hard ownership sets inferred from NAF, and
high-dimensional learned race embeddings are not default revival candidates;
their sparsity or interpretability problems remain fundamental without new
data.
