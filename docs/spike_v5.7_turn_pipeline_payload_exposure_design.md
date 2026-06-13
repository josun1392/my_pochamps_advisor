# v5.7 TurnPipeline Payload Exposure Design

## Purpose

v5.6 made `TurnPipelineResult` inspectable through a local dry-run/debug report, but the result is still disconnected from `advisor_client.py` and the LLM advice payload.

This design evaluates whether `TurnPipelineResult` should be exposed to the advisor payload, where it should live if exposed, and what guardrails are required so Gemini does not treat it as a full Turn Engine result.

No actual Gemini call was executed. No Vertex AI call was executed. No production code was changed.

## Current State After v5.6

Implemented:

- `core.turn_event.TurnEvent`
- `core.turn_event.TurnPipelineResult`
- `llm.advisor_turn_events.build_turn_events_from_advice_payload(...)`
- `llm.advisor_turn_events.build_turn_pipeline_result_from_advice_payload(...)`
- `scripts/spike_turn_pipeline_debug.py`
- `docs/debug_turn_pipeline_sample_v5.6.md`

The dry-run fixture can generate events for:

- Light Ball: `damage` / `known_modifier` / `known`
- Quick Claw: `pre_move` / `candidate` / `possible`
- Focus Sash: `on_damage_before_ko` / `candidate` / `possible`
- Chilan Berry: `on_damage_before_ko` / `candidate` / `possible`

The resulting `TurnPipelineResult.simulated` value is `limited`.

Still not implemented:

- advisor payload exposure
- prompt exposure
- automatic advisor-client generation
- full Turn Engine simulation
- item trigger evaluation
- item consumption
- HP update or post-turn state mutation
- speed/order simulation
- exact RNG, status, or volatile resolution

## Payload Location Candidates

| Candidate | Shape | Pros | Cons | Recommendation |
|---|---|---|---|---|
| A | top-level `turn_pipeline` | Mirrors the existing top-level `turn_snapshot`; clearly marks pipeline output as derived context; easy to omit when absent; keeps existing `battle_input` shape unchanged. | More visible to Gemini, so it needs explicit limitations and default-off behavior. | Recommended eventual payload shape. |
| B | `battle_input.turn_pipeline` | Groups pipeline output near source UI-selected state. | Blurs raw input with derived planning output; current advice payload does not expose raw `battle_input` as the main contract surface; higher migration risk. | Not recommended. |
| C | `debug_context.turn_pipeline` | Strongly communicates debug-only intent; lower risk of user-facing overstatement. | Less consistent with top-level `turn_snapshot`; unclear whether prompt rules should read debug context; may be ignored or stripped by future payload filtering. | Useful for internal tooling, not the primary payload shape. |
| D | no exposure; dry-run only | Safest; preserves current runtime behavior completely. | Delays validating whether the LLM can use pipeline summaries safely; keeps event/context migration blocked. | Acceptable fallback, but less useful than optional explicit exposure. |

## Recommended Payload Shape

Use optional top-level `turn_pipeline` when payload exposure is explicitly requested.

Example future shape:

```json
{
  "scenario": {},
  "turn_snapshot": {},
  "turn_pipeline": {
    "input_snapshot": null,
    "selected_move_id": "thunderbolt",
    "damage_estimate_ref": "moves.my_selected_move.damage_estimate",
    "ko_context_ref": "moves.my_selected_move.ko_context",
    "events": [],
    "warnings": [],
    "limitations": [
      "This result is a limited planning summary, not a full turn simulation."
    ],
    "simulated": "limited"
  },
  "pokemon": {},
  "moves": {}
}
```

The field should be omitted when no caller explicitly supplies a pipeline result.

## Exposure Policy Options

| Policy | Pros | Cons | Recommendation |
|---|---|---|---|
| Always include | Maximum visibility; no caller choice needed. | Too risky; implies runtime support and may duplicate item context wording. | Reject. |
| Include only when generated and non-empty | Avoids empty sections. | If generation is automatic, the LLM may still over-trust it; does not solve exposure timing. | Not enough by itself. |
| Include only under explicit argument or debug flag | Preserves current default behavior; enables fixture tests and controlled local experiments. | Requires a caller to opt in. | Recommended for v5.8. |
| Include with strong prompt limitations | Necessary if exposed. | Guard text alone is not enough if the field is always present. | Required companion policy. |
| Do not include until v6.0 | Safest. | Prevents early payload-contract validation and slows migration. | Keep as fallback if v5.8 risk is judged too high. |

Recommended v5.8 policy:

- Default off.
- No automatic generation in `run_ui_selected_advice(...)`.
- Add an optional adapter only.
- Include top-level `turn_pipeline` only when a caller passes an explicit `TurnPipelineResult` or normalized dict.
- Add prompt limitations only when `turn_pipeline` is present.

## Limitations Wording

When `turn_pipeline` is present, the prompt guard should preserve this meaning in English and Korean advice:

```text
Turn pipeline is a limited planning/debug summary.
It is not a full turn simulation.
It does not resolve RNG, item consumption, post-turn HP, speed ties, exact trigger results, or exact status resolution.
Use events only as candidate or known-modifier context.
Do not treat turn_pipeline events as final battle truth.
```

Forbidden implications:

- full turn simulation completed
- item was consumed
- exact post-turn HP
- guaranteed move order
- exact item trigger result
- exact status resolution
- turn_pipeline replaces damage_estimate or ko_context

Allowed phrasing:

- pipeline events suggest candidate timing/context
- known modifier events summarize already-modeled deterministic context
- item consumption is not simulated
- post-turn HP is not finalized
- move order and random activation are not resolved

## Conflict Policy With Existing Contexts

`turn_pipeline` must not replace or override current payload surfaces.

Rules:

- `damage_estimate` remains the primitive for damage ranges, applied item effects, and raw roll-derived estimates.
- `ko_context` remains the primitive for limited KO/OHKO/2HKO-style damage-roll context.
- Existing item contexts remain the user-facing advice surfaces for now.
- `turn_pipeline.events` are an ordering/planning summary of already-visible or helper-level context.
- `turn_pipeline` must not mark blocked, unavailable, or deferred contexts as user-facing.
- `turn_pipeline` must not override item context availability or payload filtering.
- Duplicate wording should be constrained: if both item context and `turn_pipeline` are present, the prompt should use the pipeline as a concise timing summary rather than restating every item paragraph.

Suggested prompt priority:

1. Use `damage_estimate` and `ko_context` for numeric damage and KO statements.
2. Use existing item contexts for current user-facing item explanation.
3. Use `turn_pipeline` only to organize timing/stage and candidate-vs-known-modifier framing.

## v5.8 Implementation MVP

Recommended next step:

```text
v5.8 Optional TurnPipeline Payload Adapter Implementation
```

Scope:

- Add optional `turn_pipeline=None` support to `build_ui_advice_payload(...)` or a small helper beside the existing `turn_snapshot` adapter.
- If absent, preserve byte-for-behavior existing payload output.
- If present, normalize `TurnPipelineResult` or dict input and insert top-level `turn_pipeline`.
- Add prompt limitations only when `turn_pipeline` is present.
- Keep default off.
- Do not auto-generate `TurnPipelineResult` inside `run_ui_selected_advice(...)`.
- Do not connect `build_turn_pipeline_result_from_advice_payload(...)` to runtime advice generation.
- Add fixture-level tests only.

Out of scope for v5.8:

- actual Gemini calls
- automatic advisor-client generation
- LLM prompt behavior validation with live model
- full Turn Engine implementation
- item trigger evaluation
- item consumption
- HP update
- speed/order simulation
- changing damage estimates, `ko_context`, item contexts, or payload filtering

## Safety Statement

This v5.7 work is design-only.

- No production code was changed.
- No `advisor_client.py` connection was added.
- No LLM payload connection was added.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update was implemented.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- No actual Gemini call was executed.
- No Vertex AI call was executed.
