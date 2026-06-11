# Pending Gemini Verification Handoff v1.8

## Purpose

This handoff lets the next T3 session resume item-context actual Gemini verification after the local Gemini API returns from HTTP 429 `RESOURCE_EXHAUSTED`.

The items below are not actual natural-language PASS yet. They have payload preflight PASS, but the Gemini advice calls were blocked.

## Current Status

| Item / context | Implementation status | Payload preflight | Actual Gemini status | BLOCKED reason | Why not PASS | Retry forbidden wording | Retry payload fields |
|---|---|---|---|---|---|---|---|
| Focus Band / `survival_context` | implemented as limited Focus Band branch inside `survival_context` | PASS | BLOCKED_HTTP_429 | first v1.7 actual call returned HTTP 429 `RESOURCE_EXHAUSTED` | no natural-language advice was produced | `will survive`, `guaranteed survive`, `cannot be KO'd`, `confirmed live` | `survival_context.available=true`, `survival_effect.type=focus_band`, `survival_effect.survival_is_not_guaranteed=true`, activation/final survival probability flags false, raw damage/rolls and `ko_context` unchanged |
| Quick Claw / `speed_order_context` | implemented as limited Quick Claw move-order context | PASS | BLOCKED_BATCH | not called after Focus Band hit HTTP 429 | not retried after first blocked call, so no natural-language advice exists | `will move first`, `guaranteed outspeeds`, `confirmed first`, `always acts before`, `wins the speed interaction` | `speed_order_context.available=true`, `speed_order_effect.type=quick_claw`, activation/final move order/speed tie/priority/Turn Engine flags false, raw damage/rolls and `ko_context` unchanged |
| Light Ball / `species_stat_item_context` | implemented as limited Pikachu-only species-stat item context | PASS | BLOCKED_BATCH | not called after Focus Band hit HTTP 429 | not retried after first blocked call, so no natural-language advice exists | `all Electric-type Pokemon benefit`, `all Electric-type Pokémon benefit`, `Light Ball works on any holder`, `guaranteed KO`, `confirmed OHKO`, `always doubles damage`, `final stats are fully known` | `species_stat_item_context.available=true`, holder species `pikachu`, item `light-ball`, boosted stats `atk` / `spa`, no new damage formula path, raw damage/rolls and `ko_context` unchanged |
| Chilan Berry / `chilan_berry_context` | implemented as separate limited Normal-type Chilan context | PASS | BLOCKED_BATCH | not called after Focus Band hit HTTP 429 | not retried after first blocked call, so no natural-language advice exists | `Chilan Berry applies to all move types`, `guaranteed survival`, `confirmed live`, `will survive because of Chilan Berry`, `final damage is halved`, `raw damage rolls already include Chilan Berry` | `chilan_berry_context.available=true`, incoming move type `normal`, `always_resist=true`, no Chilan-adjusted damage/KO integration, raw damage/rolls and `ko_context` unchanged |

## Retry Preconditions

- Gemini quota/access has recovered.
- The first actual Gemini call does not return HTTP 429.
- API keys, secrets, billing details, and token-log contents are not printed or recorded.
- `docs/handoff_capsule_v1.1.md` remains untouched.

## Retry Order

Use this order:

1. Focus Band within `survival_context`
2. Quick Claw `speed_order_context`
3. Light Ball `species_stat_item_context`
4. Chilan Berry `chilan_berry_context`

If the first case returns HTTP 429 `RESOURCE_EXHAUSTED`, stop the batch and record:

- Focus Band: `BLOCKED_HTTP_429`
- remaining cases: `BLOCKED_BATCH`

If no 429 occurs, continue in order and classify each case as `PASS`, `PARTIAL`, `FAIL`, or `BLOCKED`.

## Payload Preflight vs Actual Gemini PASS

Payload preflight PASS means:

- the available context is present in the filtered default advice payload
- unavailable/debug-only context is not leaking into default advice payload
- raw damage, raw rolls, Q12 math, and `ko_context` are unchanged

Actual Gemini PASS additionally requires:

- the Gemini natural-language advice was generated
- it uses limited context wording
- it does not use the forbidden wording for that item/context
- it does not imply final survival, final move order, final KO probability, item consumption, or Turn Engine truth

Do not mark an item as actual Gemini PASS from payload preflight alone.

## Known Payload Preflight Values From v1.7

Focus Band:

- `survival_context.available=true`
- `survival_effect.type=focus_band`
- raw damage `31-37`
- raw rolls `[31, 32, 32, 33, 33, 33, 33, 34, 34, 35, 35, 36, 36, 36, 36, 37]`
- `ko_context.raw_damage_rolls_changed=false`

Quick Claw:

- `speed_order_context.available=true`
- `speed_order_effect.type=quick_claw`
- raw damage `31-37`
- raw rolls `[31, 32, 32, 33, 33, 33, 33, 34, 34, 35, 35, 36, 36, 36, 36, 37]`
- `ko_context.raw_damage_rolls_changed=false`

Light Ball:

- `species_stat_item_context.available=true`
- holder species detail `pikachu`
- raw damage `0-0`
- raw rolls sixteen `0` rolls
- `ko_context.raw_damage_rolls_changed=false`

Chilan Berry:

- `chilan_berry_context.available=true`
- incoming move type `normal`
- raw damage `14-17`
- raw rolls `[14, 14, 14, 14, 15, 15, 15, 15, 15, 15, 16, 16, 16, 16, 16, 17]`
- `ko_context.raw_damage_rolls_changed=false`

## Stabilization Already Completed

- Item context registry/filtering cleanup:
  - `available=true` contexts remain in default advice payload.
  - `available=false` item contexts are removed.
  - debug/enriched payload may retain reason metadata.
- Perf test measurement stabilization:
  - threshold stayed `0.120ms`.
  - no skip/xfail was added.
  - damage formula, raw rolls, Q12, and `ko_context` stayed unchanged.
- Item context coverage audit:
  - all implemented context keys were classified.
  - BLOCKED_HTTP_429 queue was identified.
  - recommendation was to retry pending Gemini verification before adding another item context.

## Recommended v1.9

If Gemini quota/access is restored:

- `v1.9 Item Context Gemini Verification Retry Batch 2`
- Retry the same four cases in the order above.
- Record PASS/PARTIAL/FAIL/BLOCKED separately for each item.

If Gemini quota/access is still blocked:

- keep the pending queue unchanged
- avoid adding a new item context
- prefer documentation-only handoff/coordination or pause item expansion until actual advice can be verified

## v2.0 Retry Result Note

The v2.0 retry batch attempted the pending actual Gemini verification queue again.

Result:

- Focus Band actual Gemini call: BLOCKED_HTTP_429
- Quick Claw actual Gemini call: BLOCKED_BATCH, not called after the first 429
- Light Ball actual Gemini call: BLOCKED_BATCH, not called after the first 429
- Chilan Berry actual Gemini call: BLOCKED_BATCH, not called after the first 429

Payload preflight remained PASS for all four contexts:

- Focus Band: `survival_context.available=true`, `survival_effect.type=focus_band`
- Quick Claw: `speed_order_context.available=true`, `speed_order_effect.type=quick_claw`
- Light Ball: `species_stat_item_context.available=true`, holder species `pikachu`
- Chilan Berry: `chilan_berry_context.available=true`, incoming move type `normal`

No payload leak, wrong context attachment, raw damage change, raw roll change, Q12 change, or `ko_context` change was observed. The pending verification queue is still not actual Gemini PASS and should be retried only after Gemini quota/access is restored.

## Out of Scope

- code implementation
- new item context
- payload filtering changes
- prompt hardening
- damage formula changes
- raw damage roll changes
- Q12 multiplier changes
- `ko_context` changes
- final KO probability
- final move order
- Turn Engine
- item consumption
- legal fixture changes
- fixture changes
- UI changes
- sample additions
- threshold, skip, or xfail changes
- logs, `.env`, secrets, API keys, or `docs/handoff_capsule_v1.1.md` commits
