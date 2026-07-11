# Alternative modeling perspectives

These are preference calls rather than defects in the existing design. The
main taste-level reaction is that the design is statistically thoughtful but
somewhat over-specified before the data has had a chance to speak. An
alternative would be to build a smaller empirical spine first, then earn the
more elaborate structure.

## 1. Separate “do packs matter?” from “can our schema explain why?”

The current thesis gate effectively tests whether the chosen treatment-vector
representation predicts unseen packs. That is valuable, but it combines two
questions:

- Is there meaningful race-specific variation between packs?
- Did schema v0 encode the right causes of that variation?

I would first fit a diagnostic model with heavily pooled free pack×race
effects. It cannot predict a new pack, but it can estimate how much unexplained
pack heterogeneity exists. Then I would ask how much of that variation the
treatment features explain.

That gives three possible conclusions instead of a single null:

- Little pack heterogeneity exists.
- Pack heterogeneity exists, but schema v0 misses it.
- Pack heterogeneity exists and the treatment representation predicts it.

The PRD already acknowledges this ambiguity, but I would make its resolution
part of the formal model sequence rather than residual analysis after a failed
gate.

## 2. Make “intrinsic treatment” and “realized event forecast” co-equal outputs

The headline currently becomes race performance against the projected field.
That is useful, but it entangles:

- the race's treatment under the pack;
- matchup structure;
- coach allocation;
- field composition;
- eventually Swiss pairing.

For comparing rulepacks, I would make a reference-field, neutral-coach
estimand the primary analytical output—something like performance against a
fixed canonical field. Then I would show the realistic projected-event
forecast beside it.

The first answers “What did this pack do to the race?” The second answers
“What will probably happen at this event?” Keeping them separate makes
comparisons across packs much cleaner and makes attribution less
self-referential.

## 3. Be less ambitious about the field fixed point

The fixed-point model is clever, but I am not fully convinced it reflects how
most coaches form expectations. Coaches react to last year's field, local
discussion, available miniatures, and a few salient matchups—not necessarily
to the equilibrium implied by the same fitted model being used to predict
their choices.

There is also some risk of counting meta-awareness twice: the estimated
favorability coefficient already reflects choices made by historically
meta-aware coaches, and then the fixed point adds an explicit model-consistent
response.

My preferred v1 would be:

- predict the field from loyalty, lagged regional composition, and pack
  treatment;
- calculate field-conditional favorability from that field;
- optionally perform one documented response update.

I would treat full convergence as a scenario or sensitivity analysis until it
demonstrates better held-out field prediction.

## 4. Move time-varying coach ability earlier

Static coach ability is a sensible simplification, but coach drift feels more
foundational than several of the more exotic refinements. The dates already
exist, and static ability complicates the interpretation of historical
validation because later matches inform the estimate of earlier ability.

I would probably begin with a modest dynamic structure—perhaps coach-year
effects with strong shrinkage—or construct a strictly historical,
rules-adjusted rating stream before tackling the full joint model. It adds
complexity, but it aligns the model with the operational forecasting problem
from day one.

## 5. Use race descriptors as priors for matchup residuals, not the entire matchup model

The skew-symmetric descriptor model is elegant and interpretable. The
hesitation is epistemic: hand-authored descriptors decide in advance which
matchup geometry is allowed to exist.

With roughly 25 races there are only about 300 unordered race pairs. Depending
on actual match counts and connectivity, I would be tempted to include a
strongly shrunk pairwise residual from the start:

```text
matchup = descriptor prediction + pooled pair residual
```

Most residuals would collapse toward zero. But the model would have somewhere
to put a real matchup that the descriptor vocabulary cannot express. The
residual variance itself would tell us whether the descriptors are doing
enough work.

I would also derive as many descriptors as possible mechanically from roster
data—movement distribution, armour distribution, strength access, reroll
cost, ball-handling options—and reserve subjective annotation for genuinely
strategic concepts such as flexibility.

## 6. Start with a simpler budget model

The roster-breakpoint idea is good domain modeling. The combination of
observed-TV grids, cumulative simplex weights, per-race deviations,
hand-authored breakpoints, and later multiresolution latent cells feels like a
lot of machinery for approximately 20 packs.

My first choice would be deterministic roster-derived basis features:

- key roster configurations unlocked;
- number of viable positionals;
- remaining inducement or skill capacity;
- specific known anchor thresholds.

Those features express why 1.15M differs from 1.20M rather than asking the
statistical model to rediscover the step geometry. If that proves incomplete,
I would add a monotone residual budget function.

I might also prefer monotonicity as a strong prior rather than an absolute
constraint. More nominal budget should not hurt an optimally built roster, but
observed tournament performance includes roster-selection mistakes, field
adaptation, and correlated rule changes.

## 7. Avoid making the project hinge on one binary gate

Pre-registration is excellent discipline, but “stop if the CI does not clear
this bar” feels too crisp for twenty heterogeneous packs. A result just below
the threshold could still justify improving the schema; a tiny result just
above it might not justify the parser.

I would frame the gate as a decision report containing:

- posterior probability and magnitude of improvement;
- estimated pack heterogeneity;
- expected value of acquiring more packs;
- schema coverage failures;
- engineering cost of the next milestone.

There can still be a decision, but I would resist presenting it as a scientific
yes/no conclusion.

## 8. Let the selected pack corpus serve two different purposes

The selection rules deliberately seek contrast-rich packs, connected coaches,
large events, and variation in levers. That is exactly what I would do for
parameter identification.

It is not necessarily the corpus I would use to estimate real-world forecast
performance. A deliberately contrast-rich sample may be unlike the ordinary
packs users later query.

Ideally, I would distinguish:

- an identification corpus chosen for treatment variation;
- a representative validation set sampled from the intended deployment
  population.

Twenty packs may make that impractical initially, but the distinction should
at least be recorded so the gate is not interpreted as performance on a
representative distribution of tournaments.

## 9. Swiss pairing may deserve earlier attention—but as an output layer

Random-pairing forecasts are reasonable for getting the match model running.
Still, if the headline is actual per-race tournament winrate, Swiss pairing is
part of the data-generating process, not a decorative refinement.

I would either move the simple Swiss simulator earlier or avoid calling
random-field performance an event winrate. A schedule-neutral “expected result
against the field” label would be more precise until Swiss simulation exists.

## 10. Defer the equilibrium diagnostic aggressively

It is interesting, and a tournament organizer might enjoy it. But equilibrium
analysis is a nonlinear amplifier of every uncertainty upstream: matchups,
treatment effects, field response, scoring, and legal choices.

Until the payoff matrix is well calibrated, an equilibrium can look much more
authoritative than the underlying evidence warrants. My preference would be
to build it only after ordinary field prediction and counter-pick behavior
show convincing out-of-sample performance. Before then, simple exploitability
or best-response tables probably provide most of the practical insight.

## 11. Make predictive—not causal—attribution explicit

The user goal “which rule levers actually affect performance” naturally
invites causal interpretation, but this remains observational data with
correlated pack features and regional or event cultures.

I would label outputs as predictive counterfactuals:

> Under the fitted model, changing this encoded feature while holding the
> other annotated features fixed changes the forecast by X.

Natural experiments and same-event year pairs strengthen the case, but they do
not automatically make arbitrary feature-level attribution causal. I would
keep causal language out of the default reports.

## Overall perspective

The current design tries to encode a great deal of domain truth into the first
serious model. I would start with a more permissive diagnostic model, learn
where the signal actually lives, and then progressively replace unexplained
variation with domain structure. The present approach will produce more
interpretable parameters if its assumptions are right; this alternative would
make it easier to discover which assumptions are wrong.
