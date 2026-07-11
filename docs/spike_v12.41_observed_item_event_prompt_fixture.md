# v12.41 Observed Item Event Prompt Fixture

## Purpose

Lock safe prompt serialization for the v12.40
`item_event_context.observed_events` payload path with offline fixtures.

## Production Prompt Builder Path

- Fixtures call `run_ui_selected_advice(...)`.
- The production path builds prompts through `_build_ui_selected_prompt(...)`.
- `call_gemini` is monkeypatched with a local fake that captures the prompt.
- `_log_advisor_call` is monkeypatched to avoid token logging.
- No provider or network call is made.

## Observed-Only Prompt Guard

When `item_event_context` is present, the prompt now states that it is:

- explicitly user-confirmed observed context
- not a resolved mechanic result
- not an exact calculation
- not a post-turn state
- not an RNG result
- not a resolved turn order

The guard is absent when `item_event_context` is absent.

## Checkbox Off Fixture

With limited context disabled, an explicit event fixture verifies:

- `item_event_context` is absent
- `observed_events` is absent
- the event item name is absent
- the event type is absent
- the item-event prompt guard is absent

The off fixture uses `yache-berry` while known current items are different, so
known-item serialization cannot create a false positive.

## Checkbox On Fixture

With limited context enabled, fixtures verify each observed event type:

- `item_activation_observed`
- `item_consumption_observed`
- `item_recovery_observed`
- `item_prevention_observed`
- `item_reveal_observed`

Each normalized prompt payload event preserves:

- `side`
- `item`
- `event_type`
- `status=user_confirmed`
- `source=explicit_user_event_confirmation`
- `confidence=observed`
- optional `turn`
- optional `note`

## Known Item and Observed Event Separation

- A fixture includes a known current `leftovers` item and a separate observed
  `item_recovery_observed` event.
- The known item remains in `battle_state_context` as
  `known=true/source=user_confirmed`.
- The observed event remains in `item_event_context.observed_events` with its
  explicit event source.
- A known item without an explicit event does not create item event context.

## Invalid Raw Event Defense

Representative invalid raw events are passed through the real prompt path:

- missing side
- wrong source
- exact HP claim
- RNG and Speed/order claim

They do not create `item_event_context`, do not reappear in the prompt, and do
not introduce forbidden fields.

## Forbidden Claims and Fields

Fixtures recursively scan payloads for resolved, post-turn, exact HP/damage,
RNG, and Speed/order fields. They also reject positive prompt claims about:

- resolved full item effect
- exact restored HP or prevented damage
- exact Focus Sash survival
- Quick Claw RNG success
- final Speed order
- exact Berry recovery
- item damage modifier application
- known post-turn HP

## No Actual Gemini Call

- No actual Gemini call was executed.
- No retry was executed.
- No second provider call was executed.
- No Vertex AI call was executed.
- No provider/network call was executed.

## Next Recommendation

Recommended next:

- v12.42 Controlled Observed Item Event Smoke Design

Reason:

- Payload mapping and offline prompt safety are now covered. The next phase can
  design a controlled, approval-gated smoke plan without running a provider call.
