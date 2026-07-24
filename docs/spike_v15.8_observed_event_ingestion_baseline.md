# v15.8 Observed-Event Ingestion Baseline

## Scope

This baseline adds structured-request-only ingestion for explicit, user-confirmed
observations. It does not parse game logs, infer causes from damage, create a
persistent event history, or change legacy advice payloads.

## Existing paths and inventory

| Event | Existing source | Scope | v15.8 handling |
| --- | --- | --- | --- |
| Item activation/consumption | `MainWindow._item_event_confirmations`, populated by `_open_item_event_dialog` | Pokemon | Canonical structured-only event |
| Ability activation/reveal | No UI event source; ability dialog records known current state | Pokemon | Normalizer supports an explicit trusted event, otherwise absent |
| Condition apply/remove | No UI event source; condition dialog records known current state | Pokemon | Normalizer supports an explicit trusted event, otherwise absent |
| Observed damage, side triggers, field events | No canonical UI source | mixed | Unsupported/absent |

Known current item, ability, condition, and HP remain their existing current-state
entries. An observed event is separate and never promotes an unknown item,
ability, or condition to known current state.

## Boundary and schema

`MainWindow._start_structured_recommendation` keeps `_build_llm_battle_input()`
legacy-compatible, deep-copies its result, then supplies a detached copy of the
item-confirmation session to `capture_ui_current_state_provenance`. The helper
emits only on the structured copy:

`event_kind`, `side`, `slot_index`, `pokemon_id`, `session_id`, `source`,
`trust=observed_event`, `observed=True`, `confirmed=True`, `payload`, and the
canonical provenance block.

The frozen `TurnSnapshot.current_state.item_event_context.observed_events` is
therefore shared by deterministic snapshot input and structured summary. The
legacy base input, legacy prompt, public confirmation payload, and session source
are not mutated.

## Validation and deduplication

Pokemon-scoped events require an explicit trusted confirmation and matching
side/active slot/Pokemon/session. A wrong slot, Pokemon, or prior session is
excluded; it is never retagged. Same `event_kind` + owner/session + payload
events are deduplicated in first-seen order. Field/side event producers do not
exist yet and remain absent rather than being fabricated.

## Verification and remaining gaps

Contract tests cover item activation, duplicate handling, stale/wrong ownership
exclusion, event/current-state separation, and snapshot detachment. Provider and
network calls remain 0. Remaining work: UI capture for ability/condition events,
observed-damage provenance, side/field event producers, persistent history, and
multi-turn transition.
