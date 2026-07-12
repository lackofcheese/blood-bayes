# Joint coach–race competence and choice model

Status: discussion scratchpad. This is a deliberately small candidate inspired
by the broader conceptual network. It is not part of the approved v1 model and
does not override `PRD.md`, `MODELING.md`, or `TECHNICAL.md`.

Related visual: [PLAYER_RACE_CONCEPT_MAP.md](PLAYER_RACE_CONCEPT_MAP.md).

## 1. Core hypothesis

A coach's latent competence with a race may affect both:

1. how well the coach performs after selecting that race; and
2. the probability that the coach selects the race in the first place.

```text
                         ┌──► race choice
coach–race competence ───┤
                         └──► match performance
```

Separate match and choice models that omit this shared cause risk treating
competence-driven selection as loyalty, favorability response, or a race/pack
performance effect. A joint likelihood provides a coherent way to share
evidence while propagating uncertainty. It does not, by itself, identify the
real-world causes of competence.

## 2. Deliberately small competence model

For coach `i`, race `r`, and the information available before event `t`, define:

```text
C[i,r,t] = A[i] + B[i]' x[r] + psi * log(1 + n_NAF[i,r,t])
```

where:

- `C[i,r,t]` is latent coach–race competence;
- `A[i]` is general coach ability;
- `B[i]` is a very low-dimensional style-aptitude loading;
- `x[r]` is a frozen race-style descriptor vector;
- `n_NAF[i,r,t]` is the coach's strictly prior observed NAF games with the
  race; and
- `psi * log(1+n)` is a weak, saturating familiarity contribution, not a
  literal learning curve.

The smallest useful style version could use one coach loading. A slightly
richer version could use separate contact/control and mobility/ball-handling
loadings. Those race dimensions need not sum to one. Stunty/unreliable
mechanics and entry difficulty remain separate descriptors rather than a
forced point on the bash–agility line.

Do not initially add a free residual for every coach×race cell. It would be
sparse, liable to absorb matchup or treatment signal, and difficult to
distinguish from hidden experience.

## 3. Match-outcome channel

In the existing ordinal W/D/L model, replace or extend the portable coach
contribution with competence:

```text
eta = C[i,r_A,t] - C[j,r_B,t]
    + race_and_roster_version_contrast
    + race_by_pack_treatment_contrast
    + matchup[r_A,r_B]
```

The approved symmetric draw-cutpoint structure remains separate. This
scratchpad does not propose moving access, loyalty, or preference directly
into match performance.

All competence inputs and posteriors must obey the applicable mask:

- leave-pack-out for the treatment-schema gate;
- leave-event-out for event validation; and
- strictly pre-cutoff for prospective forecasting.

## 4. Race-choice channel

For a race legal at an event, a compact choice utility is:

```text
U[i,r,t] = beta_comp * C[i,r,t]
         + beta_fav  * favorability[r,t]
         + observed_loyalty[i,r,t]
         - novelty_friction[i,r,t]
         + popularity_and_context[r,t]
```

`beta_comp * C` is the distinctive joint-model term: coaches may select races
they expect to play well personally, independently of the race's generic pack
favorability.

Observed loyalty may use strictly prior exact-race history, recency, last race,
and repertoire summaries. It remains predictive evidence rather than a claim
to have identified psychological attachment or miniature ownership.

## 5. Optional competitive-adaptation latent

A second coach latent may represent heterogeneous responsiveness to an
available competitive edge:

```text
G[i] = competitive adaptation / switching responsiveness

U[i,r,t] += G[i] * (
    favorability_advantage[i,r,t]
    - delta * difficulty[r] * unfamiliar[i,r,t]
)
```

This is the restrained operational meaning of "power-gamer-ness." It is not a
coach-wide utility intercept, which would cancel from multinomial choice
probabilities. A high `G[i]` coach responds more strongly to a meaningful pack
advantage and may tolerate unfamiliarity when the advantage is sufficiently
large.

If used, `A[i]`, the style loading `B[i]`, and `G[i]` receive hierarchical
zero-centered priors. A correlation between general ability and competitive
adaptation is plausible, but the conservative first fit should either keep the
prior covariance diagonal or estimate only the single `corr(A,G)` term.

## 6. Concepts deliberately not separated initially

The broad conceptual network distinguishes the following because they help us
reason about bias and missing data. NAF-only observations are unlikely to
identify each as a separate latent parameter:

- miniature ownership, borrowing, money, storage, and access through friends;
- BB3, FUMBBL, league, casual, and other unrecorded experience;
- general talent, willingness to study, mathematical preparation, and
  seriousness;
- starting aptitude, learning rate, and attainable mastery ceiling;
- psychological loyalty versus practical switching cost; and
- preparation for one event versus persistent coach–race specialization.

In the compact model these remain possible explanations for competence,
loyalty, adaptation, and residual uncertainty. Assigning each a prior would
not make it identifiable.

## 7. Pull-back ladder

The point of this proposal is to permit simplification. Compare increasingly
small variants using held-out prediction and posterior diagnostics:

1. **Joint competence + adaptation:** `A`, low-dimensional `B`, and `G`.
2. **Joint competence only:** `A` and low-dimensional `B`; no heterogeneous
   adaptation.
3. **Portable ability only:** `B=0`; competence is general ability plus the
   fixed observed-history term.
4. **Approved separate-model baseline:** choice does not use inferred personal
   competence beyond observed history summaries.

Prefer the smallest variant that materially improves the relevant held-out
choice and outcome predictions without destabilising the treatment-schema
gate. Failure of a richer variant is a reason to pull back, not evidence that
the omitted real-world mechanisms do not exist.

## 8. Required checks before promotion

- Parameter-recovery rehearsal under realistic coach/race sparsity.
- Leave-event- and leave-pack-out comparison against the approved baseline.
- First-observed-use and established-history-only sensitivities.
- Check whether the competence term changes race×treatment conclusions.
- Check whether the style loading is identified beyond general ability and
  exact-race NAF history.
- Check whether `G` predicts held-out switching rather than merely explaining
  a few high-volume coaches.
- Report posterior correlations among ability, competence, loyalty,
  favorability response, and treatment effects.
- Keep ownership, hidden play, talent, and seriousness language out of fitted
  parameter labels unless new data identify those concepts directly.

## 9. Main unresolved design questions

1. Should the first style term be a single bash↔agile loading or independent
   contact and mobility loadings?
2. Does inferred competence belong in choice directly, or should the choice
   model use only the coach's belief about competence—which may be noisy or
   biased?
3. Is competitive adaptation distinct enough from observed switching and
   repertoire breadth to justify `G[i]`?
4. Can the joint likelihood learn coach–race competence without allowing
   performance on selected races to overstate competence on unselected races?
5. Should this be only a post-gate field-model refinement, or is the selection
   path important enough to include in a gate sensitivity?
