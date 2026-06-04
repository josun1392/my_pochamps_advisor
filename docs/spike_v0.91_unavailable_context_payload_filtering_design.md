# v0.91 Unavailable Context Payload Filtering Design

## 1. Current State

The advisor currently sends a single enriched battle payload to Gemini for default user-facing advice. That payload includes raw `damage_estimate`, additive `ko_context`, and several item-related limited contexts.

Available contexts are useful natural-language inputs:

- `survival_context` for Focus Sash
- `recovery_context` for Sitrus Berry and Leftovers
- `accuracy_context` for Bright Powder
- `critical_context` for Scope Lens
- `flinch_context` for King's Rock
- `multi_hit_context` for Loaded Dice, currently blocked by legal item coverage
- `resist_berry_context` for standard type-resist berries

Unavailable or deferred contexts can also remain attached to move payloads as objects with `available=false` and a stable `reason`. This is useful for tests, contract debugging, and implementation audits, but it also means Gemini can see reason metadata while producing normal advice.

v0.84 through v0.90 strengthened prompt and contract silence rules for blocked, future-only, unavailable, deferred, unconfirmed, non-triggered, and absent item contexts. This worked for several cases:

- Yache Berry on a non-super-effective move stayed quiet in v0.90.1.
- Loaded Dice blocked by legal coverage stayed quiet in v0.90.1.
- Available Yache Berry still appeared as legal limited context.

However, v0.90.1 still failed for the Chilan Berry deferred case:

- payload/debug context: `resist_berry_context.available=false`
- reason: `chilan_berry_deferred`
- raw damage unchanged: 14-17 HP / 7.7%-9.3%
- `ko_context` unchanged
- Gemini nevertheless mentioned Chilan Berry by name and said its effect was not applied

This shows that prompt-only guardrails are not enough when the default advice input still contains detailed unavailable/deferred item context.

## 2. Problem

Unavailable or deferred context reasons are valuable to developers but usually unhelpful in ordinary battle advice. They explain why the engine did not model an item effect, but default advice should focus on available, modeled, user-facing facts.

When Gemini sees an unavailable context object, it may try to be helpful by explaining that reason. For users, this can be confusing:

- It surfaces an item effect that is not part of the recommendation.
- It can imply the item should have affected the estimate.
- It encourages wording such as "item effect is not applied" even when prompt guardrails forbid that.
- It makes blocked or deferred future work look like part of the current battle model.

Prompt wording can reduce the risk, but v0.90.1 demonstrates that a visible reason can still leak into natural language. The safer design is to separate developer/debug metadata from the payload used for default advice.

## 3. Design Options

### Option A - Keep Prompt-only Silence

Keep the current single payload and continue strengthening prompt/contract wording.

Advantages:

- No code implementation needed.
- No payload shape migration.
- All diagnostics remain visible in one object.

Disadvantages:

- v0.90.1 already failed for `chilan_berry_deferred`.
- More negative prompt text makes the system prompt longer and harder to maintain.
- The model can still decide that visible unavailable reason metadata is worth explaining.

Assessment: not recommended as the primary fix.

### Option B - Remove Unavailable/Deferred Item Context From User-facing Payload

Before building the Gemini default advice prompt, strip item contexts where `available=false` and the reason is unavailable, deferred, blocked, unconfirmed, non-triggered, or absent.

Advantages:

- Reduces the chance of leakage by removing the tempting reason metadata from the advice input.
- Small implementation surface if performed during advice payload serialization.
- Keeps available legal contexts unchanged.
- Raw damage and `ko_context` can remain visible.

Disadvantages:

- If this is the only payload, developer diagnostics are lost from the advice call path.
- Tests must distinguish advice payload from debug/contract payload.
- Existing tests that assert unavailable context attachment may need a separate debug-path expectation.

Assessment: recommended for v0.92 as the smallest practical fix, as long as debug diagnostics remain available somewhere else.

### Option C - Dual Payload Structure

Create two explicit payload surfaces:

- `advice_payload`: contains user-facing, available context only.
- `debug_payload` or `diagnostics`: contains unavailable/deferred reasons and full context metadata.

Advantages:

- Clean conceptual split between advice and diagnostics.
- Keeps reasons available for developers without exposing them to Gemini default advice.
- Scales beyond item contexts if other debug-only metadata creates leakage.

Disadvantages:

- Larger implementation scope.
- Requires caller/API decisions: what is sent to Gemini, what is logged, what is displayed, and what tests assert.
- Risk of accidentally sending both payloads in the prompt if the interface is unclear.

Assessment: good longer-term direction, but likely more than v0.92 needs.

### Option D - Add `visibility` / `audience` Metadata To Context Fields

Keep context objects attached but mark each with a visibility field:

```json
{
  "available": false,
  "reason": "chilan_berry_deferred",
  "visibility": "debug_only"
}
```

or:

```json
{
  "available": false,
  "reason": "chilan_berry_deferred",
  "audience": "developer_debug"
}
```

Advantages:

- Preserves the existing shape and context location.
- Allows a generic filter to remove `debug_only` contexts before advice prompt serialization.
- Makes the intended audience explicit.

Disadvantages:

- Requires updates across all context helpers or a wrapper that annotates contexts after construction.
- If `debug_only` context is still sent to Gemini, the model may ignore visibility and leak it anyway.
- Adds one more contract concept to maintain.

Assessment: useful if paired with actual advice-payload filtering. Not sufficient by itself.

## 4. Filtering Policy

Recommended policy for v0.92:

- `available=true` limited contexts may remain in the default advice payload.
- `available=false` item contexts should be excluded from the default advice payload by default.
- The debug/diagnostic surface may retain the full unavailable context with `reason`.
- Raw `damage_estimate` should remain.
- Raw `ko_context` should remain.
- Available legal item contexts should remain.
- Candidate moves should continue to exclude damage/context payloads as they do today.
- If the user explicitly asks about an item or reason, use a separate explanation path or debug-aware route. Do not leak unavailable reasons in ordinary recommendations.

Recommended default-advice filtering target:

- `survival_context`
- `recovery_context`
- `accuracy_context`
- `critical_context`
- `flinch_context`
- `multi_hit_context`
- `resist_berry_context`
- future `charge_context`

Filtering should be based on context object semantics rather than item names:

- If the value is a dict and `available` is exactly `false`, remove it from the advice payload.
- If the context is absent, do nothing.
- If the context is available, preserve it unchanged.
- If a future context has a non-boolean availability model, require an explicit contract decision before filtering.

Reason classes that should be debug-only by default include:

- `blocked_by_legal_item_coverage`
- `future_only_until_legal_confirmed`
- `move_not_super_effective`
- `chilan_berry_deferred`
- `item_not_user_confirmed`
- `no_resist_berry`
- `no_loaded_dice`
- `no_focus_sash`
- `no_bright_powder`
- `no_scope_lens`
- `no_kings_rock`
- missing metadata reasons such as `incoming_move_type_missing`, `move_multihit_metadata_missing`, or future `move_charge_metadata_missing`

This policy is deliberately broader than Chilan Berry. The issue is not only a Chilan wording failure; it is that default advice currently sees developer-facing unavailable context.

## 5. Chilan Berry Policy

Chilan Berry remains deferred. `items_damage.json` marks Chilan Berry as `always_resist=true`, which differs from the 17 standard type-resist berries that require a super-effective type match. The current limited `resist_berry_context` intentionally does not implement this special case.

Policy:

- Keep `chilan_berry_deferred` available for debug/contract diagnostics.
- Hide Chilan deferred context from default Gemini advice payload.
- Do not mention Chilan Berry in default advice when it is deferred.
- Do not say its effect is not applied, not modeled, not included, unavailable, or absent.
- Do not implement Chilan full support in v0.91 or v0.92 unless explicitly approved as a separate feature.

## 6. Tests Plan

For v0.92 implementation, add or update tests for an advice-payload filtering helper or serialization path:

- unavailable `resist_berry_context` is removed from the default advice payload
- `chilan_berry_deferred` is hidden from the default advice payload
- `move_not_super_effective` is hidden from the default advice payload
- `blocked_by_legal_item_coverage` multi-hit context is hidden from the default advice payload
- available `resist_berry_context` remains in the default advice payload
- available Bright Powder / Scope Lens / King's Rock / Focus Sash contexts remain available when applicable
- raw `damage_estimate` remains
- raw `ko_context` remains
- candidate moves remain excluded
- debug/diagnostic payload still retains unavailable reason, or an equivalent debug helper can still expose it
- prompt no longer needs to fight visible unavailable reason metadata
- existing `resist_berry_context` helper tests remain unchanged or are moved to debug-payload assertions
- full pytest passes

Potential test shape:

```python
def test_advice_payload_filters_unavailable_item_contexts_but_keeps_damage_and_ko():
    enriched = attach_selected_move_damage_estimate(payload_with_chilan)
    advice_payload = build_advice_payload(enriched)

    move = advice_payload["moves"]["my_selected_move"]
    assert "resist_berry_context" not in move
    assert "damage_estimate" in move
    assert "ko_context" in move
```

And a paired diagnostic test:

```python
def test_debug_payload_keeps_unavailable_item_context_reason():
    enriched = attach_selected_move_damage_estimate(payload_with_chilan)

    context = enriched["moves"]["my_selected_move"]["resist_berry_context"]
    assert context["available"] is False
    assert context["reason"] == "chilan_berry_deferred"
```

## 7. Proposed v0.92 Path

Recommended next milestone:

**v0.92 - Unavailable Context Advice Payload Filtering Implementation**

Suggested scope:

- Add a small helper for default advice payload filtering.
- Apply it only at the Gemini advice prompt serialization/assembly boundary.
- Remove item context dicts with `available=false` from the payload sent to Gemini default advice.
- Preserve full enriched payload behavior for tests/debug or expose a debug helper that still shows reasons.
- Keep context helper internals mostly unchanged.
- Update contract docs and tests.
- Run focused tests and full pytest.
- Do not change damage formula, raw rolls, `ko_context`, legal fixture, or item behavior.

Non-recommended alternative:

**v0.92 - Chilan-specific Prompt Hardening**

This is not recommended because:

- The same pattern can recur for other unavailable/deferred item reasons.
- It treats a payload visibility problem as an item-specific wording problem.
- It would likely add more brittle prompt text without removing the reason metadata from the model input.

## 8. Out of Scope

The v0.91 design excludes:

- code implementation
- payload filtering implementation
- Chilan Berry full support
- damage formula changes
- raw damage roll changes
- `ko_context` changes
- item consumption tracking
- Turn Engine
- legal fixture mutation
- UI changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits
