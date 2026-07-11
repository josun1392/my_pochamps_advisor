# v12.55 Item Event Session Lifecycle

## Purpose

Add a small, explicit lifecycle around session-local
`MainWindow._item_event_confirmations` without changing the item-event payload
or prompt contract.

## Implemented Lifecycle

- The Item event button displays the current session count: `Item event (N)`.
- The dialog displays concise summaries using side, item, event type, optional
  turn, and optional note. It never displays raw event dictionaries.
- Selecting a summary loads that event into the existing fields. Apply replaces
  the selected event; Add event starts a new draft; Delete selected removes only
  that draft event. Cancel leaves session state unchanged.
- Duplicate identity is `(side, item, event_type, turn)`. Re-applying that
  identity updates the existing entry instead of appending another event; a note
  difference alone is not a new event. `turn=None` follows the same rule.
- Stored events are ordered by ascending turn, stable insertion order for equal
  turns, then unspecified turns last. Editing a turn re-applies that order.
- `Clear item events` is the explicit new-battle/session reset action. It clears
  only session-local events and updates the count. Checkbox changes, advice
  requests, Pokemon/move selection, and dialog Cancel do not clear events.

## Validation And Payload Regression

The existing explicit-user confirmation validator remains the storage boundary.
Invalid Apply/edit output preserves the prior session state. The limited-context
gate remains unchanged: off omits item events from `battle_input`; on maps only
valid stored events. Delete, edit, reset, and duplicate updates are reflected in
that existing mapping without changing its observed-only prompt behavior.

## Scope Boundaries

This lifecycle does not infer events, resolve effects, calculate HP/damage,
resolve RNG/order, modify known-item or field-state mapping, or call a provider.

## Status

`COMPLETE` - session lifecycle behavior is implemented locally; no provider call
is part of this work.
