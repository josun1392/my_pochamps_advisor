# v12.78 Current Stat Stages End-To-End Integration

## Result

`COMPLETE - READY FOR OPTIONAL STAT-STAGE ACTUAL SMOKE`

This is offline readiness only and does not authorize a provider call.

## Inventory And Boundary

The repository has separate battle-state/turn-snapshot boost representations
and damage/stat calculation support for boosts. Those paths are not changed or
fed by this feature. The existing default advice flow states that speed stages
are not otherwise modeled. There was no current-stage UI/session/payload
trusted-context path before this change.

Species stats, ability/item/move identities, damage or speed reverse
inference, common sets, animation guesses, and model guesses are not current
stage sources. Future battle-log, parser, replay, stage-change event, resolved
effect, and post-turn information remain unsupported by this contract.

## Integrated Trusted Context

The sole source is `user_confirmed_current_stat_stage` with
`status=user_confirmed` and normalized `confidence=known`. Supported canonical
stats are `attack`, `defense`, `special-attack`, `special-defense`, `speed`,
`accuracy`, and `evasion`. Values are integer stages from `-6` through `+6`,
including explicitly confirmed `0`.

The UI records one entry per `(side, stat)`, supports replacement, independent
self/opponent entries, Cancel preservation, and explicit Clear. Limited
context off retains session state but omits raw confirmation candidates,
payload context, prompt wording, acknowledgement requirements, and CLI
expected entries.

With the gate on, validated entries enter `stat_stage_context.current_stages`.
The prompt treats them as current stages only. It forbids inferring their
cause/timing, move/ability/item source, exact final stats, damage, HP, RNG,
speed tie, or final action order.

## Structured Acknowledgement And Evaluation

Acknowledgement lines use `Current stat stage | <side> | <stat> | <signed stage>`.
The deterministic parser normalizes `+1` and `1` to the same stage but rejects
out-of-range values. Exact-set validation rejects missing, extra, duplicate,
side/stat/value/category changes. The CLI evaluator retains schema and exit
codes and rejects stage-cause, this-turn-change, exact-stat/damage, order, RNG,
and post-turn claims.

## Matrix And Compatibility

Contracts cover attack -1, speed +2, multi-stat, both-side, 0, -6, +6,
invalid-only, gate-off, absent paths, exact-set failures, forbidden advice,
and UI Apply/Cancel/Clear. Condition, ability, and item-event acknowledgement
contracts remain green. Normal UI continues to receive structured advice text;
CLI JSON remains CLI-only.

## Verification

- Full regression: `1934 passed, 2 deselected`.

## Safety

- Actual Gemini/provider/network calls: none.
- No credential or token-log inspection.
- No automatic stage detection, ability/item/move inference, event resolver,
  parser/replay/Turn Engine, or calculation-engine integration.
- No core, dependency, CLI JSON schema, or exit-code changes.
