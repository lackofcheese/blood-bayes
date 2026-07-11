# Residual review of `MODELING.md`

This review records modeling observations not already covered by
`TECHNICAL_REVIEW.md` or `MODELING_PERSPECTIVES.md`.

## 1. The model lacks race- and matchup-specific draw propensity

`MODELING.md` motivates the ordinal model partly by noting that grinding races
deliberately produce 1–0 and 0–0 games
([MODELING.md:52](MODELING.md#L52)). It also correctly says that the important
restriction is which covariates enter `eta` versus `c`
([MODELING.md:125](MODELING.md#L125)).

But `c` only varies with scoring incentives and flexibility under those
incentives. At ordinary scoring, two equally matched Dwarfs and two equally
matched Wood Elves receive the same baseline draw probability. Any difference
must be forced into `eta`, which changes who is favored rather than
independently changing draw frequency.

Consider:

```text
c = softplus(
    c0
    + d[r_A] + d[r_B]
    + q · (x_A + x_B)
    + scoring terms
)
```

The race effects should be hierarchical, symmetric, and constrained for
identifiability. Mirror matches provide unusually clean information for them.

The same question applies to treatment: extra defensive skills, stacking, or
star access may change decisiveness as well as latent strength. The current
model assumes every treatment effect belongs exclusively in `eta`, but
`MODELING.md` does not justify that restriction.

## 2. The matchup term is not necessarily separated from race baselines

M7 says the bilinear descriptor term contains only interactions and therefore
will not fight the race baselines ([MODELING.md:224](MODELING.md#L224),
[MODELING.md:235](MODELING.md#L235)). That is only guaranteed if the
descriptor geometry is appropriately centered.

Let the induced race-pair matrix be:

```text
C = X M X'
```

Although `C` is skew-symmetric, it can still contain a transitive component
equivalent to race strength differences. Under uniform race weighting,
separation from race baselines requires `C · 1 = 0`; centering every descriptor
column so that `X' · 1 = 0` is one way to guarantee that.

Without this, `alpha` and `M` can divide the same signal according to their
priors, undermining both interpretation and posterior stability.

Explicitly require either:

- descriptor centering over a defined reference race distribution; or
- projection/double-centering of the induced matchup matrix onto the cyclic
  subspace.

The chosen weighting matters and should be stored with the model.

## 3. Coach ability is assumed to transfer identically across races

The model gives each coach one additive ability `theta`, while coach×race
variation is represented only by the shared experience curve. This assumes an
elite coach's advantage is the same on every roster.

A plausible alternative is that some races have higher skill ceilings or
reward particular abilities more strongly. That matters especially for
EuroBowl, where strong coaches are deliberately assigned to strategically
demanding races. If coach advantage is amplified on those races, an additive
coach adjustment may leave part of coach allocation inside the estimated race
or pack effect.

A low-dimensional extension could be:

```text
coach contribution = theta_i * (1 + b · complexity_r)
```

Alternatively, use a hierarchical race-specific loading on `theta`,
constrained to have mean one. This is much smaller than a free coach×race
effect and could be tested using coaches who switch between race archetypes.

At minimum, add this to the deferred-feature register with a residual
diagnostic.

## 4. The field model confuses the legal choice set with the practical consideration set

M10 treats multinomial logit as a natural model over the races legal at an
event ([MODELING.md:328](MODELING.md#L328)). But the PRD also says loyalty
largely reflects miniature ownership. For many coaches, most legal races are
not realistic choices at all.

A standard multinomial logit therefore asks one coefficient to do two jobs:

- whether a race is practically available to the coach;
- how attractive it is once available.

This can exaggerate the apparent favorability elasticity and make zero-history
races receive too much probability. It also brings the usual
independence-of-irrelevant-alternatives assumption: adding a similar elf race
takes probability proportionally from every alternative rather than primarily
from other elf-like choices.

Consider a two-stage model:

1. A consideration set inferred from prior races, recent acquisitions, or a
   latent ownership model.
2. Conditional choice within that set.

A simpler v1 could restrict most probability to previously played races while
retaining a small “new team” channel, then test sensitivity to that rule.

## 5. Treatment responses omit mechanistically important lever interactions

M9 specifies an additive response `gamma_r · z`. But several pack mechanisms
are inherently combinatorial:

- the value of extra skills depends on stacking permission;
- secondary access depends on the number of available skill slots;
- star access depends on the available budget;
- inducement discounts interact with roster construction and remaining
  treasury.

With only about 20 packs, fitting all pairwise interactions would be
unreasonable. Still, omitting them entirely could make schema v0 fail even
when its individual fields are correct.

Derive a small number of predeclared mechanistic composite features during
treatment-vector construction—particularly skill grants × stacking
allowance—rather than relying on a generic statistical interaction expansion.

Relatedly, `Sigma_gamma` is described as a covariance matrix
([MODELING.md:300](MODELING.md#L300)). If this means a full covariance across
all treatment coefficients, it is likely too ambitious: approximately 25
races provide weak information about a potentially large covariance matrix,
while the underlying pack levers are already correlated. The design should
choose explicitly among a diagonal, strongly regularized LKJ, or low-rank
factor structure.

## 6. “Prior games” may be a poor measurement of familiarity

M8 gives `log(1+n)` a learning-curve interpretation
([MODELING.md:259](MODELING.md#L259)). That depends on what history is
available:

- If ingestion begins with BB2020 or BB2025, experienced coaches enter
  left-truncated with artificially low counts.
- Games on earlier roster versions may transfer only partially.
- `n` grows with calendar time, so under a static coach latent it can absorb
  general coach improvement rather than race-specific familiarity.
- Continued selection of a race is endogenous: successful or committed
  coaches accumulate more games on it.

The feature can still be predictively useful, but avoid interpreting `psi`
directly as learning. The design should define the historical window,
treatment of earlier editions or roster versions, and possibly a decay or
transfer factor. The time-varying coach model is also important for separating
familiarity from general improvement.

## 7. Deferred-feature residual probes should be explicitly out-of-fold

M8 proposes examining baseline residuals and retiring the feature if no
relationship appears ([MODELING.md:292](MODELING.md#L292)). If these are
in-sample posterior residuals, the existing coach, race, and matchup terms may
already have absorbed part of the omitted structure. A false null would then
“retire” a useful feature.

These probes should use held-out posterior-predictive residuals—preferably the
existing event- or pack-level folds—and report uncertainty or power rather
than treating silence as decisive.

## Recommended priority

The first four observations are the most consequential. The descriptor
centering point is especially concrete because it affects the claimed
identifiability of the current model, rather than merely reflecting modeling
taste.
