# Next Session Prompt v1.9 - Gemini Verification Follow-Up

This document is a copy-paste-ready prompt for the next T3 session. It preserves the v2.5 Developer API Prepay recovery verification results, the v2.6 Light Ball / Chilan Berry wording polish, the v2.6.1 post-polish actual verification result, and the v2.7 available item context required-mention guard.

Update after v2.5:

- Developer API smoke recovered: `AVAILABLE`.
- Provider used: `gemini_developer_api`.
- Endpoint family used: `generativelanguage.googleapis.com`.
- Vertex AI was not used.
- Focus Band actual Gemini verification: PASS.
- Quick Claw actual Gemini verification: PASS.
- Light Ball actual Gemini verification: FAIL after v2.6.1.
- Chilan Berry actual Gemini verification: PARTIAL.
- v2.6 applied a narrow wording polish for Light Ball and Chilan Berry.
- v2.6.1 ran actual Gemini rechecks for Light Ball and Chilan Berry only.
- v2.7 added a required-mention guard for visible `available=true` item contexts.
- v2.7 did not run actual Gemini calls.

Payload preflight PASS still does not imply actual Gemini PASS. Light Ball and Chilan Berry should remain follow-up items until a post-v2.7 actual Gemini recheck is approved and run.

## Copy-Paste Prompt

```text
T3, continue from v2.7 Available Item Context Required Mention Guard.

Goal:
- Do not add new item contexts.
- Do not run extra Gemini calls unless T1/T2 explicitly approve them.
- Review v2.5 actual Gemini results:
  - Focus Band: PASS
  - Quick Claw: PASS
  - Light Ball: PARTIAL before v2.6
  - Chilan Berry: PARTIAL
- v2.6 has already applied a narrow wording polish for Light Ball and Chilan Berry.
- v2.6.1 has already run a post-polish actual Gemini recheck:
  - Light Ball: FAIL
  - Chilan Berry: PARTIAL
- v2.7 has already added a prompt guard requiring visible available item contexts to be mentioned at least once when directly relevant.
- v2.7 actual Gemini recheck has not been run.
- Do not treat Light Ball or Chilan Berry as full PASS.
- If T1/T2 approve, run a post-v2.7 actual Gemini recheck for Light Ball and Chilan Berry only.

Repo / branch / remote checks first:
1. Run `git status --short --branch`.
2. Confirm the branch is `master`.
3. Confirm tracking is `my_pochamps/master`.
4. Confirm there are no unexpected ahead commits unless T1/T2 explicitly approved them.
5. `logs/token_usage.jsonl` may be locally modified. Do not commit it and do not reset it.
6. Do not commit `.env`, secrets, API keys, billing information, token-log contents, or `docs/handoff_capsule_v1.1.md`.
7. Do not print API keys, secrets, billing details, or token-log contents.

Current actual Gemini verification status:

1. Focus Band within `survival_context`
   - Implementation: complete.
   - Payload preflight: PASS.
   - Actual Gemini status after v2.5: PASS.
   - Actual advice used limited wording: Focus Band may occasionally survive.
   - Forbidden wording observed: none.
   - Context fields:
     - `survival_context.available=true`
     - `survival_effect.type=focus_band`
     - raw damage/rolls unchanged
     - `ko_context` unchanged

2. Quick Claw `speed_order_context`
   - Implementation: complete.
   - Payload preflight: PASS.
   - Actual Gemini status after v2.5: PASS.
   - Actual advice used limited wording: Quick Claw may affect move order.
   - Forbidden wording observed: none.
   - Context fields:
     - `speed_order_context.available=true`
     - `speed_order_effect.type=quick_claw`
     - raw damage/rolls unchanged
     - `ko_context` unchanged

3. Light Ball `species_stat_item_context`
   - Implementation: complete.
   - Payload preflight: PASS.
   - Actual Gemini status after v2.6.1: FAIL.
   - Actual advice mentioned Pikachu and user-confirmed Light Ball.
   - Forbidden wording observed: none.
   - v2.5 weakness:
     - Gemini said current damage estimates do not include the stat boost from Pikachu's user-confirmed Light Ball.
     - Preferred wording is limited explanatory context: Light Ball may boost Pikachu's offensive stats in the underlying calculation, is species-specific to Pikachu, and is not a final KO guarantee.
   - v2.6 polish:
     - Prompt/contract now tells Gemini to describe available Light Ball as a Pikachu-specific offensive item context.
     - Prompt/contract now says not to say Light Ball is not included or not modeled when the available context is present.
   - v2.6.1 result:
     - Payload preflight stayed PASS.
     - Gemini still said damage estimates do not include the effect of the user-confirmed Light Ball.
     - Classification: wording guardrail failure / Gemini over-inference from generic default-assumption limitations.
   - v2.7 guard:
     - Prompt now lists visible available item contexts and requires mentioning each directly relevant context at least once.
     - Prompt forbids describing available item effects as unavailable, unmodeled, not included, not reflected, no item is considered, assuming no item, without item effects, or default no-item assumption.
   - Do not treat as full PASS.

4. Chilan Berry `chilan_berry_context`
   - Implementation: complete.
   - Payload preflight: PASS.
   - Actual Gemini status after v2.6.1: PARTIAL.
   - Actual advice mentioned Chilan Berry's potential reduction for Tackle.
   - Forbidden wording observed: none.
   - v2.5 weakness:
     - Gemini did not explicitly say Normal-type.
     - Gemini used weak "not included in the raw damage estimate" wording rather than preferred limited-context phrasing.
   - Preferred wording: Chilan Berry may reduce damage from a Normal-type move; this is limited context and not integrated into final KO odds.
   - v2.6 polish:
     - Prompt/contract now tells Gemini to describe available Chilan Berry as a Normal-type limited context.
     - Prompt/contract now says raw damage rolls and ko_context remain based on the current calculator, and not to say Chilan Berry is not included or not modeled when the available context is present.
   - v2.6.1 result:
     - Payload preflight stayed PASS.
     - Gemini did not use exact forbidden Chilan wording.
     - Gemini still omitted the positive Normal-type limited context and used generic no-item default-assumption wording.
     - Classification: wording guardrail weakness / context omission.
   - v2.7 guard:
     - Prompt now lists visible available item contexts and requires mentioning each directly relevant context at least once.
     - Prompt labels Chilan Berry / chilan_berry_context as Normal-type limited context.
   - Do not treat as full PASS.

Global prohibitions:
- No Gemini actual PASS from payload preflight alone.
- No new item implementation.
- No new mechanics.
- No payload filtering behavior change unless explicitly approved.
- No prompt hardening behavior change unless explicitly approved.
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

Suggested tests after any documentation or approved wording work:
- `uv run pytest tests/test_advisor_payload_contract.py -q`
- `uv run pytest tests/test_advisor_damage_estimate.py -q`
- `uv run pytest tests/test_damage_perf.py -q`
- `uv run pytest -q`
- If perf is timing-sensitive, rerun isolated/perf-file tests and report medians/thresholds. Do not change thresholds, skip, or xfail.

Documentation expectations:
- Record follow-up decisions in `docs/PROGRESS.md`.
- If status changes, update `docs/handoff_pending_gemini_verification_v1.8.md`.
- Keep `docs/handoff_capsule_v1.1.md` untouched.
```

## Maintainer Notes

- The old HTTP 429 blocker is no longer the current Developer API state after v2.5.
- Focus Band and Quick Claw reached actual Gemini PASS.
- Light Ball is FAIL after v2.6.1 due available-context wording failure, not API availability.
- Chilan Berry remains PARTIAL after v2.6.1 due wording quality/context omission, not API availability.
- v2.7 added available item context required-mention guard only; no actual Gemini recheck was run.
- Use "Pokemon" rather than non-ASCII variants in new handoff text unless a file already requires non-ASCII.
