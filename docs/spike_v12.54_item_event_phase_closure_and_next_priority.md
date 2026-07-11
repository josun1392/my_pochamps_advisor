# v12.54 Item Event Phase Closure and Next Priority

## Purpose

Close the Item Event phase from v12.26 through v12.53 and select one next
implementation priority without broadening the current item-event contract.

## Phase Summary

### 1. Boundary and Source Contracts

- v12.26-v12.29 fixed the known-item boundary: user-confirmed current context
  only, not activation, consumption, resolved effect, post-turn state, or exact
  battle result.
- v12.30-v12.33 inventoried sources and established
  `explicit_user_event_confirmation` as the first trusted observed-event
  source, with strict source/status/event validation.

### 2. UI and Session-Local Confirmation

- v12.34-v12.37 added test-first dialog behavior, `ItemEventDialog`, an Item
  event button, and session-local `MainWindow._item_event_confirmations`.
- Apply saves validated candidates, Cancel preserves state, Reset + Apply stores
  an empty list, and invalid dialog output is rejected.

### 3. Payload and Prompt Integration

- v12.38-v12.42 designed, tested, implemented, and closed
  limited-context-gated mapping into `item_event_context.observed_events`.
- v12.41 added observed-only prompt safety wording; v12.49 and v12.52 added
  minimal contrast/readback instructions for observed events and current known
  items without changing payload shape.

### 4. Actual Smoke Failure and Correction

- v12.45 actual smoke failed because event salience and known-item separation
  were incomplete.
- v12.46-v12.52 analyzed the failure, locked reproduction contracts, added a
  compact observed-event contrast/readback instruction, validated it offline,
  and added current-known attribution.
- No correction added resolved mechanics, exact calculations, or a new event
  source.

### 5. Final Actual Validation

- v12.51 re-smoke improved Focus Sash event readback but still missed Leftovers
  current-known attribution.
- v12.53 final re-smoke passed after the attribution correction.

## Final Contract

### Known Item

```text
known item = user-confirmed current item context only
known item != activation
known item != consumption
known item != resolved effect
known item != post-turn state
known item != exact HP/damage/order/RNG
```

### Observed Item Event

```text
source=explicit_user_event_confirmation
status=user_confirmed
confidence=observed
```

Allowed event types:

- `item_activation_observed`
- `item_consumption_observed`
- `item_recovery_observed`
- `item_prevention_observed`
- `item_reveal_observed`

Required fields: `side`, `item`, `event_type`, `status`, `source`.
Optional fields: `turn`, `note`.

### Limited Context Gate

- Checkbox off: item-event payload, context, and prompt wording are absent.
- Checkbox on: valid explicit observed events normalize into
  `item_event_context.observed_events`.
- Invalid individual events are omitted. All-invalid input omits the context.

### Prompt Behavior

When valid events exist, the prompt requests separate current-known and
observed-event readbacks by side/item, with event type for observations. It
keeps known items out of observed-event meaning and observed events out of
resolved-result meaning. Exact HP/damage, post-turn state, RNG, and final order
remain non-inferable.

## Final Actual Smoke Audit

| Version | Result | Summary |
| --- | --- | --- |
| v12.45 | FAIL | Event salience and identity separation were insufficient. |
| v12.51 | FAIL | Focus Sash event readback improved; current-known attribution was absent. |
| v12.53 | PASS | Current known item and observed event were separately read back without semantic overclaim. |

Final validation used `gemini-2.5-flash`. The v12.53 task attempted one actual
call; retry, fallback, second provider, and Vertex AI counts were zero. Final
regression result: `1645 passed, 2 deselected`. Raw token logs, credentials, and
full provider responses are not part of this closure.

## Final Status

`ITEM EVENT PHASE: CLOSED - PASS`

## Remaining Limitations

These are outside the closed observed-event scope, not defects in the current
contract:

- no event summary/readback UI, edit/delete lifecycle, duplicate policy, or
  ordering/display policy
- session reset and new-battle event-clear boundary is not defined
- battle-log, parser, replay, and Turn Engine event sources are not implemented
- observed events currently rely on explicit user confirmation
- no resolved item effect, post-turn item state, or exact HP/damage/RNG/order
  calculation exists

## Next Candidate Comparison

| Candidate | User-visible value | Readiness/dependency | Scope and risk | Testability | Timing |
| --- | --- | --- | --- | --- | --- |
| A. Item Event Session Lifecycle | Makes saved events manageable across a battle session. | Builds directly on existing dialog/button/state. | Medium, localized UI/state policy. | High with dialog/controller contracts. | Now |
| B. Battle Log Item Event Source | Reduces manual confirmation through future automation. | Needs source provenance and parser/replay design first. | Large, parser ambiguity and trust risk. | Medium after source contract. | Later |
| C. Status/Condition Source | Adds a new battle-information category. | Needs its own known/observed/resolved vocabulary. | Medium/large, duration and damage semantics. | High after design. | Later |
| D. Damage Calculator Integration | Improves calculation provenance and precision. | Requires broad unknown-input and calculator boundary design. | Large, high regression risk. | Medium. | Later |

## Selected Next Work

`v12.55 Item Event Session Lifecycle Design and Contract Tests`

This is the highest-value next step because users can now create and send
observed events but cannot inspect, edit, delete, de-duplicate, order, or
explicitly clear them at a new-battle boundary. It is localized to existing
session-local state and avoids prematurely adding automated sources or resolved
mechanics.

Recommended v12.55 scope:

- lifecycle policy design for summary/readback, edit/delete, duplicate handling,
  ordering, and session reset/new battle
- contract tests and a minimal test-only controller seam
- offline validation of existing payload-gate and prompt boundaries
- defer production UI implementation to a following task if the lifecycle
  surface is larger than the established dialog/button pattern

## No Provider Call

This closure performs no actual Gemini/provider/network call, retry, credential
check, token-log inspection, or runtime behavior change.
