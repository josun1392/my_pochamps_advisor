# Pending Gemini Verification Handoff v1.8

## Purpose

This handoff tracks item-context actual Gemini verification after the Gemini Developer API recovered from the previous HTTP 429 `RESOURCE_EXHAUSTED` blocker.

As of v2.8, payload preflight remains PASS for all four contexts. Actual Gemini advice is no longer blocked by HTTP 429:

- Focus Band: PASS
- Quick Claw: PASS
- Light Ball: PARTIAL
- Chilan Berry: PASS

Light Ball should not be treated as full actual Gemini PASS. v2.7.1 rechecked Light Ball and Chilan Berry after the required-mention guard. Chilan Berry reached PASS, while Light Ball improved from FAIL to PARTIAL but still retained generic no-item wording. v2.8 added a narrower Light Ball-specific no-item residue guard, but no actual Gemini recheck has run yet after that change.

## Current Status

| Item / context | Implementation status | Payload preflight | Actual Gemini status | Latest result | Why not full PASS if applicable | Forbidden wording checklist | Payload fields |
|---|---|---|---|---|---|---|---|
| Focus Band / `survival_context` | implemented as limited Focus Band branch inside `survival_context` | PASS | PASS | v2.5 actual advice used limited survival wording and no forbidden wording | n/a | `will survive`, `guaranteed survive`, `cannot be KO'd`, `confirmed live` | `survival_context.available=true`, `survival_effect.type=focus_band`, `survival_effect.survival_is_not_guaranteed=true`, activation/final survival probability flags false, raw damage/rolls and `ko_context` unchanged |
| Quick Claw / `speed_order_context` | implemented as limited Quick Claw move-order context | PASS | PASS | v2.5 actual advice used limited move-order wording and no forbidden wording | n/a | `will move first`, `guaranteed outspeeds`, `confirmed first`, `always acts before`, `wins the speed interaction` | `speed_order_context.available=true`, `speed_order_effect.type=quick_claw`, activation/final move order/speed tie/priority/Turn Engine flags false, raw damage/rolls and `ko_context` unchanged |
| Light Ball / `species_stat_item_context` | implemented as limited Pikachu-only species-stat item context; v2.8 adds Light Ball-specific no-item residue guard | PASS | PARTIAL | v2.8 implementation added a narrower guard, but the latest actual Gemini recheck is still v2.7.1 | v2.7.1 Gemini improved but still included generic "no item effects" wording, so this is not a clean PASS until a post-v2.8 actual recheck passes | `Light Ball is not included`, `Light Ball is not modeled`, `Light Ball is not reflected`, `no item effects`, `no item is considered`, `assuming no item`, `without item effects`, `default no-item assumption`, `item not included`, `item not modeled`, `item not reflected`, `Light Ball works on any holder`, `guaranteed KO`, `confirmed OHKO`, `always doubles damage`, `final stats are fully known`, `exact EV/IV/nature-adjusted stats are known` | `species_stat_item_context.available=true`, holder species `pikachu`, item `light-ball`, boosted stats `atk` / `spa`, no new damage formula path, raw damage/rolls and `ko_context` unchanged |
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
- Light Ball remains PARTIAL until a separate post-v2.8 actual Gemini recheck verifies that generic no-item wording no longer appears.

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
