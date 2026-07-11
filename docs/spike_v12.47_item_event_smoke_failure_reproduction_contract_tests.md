# v12.47 Item Event Smoke Failure Reproduction Contract Tests

## Purpose

Lock the v12.45 semantic-boundary failure into offline, reproducible contracts
without changing the production prompt or payload.

## Fixture A: Narrow Item Event Semantics

Fixture A captures the current production prompt with:

- self user-confirmed current `leftovers`
- opponent explicit `focus-sash` activation observation
- normalized `source=explicit_user_event_confirmation`,
  `status=user_confirmed`, and `confidence=observed`

The contract verifies separate structured locations and meanings:

- Leftovers remains a current known item only.
- Focus Sash remains an observed activation event only.
- Sides and item meanings do not merge.
- Resolved, post-turn, exact, RNG, and order fields remain absent.

The test-only readback evaluator defines the future narrow response contract:
known current Leftovers, explicitly confirmed opponent Focus Sash activation
observation, and no exact resolved effect or resulting HP.

## Fixture B: Full Advice Prioritization

Fixture B preserves broad production advice context and confirms that the
current prompt includes both `damage_estimate` context and the observed-only
item-event guard. It characterizes the current gap: production text does not
yet contain an explicit instruction to contrast the observed event with known
items or avoid replacing the explanation with unrelated damage detail.

The desired prioritization instruction is test-only expected delta, not a
production change in v12.47.

## Synthetic Failure Contracts

The test-only evaluator separately rejects:

1. identity mixing between known Leftovers and observed Focus Sash
2. event omission in unrelated battle advice
3. unsupported Focus Sash exact HP resolution
4. damage distraction only when event readback is absent

A damage range with explicit observed-event readback is not a failure by itself.
This keeps existing trusted `damage_estimate` context distinct from unsupported
item-event mechanics.

## Safety Boundary

- No actual Gemini, provider, network, retry, fallback, or credential call.
- No Gemini raw response or token-log content is used.
- No production prompt, payload, mapping, or response evaluator is added.
- No failing, skipped, or xfailed test is committed.

## Next Recommendation

`v12.48 Minimal Item Event Prompt Contrast Design`

Use the reproduction contracts to choose the smallest prompt-only contrast or
readback change before implementation. Any future actual re-smoke remains
separately approval-gated.
