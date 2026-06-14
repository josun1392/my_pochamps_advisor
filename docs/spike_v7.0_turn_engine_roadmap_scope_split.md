# v7.0 Turn Engine Roadmap / Scope Split

## Purpose

v7.0 defines the roadmap and scope split for a future full Turn Engine.

This is a design document only. It does not implement production code, run Gemini, add a turn-order resolver, resolve RNG, consume items, update HP, infer opponent sets, or change damage math.

## v6 Phase Closure Summary

The v6 phase ended with a default-off, dev-only UI path for limited TurnPipeline context:

- Optional top-level `turn_pipeline` payload adapter exists.
- `build_optional_turn_pipeline_for_advice_payload(...)` remains explicit and default-off.
- Payload snapshot tests lock default/off/on payload shape.
- Prompt/copy fixture tests lock candidate / not-resolved wording.
- Offline E2E advice fixtures verify payload -> prompt -> mocked advice flow.
- Controlled Gemini smoke passed for an explicit-on fixture.
- UI exposure design selected limited user-facing terminology.
- UI dev flag implementation added the default-off `턴 이벤트 후보 포함` checkbox.
- UI dev flag QA confirmed default unchecked, no persisted auto-on, no checkbox-toggle call, and correct status/help copy.
- Controlled UI Gemini smoke passed once through the checked UI flag path.

The current implementation can add limited candidate turn-event context to the LLM prompt. It is not a full Turn Engine.

## Limited TurnPipeline vs Full Turn Engine

### Current Limited TurnPipeline

Current `turn_pipeline` behavior:

- Provides candidate events.
- Provides known modifiers.
- Provides limited planning/debug summary.
- Is not a resolved outcome.
- Does not produce post-turn state.
- Does not resolve RNG.
- Does not consume items.
- Does not update HP.
- Does not determine final move order.
- Does not infer opponent sets.
- Preserves `damage_estimate`, `ko_context`, and existing item contexts as the core advice primitives.

### Future Full Turn Engine

A full Turn Engine would need to handle:

- Turn order resolution.
- Priority, speed, and speed tie handling.
- RNG trigger resolution.
- Item activation and consumption.
- Damage application.
- HP update.
- Fainting and survival handling.
- Post-turn state output.
- Explicit unsupported-state reporting.

The future engine should only move from candidate context to resolved outcomes after its assumptions, inputs, and unsupported cases are explicit.

## Staged Scope Split

### Stage 1: Deterministic Turn Order Context

Goal:
- Add deterministic move-order context before any full simulation.

Inputs:
- Selected player move.
- Known opponent move only if explicitly available.
- Move priority bracket.
- Known final Speed or existing speed context.
- Current Quick Claw / speed-order candidate context as non-resolved input.

Outputs:
- `acts_first`: player / opponent / unknown.
- `relation`: faster / slower / equal / unknown.
- `tie_candidate`: true / false / unknown.
- Explanation strings for priority and known Speed relation.
- Limitations showing that speed ties and RNG are not resolved.

Forbidden in this stage:
- No speed tie resolution.
- No RNG resolution.
- No Quick Claw activation resolution.
- No item consumption.
- No HP update.
- No post-turn state.
- No opponent set inference.

Risk:
- Low to medium.
- Low if restricted to known deterministic priority and Speed relation.
- Medium if UI data is incomplete or if priority/item wording implies final order.

### Stage 2: Deterministic Damage Application Preview

Goal:
- Reuse existing damage primitives without applying final HP.

Inputs:
- Existing `damage_estimate`.
- Existing `ko_context`.
- Known selected move context.
- Known item modifiers already represented by damage estimate item effects.

Outputs:
- Damage range summary.
- Existing KO interpretation reuse.
- "Preview only" limitations.

Forbidden in this stage:
- No RNG roll selection.
- No final HP update.
- No exact fainting state.
- No new damage formula.
- No raw roll changes.
- No Q12 multiplier changes.
- No `ko_context` recalculation outside the existing primitive.

Risk:
- Low.
- The main risk is language drift: a preview must not become "final battle damage."

### Stage 3: Item Trigger Candidate Layer

Goal:
- Keep item effects as candidates until a later resolved simulation stage exists.

Inputs:
- Existing `TurnEvent` candidates.
- Existing item contexts: Quick Claw, Focus Band / Focus Sash, Chilan Berry, Light Ball known modifier.
- Existing payload keys and limitations.

Outputs:
- Candidate trigger list.
- Known modifier list.
- Per-item limitations.
- No-consumption and no-exact-trigger warnings.

Forbidden in this stage:
- No item activation roll.
- No item consumption.
- No exact trigger result.
- No multi-hit consumption modeling.
- No chip-damage sequencing.
- No post-turn item state.

Risk:
- Low for candidate list maintenance.
- Medium if new item families are added without item-specific guardrails.

### Stage 4: Resolved Turn Simulation Prototype

Goal:
- Prototype a narrow resolved simulation under explicit, controlled assumptions.

Inputs:
- Single selected player move.
- Single selected opponent move.
- Explicit Speed / priority data.
- Explicit item states.
- Existing damage estimate as a primitive or a clearly versioned deterministic damage input.
- Explicit assumption profile.

Outputs:
- Resolved or assumption-bound event sequence.
- Explicit unsupported states.
- Assumption summary.
- No hidden opponent inference.

Forbidden in this stage:
- No opponent set inference.
- No broad battle-state guessing.
- No unsupported item family resolution.
- No silent fallback from unknown data to resolved truth.
- No unversioned mutation of existing damage math.

Risk:
- High.
- This is the first stage where candidate events may become resolved outcomes, so prompt and contract language must change carefully.

### Stage 5: Post-turn State Update

Goal:
- Produce post-turn state only after resolved assumptions are available.

Inputs:
- Resolved event sequence from Stage 4.
- Pre-turn battle state.
- Damage application result.
- Item activation and consumption results.
- Faint/survival results.

Outputs:
- Updated HP.
- Consumed item flags.
- Fainted flags.
- Post-turn battle state.
- Explanation of assumptions and unsupported effects.

Forbidden in this stage:
- No post-turn state without resolved assumptions.
- No HP update from candidate-only damage preview.
- No item consumed flags from candidate-only events.
- No hidden RNG resolution.
- No inferred opponent set state.

Risk:
- High.
- Incorrect post-turn state is more damaging than an omitted state because it can mislead later advice.

## Stage Risk Summary

Low risk:

- Deterministic context summaries that do not claim final order.
- Existing damage estimate reuse.
- Existing candidate event list and known modifier list.

Medium risk:

- Speed relation interpretation.
- Priority handling.
- UI wording around "likely acts first."
- Adding new item trigger families.

High risk:

- RNG resolution.
- Item activation and consumption.
- Post-turn HP update.
- Faint/survival finalization.
- Opponent move or set inference.
- Full resolved event sequence.

## Unsupported Boundaries

Until a later milestone explicitly implements and tests them, the following remain unsupported:

- Full Turn Engine.
- Resolved turn simulation.
- Final turn order.
- Speed tie result.
- RNG result.
- Quick Claw activation result.
- Focus Sash / Focus Band consumption.
- Chilan Berry consumption.
- Final HP after the turn.
- Fainted-state update.
- Opponent set inference.
- Hidden move choice inference.
- Status, volatile, weather, terrain, and field-condition sequencing.

## v7.1 Options

### Option A: v7.1 Deterministic Turn Order Context Design

Design the safest first stage before any full engine work.

Scope:

- Priority bracket.
- Known Speed relation.
- Tie candidate detection.
- Unknown relation handling.
- No speed tie resolver.
- No RNG.
- No item consumption.
- No HP update.

Pros:

- Smallest step toward Turn Engine semantics.
- Builds on existing `speed_context` and `speed_order_context`.
- Keeps resolved simulation out of scope.

Cons:

- Needs careful copy so "likely first" does not become "guaranteed first."

### Option B: v7.1 Battle State / Opponent Move Context Expansion

Expand state and opponent move context before resolving turns.

Scope:

- More complete known opponent move context.
- Clearer selected/possible move distinction.
- Better state available to LLM advice.

Pros:

- May improve advice quality sooner.
- Can remain additive and non-resolved.

Cons:

- More UI/input surface.
- Risk of inferred opponent information being overstated.

### Option C: v7.1 Resolved Turn Simulation Prototype Design

Design a narrow resolved simulation prototype.

Pros:

- Directly targets full engine capability.

Cons:

- Highest risk.
- Too early without deterministic order context and explicit assumption boundaries.

## Recommendation

Recommended next step:

```text
v7.1 Deterministic Turn Order Context Design
```

Rationale:

- It is the safest bridge from limited TurnPipeline context toward future engine work.
- It can stay design-only or contract-only at first.
- It avoids RNG, item consumption, HP update, and resolved simulation.
- It creates useful scope boundaries before any full Turn Engine implementation.

Safe alternative:

```text
v7.1 Battle State / Opponent Move Context Expansion
```

Do not start with a resolved simulation prototype. The roadmap should first clarify deterministic order context and unsupported boundaries.

## Safety Statement

- No production code was implemented in v7.0.
- No actual Gemini call was executed.
- No Vertex AI call was executed.
- No full Turn Engine was implemented.
- No resolved turn simulation was implemented.
- No turn order resolver was implemented.
- No speed tie resolver was implemented.
- No RNG resolver was implemented.
- No item consumption was implemented.
- No HP update was implemented.
- No opponent set inference was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- `logs/token_usage.jsonl` was not committed or reset.
