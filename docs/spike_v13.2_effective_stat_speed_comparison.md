# v13.2 Deterministic Effective Stat And Speed Comparison

## Inventory

- `current_stat_stage_context` already normalizes Attack, Defense, Special
  Attack, Special Defense, Speed, Accuracy, and Evasion at -6..+6, but did not
  calculate from them. Accuracy/Evasion remain outside this numeric-final-stat
  adapter.
- Legacy `stat_profiles` remains the Champions final-stat source for
  `advisor_damage_estimate` and legacy `speed_context`; its user-confirmed
  Speed path can include the pre-existing Choice Scarf exception. It is not
  read or overwritten by this v13.2 path.
- Existing `turn_order_context` and `speed_order_context` are limited helpers:
  priority, Quick Claw, speed ties, and final turn order are not resolved.
- Field state can identify Trick Room and Tailwind, and ability/item contexts
  can identify candidates such as Swift Swim, Protosynthesis, Quark Drive, or
  Choice Scarf. None is an activation or applicable speed modifier here.
- Core damage/Q12/raw-roll calculators and `field_profiles` remain untouched.

## Contract

`build_effective_stat_inputs` uses only normalized
`final_stat_context.current_final_stats` and
`stat_stage_context.current_stages`. For Attack, Defense, Special Attack,
Special Defense, and Speed it computes floor-rounded standard stages:

- non-negative stage: `final_stat * (2 + stage) // 2`
- negative stage: `final_stat * 2 // (2 - stage)`

HP has no stage and is omitted from effective results. A final stat without a
stage uses stage zero; a stage without its final stat creates no result.
`speed_comparison` is only `self_faster`, `opponent_faster`, `tie`, or
`unavailable`, with `calculation_scope=stage_only`. It never resolves move
order or a tie winner.

The gated, separate `deterministic_calculation_context` contains calculated
results with `calculation_scope=final_stat_plus_stage_only` and a fixed compact
excluded-modifiers list. It is separate from user-confirmed input context and
from legacy `stat_profiles`/damage/speed outputs.

## Response Boundary

The LLM receives result values rather than calculating them. Its response has
separate exact-set blocks: `[Trusted Context]`, `[Deterministic Results]`, and
`[Advice]`. The result parser/evaluator rejects changed/missing result lines,
scope changes, a result-only response, and claims that stage-only Speed settles
final order, item/ability/field modifiers, a tie winner, damage, or KO.

## Verification

- Targeted calculation and integration contracts plus relevant v12/v13
  regression: 614 passed.
- `uv run pytest -q`: 1999 passed, 2 deselected in 41.52s (offline full suite).
