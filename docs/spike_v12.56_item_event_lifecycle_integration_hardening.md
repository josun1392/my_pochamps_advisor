# v12.56 Item Event Lifecycle Integration Hardening

## Purpose

Harden the v12.55 session lifecycle through the actual offline path from dialog
Apply to `MainWindow._item_event_confirmations`, limited-context payload
mapping, and the observed-event prompt guard.

## Integration Contract

- Apply updates session state and the `Item event (N)` readback.
- With limited context enabled, valid lifecycle state reaches
  `item_event_context.observed_events` and activates the existing observed-only
  contrast/readback guard.
- Edit replaces the old value in both payload and prompt. Delete removes the
  selected event; Clear removes all session events, resets the count, and omits
  both context and guard.
- Limited-context off is a payload gate only: it preserves session state and
  count. Re-enabling it maps the stored events again.

## Duplicate And Ordering Policy

- Identity is `(side, item, event_type, turn)`; note-only changes update the
  same event, including when `turn` is `None`.
- A new event with an existing identity updates the stored identity rather than
  creating a duplicate.
- If an edit changes an event into another existing identity, the edited value
  wins and the prior duplicate is removed.
- Events sort numerically by turn, retain stable order for equal turns, and put
  `turn=None` last. Delete preserves the remaining order; a turn edit reorders.

## Clear UX

`Clear item events` remains an immediate explicit session/new-battle action.
It is intentionally a separate command from the limited-context checkbox. No
confirmation dialog was added: the control is narrowly scoped, the current
count is visible, and a larger confirmation flow would not improve the
contracted state boundary. After a delete, the dialog clears selection rather
than auto-selecting the next entry, preventing a repeated Delete from removing
another event inadvertently.

## Safety And Scope

All integration coverage uses a mocked provider capture; no actual Gemini,
provider, network, retry, fallback, or Vertex AI call occurs. Existing payload
shape, prompt wording, known-item behavior, field state, damage estimates, and
turn behavior remain unchanged.

## Status

`COMPLETE` - lifecycle UI/state integration and offline payload/prompt
regression are covered.
