# v0.44 Opponent Sample Debug Inspection Design

## 1. Current State

- `opponent_assumptions` is present in the LLM payload.
- `data/static/pokemon_stat_samples.json` contains the repo-native minimal sample pack from v0.42.
- `llm/opponent_assumptions.py` builds context-only possible opponent sample profiles for the active opponent species.
- `ui/main_window.py` attaches `opponent_assumptions` to `_build_llm_battle_input()`.
- v0.43 prompt polish makes Gemini mention possible sample context in one concise line when samples are available.
- v0.43.1 local Gemini verification confirmed that the one-line sample visibility wording appears.
- Samples remain:
  - `context_only`
  - `sample_assumed`
  - `is_user_confirmed: false`
  - not connected to `damage_estimate`
  - not connected to `speed_context`
- Developers still need tests or Gemini output to indirectly confirm which samples entered the payload.

## 2. Problem Definition

- The app does not currently expose whether the active opponent has sample assumptions in the generated payload.
- Species normalization issues, such as form slugs, are hard to inspect visually while using the app.
- Developers cannot quickly see which `top_k` samples were included for the current active opponent.
- During development, it is useful to confirm that sample stats are not connected to damage, Speed, KO, survival, or final turn order calculations.
- If Gemini does not mention samples, developers cannot easily tell whether:
  - no samples were in the payload,
  - samples were present but unavailable,
  - the prompt wording was ignored,
  - or the response did not need to mention them.
- Exposing this directly to general users risks confusion because possible samples are not confirmed opponent sets.

## 3. Debug Inspection Goals

- Keep inspection developer/debug-only.
- Show the current LLM payload's `opponent_assumptions` section or a safe summary of it.
- Make `calculation_usage: context_only` obvious.
- Make `is_user_confirmed: false` obvious.
- Show that samples are not damage or Speed calculation inputs.
- Show enough identifying fields for debugging:
  - `sample_id`
  - `species_id`
  - `role`
  - `archetype_id`
  - `confidence`
  - `possible_items`
  - `limitations`
- Avoid making the user-facing battle advice longer or more technical.
- Avoid writing secrets, `.env` values, or API keys to any export.

## 4. Options Comparison

### Option A - Debug log only

LLM payload generation logs an `opponent_assumptions` summary to a debug log.

Pros:
- No UI change.
- Low implementation complexity.
- Does not affect user-facing advice.

Cons:
- Harder for T1 to inspect during app use.
- Requires log file hygiene.
- `logs/` must stay uncommitted.
- Log output can become stale or noisy.

### Option B - Payload export / copy button

The app can export the current LLM payload or a safe subset to JSON, or copy a formatted debug payload to the clipboard.

Pros:
- Most accurate view of what Gemini receives.
- Lets T1 compare payload and model response directly.
- Can start with `opponent_assumptions` only to keep output small.
- Can avoid a permanent UI panel.

Cons:
- Requires a small UI or developer command surface.
- Full payload export may be lengthy.
- Export path and git hygiene need explicit handling.

### Option C - Developer-only debug panel

The app includes a collapsible developer panel showing `opponent_assumptions` summary.

Pros:
- Fast visual confirmation while using the app.
- Good for repeated manual testing.

Cons:
- Adds UI complexity.
- Risk of leaking debug concepts into normal battle advice.
- Needs a dev-mode gate or hidden toggle.

### Option D - AI analysis panel bottom summary

The advice panel appends a one-line debug summary below the AI response.

Pros:
- Very easy to notice.
- No separate export workflow.

Cons:
- Mixes debug state with user-facing advice.
- Could teach users to over-trust sample assumptions.
- Not recommended until debug UX is clearly separated.

### Option E - CLI/debug script

A developer script prints `opponent_assumptions` or a safe summary for a provided species.

Pros:
- No UI change.
- Good for repository validation and tests.
- Simple to run in development.

Cons:
- Does not inspect the exact live UI payload unless it recreates enough app state.
- Less useful during manual app testing.

## 5. T3 Recommendation

Recommended next step:
- `v0.45 - Opponent Assumptions Debug Export Implementation`.

Preferred shape:
- Start with Option B.
- Export or copy an `opponent_assumptions`-only debug summary.
- Keep full LLM payload export as optional or deferred.
- Do not add a persistent user-facing debug panel yet.

Rationale:
- The active app already builds the full payload in `MainWindow._build_llm_battle_input()`.
- Exporting the relevant section gives T1 the exact runtime state without asking Gemini to reveal it indirectly.
- An `opponent_assumptions`-only export avoids large JSON dumps and minimizes privacy/git-hygiene risk.
- UI panel work can wait until v0.46+ if repeated manual inspection becomes common.

Alternative:
- `v0.45 - Opponent Assumptions Debug Script`.
- This is safer than UI work but less direct for live app inspection.

## 6. Proposed Debug Summary Shape

Candidate summary:

```json
{
  "opponent_species_id": "rotom-wash",
  "opponent_assumptions_available": true,
  "calculation_usage": "context_only",
  "possible_sample_count": 1,
  "included_top_k": 1,
  "possible_samples": [
    {
      "sample_id": "rotom_wash_defensive_pivot_repo_v42",
      "species_id": "rotom-wash",
      "role": "defensive_pivot",
      "archetype_id": "rotom_wash_defensive_pivot_repo_v42",
      "is_user_confirmed": false,
      "confidence": "estimated",
      "possible_items": ["leftovers", "sitrus-berry"],
      "used_for_damage": false,
      "used_for_speed": false
    }
  ],
  "guardrails": {
    "not_confirmed": true,
    "not_damage_input": true,
    "not_speed_input": true,
    "not_final_turn_order": true
  }
}
```

Unavailable summary candidate:

```json
{
  "opponent_species_id": "unknown-species",
  "opponent_assumptions_available": false,
  "reason": "no_samples_for_species",
  "calculation_usage": "context_only",
  "possible_sample_count": 0,
  "possible_samples": [],
  "guardrails": {
    "do_not_invent_samples": true,
    "not_damage_input": true,
    "not_speed_input": true
  }
}
```

Fields deliberately excluded from the short summary:
- full stats by default
- full source metadata by default
- `update_policy` detail
- complete Top-K sample metadata
- any API key, model key, environment variable, or token usage detail

## 7. Payload Export Scope

Two export scopes are worth separating:

### Scope A - `opponent_assumptions` summary only

Recommended for v0.45.

- Small output.
- Directly answers the current debugging need.
- Easier to keep free of secrets.
- Easier to compare to Gemini response.

### Scope B - full LLM payload

Useful later, but more sensitive.

- Shows the exact prompt payload boundary.
- Can be long and may include more user-entered battle state.
- Needs stricter privacy review.

Export storage policy:
- Do not write exports by default unless the developer requests it.
- Prefer clipboard/copy-ready string first.
- If file export is implemented, use a git-ignored debug path such as:
  - `logs/debug_payloads/`
  - `logs/debug_payloads/opponent_assumptions_latest.json`
- Keep export files out of commits.

## 8. Safety / Privacy / Git Hygiene

- Debug export must not include API keys, `.env` values, secrets, or raw authentication data.
- Exported debug files must live under an ignored path, likely `logs/debug_payloads/`.
- `logs/` remains excluded from commits.
- `logs/token_usage.jsonl` remains unrelated to payload export.
- Debug export should be developer-only and not part of normal user-facing advice.
- Any future full-payload export should include a test or review checklist for secret-like field names.
- Do not add scraping, external source fetching, or generated data pipelines as part of debug inspection.

## 9. Tests Plan

Future implementation should test:

- `opponent_assumptions` summary builder for available samples.
- Unavailable summary when no sample exists for the active species.
- Unavailable summary when active opponent is missing.
- `calculation_usage` remains `context_only`.
- Every summary sample has `is_user_confirmed: false`.
- Every summary sample reports `used_for_damage: false`.
- Every summary sample reports `used_for_speed: false`.
- Summary guardrails include:
  - `not_confirmed`
  - `not_damage_input`
  - `not_speed_input`
  - `not_final_turn_order`
- Exported summary does not include secret-like keys.
- Export path is documented as git-ignored if file export is implemented.
- Existing `opponent_assumptions` regression tests still pass.
- Existing advisor payload contract regression tests still pass.

## 10. v0.45 Candidate

Recommended:
- `v0.45 - Opponent Assumptions Debug Export Implementation`.

Include:
- `opponent_assumptions` summary builder.
- Copy-ready JSON string or optional export function.
- Tests for available/unavailable summaries.
- Tests for no damage/speed usage flags.
- Docs and progress update.
- No general UI panel yet unless the implementation can keep it clearly developer-only.
- No damage/speed integration.

Alternative:
- `v0.45 - Opponent Assumptions Debug Script`.

Include:
- CLI/debug script that accepts a species id.
- Prints the same safe summary shape.
- No UI changes.

T3 recommendation:
- Prefer Debug Export Implementation if T1 wants live app-state inspection.
- Prefer Debug Script if T1/T2 want the smallest non-UI implementation first.

## 11. Out of Scope

- Code implementation.
- UI implementation.
- Fixture changes.
- Sample additions.
- Damage/speed integration.
- Treating samples as user-confirmed.
- Calculation mode implementation.
- Bayesian update.
- KO/OHKO/2HKO.
- Turn Engine.
- Item effect changes.
- External scraping or build script.
- logs, `.env`, secrets, API keys, or handoff capsule commits.
