# Closed Gemini Verification Handoff v1.8

## Purpose

This handoff tracks the now-closed item-context actual Gemini verification queue after the Gemini Developer API recovered from the previous HTTP 429 `RESOURCE_EXHAUSTED` blocker.

As of v3.1.1, payload preflight remains PASS for all four contexts. Actual Gemini advice is no longer blocked by HTTP 429, and the pending item-context actual verification queue is closed:

- Focus Band: PASS
- Quick Claw: PASS
- Light Ball: PASS after v3.1.1
- Chilan Berry: PASS

v2.7.1 rechecked Light Ball and Chilan Berry after the required-mention guard. Chilan Berry reached PASS, while Light Ball improved from FAIL to PARTIAL but still retained generic no-item wording. v2.8 added a narrower Light Ball-specific no-item residue guard. v2.8.1 rechecked Light Ball only, but Gemini still used generic `no item` / not-applied wording, so Light Ball remained FAIL. v3.1 integrated eligible Pikachu + Light Ball into the advisor damage estimate, and v3.1.1 actual Gemini verification reached PASS.

## Closure Summary

Final status:

- Focus Band / `survival_context`: PASS.
- Quick Claw / `speed_order_context`: PASS.
- Chilan Berry / `chilan_berry_context`: PASS.
- Light Ball / `species_stat_item_context`: PASS.

No item-context entry from the v1.8 pending queue remains BLOCKED, BLOCKED_BATCH, PARTIAL, FAIL, or pending. Historical weaker results remain below as context for why the current safeguards exist.

Light Ball resolution path:

- v2.5: PARTIAL.
- v2.6.1: FAIL.
- v2.7.1: PARTIAL.
- v2.8.1: FAIL.
- v2.9: identified the payload truth conflict between available Light Ball context and no-item / not-applied damage estimate signals.
- v3.0: designed damage estimate integration.
- v3.1: integrated eligible user-confirmed Pikachu + Light Ball into the advisor damage estimate.
- v3.1.1: actual Gemini verification PASS.

Final Light Ball rule:

- `species_stat_item_context.available=true` now aligns with `damage_estimate.item_effects.attacker_item.status=applied`.
- `species_stat_item_context` is the sibling explanation for the applied damage estimate item effect.
- Eligible Light Ball raw rolls and `ko_context` use the adjusted estimate; non-Light-Ball behavior remains unchanged.

## Current Status

| Item / context | Implementation status | Payload preflight | Actual Gemini status | Latest result | Why not full PASS if applicable | Forbidden wording checklist | Payload fields |
|---|---|---|---|---|---|---|---|
| Focus Band / `survival_context` | implemented as limited Focus Band branch inside `survival_context` | PASS | PASS | v2.5 actual advice used limited survival wording and no forbidden wording | n/a | `will survive`, `guaranteed survive`, `cannot be KO'd`, `confirmed live` | `survival_context.available=true`, `survival_effect.type=focus_band`, `survival_effect.survival_is_not_guaranteed=true`, activation/final survival probability flags false, raw damage/rolls and `ko_context` unchanged |
| Quick Claw / `speed_order_context` | implemented as limited Quick Claw move-order context | PASS | PASS | v2.5 actual advice used limited move-order wording and no forbidden wording | n/a | `will move first`, `guaranteed outspeeds`, `confirmed first`, `always acts before`, `wins the speed interaction` | `speed_order_context.available=true`, `speed_order_effect.type=quick_claw`, activation/final move order/speed tie/priority/Turn Engine flags false, raw damage/rolls and `ko_context` unchanged |
| Light Ball / `species_stat_item_context` | v3.1 integrates user-confirmed Pikachu + Light Ball into advisor damage estimates and keeps `species_stat_item_context` as the applied-item sibling explanation | PASS | PASS | v3.1.1 actual response described Water Pulse as default assumptions plus the supported Light Ball modifier, said Light Ball is Pikachu-specific, and said the modifier is applied for Pikachu in the damage estimate | n/a | `Light Ball is not included`, `Light Ball is not modeled`, `Light Ball is not reflected`, `no item effects`, `no item is considered`, `assuming no item`, `without item effects`, `default no-item assumption`, `item not included`, `item not modeled`, `item not reflected`, `Light Ball works on any holder`, `guaranteed KO`, `confirmed OHKO`, `always doubles damage`, `final stats are fully known`, `exact EV/IV/nature-adjusted stats are known` | `species_stat_item_context.available=true`, holder species `pikachu`, item `light-ball`, boosted stats `atk` / `spa`, `damage_estimate.item_effects.attacker_item.status=applied`, raw damage/rolls and `ko_context` use adjusted estimate rolls |
| Chilan Berry / `chilan_berry_context` | implemented as separate limited Normal-type Chilan context | PASS | PASS | v2.7.1 actual recheck described Chilan Berry as Normal-type limited context and preserved raw rolls / `ko_context` limits | n/a | `Chilan Berry is not included`, `Chilan Berry is not modeled`, `no item is considered`, `assuming no item`, `without item effects`, `default no-item assumption`, `Chilan Berry applies to all move types`, `guaranteed survival`, `confirmed live`, `will survive because of Chilan Berry`, `final damage is halved`, `raw damage rolls already include Chilan Berry`, `KO chance is reduced to` | `chilan_berry_context.available=true`, incoming move type `normal`, `always_resist=true`, no Chilan-adjusted damage/KO integration, raw damage/rolls and `ko_context` unchanged |

## Payload Preflight vs Actual Gemini PASS

Payload preflight PASS means:

- the available context is present in the filtered default advice payload
- unavailable/debug-only context is not leaking into default advice payload
- raw damage, raw rolls, Q12 math, and `ko_context` are unchanged

Actual Gemini PASS additionally requires:

- a successful Gemini natural-language response
- limited context wording
- no forbidden wording for that item/context
- no implication of final survival, final move order, final KO probability, item consumption, or Turn Engine truth

Do not mark an item as actual Gemini PASS from payload preflight alone.

## v2.5 Prepay Recovery Retry Result

The v2.5 retry first ran a minimal Developer API smoke prompt after T1 completed Prepay recovery.

Smoke:

- provider: `gemini_developer_api`
- endpoint family: `generativelanguage.googleapis.com`
- model: `gemini-2.5-flash`
- prompt: `Reply exactly: OK`
- result: AVAILABLE
- response summary: `OK`

Pending item-context actual verification then ran once per item:

- Focus Band actual Gemini call: PASS
- Quick Claw actual Gemini call: PASS
- Light Ball actual Gemini call: PARTIAL
- Chilan Berry actual Gemini call: PARTIAL

No forbidden wording appeared in any of the four actual advice responses. Payload preflight stayed PASS for all four contexts. No payload leak, wrong context attachment, raw damage change, raw roll change, Q12 change, or `ko_context` change was observed.

Actual call budget used in v2.5:

- smoke calls: 1
- item verification calls: 4
- total actual calls: 5
- automatic retries: none
- Vertex AI calls: none

## Follow-Up Recommendation

Recommended next action:

- v2.7.1 verified Chilan Berry as actual Gemini PASS after the required-mention guard.
- v2.8 implemented a narrower Light Ball-specific no-item residue guard.
- v2.8.1 actual Gemini recheck still failed for Light Ball because generic no-item / not-applied wording remained.
- v3.1 integrated eligible Pikachu + Light Ball into the advisor damage estimate so `item_effects`, assumptions, raw rolls, and `ko_context` no longer conflict with the available context.
- v3.1.1 verified Light Ball actual Gemini wording as PASS.
- The original Focus Band / Quick Claw / Light Ball / Chilan Berry pending queue is now closed.
- Prefer `v3.3 Item Context System Stabilization` before adding more item contexts.
- After stabilization, the larger product direction should be `v4.0 Turn Engine / Battle State Design`.
- Rationale: many remaining item candidates depend on item consumption, timing, status, stat-stage, recovery timing, or turn-order modeling; adding more limited contexts first may recreate payload/source-of-truth tension.

## Out of Scope

- code implementation unless T1/T2 approve a follow-up
- new item context
- payload filtering changes
- prompt hardening without approval
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
- logs, `.env`, secrets, API keys, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits
