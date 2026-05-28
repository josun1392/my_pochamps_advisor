# v0.52 Item / Survival Roadmap Return Design

## Current State

The opponent sample/debug line is now stable enough to pause:

- repo-native opponent sample pack exists
- `opponent_assumptions` is context-only
- sample visibility guardrails exist
- developer debug summary exists
- minimal metadata enrichment exists
- payload versioning exists
- CLI debug script exists

The main battle-advice item state is:

- Type boosting item damage modifiers are implemented for legal, catalog-backed type boosting items.
- `damage_estimate.item_effects.attacker_item` is the source of truth for whether an item modifier was applied.
- Choice Scarf effective Speed is implemented only in `speed_context` when the item is user-confirmed.
- Choice Scarf remains not final turn order.
- Focus Sash, Leftovers, Sitrus Berry, Bright Powder, Scope Lens, King's Rock, and similar non-damage items are selectable/recognized where legal, but their effects are not connected.
- KO/OHKO/2HKO judgment is not connected to advisor responses.
- Turn Engine state does not exist.

Lower-level damage/probability helpers already contain useful pieces:

- `advisor.damage.rolls.calc_ko_chance` can reason over damage rolls and HP, but it is not connected to the LLM payload.
- `DamageContext` has current/max HP fields, but the current LLM damage estimate path still treats estimates as default-assumption references.
- Item catalogs include more possible effect families than the advisor currently exposes.

## Problem Definition

The current advice is still damage-range centered. That is useful, but real battle decisions often depend on:

- survival
- recovery
- Focus Sash
- hit chance
- critical-hit chance
- flinch chance
- KO/OHKO/2HKO probability

Implementing all of these at once would be too broad. The main risks are:

- accidentally presenting limited context as final battle truth
- mixing item effects into raw damage rolls
- implying Turn Engine sequencing that does not exist
- treating unconfirmed items as active effects
- overloading the LLM with probability claims before payload contracts are ready

The roadmap should expand in small, explicitly guarded layers.

## Candidate Feature Areas

### A. Focus Sash Survival Support

Focus Sash can let a Pokemon survive a would-be KO at 1 HP when it starts the hit at full HP.

Pros:

- High practical advice value.
- Can be limited to user-confirmed item state.
- Can be described as survival context without changing raw damage rolls.
- Does not require modeling every recovery or probability system first.

Cons:

- Multi-hit moves complicate the effect.
- Hazards, prior chip, weather, residual damage, and exact turn sequencing matter.
- Needs careful wording because "survive at 1 HP" can sound final.

Assessment:

- Best next design target if scoped as limited survival context.

### B. Sitrus Berry / Leftovers Recovery Context

These items affect HP after damage or at end of turn.

Pros:

- Common and strategically important.
- Already legal item options.
- Good later bridge into survival and turn state.

Cons:

- Requires HP threshold logic.
- Requires item consumption state for Sitrus Berry.
- Requires end-of-turn timing for Leftovers.
- Easily becomes Turn Engine work.

Assessment:

- Good after Focus Sash and KO design, not first.

### C. Bright Powder Accuracy Context

Bright Powder changes hit probability rather than deterministic damage.

Pros:

- User-interest item.
- Good entry point for accuracy/evasion probability design.

Cons:

- Requires hit chance modeling.
- Needs interaction with move accuracy, accuracy/evasion stages, No Guard, Keen Eye-like exceptions, and possibly compound probability with damage rolls.

Assessment:

- Should wait for an accuracy/probability design pass.

### D. Scope Lens / Critical-Hit Context

Scope Lens increases critical-hit chance.

Pros:

- Crits are already partially represented in lower-level damage mechanics.
- Can eventually improve risk assessment.

Cons:

- Needs critical-hit stage policy.
- Needs probability wording and possible expected-damage context.
- Can interact with abilities, screens, boosts, and move-specific crit stages.

Assessment:

- Better after KO probability design.

### E. King's Rock Flinch Context

King's Rock can add flinch chance to eligible moves.

Pros:

- High practical impact when applicable.
- Useful for risk warnings.

Cons:

- Requires turn order, target action state, move eligibility, multi-hit behavior, and ability interactions.
- Strongly Turn Engine adjacent.

Assessment:

- Defer until turn-order or probability architecture is stronger.

### F. KO/OHKO/2HKO Probability

Damage rolls can support KO probability and 2HKO estimates.

Pros:

- Directly improves advice quality.
- Builds on existing damage roll output.
- `advisor.damage.rolls.calc_ko_chance` already exists.

Cons:

- Needs exact/current HP clarity.
- Recovery, Focus Sash, residual chip, and multi-turn assumptions quickly complicate semantics.
- If implemented before survival context, Focus Sash cases can produce misleading KO claims.

Assessment:

- Important, but Focus Sash limited survival design should come first so KO wording knows how to avoid survival-item overclaims.

## Recommended Direction

T3 recommendation:

- v0.53 should be **Focus Sash Survival Design**.
- v0.54 should be **Focus Sash Limited Survival Implementation** if v0.53 is approved.
- KO/OHKO/2HKO probability should follow after survival-item guardrails are designed.

Reasoning:

- Focus Sash can be limited to a user-confirmed item.
- It improves advice without requiring full Turn Engine state.
- It can remain separate from raw damage rolls.
- It forces the right language for "limited survival context" before broader KO probability is added.
- It addresses a known legal-but-not-modeled item with high gameplay relevance.

Alternative paths:

- KO/OHKO/2HKO first:
  - stronger immediate damage advice
  - but more likely to overclaim in Focus Sash/recovery cases
- Bright Powder first:
  - addresses accuracy interest
  - but requires a new probability layer before the survival story is settled

Focus Sash is the smallest useful bridge from item selection to survival context.

## Focus Sash Limited Scope Proposal

v0.53 design should propose this narrow scope.

Include:

- Defender item is user-confirmed `focus-sash`.
- Defender HP is full or can be treated as full by current UI state.
- A selected or known move damage estimate exists.
- Damage rolls indicate at least one lethal roll against the current/default HP reference.
- Payload adds limited context such as:
  - "may survive at 1 HP due to Focus Sash under limited assumptions"

Do not change:

- raw damage rolls
- raw damage range
- type effectiveness
- item damage modifier math

Exclude:

- multi-hit moves
- hazards
- residual damage
- weather chip
- prior damage when exact HP is unavailable
- ability interactions
- Mold Breaker-like exceptions
- item consumption tracking
- exact turn sequencing
- final battle truth claims

The first version should prefer conservative wording over exact promises.

## Payload / LLM Direction

Two payload options:

### Option A - Add `survival_context`

Example shape:

```json
{
  "survival_context": {
    "mode": "limited_focus_sash_v0.54_candidate",
    "available": true,
    "scope": "selected_move_only",
    "defender": "opponent_active",
    "item_id": "focus-sash",
    "item_source": "user_confirmed",
    "is_final_survival_truth": false,
    "raw_damage_rolls_changed": false,
    "may_survive_at_1_hp": true,
    "limitations": [
      "Focus Sash context is limited.",
      "Multi-hit, hazards, residual damage, and turn sequencing are not modeled."
    ]
  }
}
```

Pros:

- Keeps survival separate from raw damage.
- Easy for the LLM to distinguish damage range from survival caveat.
- Can later expand to recovery or KO contexts.

Cons:

- Adds a new top-level or nested payload section.
- Needs contract tests.

### Option B - Add nested `damage_estimate.survival_context`

Pros:

- Lives near the relevant move estimate.
- Easier to attach to selected move and opponent known move estimates.

Cons:

- More likely to be confused as modifying damage rolls.
- May need duplication for each move estimate.

Recommendation:

- Design v0.53 around a `survival_context` object but decide during implementation whether it is nested under each relevant `damage_estimate` or exposed as a top-level summary.
- The contract must state that survival context does not alter raw damage rolls.

LLM guardrails:

- Do not say "definitely survives."
- Say "may survive at 1 HP due to Focus Sash under limited assumptions."
- Do not claim Focus Sash works through multi-hit, hazards, residual, or prior damage unless explicitly modeled.
- If Focus Sash is not modeled for a case, say so plainly.
- Do not infer Focus Sash unless item profile is user-confirmed.

## Test Plan

Future Focus Sash design/implementation tests should cover:

- Focus Sash user-confirmed + full HP + lethal damage.
- Focus Sash user-confirmed + not full HP.
- no Focus Sash.
- unconfirmed Focus Sash.
- missing item profile.
- multi-hit move excluded.
- survival context does not alter raw damage rolls.
- survival context does not alter type boosting item modifiers.
- survival context does not create KO/OHKO/2HKO claims.
- LLM guardrail does not claim final battle truth.
- existing type boosting item regression.
- existing Choice Scarf `speed_context` regression.
- existing opponent assumptions regression.

Later KO/OHKO/2HKO tests should explicitly include Focus Sash and recovery guardrails before user-facing claims are enabled.

## Roadmap Proposal

Recommended sequence:

1. `v0.53 - Focus Sash Survival Design`
2. `v0.54 - Focus Sash Limited Survival Implementation`
3. `v0.55 - Focus Sash Local Gemini Verification`
4. `v0.56 - KO/OHKO/2HKO Probability Design`
5. `v0.57 - Sitrus/Leftovers Recovery Design`
6. `v0.58 - Accuracy/Crit/Flinch Item Coverage Design`

Why this order:

- Focus Sash establishes survival wording and item-source guardrails.
- KO probability can then avoid overclaiming in survival-item cases.
- Recovery needs turn/threshold policy, so it follows after survival basics.
- Accuracy/crit/flinch need probability semantics, so they come after KO probability design.

Alternatives:

- `v0.53 - KO/OHKO/2HKO Design`
  - Pro: immediate improvement to damage advice
  - Con: risky before Focus Sash/recovery guardrails
- `v0.53 - Bright Powder Accuracy Design`
  - Pro: useful user-interest item
  - Con: requires probability system before survival context is settled

T3 recommendation:

- Choose Focus Sash first.
- Keep Turn Engine out of scope.
- Keep the first survival context limited, explicit, and user-confirmed only.

## Out of Scope

- Code implementation.
- Item effect implementation.
- Survival calculation implementation.
- KO/OHKO/2HKO implementation.
- Turn Engine implementation.
- UI changes.
- Fixture changes.
- Sample additions.
- Damage/speed integration changes.
- Logs, `.env`, secrets, API keys, or handoff capsule commits.
