# v12.30 Item Event Source Inventory

## Purpose

Inventory the source candidates that could support future item activation,
consumption, resolved item effects, and post-turn item state.

The previous phase closed the current known-item boundary: a user-confirmed
item is current context only. It is not an item event and must not be promoted
to activation, consumption, resolved effects, post-turn item state, exact
damage, post-turn HP, or resolved Speed/order.

This is inventory/design documentation only. No production code, tests,
payload behavior, parser, Turn Engine behavior, prompt guard wording, provider
behavior, dependency files, or logs are changed.

No actual Gemini call was made.

## Current Phase Status

Current supported states:

- `unknown_item`
- `known_item`
- `candidate_activation` wording boundary only

Current supported source:

- `user_confirmed_current_item` -> `known_item` only

Future-only states:

- `observed_activation`
- `observed_consumption`
- `resolved_item_effect`
- `post_turn_item_state`

Future-only work still requires source contracts, payload contracts, parser or
event input design, tests, prompt/response safety checks, and explicit approval.

## Item Event State Model

| State | Meaning | Current status |
| --- | --- | --- |
| `unknown_item` | Item is unconfirmed or absent from trusted input. | Supported. |
| `known_item` | Current item is user-confirmed or explicitly entered as current context. | Supported. |
| `candidate_activation` | Conditions suggest the item could matter, but activation is not confirmed. | Supported as wording boundary only. |
| `observed_activation` | A trusted source explicitly observed activation. | Future-only. |
| `observed_consumption` | A trusted source explicitly observed consumption. | Future-only. |
| `resolved_item_effect` | An approved resolver calculated or applied the effect. | Future-only. |
| `post_turn_item_state` | Post-turn item state is known or calculated. | Future-only. |

Boundary:

```text
known_item
!= observed_activation
!= observed_consumption
!= resolved_item_effect
!= post_turn_item_state
```

## Source Inventory

### 1. `user_confirmed_current_item`

Meaning:

- the user directly enters or confirms the currently held item
- this source describes current item identity only

Allowed now:

- `known_item`
- `candidate_activation` wording, where existing guardrails allow strategic discussion

Forbidden:

- `observed_activation`
- `observed_consumption`
- `resolved_item_effect`
- `post_turn_item_state`

Validation:

- require explicit item value
- require current-item source metadata
- do not infer event timing, consumption, or resolved effects from item value

### 2. `explicit_user_event_confirmation`

Meaning:

- the user explicitly confirms an item event, such as "it just activated" or "it was just consumed"

Future allowed candidate states:

- `observed_activation`
- `observed_consumption`

Not implemented in the current phase.

Validation requirements:

- user input must explicitly identify the item event
- event type must distinguish activation from consumption
- side and item identity should be captured when available
- turn/time is optional but recommended
- user event confirmation must remain separate from current-item confirmation

### 3. `battle_log_observed`

Meaning:

- battle log text explicitly states an item activation or consumption event

Future allowed candidate states:

- `observed_activation`
- `observed_consumption`

Examples:

- `Focus Sash activated`
- `Berry was consumed`
- `Quick Claw activated`

Not implemented in the current phase.

Validation requirements:

- raw log event must contain an item event marker
- source reference must be preserved
- event side, item, and turn should be captured when available
- ambiguous text must stay untrusted until parser rules are defined

### 4. `parser_observed`

Meaning:

- a parser converts battle log or event text into a structured item event

Future allowed candidate states:

- `observed_activation`
- `observed_consumption`

Not implemented in the current phase.

Validation requirements:

- parser output must include event type
- parser output must include item
- parser output must include side
- parser output should include turn if available
- parser output must include confidence
- parser output must preserve a source reference to the raw event
- parser output must stay separate from current UI known-item payloads

### 5. `imported_replay_observed`

Meaning:

- imported replay data explicitly contains an item activation or consumption event

Future allowed candidate states:

- `observed_activation`
- `observed_consumption`

Not implemented in the current phase.

Validation requirements:

- replay event must map to side, item, and event type
- replay event should map to turn number or timestamp
- importer must preserve event provenance
- imported replay events must not be mixed with inferred set or meta data

### 6. `future_turn_engine_resolved`

Meaning:

- an approved Turn Engine or smaller approved resolver calculates the item effect from explicit inputs, conditions, order, damage, and RNG where relevant

Future allowed candidate states:

- `resolved_item_effect`
- `post_turn_item_state`

Not implemented in the current phase.

Validation requirements:

- record source inputs
- record assumptions
- record whether RNG, order, priority, and damage were resolved or still assumed
- do not hide RNG/order/damage assumptions behind a final-looking result
- do not emit post-turn item state unless the resolver explicitly supports it

## Allowed Current Source

The only current allowed source is:

```text
user_confirmed_current_item -> known_item only
```

This source can support current-item strategy discussion. It cannot support
observed item events, resolved item effects, post-turn state, exact damage, or
resolved order.

## Future Trusted Sources

Future trusted source candidates:

- `explicit_user_event_confirmation`
- `battle_log_observed`
- `parser_observed`
- `imported_replay_observed`
- `future_turn_engine_resolved`

These sources are not automatically trusted today. Each requires a separate
source contract, payload contract, prompt/response safety coverage, and
implementation approval before runtime use.

## Forbidden Sources

These sources must not create item activation, item consumption, resolved item
effects, or post-turn item state:

- species/common/meta inference
- damage reverse inference
- HP percentage inference
- move selection inference
- opponent_move_context inference
- turn_order_context inference
- field_state inference
- legality gate inference
- resist berry context inference
- LLM/model guess
- hidden item guess
- "usually runs item X" style inference

These sources also must not promote an unknown item to a known item.

## Item-Specific Examples

### Focus Sash

Known:

- `user_confirmed_current_item` -> `known_item`

Candidate:

- full HP plus an incoming KO-like situation may support `candidate_activation` wording only
- wording can say Focus Sash could matter

Observed:

- `battle_log_observed`, `parser_observed`, or `explicit_user_event_confirmation` could support `observed_activation` / `observed_consumption` in a future phase

Resolved:

- `future_turn_engine_resolved` could support `survived_at_1_hp` and consumed item state in a future phase

Current forbidden claims:

- Focus Sash activated
- Focus Sash was consumed
- post-hit HP is exactly 1
- survival is resolved

### Quick Claw

Known:

- `user_confirmed_current_item` -> `known_item`

Candidate:

- could activate wording only

Observed:

- `battle_log_observed`, `parser_observed`, or `explicit_user_event_confirmation` could support `observed_activation` in a future phase

Resolved:

- `future_turn_engine_resolved` with approved RNG/order resolver could support a Speed/order effect in a future phase

Current forbidden claims:

- Quick Claw activated
- RNG roll is known
- resolved turn order changed

### Berry

Known:

- `user_confirmed_current_item` -> `known_item`

Candidate:

- trigger condition may matter as strategic context

Observed:

- `battle_log_observed`, `parser_observed`, or `explicit_user_event_confirmation` could support `observed_consumption` in a future phase

Resolved:

- `future_turn_engine_resolved` could support recovery or damage reduction applied in a future phase

Current forbidden claims:

- Berry was consumed
- recovery was applied
- damage reduction was applied
- exact activation timing is known

### Leftovers

Known:

- `user_confirmed_current_item` -> `known_item`

Observed/resolved distinction:

- a future observed log event may confirm a recovery event
- a future approved resolver may apply end-turn recovery

Current forbidden claims:

- Leftovers recovered HP this turn
- exact recovery changed post-turn HP
- post-turn item effect was simulated

### Choice Scarf

Known:

- `user_confirmed_current_item` -> `known_item`

Observed/resolved distinction:

- known item can affect strategic Speed consideration
- lock state requires observed move lock or explicit user confirmation
- resolved order requires a Speed/order calculator or approved Turn Engine

Current forbidden claims:

- exact final move order is resolved
- the holder definitely moves first
- lock state is confirmed without an observed/user-confirmed source

## Future Payload Shape Candidate

Future-only candidate shape:

```yaml
item_event_context:
  known_item:
    value: focus-sash
    source: user_confirmed_current_item
  observed_events:
    - type: observed_activation
      item: focus-sash
      source: battle_log_observed
      turn: 5
      confidence: observed
  resolved_effects:
    - type: resolved_item_effect
      item: focus-sash
      effect: survived_at_1_hp
      source: future_turn_engine_resolved
      turn: 5
      confidence: calculated
  post_turn_item_state:
    value: consumed
    source: future_turn_engine_resolved
```

This is not implemented in v12.30. It is a schema candidate only. Payload
contract tests should lock trusted-source requirements before any runtime
adapter is added.

## Validation Requirements

`explicit_user_event_confirmation`:

- user input must explicitly identify item event
- event type must be activation or consumption
- turn/time optional but recommended

`battle_log_observed`:

- raw log event must contain item event marker
- parser must preserve source reference
- ambiguous log text must not become an observed item event

`parser_observed`:

- parser output must include event type, item, side, turn if available, and confidence
- parser output must preserve raw event provenance

`imported_replay_observed`:

- replay event must map to turn/side/item event
- importer must preserve replay provenance

`future_turn_engine_resolved`:

- must record assumptions
- must record source inputs
- must not hide RNG/order/damage assumptions
- must distinguish calculated effects from observed events

## Future Implementation Path

Recommended order:

1. Add contract tests that reject future item event fields unless a trusted source is explicitly present.
2. Design explicit user item event confirmation before UI implementation.
3. Inventory battle log and replay event formats.
4. Add parser schema only after source contract tests exist.
5. Add runtime payload adapter behind explicit gates.
6. Add prompt/response fixture coverage for observed event wording.
7. Consider resolver/Turn Engine integration only after observed-source paths are locked.

## Test Recommendations

Recommended next tests:

- reject `observed_events` without trusted source
- reject `resolved_effects` without `future_turn_engine_resolved`
- reject `post_turn_item_state` without approved resolver source
- verify `user_confirmed_current_item` remains `known_item` only
- verify forbidden sources cannot create observed/resolved item events
- verify field, turn-order, opponent-move, damage, legality, and resist-berry contexts do not become item event sources

## Non-Goals

v12.30 does not implement:

- item activation
- item consumption
- resolved item effects
- post-turn item state
- post-turn HP from item
- battle log parser
- replay parser
- Turn Engine
- damage formula changes
- `damage_estimate` changes
- `ko_context` changes
- Q12 multiplier changes
- raw damage roll changes
- RNG resolver
- speed tie resolver
- Quick Claw activation resolution
- hidden item inference
- opponent set/item inference
- prompt guard wording changes
- provider calls

## Next Recommendation

Recommended next:

- v12.31 Item Event Source Contract Tests

Reason:

- the source inventory is now documented
- the next safe step is to lock that future item event fields cannot enter the payload without trusted observed or resolved sources

Alternatives:

- v12.31 Explicit User Item Event Confirmation Design
- v12.31 Battle Log Parser Spike
