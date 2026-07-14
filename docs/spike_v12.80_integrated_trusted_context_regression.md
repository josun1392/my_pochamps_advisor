# v12.80 Integrated Trusted-Context Regression

## Representative Production Fixture

The offline production-path fixture combines user-confirmed self burn,
opponent condition unknown, self Intimidate, opponent ability unknown, three
current stat stages, rain, terrain none, Trick Room, self Reflect, opponent
Tailwind, and an opponent Focus Sash activation observation. Raw confirmations
are normalized by the existing production path before expected acknowledgement
entries are built.

The exact acknowledgement set covers current condition, current ability,
current stat stage, current weather, current terrain, current global field
effect, current side field effect, and observed item event. Known current items
remain existing `item_profiles`/item-context data; they do not have a separate
structured acknowledgement category and were not added to this fixture.

## Integrated Checks

- Exact-set parsing rejects missing, extra, duplicate, category, side,
  identity, stage-value, and event-type changes.
- Gate-off omits all v12 trusted contexts, their prompt guards, and expected
  acknowledgement entries while retaining normal advice flow.
- Existing semantic evaluator rejects condition timing/inference, ability
  activation and stat-drop claims, stage-cause claims, resolved item effects,
  field duration/source claims, and exact damage/HP/order claims.
- Mocked normal UI advice preserves the complete `[Trusted Context]` and
  `[Advice]` response. The sanitized CLI remains offline-tested only; its
  schema, exit codes, no-retry behavior, and raw-response non-disclosure are
  unchanged.

## Actual Evidence

- v12.71 structured condition/item acknowledgement: 2/2 assessable semantic
  PASS, one response unavailable, `PASS - LIMITED SAMPLE`.
- v12.77 condition/ability/item fixture: 3/3 semantic PASS,
  `PASS - STABLE`.
- Stat-stage and field-state trusted contexts are offline-only. No v12.80
  provider call was made.

## Result

`COMPLETE - V12 PHASE CLOSED`.
