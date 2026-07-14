# v12.77 Ability Smoke Fixture Integration And Actual Stability

## Fixture Integration

Added the fixed single-attempt CLI fixture
`current-condition-ability-item-event`. It preserves the existing
`current-condition-item-event` fixture and accepts only an explicit fixture
allowlist.

Its raw production input contains:

- current conditions: self `burn`, opponent `unknown`;
- current abilities: self `intimidate`, opponent `unknown`;
- observed item event: opponent `focus-sash` /
  `item_activation_observed`.

Raw entries omit confidence. Production normalization supplies `known` for
condition and ability entries and `observed` for the item event. Expected
structured acknowledgement entries are generated from that normalized payload,
including all five condition, ability, and event identities.

The CLI JSON schema and exit codes are unchanged. Subprocess contracts cover
the new fixture, exact-set pass, missing ability entry, unknown-ability
inference, activation/stat-drop claim rejection, and raw-response
non-disclosure.

## Actual Calls

All calls used `gemini-2.5-flash`, the same fixed fixture, prompt, evaluator,
and generation environment. No code or fixture changed after the first call.

| Attempt | Provider | Response | Semantic | Usage (input/output/cached) | Cost |
| --- | --- | --- | --- | --- | --- |
| 1 | success | available | pass | 5905 / 158 / 0 | USD 0.0 |
| 2 | success | available | pass | 5905 / 104 / 0 | USD 0.0 |
| 3 | success | available | pass | 5905 / 95 / 0 | USD 0.0 |

Each sanitized summary reported an exact trusted-context acknowledgement match
with no detected forbidden condition/item-event outcome claim. The evaluator
also applied the ability exact-set and forbidden-claim boundary. Raw responses,
prompts, provider objects, credentials, and token-log contents were not stored
or output.

## Final Stability Status

`PASS - STABLE`

- semantic PASS: 3
- semantic FAIL: 0
- response unavailable: 0
- evaluator failure: 0
- provider failure: 0
- CLI/precall failure: 0

The three semantic passes confirm the required acknowledgement exact set,
unknown ability boundary, no detected activation/suppression/resolved/exact
claim, condition/item-event coexistence, and a present advice body. This is
evidence for this fixed fixture only; it does not authorize unrelated provider
calls or general ability inference.

## Verification And Safety

- Pre-call ability/CLI/acknowledgement/condition/item-event contracts: passed.
- Post-call targeted tests: passed.
- Full regression: `1893 passed, 2 deselected`.
- No retry, fallback, second provider, Vertex AI, credential validation call,
  response recovery, or additional provider attempt occurred.
- `config/env.example` and `logs/token_usage.jsonl` remained unstaged and were
  not read, staged, committed, reset, or restored.
