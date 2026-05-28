# v0.50 Developer Debug Access Design

## Current State

`opponent_assumptions` debug support exists at the helper level:

- `build_opponent_assumptions_debug_summary(payload)`
- `build_opponent_assumptions_debug_summary_from_assumptions(opponent_assumptions)`
- `format_opponent_assumptions_debug_json(summary)`

The helper output has been verified through tests and local checks. It safely reports:

- mode, `schema_version`, `metadata_version`, and compact `payload_features`
- opponent assumptions availability
- possible sample count and included Top-K count
- sample id, species id, role, archetype id, confidence, and possible items
- `is_user_confirmed: false`
- `used_for_damage: false`
- `used_for_speed: false`
- context-only guardrails

The summary deliberately excludes full stats, SP distribution, full source metadata, full LLM payload content, secrets, environment values, API keys, and token logs.

The remaining gap is access. Developers can call the helper from tests or ad hoc scripts, but the running application does not expose a button, command, hotkey, or debug script for inspecting the current active opponent summary. In normal app use, developers still infer sample behavior indirectly from Gemini responses or test output.

## Problem Definition

Developers need a quick way to inspect the `opponent_assumptions` summary while working on sample, item, and future survival/KO features.

Current problems:

- The active opponent's sample payload is difficult to inspect during app execution.
- The helper exists, but there is no discoverable developer access surface.
- Adding visible debug UI directly to the battle interface could confuse normal users.
- Full payload export is unnecessary and increases secret/log hygiene risk.
- Debug output should remain separate from production-facing advice.
- When Gemini does not mention sample context, developers need to know whether the payload was absent or the model simply omitted it.

## Goals

- Provide developer-only access.
- Show `opponent_assumptions` summary only.
- Avoid full LLM payload export.
- Avoid full stats and SP distribution dumps.
- Never include secrets, environment values, API keys, or token logs.
- Keep normal user-facing UI simple.
- Preserve `context_only`, not-confirmed, and no damage/speed integration semantics.
- Support future debugging for item, survival, KO, and sample expansion work without turning debug state into battle truth.

## Options Comparison

### Option A - CLI/debug script

Example:

```powershell
uv run python scripts/debug_opponent_assumptions.py --species rotom-wash
```

The script would build an opponent-active payload for a species id, call the existing `opponent_assumptions` builder, and print the debug summary JSON to stdout.

Pros:

- No UI changes.
- Clearly developer-only.
- Easy to document.
- Easy to test.
- Low risk for normal app UX.
- Keeps full payload export out of scope.

Cons:

- Does not inspect the exact live UI state.
- Requires the developer to know or copy the species id.
- Does not include live panel selections unless future arguments are added.

### Option B - Copy debug JSON button in app

Add a developer-facing "Copy Opponent Assumptions Debug JSON" action near the AI advice area or a developer-only section.

Pros:

- Inspects live app state.
- Fast for manual QA.
- Helps distinguish payload absence from model omission.

Cons:

- Requires UI changes.
- Needs careful discoverability and user-facing isolation.
- Could confuse regular users if visible.
- Needs clipboard behavior tests or manual QA.

### Option C - Hidden developer hotkey

Add a hidden action such as `Ctrl+Shift+D` to copy the current `opponent_assumptions` debug summary.

Pros:

- No visible UI clutter.
- Can inspect live app state.
- Useful for T1/T2 manual verification.

Cons:

- Low discoverability.
- Needs explicit docs.
- Requires app-state plumbing and shortcut tests.
- Hidden behavior can surprise maintainers if not documented.

### Option D - Debug log only

Write a summary line or JSON file when an LLM request is generated.

Pros:

- No UI surface.
- Captures real generated payload timing.
- Useful for repeated QA sessions.

Cons:

- Requires log hygiene.
- Can generate many files.
- `logs/` must remain uncommitted.
- File writing is more risky than stdout/copy-only behavior.

### Option E - Developer-only collapsible panel

Add an internal debug panel that shows the summary in the app.

Pros:

- Easiest to inspect during live app use.
- Can evolve into broader debug tooling.

Cons:

- Most UI complexity.
- Highest risk of mixing debug data with battle advice.
- Too much for the current maturity of the feature.

## Recommended Direction

The safest next step is **Option A: CLI/debug script**.

Recommended v0.51 path:

- Add a small developer CLI script.
- Input: `species_id`.
- Output: opponent assumptions debug summary JSON to stdout.
- Use existing repository and payload builder paths.
- Do not export full LLM payload.
- Do not write files by default.
- Do not add UI.
- Add tests around available and unavailable species output.

This gives developers a reliable and low-risk access path before touching live app UX. It also makes the debug summary contract more concrete before any future copy button or hidden hotkey.

After the CLI is stable, a later live app access design can compare:

- hidden hotkey
- developer-only copy button
- debug panel

## Proposed v0.51 Candidate

### Candidate 1 - v0.51 Opponent Assumptions Debug CLI Script Implementation

Scope:

- `scripts/debug_opponent_assumptions.py`
- Accept `--species <species_id>`.
- Optionally accept `--top-k`, defaulting to the existing payload default.
- Build an opponent active object from the provided species id.
- Call `build_opponent_assumptions_payload`.
- Call `build_opponent_assumptions_debug_summary`.
- Print `format_opponent_assumptions_debug_json(summary)` to stdout.
- Exit nonzero only for script/runtime failures, not for unavailable species.
- No file writes by default.
- No UI.
- No full payload.
- No secrets.
- Tests for output shape and safety.

This is the recommended first implementation.

### Candidate 2 - v0.51 Opponent Assumptions Live Debug Copy Design

Scope:

- Design how live app state would be copied.
- Compare visible button vs hidden hotkey.
- Define clipboard behavior and discoverability.
- Defer implementation to v0.52+.

This is useful, but should follow the CLI unless live-state inspection becomes urgent.

## Debug Access Scope

The debug access surface should expose only:

- current or requested opponent species id
- `opponent_assumptions_available`
- unavailable reason when present
- `mode`, `schema_version`, `metadata_version`
- compact `payload_features`
- `calculation_usage`
- possible sample count
- included Top-K count
- sample id and species id
- role and archetype id
- confidence
- possible items
- `is_user_confirmed`
- `used_for_damage`
- `used_for_speed`
- guardrails

It must not expose:

- full LLM payload
- Gemini prompt
- damage estimate internals
- full stats
- SP distribution
- full source metadata
- API key
- `.env`
- token logs
- arbitrary environment variables

## Git Hygiene

- Debug output files must not be committed.
- v0.51 CLI should prefer stdout over file writes.
- If file export is added later, use a git-ignored path such as `logs/debug_payloads/`.
- Any future file-writing implementation must verify or document ignore coverage before use.
- Generated debug JSON must not be staged.
- `logs/token_usage.jsonl` remains unrelated and must not be committed.

## Tests Plan

Future implementation tests should cover:

- available species CLI output.
- unknown species CLI output.
- no secrets in output.
- no full stats in output.
- no SP distribution in output.
- no full LLM payload in output.
- `schema_version` and `metadata_version` display.
- role, archetype id, and possible items display.
- `used_for_damage: false`.
- `used_for_speed: false`.
- context-only and not-confirmed guardrails.
- existing `opponent_assumptions` tests remain unchanged.

If a live app copy action is implemented later, tests should additionally cover:

- current active opponent selection.
- missing opponent selection.
- clipboard/copy target behavior where feasible.
- no user-facing advice injection.

## Return to Main Roadmap

v0.50 closes the design loop for opponent sample debug access. The opponent sample/debug work has now covered:

- context-only payload
- repo-native minimal samples
- visibility guardrails
- debug summary
- metadata enrichment
- versioning
- developer access design

After a minimal debug access implementation, the project should return to the main battle-advice roadmap.

Likely mainline candidates:

- item effect expansion
- survival/recovery item design
- KO/OHKO/2HKO design
- Focus Sash behavior
- Leftovers and Sitrus Berry survival context
- Bright Powder / accuracy-adjacent design

Opponent assumptions should remain supporting context until a separate calculation-mode design explicitly integrates them.

## Out of Scope

- Code implementation.
- UI implementation.
- Hotkey implementation.
- CLI script implementation.
- Fixture changes.
- Sample additions.
- Damage/speed integration.
- User-confirmed treatment changes.
- Full payload export.
- Full stats exposure.
- Calculation mode implementation.
- Bayesian update implementation.
- Turn Engine implementation.
- Logs, `.env`, secrets, API keys, or handoff capsule commits.
