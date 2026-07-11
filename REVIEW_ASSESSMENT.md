# Assessment of the three review documents

Verdict on `TECHNICAL_REVIEW.md`, `MODELING_REVIEW.md`, and
`MODELING_PERSPECTIVES.md`, after checking their load-bearing claims
against `PRD.md`, `TECHNICAL.md`, and `MODELING.md`.

Summary: the two review documents are accurate and well-referenced —
nearly all findings are endorsed as real issues. The perspectives
document is what it says it is: defensible taste, about half of which is
worth acting on. The recommended fix sequence is at the end.

## 1. TECHNICAL_REVIEW.md — agree with all 12; top-6 priority is right

Independently verified:

- **#1 (gate isolation): confirmed.** W16's challenger adds both
  race×treatment and the FR8c cutpoint terms while the baseline cutpoint
  is bare `c0` ([TECHNICAL.md:667](TECHNICAL.md#L667),
  [TECHNICAL.md:680](TECHNICAL.md#L680)). The global `κ·s_p`
  draw-propensity term applies to held-out packs (s_p is annotated), so
  the gate could clear on draw-rate modeling alone — not the PRD's
  thesis. Additional wrinkle the review does not mention: the PRD is
  internally ambiguous — §9a's challenger definition says only
  "+ race×treatment interactions" ([PRD.md:363](PRD.md#L363)), yet pass
  criterion (c) checks the FR8c λ signature. Putting `κ·s_p` in both
  models is the right fix.
- **#3 (coach prior): confirmed, genuinely inconsistent.** A single
  static θ_i cannot have a per-match prior mean, and T5.3 specifies
  exactly that ("as of the match's tournament start",
  [TECHNICAL.md:318](TECHNICAL.md#L318)). Not pedantry: as written it is
  unimplementable without an arbitrary choice someone would make
  silently.
- **#9 (fictitious play): confirmed, and sharpened.** Under 2/1/0
  scoring the payoff matrix is exactly constant-sum
  (E[pts A] + E[pts B] = 2·P(W) + 2·P(L) + 2·P(D) = 2), so Robinson's
  theorem applies and T6.3's convergence claim holds. Under 3/1/0 the
  sum is 3 − P(D) — draws break constant-sum by exactly the draw mass,
  which is large in this game. The failure case is not exotic; it is one
  of the two most common scoring systems.
- **#2 (bonus points): confirmed.** Straightforward PRD↔TECHNICAL
  contradiction: FR9a promises expected points under TD/CAS bonus
  scoring ([PRD.md:221](PRD.md#L221)); T6.2 computes points from W/D/L
  only ([TECHNICAL.md:517](TECHNICAL.md#L517)) and no margin model
  exists in v1. Requires an explicit scope decision (base result points
  only in v1, stated) or a small conditional bonus model.
- **#5 (fold-local preprocessing): confirmed.** The sharpest sub-point
  is the undefined query behavior for a held-out TV outside training
  support (no enclosing interval exists under the T4.3 placement rule),
  not the z-scoring itself, whose leakage effect is small but easy to
  eliminate.
- **#6 (field-model cross-fitting): confirmed.** In-sample favorability
  would inflate β_fav; T6.2's uncertainty propagation is also ambiguous
  about whether field-model coefficient posteriors are sampled.

On **#4** (BB2020 pooling): T10 does explicitly defer the structure, but
the review's ask — a structural contract like `alpha[r] + delta[r,v]`
now — is cheap, and its catch that "sum-to-zero within each
roster-version block" is ill-defined is real: versions are not globally
aligned across races, so the constraint block genuinely needs
definition. **#7, #11, #12** are minor doc-consistency items and are
presented as such (note W23 already says "gates FR9a *interpretation*" —
the residual inconsistency is on the PRD side).

## 2. MODELING_REVIEW.md — agree; #1 and #2 are the standout findings

- **#1 (race draw propensity): the most consequential modeling gap
  across all three documents.** At average scoring, a Dwarf mirror and a
  Wood Elf mirror get identical draw probability, which contradicts the
  game. It propagates: E[points] drives FR9a favorability and the FR10
  headline, and packs weight draws differently — so missing race-level
  draw propensity undermines exactly the cross-pack comparability the
  project exists to provide. The proposed symmetric `d[r_A] + d[r_B]`
  cutpoint term is cheap and preserves every invariance property in M4.
- **#2 (descriptor centering): mathematically correct — verified.** A
  skew-symmetric bilinear form can encode a purely transitive component:
  if some direction w has roughly constant projection `x_r·w` across
  races (true for uncentered, all-positive descriptors), then
  `M = uw′ − wu′` yields `m(A,B) ≈ v_A − v_B`, which is α's job. M7's
  "the matchup term carries only what α cannot"
  ([MODELING.md:224](MODELING.md#L224)) is therefore not guaranteed by
  skew-symmetry alone; column-centering X (so `X′1 = 0`, hence
  `C·1 = 0`) is the missing condition. This is the one finding that
  corrects an identifiability claim the current docs actually make — a
  defect, not an improvement.
- **#5 (Σ_γ): agree** — a full covariance over treatment coefficients
  informed by ~25 races is a concrete spec gap; choose
  diagonal / regularized LKJ / low-rank explicitly. The predeclared
  mechanistic composites (skill grants × stacking) are also the right
  call at N≈20.
- **#7 (out-of-fold probes): agree** — in-sample posterior residuals
  would retire M11 register features too cheaply; a false null there is
  a real cost given the register's design intent.
- **#3, #4, #6: agree** at the recommended severity — #3 belongs in the
  M11 register with a residual diagnostic (not a v1 change); #4 (choice
  set vs. consideration set, IIA) matters for field-model quality; #6's
  caveats on interpreting ψ as learning are correct.

## 3. MODELING_PERSPECTIVES.md — act on about half; record the rest

Worth acting on:

- **#1 (heterogeneity diagnostic):** a pooled free pack×race
  variance-component model decomposes a null gate into "no
  heterogeneity" vs. "schema missed it" — much better than post-hoc
  residual analysis. T8.8's warning against free race×pack terms is
  about the thesis model, not a variance diagnostic; this does not
  conflict.
- **#8 (corpus purposes):** record that the contrast-rich selection
  corpus does not estimate representative deployment performance, so the
  gate is not read as that.
- **#11 (predictive, not causal):** agree; converges with
  TECHNICAL_REVIEW #10. Keep causal wording out of default reports.
- **#5 (second half):** derive descriptors mechanically from roster data
  where possible; reserve subjective annotation for strategic concepts.
  (The pooled pair-residual half is attractive but is essentially an
  earlier, simpler version of the scheduled W27 residual — reasonable to
  pull forward, not mandatory.)

Push back or downgrade:

- **#7 (soften the binary gate): disagree with replacing the bar.** The
  crisp pre-registered criterion is the anti-self-deception device, and
  §9a already surrounds it with everything the review wants (power
  documentation, advisory anchors, null-interpretation plan). Publish
  the richer decision report *alongside* the frozen criterion, not
  instead of it.
- **#9, #10: mostly already addressed.** FR10's headline is already
  "expected winrate vs. projected field" with a labeled
  `pairing_assumption` field (T6.4), and FR12 is already exploratory,
  diagnostic-only, and ~50 lines — deferring it harder saves almost
  nothing. Residual value: keep "event winrate" phrasing out of UI copy
  until the Swiss simulator exists.
- **#3 (fixed point): lower-stakes than it reads.** With ρ ≈ 0.5 damping
  and expected 1–2 effective rounds, the current design and the proposed
  "one documented response update" are nearly the same computation. The
  meta-awareness double-counting worry rates a sensitivity check, not a
  redesign.
- **#4 (time-varying coach earlier): split decision.** FR8b's deferral
  defense is real — baseline and challenger share the coach term, so
  drift bias largely cancels at the gate. But TECHNICAL_REVIEW #3 must
  be fixed regardless, and coach-year latents happen to resolve both;
  that tips toward the perspective more than it would otherwise deserve.

## 4. Recommended fix sequence

All of the following change what the gate measures, so they land before
`eval/GATE.md` is frozen (W14):

1. Gate isolation — identical nuisance terms incl. `κ·s_p` in baseline
   and challenger (TECHNICAL_REVIEW #1).
2. Coach-prior consistency — one lagged Glicko snapshot per coach, or
   coach-period latents (TECHNICAL_REVIEW #3).
3. Race draw propensity in `c` (MODELING_REVIEW #1).
4. Descriptor centering / `C·1 = 0` requirement, with the reference
   weighting stored (MODELING_REVIEW #2).
5. Fold-local preprocessing + defined out-of-support query behavior
   (TECHNICAL_REVIEW #5).
6. Bonus-points scope decision for favorability (TECHNICAL_REVIEW #2).

Also pre-gate because they are cheap spec work: Σ_γ structure choice and
mechanistic composite features (MODELING_REVIEW #5), out-of-fold probe
requirement (MODELING_REVIEW #7), BB2020 pooling contract + sum-to-zero
block definition (TECHNICAL_REVIEW #4), the pack×race heterogeneity
diagnostic (PERSPECTIVES #1), and the corpus-purpose caveat
(PERSPECTIVES #8).

Everything else lands with its milestone (field-model cross-fitting
before W19/W20; FR11 estimand before W21; fictitious-play convergence
handling before W22; FR9c contract before W25). The one framing to
resist adopting is PERSPECTIVES #7's move away from a binding
pre-registered criterion.
