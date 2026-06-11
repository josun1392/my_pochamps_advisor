# Next Session Prompt v1.9 - Gemini Verification Follow-Up

This document is a copy-paste-ready prompt for the next T3 session. It preserves the v2.5 Developer API Prepay recovery verification results and the v2.6 Light Ball / Chilan Berry wording polish status.

Update after v2.5:

- Developer API smoke recovered: `AVAILABLE`.
- Provider used: `gemini_developer_api`.
- Endpoint family used: `generativelanguage.googleapis.com`.
- Vertex AI was not used.
- Focus Band actual Gemini verification: PASS.
- Quick Claw actual Gemini verification: PASS.
- Light Ball actual Gemini verification: PARTIAL.
- Chilan Berry actual Gemini verification: PARTIAL.
- v2.6 applied a narrow wording polish for Light Ball and Chilan Berry.
- v2.6 did not run actual Gemini rechecks.

Payload preflight PASS still does not imply actual Gemini PASS. Light Ball and Chilan Berry should remain follow-up items until T1/T2 approve and run a post-polish actual Gemini recheck.

## Copy-Paste Prompt

```text
T3, continue from v2.6 Light Ball / Chilan Berry Limited Wording Polish.

Goal:
- Do not add new item contexts.
- Do not run extra Gemini calls unless T1/T2 explicitly approve them.
- Review v2.5 actual Gemini results:
  - Focus Band: PASS
  - Quick Claw: PASS
  - Light Ball: PARTIAL
  - Chilan Berry: PARTIAL
- v2.6 has already applied a narrow wording polish for Light Ball and Chilan Berry.
- Do not treat Light Ball or Chilan Berry as full PASS until T1/T2 approves and runs a post-polish actual Gemini recheck.

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
   - Actual Gemini status after v2.5: PARTIAL.
   - Actual advice mentioned Pikachu and user-confirmed Light Ball.
   - Forbidden wording observed: none.
   - v2.5 weakness:
     - Gemini said current damage estimates do not include the stat boost from Pikachu's user-confirmed Light Ball.
     - Preferred wording is limited explanatory context: Light Ball may boost Pikachu's offensive stats in the underlying calculation, is species-specific to Pikachu, and is not a final KO guarantee.
   - v2.6 polish:
     - Prompt/contract now tells Gemini to describe available Light Ball as a Pikachu-specific offensive item context.
     - Prompt/contract now says not to say Light Ball is not included or not modeled when the available context is present.
   - Do not treat as full PASS until T1/T2 approves and runs a post-polish actual Gemini recheck.

4. Chilan Berry `chilan_berry_context`
   - Implementation: complete.
   - Payload preflight: PASS.
   - Actual Gemini status after v2.5: PARTIAL.
   - Actual advice mentioned Chilan Berry's potential reduction for Tackle.
   - Forbidden wording observed: none.
   - v2.5 weakness:
     - Gemini did not explicitly say Normal-type.
     - Gemini used weak "not included in the raw damage estimate" wording rather than preferred limited-context phrasing.
   - Preferred wording: Chilan Berry may reduce damage from a Normal-type move; this is limited context and not integrated into final KO odds.
   - v2.6 polish:
     - Prompt/contract now tells Gemini to describe available Chilan Berry as a Normal-type limited context.
     - Prompt/contract now says raw damage rolls and ko_context remain based on the current calculator, and not to say Chilan Berry is not included or not modeled when the available context is present.
   - Do not treat as full PASS until T1/T2 approves and runs a post-polish actual Gemini recheck.

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
- Light Ball and Chilan Berry remain PARTIAL due wording quality, not API availability.
- v2.6 applied wording polish only; no actual Gemini recheck was run.
- Use "Pokemon" rather than non-ASCII variants in new handoff text unless a file already requires non-ASCII.
