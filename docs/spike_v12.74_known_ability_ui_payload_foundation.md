# v12.74 Known Ability UI and Payload Foundation

## UI and session state

`LLMAdvicePanel` now provides an `Ability` action and `Clear current abilities`
action. `CurrentAbilityDialog` has a self/opponent selector, editable validated
ability input, explicit `unknown` option, and a compact saved-state readback.
It deliberately does not present species ability lists as selected current
abilities.

`MainWindow._current_ability_confirmations` is side-keyed. A valid Apply
replaces only that side, both sides can coexist, and Cancel, close, and invalid
Apply preserve the previous state. Clear is the only added reset path; changing
Pokemon, selecting a move, requesting advice, or disabling limited context does
not clear ability state. There is no separate new-battle reset hook in the
existing UI path, so explicit Clear is the current supported reset action.

## Validation and payload foundation

The dialog, session normalization, MainWindow battle-input construction, and
payload adapter all reuse `normalize_user_confirmed_current_ability(...)`.
Canonical input such as `Quark Drive`, `Mold Breaker`, and `Neutralizing Gas`
becomes lowercase kebab-case. `unknown` remains valid; `none`, multi-ability
candidate lists, wrong sources/statuses, future/species/meta sources, and
recursive activation/suppression/replacement/resolved/exact/RNG/order fields
are rejected.

With limited context disabled, session state and the `Ability (N)` summary stay
visible but `current_ability_confirmations` is absent from battle input. With
it enabled, valid entries become the validated payload foundation:

```text
ability_context.current_abilities
```

Each side has at most one normalized entry and invalid entries are omitted;
all-invalid input omits `ability_context`.

## Prompt isolation

This is intentionally not ability prompt integration. Raw ability confirmations
are always removed before provider serialization. The intermediate
`ability_context` foundation is also removed by `_build_ui_selected_prompt`
until a separate prompt contract is approved. No ability guard, natural-language
readback, `[Trusted Context]` ability line, CLI evaluator rule, or provider
fixture was added. Existing condition/item acknowledgement behavior is unchanged.

## Verification

- current ability UI contract: 5 passed
- current ability payload foundation: 20 passed
- known ability source contract: 50 passed
- UI turn pipeline flag flow: 19 passed
- advisor payload: 500 passed
- trusted acknowledgement: 13 passed
- trusted acknowledgement matrix: 21 passed
- item-event payload mapping: 27 passed
- current-condition payload/prompt: 14 passed
- full suite: 1,862 passed, 2 deselected
- `git diff --check` and `git diff --cached --check`: passed

## Status

**COMPLETE**

No actual provider/network call, retry/fallback/Vertex AI call, ability event
or suppression/replacement implementation, automatic detection, parser/replay/
Turn Engine work, exact calculation, dependency change, or prompt/
acknowledgement expansion occurred.
