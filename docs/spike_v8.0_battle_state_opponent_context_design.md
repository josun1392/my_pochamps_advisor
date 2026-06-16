# v8.0 Battle State / Opponent Move Context Expansion Design

## Purpose

v8.0 designs the next phase after v7 Turn Order UI Integration Closure.

The goal is to improve advice quality by expanding explicitly known battle-state and opponent-move context before building any full Turn Engine.

This is design only:

- no production code implementation
- no actual Gemini call
- no Vertex AI call
- no full Turn Engine
- no resolved turn order
- no hidden opponent set inference

## v7 Closure Recap

The v7 phase completed `turn_order_context` through the full safe exposure path:

- deterministic helper
- payload adapter
- prompt guard
- UI dev flag integration
- offline E2E fixture
- controlled UI Gemini smoke retry

v7.16 controlled UI Gemini smoke result:

- actual Gemini call count: 1
- retry count: 0
- result: PASS
- no exact final order claim
- no speed tie resolution claim
- no Quick Claw activation certainty claim
- no item consumption claim
- no post-turn HP claim
- no full simulation claim

Current limitation after v7:

```text
turn_order_context can give cautious ordering hints, but its quality is limited by weak opponent move/source context.
```

## Current Known Sources

The UI-selected advice path can currently know or safely derive:

- own selected Pokemon
- opponent selected Pokemon
- own selected move
- own user-confirmed move slots
- opponent user-confirmed move slots, when the user selects them
- known move metadata from cache or Champions move metadata
- visible HP percent when available
- base species stats when available
- user-confirmed final stats when explicitly entered
- user-confirmed item profiles when explicitly selected
- item context candidates already derived by existing helpers
- `turn_snapshot` as selected/pre-turn known state
- `turn_pipeline` as limited candidate/debug context
- `turn_order_context` as limited planning context
- `opponent_moves.known_moves` as user-confirmed only
- `opponent_moves.candidate_moves` as Champions movepool possibilities only, not confirmed moves
- `opponent_assumptions` as possible sample context only, not confirmed opponent sets

Current move metadata available through `MoveView` is narrow:

- move id
- English/Korean name where available
- type
- category
- power
- accuracy
- PP

PokeAPI cache may contain more raw metadata such as priority and target, but the current `MoveRepository` view does not expose those fields to the UI-selected payload.

## Current Unknowns

The UI-selected advice path does not safely know:

- opponent selected move, unless explicitly selected by the user
- opponent actual moveset
- opponent hidden item, unless explicitly selected
- EV/IV/nature
- final Speed, unless explicitly confirmed
- stat boosts, unless explicitly provided
- major status / volatile state, unless explicitly provided
- weather, terrain, screens, hazards, or room effects, unless explicitly provided
- exact HP value beyond visible percent
- RNG result
- Quick Claw activation result
- speed tie result
- post-turn HP state
- final move order

## Existing Opponent Move Surface

The current payload already has an `opponent_moves` section:

- `known_moves`: user-confirmed opponent move slots
- `candidate_moves`: Champions movepool candidates with `confidence="possible_not_confirmed"`
- `candidate_source_status`
- limitations that candidate moves are not confirmed

This is useful but still mixed into the broader payload shape. v8 should avoid replacing it immediately. Instead, v8.1 can freeze a more explicit, optional `opponent_move_context` contract that summarizes safe opponent move information and preserves the current boundaries.

## Opponent Move Context Design

Draft optional top-level shape:

```python
{
    "kind": "opponent_move_context",
    "confidence": "limited",
    "source_policy": "explicit_or_visible_only",
    "selected_opponent_move": {
        "status": "unknown",
        "move": None,
    },
    "known_opponent_moves": [
        {
            "move_id": "earthquake",
            "source": "user_confirmed",
            "metadata": {
                "type": "ground",
                "category": "physical",
                "power": 100,
                "accuracy": 100,
                "priority": "unknown",
            },
        }
    ],
    "candidate_damaging_moves": [],
    "candidate_status_moves": [],
    "priority_move_candidates": [],
    "coverage_type_candidates": [],
    "unknowns": [
        "opponent selected move",
        "opponent actual moveset",
        "hidden item",
        "EV/IV/nature",
    ],
    "unsupported": [
        "hidden moveset inference",
        "opponent set inference",
        "RNG resolution",
        "full turn resolution",
    ],
}
```

Design rules:

- `known_opponent_moves` may contain only explicitly user-confirmed moves.
- `candidate_*` lists may contain only visible/cache-backed candidates and must be labeled unconfirmed.
- Candidate moves must not be treated as selected moves.
- Champions movepool candidates are possible move-pool context, not observed moves.
- Missing cache metadata should become `unknown`, not inferred.
- Priority may be added only when exposed by trusted move metadata.
- No metagame set or sample set should become confirmed context.

## Move Metadata Candidates

Safe metadata candidates for later contracts:

- move id
- move name
- type
- category: physical / special / status
- power if known
- accuracy if known
- priority if known
- target if known
- effect summary if safely available
- makes-contact flag if known
- multi-hit flag if known
- recovery/status/boosting move flags if already available from trusted metadata
- source and source status for every metadata field

Metadata that should remain unknown unless explicitly available:

- priority from raw cache when the repository does not expose it
- target from raw cache when not normalized into a contract
- secondary effect details without a safe summary contract
- move legality beyond current Champions movepool source status

Forbidden:

- hidden set inference
- saying the opponent likely has a move unless the source is explicitly a candidate context and labeled unconfirmed
- unverified metagame set assumptions
- EV/IV/nature estimation
- hidden item inference

## Battle State Context Design

Draft optional top-level shape:

```python
{
    "kind": "battle_state_context",
    "confidence": "limited",
    "visible_state": {
        "own_hp_percent": 100,
        "opponent_hp_percent": 100,
        "known_status": {
            "own": "unknown",
            "opponent": "unknown",
        },
        "known_boosts": {
            "own": {},
            "opponent": {},
        },
        "weather": "unknown",
        "terrain": "unknown",
        "screens": "unknown",
    },
    "unknowns": [
        "exact HP",
        "EV/IV/nature",
        "hidden item",
        "hidden moves",
        "unprovided boosts",
        "unprovided weather/terrain/screens",
    ],
    "unsupported": [
        "post-turn state update",
        "RNG resolution",
        "full turn resolution",
    ],
}
```

Design rules:

- This is a visible-state summary, not a battle-state manager.
- Unknown weather, terrain, boosts, and screens must remain unknown.
- Do not infer field state from species, moves, or common sets.
- Do not compute post-turn HP.
- Do not resolve item triggers or status outcomes.

## Payload Integration Options

Option A: top-level optional `opponent_move_context`

- Best first step.
- Directly targets the advice-quality gap from missing opponent move/source context.
- Can stay fixture-level in v8.1 before helper or runtime adapter work.

Option B: top-level optional `battle_state_context`

- Useful for visible state and unknown boundaries.
- Broader than opponent moves and may touch more UI state.
- Safer after `opponent_move_context` is fixed.

Option C: enrich existing `opponent_moves`

- Lowest payload churn.
- Risk: keeps contract spread across the broader payload and makes future prompt guards less explicit.

Recommendation:

```text
Use a future optional top-level opponent_move_context first.
```

Keep the same safety posture used by `turn_pipeline` and `turn_order_context`:

- default-off initially
- explicit-only adapter when implemented
- fixture-level contract first
- prompt guard before any provider smoke

## Prompt Guard Direction

Future prompt guard meaning:

```text
Opponent move context is based only on explicitly known or visible data.
Do not infer hidden movesets.
Do not infer EVs, IVs, nature, item, weather, terrain, or boosts unless explicitly provided.
Do not treat candidate moves as confirmed selected moves.
```

Korean documentation wording:

```text
상대 기술 정보는 명시적으로 알려진 정보 또는 UI에 보이는 정보에 한정한다.
후보 기술을 실제 선택 기술로 확정하지 않는다.
숨겨진 기술배치, 아이템, EV/IV/nature, 보정 상태를 추론하지 않는다.
```

Prompt guard should also say:

- known moves are user-confirmed only
- candidate moves are possible/unconfirmed only
- selected opponent move remains unknown unless explicitly selected
- move priority is unknown unless trusted metadata provides it
- no full Turn Engine or resolved move order is implied

## Safety Boundaries

Maintain these boundaries throughout v8:

- no actual Gemini call during design/contract steps
- no full Turn Engine
- no resolved turn order
- no opponent set inference
- no hidden moveset inference
- no EV/IV/nature inference
- no hidden item inference
- no weather/terrain/boost inference
- no speed tie resolver
- no RNG resolver
- no Quick Claw activation resolution
- no item consumption
- no post-turn HP update
- no damage formula change
- no raw damage roll change
- no Q12 multiplier change
- no `ko_context` calculation change
- no payload filtering behavior change

## Staged Implementation Plan

Stage 1: `v8.1 Opponent Move Context Payload Contract`

- Freeze the optional `opponent_move_context` fixture-level shape.
- Define allowed values.
- Define required `unknowns` and `unsupported` boundaries.
- Reject fields that imply confirmed hidden moves or selected opponent action.
- No runtime adapter yet.

Stage 2: `v8.2 Opponent Move Context Helper`

- Build a helper from existing `opponent_moves` and move metadata.
- Preserve `known` vs `candidate` separation.
- Extract category/type/power/accuracy and priority only when trusted metadata exposes it.
- No hidden set inference.

Stage 3: `v8.3 Opponent Move Context Payload Adapter`

- Add an optional explicit-only adapter.
- Default-off path remains unchanged.
- Context omitted if no safe source exists.

Stage 4: `v8.4 Opponent Move Context Prompt Guard Tests`

- Lock guard wording before prompt integration.
- Protect against candidate-as-confirmed wording.

Stage 5: `v8.5 Opponent Move Context Prompt Integration`

- Insert guard and serialized context only when present.
- No actual Gemini call until offline fixture passes.

Stage 6: `v8.6 Offline Advice Fixture`

- Mock provider path.
- Verify default-off, explicit-on, and coexistence with `turn_pipeline` / `turn_order_context`.

Later:

- `battle_state_context` payload contract
- visible field/status/source extraction design
- controlled smoke design only after offline fixtures are stable

## Next Recommendation

Recommended next:

```text
v8.1 Opponent Move Context Payload Contract
```

Reason:

- Opponent move/source context directly limits advice quality.
- It can reduce priority unknowns once trusted metadata is surfaced.
- It is safer than full Turn Engine work.
- It preserves the v7 pattern: design -> contract -> helper -> adapter -> prompt guard -> offline fixture -> controlled smoke only after approval.

Safe alternative:

```text
v8.1 Battle State Context Payload Contract
```

This is useful but broader. Opponent move context should come first.

## Safety Statement

- No production code was changed in v8.0.
- No actual Gemini call was made.
- No retry was made.
- No Vertex AI call was made.
- No UI checkbox behavior was changed.
- No saved setting auto-enable was added.
- No full Turn Engine was implemented.
- No resolved turn order was implemented.
- No opponent set inference or hidden moveset inference was implemented.
- No EV/IV/nature, hidden item, weather, terrain, or boosts were inferred.
- No speed tie resolver, RNG resolver, Quick Claw activation resolution, item consumption, or post-turn HP update was implemented.
- No damage formula, raw damage rolls, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
