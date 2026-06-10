# v1.6 Item Context Coverage / Pending Verification Design

## Purpose

Audit the implemented item/advice context surface before adding another item context.

This is a documentation and verification-coverage pass only. It does not add item mechanics, change payload filtering, alter prompts, change tests, or touch damage calculation.

## Current Context Surface

The default Gemini advice payload is produced from the enriched/debug payload through `build_ui_advice_payload()` and `filter_context_for_default_advice()`.

General policy:

- `available=true` item/advice contexts may remain in the default advice payload.
- `available=false`, blocked, deferred, unsupported, unconfirmed, non-triggered, or absent item contexts are removed from the default advice payload.
- debug/enriched payload may retain unavailable reasons for diagnostics and tests.
- `speed_context` is the top-level Speed comparison exception and is not treated as a move-level item context.
- raw `damage_estimate`, raw damage rolls, Q12 modifier math, and `ko_context` remain separate from item advice contexts unless an existing deterministic damage helper already reports an applied item effect.

## Coverage Table

| Context key | Representative item(s) | Champions legal gate | Default advice payload exposure | Unavailable/default filtering | Debug/enriched reason retained | Raw damage / KO effect | Actual Gemini verification |
|---|---|---:|---|---|---|---|---|
| `survival_context` | Focus Sash, Focus Band | yes | available Focus Sash/Focus Band context remains | unavailable survival context removed; item profile hidden unless another available context keeps it | yes | no raw damage or `ko_context` change; survival note only | PARTIAL for Focus Sash; BLOCKED_HTTP_429 for Focus Band |
| `recovery_context` | Sitrus Berry, Leftovers | yes | available recovery context remains | unavailable recovery context removed | yes | no raw damage or `ko_context` change; recovery not integrated into KO | PARTIAL |
| `accuracy_context` | Bright Powder | yes | available accuracy context remains | unavailable accuracy context removed | yes | no raw damage or `ko_context` change; hit chance not integrated | PASS |
| `critical_context` | Scope Lens | yes | available critical context remains | unavailable critical context removed | yes | no raw damage or `ko_context` change; crit chance not integrated | PASS |
| `flinch_context` | King's Rock | yes | available flinch context remains | unavailable flinch context removed | yes | no raw damage or `ko_context` change; flinch chance not integrated | PARTIAL |
| `multi_hit_context` | Loaded Dice | yes, but current item is blocked because absent from legal fixture | available context would remain only if legal-gated and available | blocked/unavailable context removed; item profile hidden | yes | no raw damage or `ko_context` change; hit-count probability not integrated | PASS for blocked quietness; NOT_RUN for legal available context |
| `resist_berry_context` | Yache Berry and 16 other standard type-resist berries | yes | available standard super-effective berry context remains | non-SE/unavailable reason removed; item profile hidden | yes | no raw damage or `ko_context` change; berry-adjusted damage/KO not integrated | PASS |
| `type_boost_context` | Charcoal, Mystic Water, Magnet, supported type-boost items | yes plus damage metadata support | available matching-type context remains | mismatch/non-legal/unsupported context removed; local item effects scrubbed when needed | yes | explanatory sibling for already supported damage item effects; does not add new KO context | PASS |
| `speed_context` | Choice Scarf | yes for item-specific effective Speed modifier | top-level `speed_context` remains when available; Choice Scarf stays here, not in `speed_order_context` | unavailable Speed context follows existing top-level Speed behavior | yes | no damage or `ko_context` effect; not final turn order | PASS |
| `speed_order_context` | Quick Claw | yes | available Quick Claw limited context remains | unavailable/non-Quick-Claw reason removed; item profile hidden unless another available context keeps it | yes | no speed calculation, move-order truth, damage, or `ko_context` effect | BLOCKED_HTTP_429 |
| `species_stat_item_context` | Light Ball on Pikachu | yes plus species-stat metadata | available Pikachu + Light Ball context remains | non-Pikachu/unconfirmed reason removed; item profile hidden | yes | explanatory sibling; `damage_estimate.item_effects` is source of truth; no new KO context | BLOCKED_HTTP_429 |
| `chilan_berry_context` | Chilan Berry | yes plus Normal `always_resist` metadata | available Normal damaging move context remains | non-Normal/unconfirmed reason removed; item profile hidden | yes | no raw damage or `ko_context` change; Chilan-adjusted damage/KO not integrated | BLOCKED_HTTP_429 |

## Actual Gemini PASS / PARTIAL / BLOCKED Summary

### PASS

- `accuracy_context` / Bright Powder:
  - Later verification approved hit-reliability wording, raw damage unchanged, and no final hit probability claims.
- `critical_context` / Scope Lens:
  - Scope Lens was described as crit likelihood, not raw damage or direct boost.
- `resist_berry_context` / Yache Berry:
  - v0.89.1 verified available Yache wording and non-SE unavailable quietness.
- `type_boost_context` / Charcoal, Mystic Water, Magnet:
  - v0.94.1 verified limited context wording and unavailable/non-legal quietness.
- `speed_context` / Choice Scarf:
  - local verification confirmed raw/effective Speed distinction without final turn-order claims.
- blocked item quietness for future-only/non-legal cases:
  - Loaded Dice and Power Herb quietness passed after payload filtering and generic-unavailable wording hardening.

### PARTIAL

- `survival_context` / Focus Sash:
  - safety and visibility passed, but historical actual advice omitted some limitation wording.
- `recovery_context` / Sitrus Berry:
  - safety passed, but historical actual advice did not fully state `ko_context` unchanged / turn sequencing limits.
- `flinch_context` / King's Rock:
  - safety passed, but wording had historical awkwardness and limitation weakness.
- `multi_hit_context` / Loaded Dice:
  - blocked quietness passed, but a legal available Loaded Dice context has not been exercised because `loaded-dice` is not in the Champions legal fixture.

### BLOCKED_HTTP_429

These have payload preflight PASS but actual Gemini natural-language advice is still pending because the local Gemini call returned HTTP 429 `RESOURCE_EXHAUSTED`:

- Focus Band via `survival_context`
- Quick Claw via `speed_order_context`
- Light Ball via `species_stat_item_context`
- Chilan Berry via `chilan_berry_context`

### NOT_RUN

- Legal available `multi_hit_context` for Loaded Dice is not runnable under current policy because Loaded Dice remains absent from `data/static/champions_legal_items.json`.
- Any future Power Herb `charge_context` remains out of scope and unimplemented.

## Pending Verification Queue

Priority 1 - retry after Gemini quota/access is restored:

1. `chilan_berry_context`
   - newest context
   - payload preflight PASS
   - actual advice BLOCKED by HTTP 429
   - risk: Normal-only wording and no final damage/survival overclaim
2. `species_stat_item_context`
   - payload preflight PASS
   - actual advice BLOCKED by HTTP 429
   - risk: Light Ball must stay Pikachu-specific and not become generic item advice
3. `speed_order_context`
   - payload preflight PASS
   - actual advice BLOCKED by HTTP 429
   - risk: Quick Claw must not become guaranteed first-move wording
4. Focus Band within `survival_context`
   - payload preflight PASS
   - actual advice BLOCKED by HTTP 429
   - risk: may occasionally survive must not become guaranteed survival

Priority 2 - re-run older PARTIAL contexts after quota/access is restored:

1. Focus Sash `survival_context`
2. Sitrus / Leftovers `recovery_context`
3. King's Rock `flinch_context`

Priority 3 - optional batch regression:

1. Bright Powder `accuracy_context`
2. Scope Lens `critical_context`
3. Yache Berry `resist_berry_context`
4. Charcoal/Mystic Water/Magnet `type_boost_context`
5. Choice Scarf `speed_context`
6. Loaded Dice / Power Herb blocked quietness

## Should v1.x Add Another Item Context Now?

Recommendation: do not add the next item context immediately.

Rationale:

- The registry/filtering payload preflight is healthy.
- Full pytest is currently passing after v1.5.1.
- However, four recently added or expanded contexts are pending actual natural-language verification due HTTP 429.
- Adding more item contexts would increase the pending Gemini verification backlog and make later regression attribution harder.

It is still safe to do documentation-only cleanup, verification planning, and test-only audits. A new item implementation should wait until the BLOCKED_HTTP_429 queue is retried or T1/T2 explicitly accepts the pending verification risk.

## Recommended v1.7 Path

Recommended:

- `v1.7 Item Context Gemini Verification Retry Batch`

Scope:

- no code implementation
- no new item context
- retry actual Gemini calls for:
  - Chilan Berry Normal available
  - Light Ball Pikachu available
  - Quick Claw available
  - Focus Band lethal available
- include quietness checks for unavailable/default-filtered cases where practical
- record PASS / PARTIAL / FAIL / BLOCKED explicitly
- keep API key, billing, secret, and token-log details out of docs

Fallback if Gemini quota remains blocked:

- `v1.7 Handoff / Pending Verification Capsule`
- summarize the BLOCKED_HTTP_429 queue for T1/T2 and stop item expansion until access is restored.

Not recommended:

- new item implementation before retrying the pending actual advice queue
- Chilan-specific prompt hardening without a demonstrated post-filtering natural-language failure
- threshold/skip/xfail changes for perf tests during a documentation audit

## v1.7 Retry Result Note

The v1.7 retry batch attempted the pending actual Gemini verification queue again.

Result:

- Focus Band actual Gemini call: BLOCKED_HTTP_429
- Quick Claw actual Gemini call: BLOCKED_BATCH, not called after the first 429
- Light Ball actual Gemini call: BLOCKED_BATCH, not called after the first 429
- Chilan Berry actual Gemini call: BLOCKED_BATCH, not called after the first 429

Payload preflight remained PASS for all four contexts, so the pending verification queue is unchanged and should be retried only after Gemini quota/access is restored.

## Out of Scope

- code implementation
- filtering logic changes
- new item context
- prompt hardening
- damage formula changes
- raw damage roll changes
- Q12 multiplier changes
- `ko_context` changes
- final KO probability
- final move order
- Turn Engine
- item consumption
- legal fixture mutation
- fixture changes
- UI changes
- sample additions
- threshold, skip, or xfail changes
- logs, `.env`, secrets, API keys, or handoff capsule commits
