# v12.60 Current Condition Offline Response Validation and Smoke Readiness

## Purpose

Validate the v12.59 current-condition payload and prompt boundary offline, then
determine whether its fixed fixture is ready for a separately approved single
actual Gemini smoke.

## Prompt Capture

The mocked production route is exercised as:

```text
run_ui_selected_advice
-> validation/filtering
-> condition_context.current_conditions
-> _build_ui_selected_prompt
-> mocked call_gemini capture
```

For valid condition context, the compact guard now requires a brief readback of
each side and condition type as user-confirmed present-state context. It still
distinguishes `none` (user-confirmed no current major status) from `unknown`
(current major status not known), and prohibits application/tick, exact damage,
duration, post-turn, RNG, and final-order inference.

The guard is absent for disabled, absent, empty, and all-invalid condition
paths. Item-event-only input retains its item-event guard without adding a
condition guard.

## Synthetic Response Contract

A small fixture-specific, test-only evaluator accepts a response that:

- identifies self burn as a user-confirmed current condition;
- identifies the opponent condition as unknown;
- keeps burn application timing and exact damage unknown; and
- leaves post-turn HP, RNG, and final order unresolved.

It rejects side mixing, unknown-condition guesses, application/trigger or
resolved promotion, exact/post-turn claims, duration/RNG/order claims,
`none` as a removal event, and condition omission in unrelated advice. This is
not a generic NLP evaluator or production response evaluator.

## Coexistence

The self-burn fixture and an opponent Focus Sash observed-item-event fixture
retain separate payload sections and both prompt guards. Neither is converted
into the other source or meaning.

## Readiness

**READY FOR SINGLE ACTUAL CONDITION SMOKE**

This readiness is based only on offline contract coverage and full regression.
It is not approval to call a provider. A future smoke requires separate T1/T2
approval, a fixed input, one permitted call at most, no retry/fallback/second
provider/Vertex AI, and sanitized reporting.

## Scope Preserved

No automatic condition detection, condition events, parser/replay/Turn Engine,
exact status calculation, duration/RNG resolver, post-turn state, or damage and
speed behavior was implemented. No actual Gemini/provider/network call was
made.
