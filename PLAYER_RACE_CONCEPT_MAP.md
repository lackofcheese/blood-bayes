# Coach, race choice, and performance — conceptual map

Status: informal discussion canvas. This is intentionally broader than the
implemented model. Arrows mean "plausibly influences" rather than a formal,
complete causal claim. The map may contain concepts that cannot be separately
identified from NAF data.

The deliberately reduced statistical proposal inspired by this map is
recorded separately in
[JOINT_COACH_RACE_MODEL_SCRATCHPAD.md](JOINT_COACH_RACE_MODEL_SCRATCHPAD.md).

The standalone rendered version is
[player_race_concept_map.svg](diagrams/player_race_concept_map.svg); its
editable source is [player_race_concept_map.dot](diagrams/player_race_concept_map.dot).

A second, more staged overview incorporating the independent visual and
conceptual reviews is available as
[player_race_process_map.svg](diagrams/player_race_process_map.svg), with
editable source at
[player_race_process_map.dot](diagrams/player_race_process_map.dot). It keeps
the original map as the broad inventory and uses the second map to clarify
selection, tournament realisation, and time.

Observed-data relationships are kept out of the influence network. They have
their own noncausal proxy map:
[player_race_proxy_map.svg](diagrams/player_race_proxy_map.svg), with editable
source at [player_race_proxy_map.dot](diagrams/player_race_proxy_map.dot).

![Coach, race choice, and performance conceptual map](diagrams/player_race_concept_map.svg)

The Mermaid source below is retained as a Markdown-native alternative.

```mermaid
flowchart LR
  %% ───────────────────────────── Context ─────────────────────────────
  subgraph CONTEXT[Pack, race, and social context]
    direction TB
    PACK[Pack treatment<br/>resources, legality, scoring]
    RACE[Race style geometry<br/>bash · ag · stunty/unusual mechanics]
    DIFF[Entry and mastery difficulty]
    META[Region, community, public meta]
    FORMAT[Event format<br/>open or squad]
    FIELD[Expected field and opponents]
    FAV[Perceived pack/field favorability]
  end

  %% ───────────────────── Persistent coach concepts ──────────────────
  subgraph TRAITS[Relatively persistent coach characteristics]
    direction TB
    TALENT[General game talent<br/>planning, calculation, risk judgement]
    STYLEAPT[Style-specific aptitude]
    LEARN[Learning capacity / ceiling]
    INVEST[Competitive investment<br/>time, preparation, willingness to optimise]
    PREF[Style and exact-race preference]
    EXPLORE[Exploration / switching disposition]
    RESOURCES[Material and social resources<br/>money, storage, friends, borrowing]
  end

  %% ───────────────────── Latent pre-event state ─────────────────────
  subgraph STATE[Coach state immediately before the event]
    direction TB
    GABILITY[Current general ability]
    HEXP[Hidden experience<br/>league, online, casual, earlier play]
    NAFPLAY[Prior NAF tournament play]
    TEXP[Total race-specific experience]
    STYLEEXP[Transferable style experience]
    COMP[Coach-race competence<br/>personal expected strength on this race]
    ACCESS[Practical race access]
    LOYALTY[Current loyalty / attachment]
    ADAPT[Competitive adaptation<br/>responsiveness to an available edge]
  end

  %% ───────────────────── Choice and performance ─────────────────────
  subgraph CURRENT[Current event t]
    direction TB
    CHOICE[Race chosen / assigned]
    BUILD[Realised roster and build]
    PAIR[Opponent, pairing, and matchup]
    PERFORMANCE[Latent match performance]
    OUTCOME[Observed W / D / L<br/>optional TD/CAS]
  end

  subgraph NEXT[Later event t+1]
    direction TB
    FUTURE[Updated experience, access,<br/>loyalty, beliefs, and ability]
  end

  %% Context structure
  RACE --> DIFF
  RACE --> STYLEEXP
  RACE --> PAIR
  PACK --> FAV
  PACK --> BUILD
  PACK --> PERFORMANCE
  META --> FAV
  META --> FIELD
  META --> ACCESS
  FORMAT --> CHOICE
  FORMAT --> PAIR
  FIELD --> FAV
  FIELD --> PAIR

  %% Formation of ability and preparedness
  TALENT --> GABILITY
  STYLEAPT --> COMP
  LEARN --> COMP
  INVEST --> GABILITY
  INVEST --> HEXP
  INVEST --> ADAPT
  HEXP --> TEXP
  NAFPLAY --> TEXP
  TEXP --> COMP
  TEXP --> STYLEEXP
  STYLEEXP --> COMP
  GABILITY --> COMP
  DIFF --> COMP

  %% Preference, access, and switching
  PREF --> LOYALTY
  EXPLORE --> ADAPT
  RESOURCES --> ACCESS

  %% Joint choice-performance heart
  ACCESS --> CHOICE
  LOYALTY --> CHOICE
  ADAPT --> CHOICE
  FAV --> CHOICE
  COMP --> CHOICE
  CHOICE --> BUILD
  BUILD --> PERFORMANCE
  COMP --> PERFORMANCE
  PAIR --> PERFORMANCE
  PERFORMANCE --> OUTCOME

  %% Explicitly future-facing feedback
  CHOICE --> FUTURE
  OUTCOME --> FUTURE

  %% Styling
  classDef context fill:#fff1c9,stroke:#9b6a00,stroke-width:1.5px,color:#2c2000;
  classDef trait fill:#eadfff,stroke:#6842a6,stroke-width:1.5px,color:#24143c;
  classDef latent fill:#dcecff,stroke:#2867a3,stroke-width:1.5px,color:#10243a;
  classDef current fill:#ffe0e6,stroke:#9d3850,stroke-width:1.5px,color:#36121b;
  classDef future fill:#eeeeee,stroke:#666,stroke-width:1.5px,color:#222;
  classDef heart fill:#d8f0ff,stroke:#004f87,stroke-width:3px,color:#08253a;

  class PACK,RACE,DIFF,META,FORMAT,FIELD,FAV context;
  class TALENT,STYLEAPT,LEARN,INVEST,PREF,EXPLORE,RESOURCES trait;
  class GABILITY,HEXP,NAFPLAY,TEXP,STYLEEXP,ACCESS,LOYALTY,ADAPT latent;
  class COMP heart;
  class CHOICE,BUILD,PAIR,PERFORMANCE,OUTCOME current;
  class FUTURE future;
```

## How to read it

- **Solid arrows** mean a plausible influence worth keeping in mind.
- In the rendered Graphviz version, muted-red arrows converge on race choice
  and the current-event process; thick blue arrows highlight the two shared
  coach–race competence paths. These colours are routing aids, not different
  causal claims.
- Evidence and measurement relationships are deliberately absent. They are
  incomplete if mixed into this network and belong in the separate proxy map.
- The thick-bordered **coach–race competence** node is the heart of the joint
  idea: it can affect both the probability of choosing a race and performance
  after choosing it.
- `Practical race access` deliberately combines ownership, borrowing, money,
  friends, storage, and preparation feasibility. The broad map distinguishes
  it from psychological loyalty even though NAF-only data may not.
- `Competitive adaptation` is the neutral name for the proposed
  "power-gamer-ness" construct: willingness and ability to respond to an
  available competitive edge. In an implemented choice model it would most
  naturally appear as a coach-specific response to favorability and
  unfamiliar-race friction, not as a standalone intercept.
- Bash and Ag are separate Blood Bowl dimensions and are not constrained to
  sum to one. Stunty and unusual mechanics are separate parts of the race
  geometry.
- The event-`t+1` box makes learning and loyalty feedback temporal rather than
  same-event reverse causation.

## Observation and proxy map

This second network is explicitly noncausal. Undirected dotted connections
mean only that an observation may contain information about a concept. It is
not exhaustive, and no direction of causation or Bayesian updating is implied.

![Observed NAF data and possible latent interpretations](diagrams/player_race_proxy_map.svg)

```mermaid
flowchart LR
  subgraph DATA[Observed NAF summaries]
    HISTORY[Race history<br/>games · events · recency · last race]
    RESULTS[Prior match results]
    REPERTOIRE[Repertoire breadth · entropy · switching]
    FIRST[First observed use and its performance]
  end

  subgraph CONCEPTS[Possible latent interpretations]
    EXPERIENCE[Total race experience]
    COMPETENCE[Coach-race competence]
    ABILITY[General ability]
    LOYALTY[Psychological loyalty / preference]
    ACCESS[Miniature and practical access]
    EXPLORATION[Exploration / switching disposition]
    INVESTMENT[Competitive investment / preparation]
    HIDDEN[Hidden league, online, and casual play]
  end

  HISTORY -.- EXPERIENCE
  HISTORY -.- LOYALTY
  HISTORY -.- ACCESS
  RESULTS -.- ABILITY
  RESULTS -.- COMPETENCE
  REPERTOIRE -.- EXPLORATION
  REPERTOIRE -.- ACCESS
  REPERTOIRE -.- INVESTMENT
  FIRST -.- COMPETENCE
  FIRST -.- HIDDEN
  FIRST -.- INVESTMENT
```

## Observationally entangled clusters

The map intentionally keeps these concepts separate for discussion, although
the available data may require collapsing them:

1. Hidden experience, starting aptitude, learning rate, and preparation.
2. Ownership/access, psychological loyalty, preference, and switching cost.
3. General ability, style-specific aptitude, and coach–race competence.
4. Competitive investment, exploration, and responsiveness to favorability.
5. Pack treatment, enabled build, matchup exposure, and realised performance.

The eventual model should be drawn as a highlighted subset of this map rather
than replacing it. Greyed-out nodes would then remain visible as omitted
mechanisms and possible sources of residual structure or bias.
