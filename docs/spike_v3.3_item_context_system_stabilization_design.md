# v3.3 Item Context System Stabilization Design

## Purpose

v3.2 closed the original item-context actual Gemini verification queue:

| Item / context | Actual Gemini status |
|---|---|
| Focus Band / `survival_context` | PASS |
| Quick Claw / `speed_order_context` | PASS |
| Chilan Berry / `chilan_berry_context` | PASS |
| Light Ball / `species_stat_item_context` | PASS |

The next step should not be another item context by default. The current system now has enough item surfaces that source-of-truth, filtering, and prompt guard structure should be stabilized before expansion.

This is design-only. No Gemini call, Vertex AI call, code implementation, payload filtering change, damage formula change, raw damage roll change, Q12 change, or `ko_context` change was made.

## Current Structure

### Registry

`llm/advisor_payload_contract.py` currently defines:

- `ADVICE_ITEM_CONTEXT_KEYS`
- `ADVICE_CONTEXT_KEYS`
- `ADVICE_CONTEXT_SIDE_FIELDS`
- `ADVICE_CONTEXTS_REQUIRING_MOVE_LOCAL_ITEM_EFFECT_SCRUB`
- `DEBUG_ONLY_REASON_PHRASES`
- `ADVISOR_KNOWN_LIMITATIONS`

The registry includes the active move-level item contexts:

- `survival_context`
- `recovery_context`
- `accuracy_context`
- `critical_context`
- `flinch_context`
- `multi_hit_context`
- `type_boost_context`
- `species_stat_item_context`
- `speed_order_context`
- `resist_berry_context`
- `chilan_berry_context`
- `charge_context`

`speed_context` is included in `ADVICE_CONTEXT_KEYS` but intentionally excluded from `ADVICE_ITEM_CONTEXT_KEYS`. It is the top-level Speed comparison exception, especially for Choice Scarf, and should not be folded into move-level `speed_order_context`.

### Default Advice Filtering

`llm/advisor_client.py` owns the default-advice filter:

- collect available item context sides
- hide move-local unavailable type-boost/species-stat item effects
- remove unavailable item contexts
- hide item profiles for item sides that only had unavailable/debug context
- hide scrubbed item effects
- remove debug-only limitations

The policy is consistent:

- `available=true` item contexts stay in default advice payload.
- `available=false`, blocked, deferred, unsupported, unconfirmed, non-triggered, or absent item contexts are removed from default advice payload.
- enriched/debug payload may retain unavailable reasons.
- debug-only reason phrases should not leak into default advice.

The main special case is Choice Scarf:

- Choice Scarf remains modeled through top-level `speed_context`.
- Choice Scarf should not become `speed_order_context`.
- filtering keeps item profiles when an available `speed_context` speed modifier uses the item.

### Required Mention Guard

`llm/advisor_client.py` currently builds the available item context mention guard from the filtered default advice payload:

- `_build_available_item_context_required_mention_guard(...)`
- `_collect_available_item_context_labels(...)`
- `_available_item_context_label(...)`

The guard tells the LLM:

- available item contexts are present
- mention each listed available item context at least once when directly relevant
- do not describe available item effects as unavailable, unmodeled, not included, not reflected, no item considered, assuming no item, without item effects, or default no-item assumption
- keep wording limited and do not convert context into final KO odds, guaranteed survival, guaranteed move order, exact final stats, or final battle truth

Light Ball has extra item-specific guard text because v2.8.1 showed generic no-item residue even after the common guard. Chilan Berry uses label-level wording plus contract limitations and reached PASS in v2.7.1.

## Context Status

| Context key | Purpose | Legal gate | Default exposure | Actual Gemini status | Raw damage / `ko_context` effect | Remaining limitation | Turn Engine needed |
|---|---|---|---|---|---|---|---|
| `survival_context` | Focus Sash / Focus Band limited survival note | yes | available context kept; unavailable reasons hidden | PASS for Focus Band; historical PARTIAL for Focus Sash | no raw roll change; `ko_context` does not include activation | activation probability, item consumption, multi-hit/chip sequencing | yes |
| `recovery_context` | Sitrus / Leftovers limited recovery note | yes | available context kept; unavailable reasons hidden | PARTIAL | no raw roll change; `ko_context` excludes recovery | activation timing, end-of-turn timing, item consumption, switching | yes |
| `accuracy_context` | Bright Powder hit-reliability note | yes | available context kept; unavailable reasons hidden | PASS | no raw roll change; `ko_context` excludes hit chance | final hit probability, accuracy/evasion stages, weather/ability | yes |
| `critical_context` | Scope Lens crit-likelihood note | yes | available context kept; unavailable reasons hidden | PASS | no raw roll change; `ko_context` excludes crit chance | crit stages, crit-adjusted damage/KO probability | partial; battle calc expansion first |
| `flinch_context` | King's Rock flinch-pressure note | yes | available context kept; unavailable reasons hidden | PARTIAL | no raw roll change; `ko_context` excludes flinch | final flinch probability, action denial, speed order | yes |
| `multi_hit_context` | Loaded Dice multi-hit reliability note | legal available context not exercised; blocked quietness covered | available would stay; blocked/unavailable hidden | PASS for blocked quietness; NOT_RUN for legal available Loaded Dice | no raw roll change; `ko_context` excludes hit-count changes | hit-count distribution, per-hit mechanics, Focus Sash interactions | yes |
| `resist_berry_context` | standard 17 super-effective type-resist berries | yes | available SE berry context kept; non-SE hidden | PASS | no berry-adjusted raw roll or `ko_context` integration | consumption, multi-hit, ability/weather/Tera interactions | yes |
| `type_boost_context` | Charcoal / Mystic Water / Magnet style applied damage item explanation | yes plus damage metadata | matching available context kept; mismatch hidden | PASS | sibling explanation for already-applied damage item effects | final battle truth and unsupported catalog gaps | no for current scope |
| `speed_context` | raw/effective Speed comparison and Choice Scarf effective Speed | yes for item modifier | top-level context, not move-level item context | PASS for Choice Scarf | no damage or `ko_context` effect | not final move order, no priority/field state | yes |
| `speed_order_context` | Quick Claw limited move-order note | yes | available Quick Claw context kept; unavailable hidden | PASS | no damage or `ko_context` effect | activation probability, priority, ties, field state, item consumption | yes |
| `species_stat_item_context` | Light Ball sibling explanation for applied Pikachu damage estimate modifier | yes plus species-stat metadata | available Pikachu + Light Ball context kept; non-Pikachu/unconfirmed hidden | PASS | eligible Light Ball raw rolls and `ko_context` use adjusted estimate rolls | exact final stats are not inferred; limited to eligible Pikachu attacker estimates | no for current scope |
| `chilan_berry_context` | Chilan Berry Normal-type limited context | yes plus Normal `always_resist` metadata | available Normal damaging move context kept; non-Normal/unconfirmed hidden | PASS | no Chilan-adjusted raw roll or `ko_context` integration | consumption and final survival/KO odds not modeled | yes |

## Observations

### What Is Stable

- Registry tests already assert the current context surface.
- Unavailable context removal is centralized in `filter_context_for_default_advice(...)`.
- Debug-only reason phrases have explicit tests.
- The available item mention guard is generated from the filtered default advice payload, so hidden contexts do not create required mentions.
- Light Ball is now an applied damage estimate item effect with a sibling context, resolving the previous payload truth conflict.

### Current Friction

- Prompt and contract wording are long and partially duplicated between `ADVISOR_KNOWN_LIMITATIONS`, prompt text in `advisor_client.py`, context helper limitations, tests, and docs.
- The available item label registry lives in `advisor_client.py`, not beside `ADVICE_ITEM_CONTEXT_KEYS`.
- Item-specific guard text is embedded in prompt construction, especially Light Ball.
- Debug-only phrase filtering is centralized, but the list of phrases and item-context-specific unavailable wording are scattered.
- `charge_context` is present in the registry surface, but Power Herb remains blocked/future-only; this is a good example of why registry presence and implemented user-facing behavior should be documented separately.
- `speed_context` is intentionally special, and future changes could accidentally treat Choice Scarf like a move-level `speed_order_context` item if that exception is not made more explicit.

## Cleanup Options for v3.4

### Option A - Move Item Context Guard Metadata Into a Registry Helper

Create a documentation-backed helper module or structure that maps context key to:

- user-facing label
- mention requirement
- forbidden wording category
- whether raw rolls can change
- whether `ko_context` can change
- whether it is move-level or top-level

Pros:

- Reduces item-specific branching in `advisor_client.py`.
- Makes new context additions harder to forget.
- Gives tests one compact source of truth.

Cons:

- Requires careful migration because prompt wording tests are precise.
- Could over-abstract contexts that still have very different mechanics.

Priority: high.

### Option B - Centralize Available Mention Labels

Move `_available_item_context_label(...)` behavior closer to `ADVICE_ITEM_CONTEXT_KEYS` or a new contract registry table.

Pros:

- Lower risk of adding a context key without a useful mention label.
- Keeps labels aligned with docs and tests.

Cons:

- Still leaves longer prompt/limitation prose elsewhere unless combined with Option A.

Priority: high.

### Option C - Centralize Debug-Only Reason Phrase Filtering

Unify context-specific "do not mention unavailable reason" wording into a shared policy section plus a per-context exception table.

Pros:

- Reduces repeated not-modeled / not-included / unavailable wording.
- Helps prevent another Light Ball-style no-item residue conflict.

Cons:

- Needs careful preservation of blocked-item quietness tests.
- May require updating several documentation sections at once.

Priority: medium.

### Option D - Reorganize `docs/advisor_payload_contract.md`

Convert the long context descriptions into a table-first structure:

- context key
- trigger
- default payload behavior
- debug behavior
- raw damage effect
- `ko_context` effect
- actual Gemini status
- Turn Engine dependency

Pros:

- Makes the contract easier to audit before adding items.
- Helps T1/T2 see which contexts are explanatory-only vs applied.

Cons:

- Documentation-only but potentially noisy.
- Must preserve historical detail where it matters for tests and handoff.

Priority: medium.

### Option E - Archive Old Pending Handoff Language

Keep `docs/handoff_pending_gemini_verification_v1.8.md` as historical, but add a clear archive/closed banner and link future sessions to the v3.2 closure instead of retry instructions.

Pros:

- Avoids future T3 sessions treating old BLOCKED/PARTIAL history as current.
- Reduces accidental duplicate Gemini calls.

Cons:

- Mostly documentation hygiene; lower code risk reduction than Options A/B/C.

Priority: low to medium.

## Recommended v3.4 Plan

Implement only structure cleanup, not new item mechanics:

1. Add or document an item-context guard metadata registry.
2. Move available item context labels out of ad hoc prompt construction.
3. Add tests proving every `ADVICE_ITEM_CONTEXT_KEYS` entry has:
   - a mention label
   - default advice filtering behavior
   - explicit raw damage / `ko_context` policy
4. Keep Choice Scarf `speed_context` as a documented top-level exception.
5. Do not add new items in the same commit.

## Why Turn Engine / Battle State Should Come Next

Many remaining legal item candidates need state, timing, or event modeling rather than another isolated context:

- Shell Bell and healing berries need recovery timing, damage-dealt tracking, thresholds, and item consumption.
- White Herb and Mental Herb need stat-stage/status timing and one-time use.
- Mega Stones need form/state subsystem support.
- Quick Claw and Focus Band already have limited notes, but true behavior needs activation timing/probability and turn order.
- Loaded Dice needs multi-hit event modeling and per-hit interactions.
- Resist berries and Chilan Berry need consumption, multi-hit handling, and final survival/KO integration before full mechanics.

Adding more limited contexts without Battle State increases the chance of payload truth conflicts: the model sees a context, but the raw estimate or `ko_context` cannot honestly integrate it. Light Ball was the useful warning sign; it only became PASS once the payload's available context and damage estimate source of truth were aligned.

## Non-Goals

- No actual Gemini verification.
- No Vertex AI call.
- No code implementation.
- No new item context.
- No payload filtering change.
- No prompt hardening behavior change.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No threshold, skip, or xfail change.
- No logs, `.env`, secrets, API keys, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.
