# v6.8 Payload Snapshot Lockdown

## Purpose

v6.8 locks the default/off/on TurnPipeline payload shapes with plain pytest dictionary assertions. It does not use an external snapshot dependency and does not add large golden JSON files.

No actual Gemini call was executed. No Vertex AI call was executed.

## Locked Paths

Default path:

```text
build_ui_advice_payload(payload)
_build_ui_selected_prompt(payload)
```

Expected behavior:

- no top-level `turn_pipeline`
- no TurnPipeline prompt guard
- existing `damage_estimate`, `ko_context`, and item contexts remain present

Explicit off path:

```text
build_optional_turn_pipeline_for_advice_payload(payload, enable_turn_pipeline=False)
build_ui_advice_payload(payload, turn_pipeline=None)
_build_ui_selected_prompt(payload, enable_turn_pipeline=False)
```

Expected behavior:

- helper returns `None`
- payload remains equal to the default payload
- prompt remains equal to the default prompt
- no top-level `turn_pipeline`

Explicit on path:

```text
build_optional_turn_pipeline_for_advice_payload(payload, enable_turn_pipeline=True)
build_ui_advice_payload(payload, turn_pipeline=result)
_build_ui_selected_prompt(payload, enable_turn_pipeline=True)
```

Expected behavior:

- top-level `turn_pipeline` is added only when explicitly supplied or explicitly enabled
- `turn_pipeline.simulated == "limited"`
- event order remains Light Ball, Quick Claw, Focus Sash, Chilan Berry
- prompt guard is present
- prompt guard says candidate events are not resolved outcomes

Mapping path:

```text
build_ui_advice_payload(payload, turn_pipeline=result.to_dict())
```

Expected behavior:

- mapping input normalizes to the same top-level `turn_pipeline` shape as the dataclass result

## Existing Context Preservation

The lockdown test keeps these existing surfaces unchanged:

- `damage_estimate`
- `ko_context`
- `species_stat_item_context`
- `speed_order_context`
- `survival_context`
- `chilan_berry_context`

`turn_pipeline` remains additive. It does not replace those contexts.

## Rejected Shape

`simulated="full"` remains rejected by `build_ui_advice_payload(...)`.

## Known Perf Note

The existing timing-sensitive perf behavior remains unchanged:

- `test_item_damage_calculation_under_point_12ms_average` may intermittently exceed `0.120000ms` in full-suite or ordering-sensitive runs
- isolated target and `tests/test_damage_perf.py -q` generally pass
- no threshold, skip, xfail, formula, raw roll, Q12, or `ko_context` change was made

## Safety Boundaries

This work does not:

- run actual Gemini calls
- run Vertex AI calls
- add a UI checkbox
- automatically enable TurnPipeline from the user-facing advice button
- implement a full Turn Engine
- evaluate item triggers
- consume items
- update HP or post-turn state
- resolve RNG, speed ties, exact trigger outcomes, status, or volatile state
- change damage formula, raw rolls, Q12 multipliers, `ko_context`, or payload filtering

## Next Candidate

Recommended next step:

```text
v6.9 Controlled Gemini Smoke Design
```

This should remain design-first unless T1/T2 explicitly approve an actual Gemini call with a pre-approved fixture, quota/cost expectation, and clear stop conditions.
