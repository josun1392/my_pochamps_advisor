# v12.70 Structured Trusted-Context Acknowledgement Integration

## Implementation

Valid normalized condition and observed-item-event context now adds a compact
response prefix requirement:

```text
[Trusted Context]
- Current condition | <side> | <condition_type>
- Observed item event | <side> | <item> | <event_type>

[Advice]
...
```

The lines are generated dynamically from normalized prompt payload entries.
No fixture values are hardcoded. Condition-only and item-event-only prompts
include only their applicable line types; absent or disabled context adds no
structured acknowledgement instruction.

## Deterministic validation

`llm.advisor_client` now provides a small acknowledgement parser and validator:

- It parses only the `[Trusted Context]` block and checks for `[Advice]` body
  presence.
- It normalizes category case and Focus Sash spacing, while retaining side,
  condition/item identity, and event type.
- Expected entries are generated from the production normalized prompt payload.
- Validation requires ordered exact equality and rejects missing, extra,
  duplicate, malformed, swapped, or changed entries.

The CLI evaluator now builds expected entries from the same normalized
production prompt payload, applies deterministic acknowledgement validation,
then retains forbidden resolved/exact/timing/RNG/order, unknown-inference, and
advice-body checks. Its JSON schema and exit-code contract are unchanged.

## Offline contracts

Parser tests cover canonical and minor valid formatting, `none`, block missing,
missing/extra/duplicate lines, side/category swaps, unknown identity changes,
event-type omission, malformed delimiters, and empty advice. CLI subprocess
tests confirm canonical structured acknowledgement produces semantic pass,
semantic fail remains exit code 0, and raw fake-provider text is not exposed.

## Readiness

**READY FOR STRUCTURED ACKNOWLEDGEMENT ACTUAL SMOKE**

This is offline readiness only. No actual provider call, credential check, raw
response recovery, or token-log reading occurred.
