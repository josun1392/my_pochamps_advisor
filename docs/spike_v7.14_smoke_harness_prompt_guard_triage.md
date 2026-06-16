# v7.14 Smoke Harness Prompt Guard Triage

## Purpose

v7.14 triages why the v7.13 Controlled UI Gemini Smoke stopped before any provider call.

This milestone does not call Gemini, retry Gemini, call Vertex AI, change UI behavior, or implement a full Turn Engine.

## v7.13 BLOCKED Recap

v7.13 result:

- pre-check result: passed
- actual Gemini call count: 0
- retry count: 0
- stop condition: unexpected exception before call
- result classification: `BLOCKED`
- provider response: none
- token/cost summary: none

The local smoke harness used a strict prompt equality check between:

- a directly built pre-check prompt
- the prompt captured from `run_ui_selected_advice(...)` immediately before the provider wrapper

That strict equality guard raised before the provider call.

## Equality Guard Raise Cause

Cause classification:

```text
dynamic field difference
```

The direct pre-check prompt called `_build_ui_selected_prompt(...)` without an explicit `turn_snapshot`.

The actual `run_ui_selected_advice(...)` path first calls `try_build_turn_snapshot_from_battle_input(...)`, then passes that snapshot into `_build_ui_selected_prompt(...)`.

Therefore the provider-path prompt contained a top-level `turn_snapshot` and the associated TurnSnapshot guard, while the direct pre-check prompt did not.

This is not a `turn_pipeline` or `turn_order_context` safety regression.

## Safe Diff Summary

Raw full prompt was not recorded.

Safe structural summary:

- equality result: prompts differed
- difference section: optional top-level payload context
- actual/provider-path prompt added: `turn_snapshot`
- expected/direct prompt missing: `turn_snapshot`
- both prompts included: `turn_pipeline`
- both prompts included: `turn_order_context`
- both prompts included the TurnPipeline guard
- both prompts included the turn-order context guard
- actual/provider-path prompt additionally included the TurnSnapshot guard

The actual provider-path prompt was longer because it included selected/pre-turn known state context.

## Safety Anchor Status

Safety anchors were present in the provider-path prompt:

- TurnPipeline guard present: yes
- `limited planning/debug summary only, not full turn simulation`: yes
- turn-order guard present: yes
- `limited planning context, not a resolved move order`: yes
- `Do not claim exact final move order`: yes
- `Do not claim speed ties are resolved`: yes
- `Do not claim RNG items activate`: yes
- `Do not infer item consumption`: yes
- `Do not infer post-turn HP`: yes
- full-simulation guard present through TurnSnapshot / TurnPipeline wording: yes

Quick Claw remains an unresolved candidate context. The triage found no prompt-path indication that Quick Claw activation is confirmed.

## Options Compared

### Option A: Keep strict exact equality and update expected fixture

Pros:

- strongest drift detection
- catches any prompt construction change

Cons:

- brittle when the direct pre-check path does not exactly mirror `run_ui_selected_advice(...)`
- can block a safe provider smoke due to unrelated optional context differences

### Option B: Use focused anchors and forbidden positive wording only

Pros:

- directly checks the safety purpose of the smoke
- less fragile to formatting, serialization, and optional context differences

Cons:

- weaker full-prompt drift detection
- may miss unrelated payload drift unless covered elsewhere

### Option C: Keep strict fixtures offline; use focused anchors in the smoke harness

Pros:

- preserves exact prompt / payload drift checks in offline tests
- makes the provider-call gate focus on safety-critical anchors
- avoids blocking a one-call smoke because a safe optional context was present in the real path

Cons:

- requires the smoke harness to report structural prompt differences rather than fail on exact text mismatch

## Selected Recommendation

Recommend Option C.

For the next controlled smoke:

- build the pre-check prompt through the same path as `run_ui_selected_advice(...)`, or capture the provider-path prompt via a no-provider dry run
- do not require direct `_build_ui_selected_prompt(...)` output to be byte-for-byte equal unless it uses the same `turn_snapshot`
- gate provider calls on focused safety anchors:
  - `turn_pipeline` present
  - `turn_order_context` present
  - TurnPipeline guard present
  - turn-order context guard present
  - exact order / speed tie / RNG / item consumption / post-turn HP prohibitions present
- keep exact prompt-shape checks in offline pytest fixtures
- keep forbidden positive wording checks for response classification

## Next Recommendation

Recommended:

```text
v7.15 Controlled UI Gemini Smoke Harness Alignment
```

Scope:

- no provider call by default
- align the smoke harness pre-check with the actual `run_ui_selected_advice(...)` prompt path
- add or document a no-provider capture path for the exact prompt that would be sent
- keep focused safety anchors as the provider-call gate

After that, a new controlled Gemini smoke still requires explicit T1 approval for a maximum-one-call provider attempt.

Alternative:

```text
v7.15 Controlled UI Gemini Smoke Retry
```

Only choose this if the harness alignment is already incorporated and T1 explicitly approves a new one-call smoke.

## Safety Statement

- No actual Gemini call was executed.
- No Gemini retry was executed.
- No Vertex AI call was executed.
- No production behavior was changed.
- No UI checkbox behavior was changed.
- Checkbox toggle alone was not changed to call Gemini.
- No saved setting auto-enable was implemented.
- No full Turn Engine was implemented.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, opponent set inference, or EV/IV/nature inference was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- Raw full prompt was not recorded.
- Secrets, billing details, and token log raw contents were not recorded.
