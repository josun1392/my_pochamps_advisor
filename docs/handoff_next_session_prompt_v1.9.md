# Next Session Prompt v1.9 - Pending Gemini Verification

This document is a copy-paste-ready prompt for the next T3 session. It preserves the pending actual Gemini verification queue that remains blocked by HTTP 429 `RESOURCE_EXHAUSTED`.

## Copy-Paste Prompt

```text
T3, continue from v1.9 Pending Verification Capsule Finalization.

Goal:
- Resume only the pending actual Gemini natural-language verification queue when Gemini quota/access has recovered.
- Do not add new item contexts.
- Do not change payload filtering, prompt guardrails, damage formula, raw damage rolls, Q12 math, ko_context, legal fixtures, tests thresholds, skip, or xfail.
- Do not mark payload preflight PASS as actual Gemini PASS.

Repo / branch / remote checks first:
1. Run `git status --short --branch`.
2. Confirm the branch is `master`.
3. Confirm tracking is `my_pochamps/master`.
4. Confirm there are no unexpected ahead commits unless T1/T2 explicitly approved them.
5. `logs/token_usage.jsonl` may be locally modified. Do not commit it and do not reset it.
6. Do not commit `.env`, secrets, API keys, billing information, token-log contents, or `docs/handoff_capsule_v1.1.md`.
7. Do not print API keys, secrets, billing details, or token-log contents.

Current pending verification queue:
1. Focus Band within `survival_context`
   - Implementation: complete.
   - Payload preflight: PASS.
   - Actual Gemini status: BLOCKED_HTTP_429.
   - Context fields to verify before actual call:
     - `survival_context.available=true`
     - `survival_effect.type=focus_band`
     - raw damage `31-37`
     - raw rolls `[31, 32, 32, 33, 33, 33, 33, 34, 34, 35, 35, 36, 36, 36, 36, 37]`
     - `ko_context.raw_damage_rolls_changed=false`
   - Actual advice should say limited survival only, such as `may occasionally survive` / `survival is not guaranteed`.
   - Forbidden wording:
     - `will survive`
     - `guaranteed survive`
     - `cannot be KO'd`
     - `confirmed live`

2. Quick Claw `speed_order_context`
   - Implementation: complete.
   - Payload preflight: PASS.
   - Actual Gemini status: BLOCKED_BATCH.
   - Context fields to verify before actual call:
     - `speed_order_context.available=true`
     - `speed_order_effect.type=quick_claw`
     - raw damage `31-37`
     - raw rolls `[31, 32, 32, 33, 33, 33, 33, 34, 34, 35, 35, 36, 36, 36, 36, 37]`
     - `ko_context.raw_damage_rolls_changed=false`
   - Actual advice should say limited move-order context only, such as `may affect move order` / `not guaranteed priority`.
   - Forbidden wording:
     - `will move first`
     - `guaranteed outspeeds`
     - `confirmed first`
     - `always acts before`
     - `wins the speed interaction`

3. Light Ball `species_stat_item_context`
   - Implementation: complete.
   - Payload preflight: PASS.
   - Actual Gemini status: BLOCKED_BATCH.
   - Context fields to verify before actual call:
     - `species_stat_item_context.available=true`
     - holder species detail is `pikachu`
     - raw damage `0-0`
     - raw rolls are sixteen `0` rolls
     - `ko_context.raw_damage_rolls_changed=false`
   - Actual advice should limit Light Ball to Pikachu and avoid final stat or KO certainty.
   - Forbidden wording:
     - `all Electric-type Pokemon benefit`
     - `Light Ball works on any holder`
     - `guaranteed KO`
     - `confirmed OHKO`
     - `always doubles damage`
     - `final stats are fully known`

4. Chilan Berry `chilan_berry_context`
   - Implementation: complete.
   - Payload preflight: PASS.
   - Actual Gemini status: BLOCKED_BATCH.
   - Context fields to verify before actual call:
     - `chilan_berry_context.available=true`
     - incoming move type is `normal`
     - raw damage `14-17`
     - raw rolls `[14, 14, 14, 14, 15, 15, 15, 15, 15, 15, 16, 16, 16, 16, 16, 17]`
     - `ko_context.raw_damage_rolls_changed=false`
   - Actual advice should limit Chilan Berry to Normal-type move damage and avoid final survival or adjusted-roll claims.
   - Forbidden wording:
     - `Chilan Berry applies to all move types`
     - `guaranteed survival`
     - `confirmed live`
     - `will survive because of Chilan Berry`
     - `final damage is halved`
     - `raw damage rolls already include Chilan Berry`

Payload preflight PASS is not actual Gemini PASS:
- Payload preflight PASS means the default advice payload has the expected available context, no unavailable/debug-only item reason leak, and raw damage / raw rolls / Q12 / ko_context remain unchanged.
- Actual Gemini PASS requires a successful Gemini natural-language response that uses limited wording and avoids every forbidden phrase for that item.
- If the actual call is blocked by HTTP 429 `RESOURCE_EXHAUSTED`, record BLOCKED, not PASS.

Gemini retry conditions:
- Retry only when Gemini quota/access appears restored.
- If the first actual call returns HTTP 429 `RESOURCE_EXHAUSTED`, stop the batch immediately.
- If the first call is HTTP 429, record Focus Band as `BLOCKED_HTTP_429` and the remaining items as `BLOCKED_BATCH`.
- If no 429 occurs, run in this order: Focus Band -> Quick Claw -> Light Ball -> Chilan Berry.
- Classify each item as `PASS`, `PARTIAL`, `FAIL`, or `BLOCKED`.

Failure classification:
- `payload leak`
- `wording guardrail failure`
- `Gemini over-inference`
- `wrong item/context attachment`
- `API BLOCKED_HTTP_429`

Global prohibitions:
- No Gemini actual PASS from payload preflight alone.
- No new item implementation.
- No new mechanics.
- No payload filtering behavior change.
- No prompt hardening behavior change unless an actual failure is confirmed and T1/T2 approve it.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No ko_context calculation change.
- No final KO probability.
- No final move order.
- No Turn Engine.
- No item consumption.
- No legal fixture mutation.
- No fixture mutation.
- No UI or sample additions.
- No threshold changes.
- No skip or xfail.
- No logs, `.env`, secrets, API keys, billing details, token-log contents, or `docs/handoff_capsule_v1.1.md` commit.

Suggested tests after recording verification results:
- `uv run pytest tests/test_advisor_payload_contract.py -q`
- `uv run pytest tests/test_advisor_damage_estimate.py -q`
- `uv run pytest tests/test_damage_perf.py -q`
- `uv run pytest -q`
- If perf is timing-sensitive, rerun isolated/perf-file tests and report medians/thresholds. Do not change thresholds, skip, or xfail.

Documentation expectations:
- Record results in `docs/PROGRESS.md`.
- If the queue status changes, update `docs/handoff_pending_gemini_verification_v1.8.md` or create a new handoff note as directed by T1/T2.
- Keep `docs/handoff_capsule_v1.1.md` untouched.

Before v2.0 / next milestone, T1/T2 should decide:
- Whether to retry this pending Gemini queue as soon as quota recovers.
- Whether to pause new item context expansion until actual Gemini PASS exists for Focus Band, Quick Claw, Light Ball, and Chilan Berry.
- Whether adding more item contexts is acceptable while these four remain actual Gemini BLOCKED.
- Whether a release/milestone can be marked complete with payload preflight PASS but actual Gemini BLOCKED.
- Whether to refresh handoff docs after actual PASS/PARTIAL/FAIL results.
```

## Maintainer Notes

- This prompt is intentionally conservative: payload preflight PASS does not imply actual Gemini PASS.
- The current pending items are implemented and payload-preflighted, but actual natural-language verification remains blocked by API quota/access.
- Use "Pokemon" rather than non-ASCII variants in new handoff text unless a file already requires non-ASCII.
